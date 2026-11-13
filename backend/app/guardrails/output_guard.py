"""
Bộ kiểm duyệt an toàn đầu ra của mô hình ngôn ngữ lớn (L5 Output Guard) — [W07-T4.1, T4.2, T4.3].

Thực thi 9 quy tắc chính sách đầu ra định nghĩa trong `output_policies.yaml`:
1. `OUT-LEAK`: Chặn lộ thẻ XML nội bộ, System Prompt hoặc biến hệ thống (`FAIL`).
2. `OUT-RESCREEN`: Phát hiện câu trả lời khẳng định tình trạng cấp cứu/nguy kịch -> nâng rủi ro (`RISK_UP`).
3. `OUT-FALSE-REASSURE`: Chặn câu trấn an tuyệt đối gây chủ quan y khoa (`FAIL`).
4. `OUT-STOP-MED`: Chặn lời khuyên tự ý ngưng hoặc bỏ thuốc điều trị (`FAIL`).
5. `OUT-DIAG`: Chặn câu kết luận chẩn đoán bệnh lý xác định thay bác sĩ (`FAIL`).
6. `OUT-DOSE-LEAK`: Chặn con số liều lượng (`mg`, `mcg`, `nhát`, `viên`, `ml`) không có trong ngữ cảnh (`FAIL`).
7. `OUT-MED-ALLOW`: Chặn tên thuốc nằm ngoài danh sách cho phép của lượt hội thoại (`FAIL`).
8. `OUT-CITE`: Xác thực và tự động chuẩn hóa dòng `Tài liệu tham khảo:` khớp với chunk truy xuất (`REWRITTEN`).
9. `OUT-DISCLAIMER`: Tự động gắn dòng `Lưu ý y tế:` nếu phản hồi chưa có (`REWRITTEN`).
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from backend.app.orchestration.state import (
    AftercareState,
    append_guard_event,
    escalate_risk,
)

DEFAULT_OUTPUT_POLICY_PATH = (
    Path(__file__).resolve().parent / "policies" / "output_policies.yaml"
)

# Ánh xạ biệt dược <-> hoạt chất tương đương trong phác đồ Hen phế quản
_EQUIVALENT_MED_GROUPS: List[Set[str]] = [
    {"symbicort", "budesonide", "formoterol", "pulmicort"},
    {"ventolin", "salbutamol", "albuterol"},
    {"seretide", "fluticasone", "salmeterol"},
    {"berodual", "ipratropium", "fenoterol"},
    {"singulair", "montelukast"},
    {"spiriva", "tiotropium"},
    {"medrol", "methylprednisolone", "prednisolone", "prednisone"},
    {"bricanyl", "terbutaline"},
]

_RE_NEGATION_PREFIX = re.compile(
    r"(?i)(?:không\s+được|tuyệt\s+đối\s+không|không\s+nên|chưa\s+được|tránh|đừng)\s*$"
)
_RE_CITATION_LINE = re.compile(
    r"(?im)^[ \t]*(?:[-*•]\s*)?(?:tài\s+liệu\s+tham\s+khảo|nguồn\s+tham\s+khảo|trích\s+dẫn)\s*:\s*(.+)$"
)


@dataclass
class OutputGuardResult:
    """Kết quả đánh giá của hàng rào an toàn đầu ra (L5 Output Guard)."""

    decision: str = "PASS"  # "PASS" | "REWRITTEN" | "FAIL" | "RISK_UP"
    response_text: str = ""
    triggered_rules: List[str] = field(default_factory=list)
    detail: str = ""
    escalated_risk_level: Optional[str] = None


def _normalize_number_str(num_str: str) -> str:
    return re.sub(r"\s+", "", num_str.replace(",", ".").lower())


def _extract_dose_tokens(text: str, dose_regex: re.Pattern) -> Set[str]:
    """Trích xuất tập hợp các biểu thức liều lượng đã chuẩn hóa (ví dụ: '160/4.5mcg', '2nhat')."""
    tokens: Set[str] = set()
    for match in dose_regex.finditer(text or ""):
        raw_num = _normalize_number_str(match.group(1))
        raw_unit = match.group(2).strip().lower()
        tokens.add(f"{raw_num} {raw_unit}")

    # Hỗ trợ khoảng liều trong ngữ cảnh gốc như "2-4 nhát" hoặc "1 - 2 viên"
    range_pattern = re.compile(
        r"(?i)\b(\d+)\s*[-–~đến]+\s*(\d+)\s*(mg|mcg|nhát|viên|ống|ml)\b"
    )
    for rmatch in range_pattern.finditer(text or ""):
        try:
            low = int(rmatch.group(1))
            high = int(rmatch.group(2))
            unit = rmatch.group(3).strip().lower()
            if low <= high and (high - low) <= 10:
                for val in range(low, high + 1):
                    tokens.add(f"{val} {unit}")
        except ValueError:
            pass
    return tokens


class OutputPolicyGuard:
    """Bộ máy kiểm duyệt đầu ra tất định dựa trên cấu hình YAML."""

    def __init__(self, policy_path: Optional[Path] = None):
        self.policy_path = policy_path or DEFAULT_OUTPUT_POLICY_PATH
        self.version: str = "1.0.0"
        self.medical_disclaimer: str = (
            "Lưu ý y tế: Thông tin chỉ mang tính hỗ trợ giáo dục sức khỏe, "
            "không thay thế chẩn đoán hoặc chỉ định của bác sĩ điều trị."
        )
        self.controlled_medications: List[str] = []
        self._med_patterns: Dict[str, re.Pattern] = {}
        self.rules_by_id: Dict[str, Dict[str, Any]] = {}
        self._dose_regex: re.Pattern = re.compile(
            r"(?i)\b(\d+(?:[.,]\d+)?(?:\s*/\s*\d+(?:[.,]\d+)?)?)\s*(mg|mcg|nhát|viên|ống|ml)\b"
        )
        self._load_policies()

    def _load_policies(self) -> None:
        raw = yaml.safe_load(self.policy_path.read_text(encoding="utf-8")) or {}
        self.version = str(raw.get("version", "1.0.0"))
        if raw.get("medical_disclaimer"):
            self.medical_disclaimer = str(raw["medical_disclaimer"]).strip()

        meds = raw.get("controlled_medications_catalog") or []
        self.controlled_medications = [str(m).strip().lower() for m in meds if m]
        self._med_patterns = {
            med: re.compile(rf"(?i)\b{re.escape(med)}\b")
            for med in self.controlled_medications
        }

        for item in raw.get("rules", []):
            rid = str(item["rule_id"])
            compiled_patterns = [re.compile(p) for p in item.get("patterns", [])]
            compiled_allow = [re.compile(p) for p in item.get("allow_patterns", [])]
            if item.get("dose_regex"):
                self._dose_regex = re.compile(str(item["dose_regex"]))
            self.rules_by_id[rid] = {
                **item,
                "compiled_patterns": compiled_patterns,
                "compiled_allow": compiled_allow,
            }

    def _build_reference_corpus(self, state: AftercareState) -> str:
        """Gộp toàn bộ nguồn dữ liệu hợp lệ của lượt hội thoại để đối chiếu liều lượng và tên thuốc."""
        parts: List[str] = []
        for chunk in state.get("retrieved_chunks") or []:
            parts.append(str(chunk.get("section_title") or ""))
            parts.append(str(chunk.get("citation") or ""))
            parts.append(str(chunk.get("content") or ""))
        if state.get("profile"):
            parts.append(
                json.dumps(state.get("profile"), ensure_ascii=False, default=str)
            )
        if state.get("clean_message"):
            parts.append(str(state.get("clean_message")))
        if state.get("raw_message"):
            parts.append(str(state.get("raw_message")))
        if state.get("history"):
            parts.append(
                json.dumps(state.get("history"), ensure_ascii=False, default=str)
            )
        return "\n".join(parts)

    def _allowed_medications_for_turn(self, reference_text: str) -> Set[str]:
        """Xác định tập hợp tên thuốc được phép xuất hiện trong câu trả lời của lượt hiện tại."""
        allowed: Set[str] = set()
        for med, pat in self._med_patterns.items():
            if pat.search(reference_text):
                allowed.add(med)
                for group in _EQUIVALENT_MED_GROUPS:
                    if med in group:
                        allowed.update(group)
        return allowed

    def _check_regex_rule(
        self, rule_id: str, text: str, check_negation_prefix: bool = False
    ) -> Optional[str]:
        rule = self.rules_by_id.get(rule_id)
        if not rule:
            return None
        for pat in rule.get("compiled_patterns", []):
            for match in pat.finditer(text):
                if check_negation_prefix:
                    prefix = text[max(0, match.start() - 35) : match.start()]
                    if _RE_NEGATION_PREFIX.search(prefix):
                        continue
                return match.group(0)
        return None

    def _validate_and_rewrite_citations(
        self, text: str, retrieved_chunks: List[Dict[str, Any]]
    ) -> tuple[str, bool]:
        """Kiểm tra dòng `Tài liệu tham khảo:` và tự động chuẩn hóa theo `retrieved_chunks` (OUT-CITE)."""
        if not retrieved_chunks:
            return text, False

        valid_citations: List[str] = []
        citation_keywords: Set[str] = set()
        for chunk in retrieved_chunks:
            cit = str(chunk.get("citation") or chunk.get("document_name") or "").strip()
            if cit and cit not in valid_citations:
                valid_citations.append(cit)
            for token in re.findall(r"[A-Za-z0-9À-ỹ_]{3,}", cit.lower()):
                citation_keywords.add(token)
            doc_tag = str(chunk.get("document_tag") or "").lower()
            if doc_tag:
                citation_keywords.update(doc_tag.split("_"))

        if not valid_citations:
            return text, False

        canonical_line = f"Tài liệu tham khảo: {'; '.join(valid_citations)}"
        match = _RE_CITATION_LINE.search(text)
        if not match:
            rewritten = text.rstrip() + "\n\n" + canonical_line
            return rewritten, True

        cited_value = match.group(1).strip().lower()
        # Kiểm tra xem trích dẫn trong câu trả lời có khớp ít nhất một từ khóa nguồn chuẩn (ví dụ: 1851, byt, gina) hay không
        has_overlap = any(
            kw in cited_value
            for kw in citation_keywords
            if kw not in {"muc", "trang", "phan", "huong", "dan", "chan", "doan", "dieu", "tri"}
        )
        if has_overlap:
            return text, False

        # Thay thế dòng trích dẫn bịa đặt bằng trích dẫn chuẩn từ đoạn tài liệu đã truy xuất
        rewritten = _RE_CITATION_LINE.sub(canonical_line, text)
        return rewritten, True

    def _ensure_disclaimer(
        self, text: str, retrieved_chunks: List[Dict[str, Any]]
    ) -> tuple[str, bool]:
        """Đảm bảo phản hồi có dòng `Lưu ý y tế:` (OUT-DISCLAIMER)."""
        if not retrieved_chunks:
            return text, False
        lowered = text.lower()
        if "lưu ý y tế:" in lowered or "không thay thế chẩn đoán" in lowered:
            return text, False
        rewritten = text.rstrip() + "\n" + self.medical_disclaimer
        return rewritten, True

    def evaluate(self, state: AftercareState) -> OutputGuardResult:
        """Kiểm duyệt câu trả lời của LLM theo thứ tự ưu tiên 9 quy tắc L5 Output Guard."""
        text = (state.get("llm_raw_output") or state.get("response_text") or "").strip()
        if not text:
            return OutputGuardResult(
                decision="FAIL",
                response_text="",
                triggered_rules=["OUT-EMPTY"],
                detail="Đầu ra của mô hình ngôn ngữ lớn bị rỗng.",
            )

        # 1. OUT-LEAK
        leak_match = self._check_regex_rule("OUT-LEAK", text)
        if leak_match:
            return OutputGuardResult(
                decision="FAIL",
                response_text="",
                triggered_rules=["OUT-LEAK"],
                detail=f"Phát hiện rò rỉ thẻ nội bộ hoặc thông tin hệ thống ('{leak_match[:60]}').",
            )

        # 2. OUT-RESCREEN
        rescreen_match = self._check_regex_rule("OUT-RESCREEN", text)
        if rescreen_match:
            new_risk = escalate_risk(state.get("risk_level"), "YELLOW_ZONE")
            return OutputGuardResult(
                decision="RISK_UP",
                response_text=text,
                triggered_rules=["OUT-RESCREEN"],
                detail=(
                    f"Phản hồi phát hiện tình trạng nguy hiểm của người bệnh ('{rescreen_match[:60]}'). "
                    f"Nâng mức rủi ro lên {new_risk}."
                ),
                escalated_risk_level=new_risk,
            )

        # 3. OUT-FALSE-REASSURE
        reassure_match = self._check_regex_rule("OUT-FALSE-REASSURE", text)
        if reassure_match:
            return OutputGuardResult(
                decision="FAIL",
                response_text="",
                triggered_rules=["OUT-FALSE-REASSURE"],
                detail=f"Phát hiện cụm trấn an tuyệt đối gây nguy cơ chủ quan ('{reassure_match[:60]}').",
            )

        # 4. OUT-STOP-MED
        stop_match = self._check_regex_rule(
            "OUT-STOP-MED", text, check_negation_prefix=True
        )
        if stop_match:
            return OutputGuardResult(
                decision="FAIL",
                response_text="",
                triggered_rules=["OUT-STOP-MED"],
                detail=f"Phát hiện lời khuyên tự ý ngưng/bỏ thuốc điều trị ('{stop_match[:60]}').",
            )

        # 5. OUT-DIAG
        diag_match = self._check_regex_rule("OUT-DIAG", text)
        if diag_match:
            return OutputGuardResult(
                decision="FAIL",
                response_text="",
                triggered_rules=["OUT-DIAG"],
                detail=f"Phát hiện kết luận chẩn đoán xác định vượt thẩm quyền ('{diag_match[:60]}').",
            )

        reference_corpus = self._build_reference_corpus(state)

        # 6. OUT-DOSE-LEAK
        output_doses = _extract_dose_tokens(text, self._dose_regex)
        if output_doses:
            allowed_doses = _extract_dose_tokens(reference_corpus, self._dose_regex)
            unverified_doses = sorted(output_doses - allowed_doses)
            if unverified_doses:
                return OutputGuardResult(
                    decision="FAIL",
                    response_text="",
                    triggered_rules=["OUT-DOSE-LEAK"],
                    detail=(
                        "Phát hiện con số liều lượng không có trong tài liệu hoặc đơn thuốc: "
                        + ", ".join(unverified_doses)
                    ),
                )

        # 7. OUT-MED-ALLOW
        mentioned_meds: List[str] = []
        for med, pat in self._med_patterns.items():
            if pat.search(text):
                mentioned_meds.append(med)
        if mentioned_meds:
            allowed_meds = self._allowed_medications_for_turn(reference_corpus)
            unauthorized_meds = sorted(set(mentioned_meds) - allowed_meds)
            if unauthorized_meds:
                return OutputGuardResult(
                    decision="FAIL",
                    response_text="",
                    triggered_rules=["OUT-MED-ALLOW"],
                    detail=(
                        "Phát hiện tên thuốc nằm ngoài danh sách cho phép của lượt hội thoại: "
                        + ", ".join(unauthorized_meds)
                    ),
                )

        # 8. OUT-CITE & 9. OUT-DISCLAIMER
        retrieved_chunks = state.get("retrieved_chunks") or []
        rewritten_rules: List[str] = []
        working_text = text

        working_text, cite_rewritten = self._validate_and_rewrite_citations(
            working_text, retrieved_chunks
        )
        if cite_rewritten:
            rewritten_rules.append("OUT-CITE")

        working_text, disclaimer_rewritten = self._ensure_disclaimer(
            working_text, retrieved_chunks
        )
        if disclaimer_rewritten:
            rewritten_rules.append("OUT-DISCLAIMER")

        if rewritten_rules:
            return OutputGuardResult(
                decision="REWRITTEN",
                response_text=working_text,
                triggered_rules=rewritten_rules,
                detail="Đã tự động chuẩn hóa trích dẫn nguồn và lưu ý y tế cho phản hồi.",
            )

        return OutputGuardResult(
            decision="PASS",
            response_text=working_text,
            triggered_rules=[],
            detail="Đầu ra vượt qua toàn bộ 9 quy tắc kiểm duyệt an toàn.",
        )


_default_output_guard: Optional[OutputPolicyGuard] = None


def get_default_output_guard() -> OutputPolicyGuard:
    global _default_output_guard
    if _default_output_guard is None:
        _default_output_guard = OutputPolicyGuard()
    return _default_output_guard


__all__ = [
    "DEFAULT_OUTPUT_POLICY_PATH",
    "OutputGuardResult",
    "OutputPolicyGuard",
    "get_default_output_guard",
]

