"""
Bộ kiểm tra chính sách đầu vào (L2 Policy & Intent Guard) — [W07-T2.3].

Nạp các quy tắc từ `backend/app/guardrails/policies/input_policies.yaml`,
tái sử dụng bộ chuẩn hóa văn bản tiếng Việt của `SymptomScreenerEngine`
để phát hiện cả văn bản có dấu, không dấu và từ viết tắt.
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml

from backend.app.clinical_agents.screener.symptom_screener import SymptomScreenerEngine
from backend.app.guardrails.templates_vi import EMPTY_INPUT_MESSAGE
from backend.app.orchestration.nodes.sanitize import sanitize_text_preserve_length

DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parent / "policies" / "input_policies.yaml"
)

EXTRA_ABBREVIATIONS = {
    r"\bko\b": "không",
    r"\bk\b": "không",
    r"\bkhg\b": "không",
    r"\bdc\b": "được",
    r"\bđc\b": "được",
    r"\bmk\b": "mình",
    r"\bbs\b": "bác sĩ",
    r"\bks\b": "kháng sinh",
}


@dataclass
class PolicyMatchResult:
    """Kết quả đối sánh một tin nhắn với bộ quy tắc chính sách đầu vào."""

    decision: Literal["ALLOW", "BLOCK"]
    rule_id: str
    rule_name: str
    response_text: Optional[str] = None
    escalation: Optional[Dict[str, str]] = None


class InputPolicyGuard:
    """Engine kiểm tra chính sách đầu vào tất định dựa trên cấu hình YAML."""

    def __init__(self, policy_path: Optional[Path] = None):
        self.policy_path = policy_path or DEFAULT_POLICY_PATH
        self._screener = SymptomScreenerEngine()
        self.version: str = "1.0.0"
        self.compiled_rules: List[Dict[str, Any]] = []
        self._load_policies()

    def _load_policies(self) -> None:
        raw_data = yaml.safe_load(self.policy_path.read_text(encoding="utf-8")) or {}
        self.version = str(raw_data.get("version", "1.0.0"))
        rules = sorted(
            raw_data.get("rules", []),
            key=lambda item: int(item.get("priority_order", 999)),
        )
        compiled: List[Dict[str, Any]] = []
        for rule in rules:
            allow_raw = rule.get("allow_patterns") or []
            accented_raw = rule.get("accented_patterns") or []
            unaccented_raw = rule.get("unaccented_patterns") or []
            compiled.append(
                {
                    "rule_id": rule["rule_id"],
                    "name": rule.get("name", rule["rule_id"]),
                    "action": rule.get("action", "BLOCK"),
                    "escalation": rule.get("escalation"),
                    "response_template": (rule.get("response_template") or "").strip(),
                    "allow_regexes": [
                        re.compile(pat, flags=re.IGNORECASE) for pat in allow_raw
                    ],
                    "allow_unaccented_regexes": [
                        re.compile(
                            SymptomScreenerEngine.strip_accents(pat),
                            flags=re.IGNORECASE,
                        )
                        for pat in allow_raw
                    ],
                    "accented_regexes": [
                        re.compile(pat, flags=re.IGNORECASE) for pat in accented_raw
                    ],
                    "unaccented_regexes": [
                        re.compile(pat, flags=re.IGNORECASE) for pat in unaccented_raw
                    ],
                }
            )
        self.compiled_rules = compiled

    def normalize_pair(self, text: str) -> tuple[str, str]:
        """Trả về cặp `(văn_bản_có_dấu_chuẩn_hóa, văn_bản_không_dấu_chuẩn_hóa)`."""
        cleaned = sanitize_text_preserve_length(text)
        normalized = self._screener.normalize_text(cleaned)
        for pattern, replacement in EXTRA_ABBREVIATIONS.items():
            normalized = re.sub(pattern, replacement, normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        unaccented = SymptomScreenerEngine.strip_accents(normalized).lower()
        return normalized, unaccented

    def evaluate_text(self, text: str) -> PolicyMatchResult:
        """Đánh giá một chuỗi văn bản và trả về `PolicyMatchResult`."""
        if not text or not text.strip():
            return PolicyMatchResult(
                decision="BLOCK",
                rule_id="IN-EMPTY",
                rule_name="Tin nhắn rỗng",
                response_text=EMPTY_INPUT_MESSAGE,
                escalation=None,
            )

        accented, unaccented = self.normalize_pair(text)
        if not accented:
            return PolicyMatchResult(
                decision="BLOCK",
                rule_id="IN-EMPTY",
                rule_name="Tin nhắn rỗng",
                response_text=EMPTY_INPUT_MESSAGE,
                escalation=None,
            )

        for rule in self.compiled_rules:
            if any(rx.search(accented) for rx in rule["allow_regexes"]) or any(
                rx.search(unaccented) for rx in rule["allow_unaccented_regexes"]
            ):
                continue

            matched = any(
                rx.search(accented) for rx in rule["accented_regexes"]
            ) or any(rx.search(unaccented) for rx in rule["unaccented_regexes"])

            if matched:
                return PolicyMatchResult(
                    decision="BLOCK",
                    rule_id=rule["rule_id"],
                    rule_name=rule["name"],
                    response_text=rule["response_template"],
                    escalation=rule["escalation"],
                )

        return PolicyMatchResult(
            decision="ALLOW",
            rule_id="POL-ALLOW",
            rule_name="Cho phép truy vấn",
            response_text=None,
            escalation=None,
        )

