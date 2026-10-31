import re
import unicodedata
from typing import Dict, Any, List, Optional
from backend.app.schemas.screener import (
    ScreenerRuleConfig,
    ScreenerInput,
    ScreenerResult
)

class SymptomScreenerEngine:
    """Engine sàng lọc triệu chứng và phân tầng nguy cơ y tế (Rule-based & Deterministic).
    
    NGUYÊN TẮC THIẾT KẾ:
      1. Tuyệt đối KHÔNG chẩn đoán tên bệnh lý (No clinical diagnosis).
      2. Định hướng hành động (Action-Oriented): Hướng dẫn sơ cứu, dùng thuốc cắt cơn theo chỉ định.
      3. Nguyên tắc Worst-case Escalation: Có 1 cờ đỏ -> RED_ZONE; có dấu hiệu bùng phát -> YELLOW_ZONE.
      4. Single Source of Truth cho cả Chatbot và Form Check-in.
    """

    # Danh mục cờ đỏ cấp cứu đe dọa tính mạng (RED FLAGS)
    CONSCIOUSNESS_FLAGS = [
        "mê man", "lơ mơ", "lờ đờ", "lả đi", "mệt lả", "ngất", "bất tỉnh",
        "gọi không thưa", "gọi không biết", "không tỉnh táo", "nằm bất động"
    ]
    HYPOXIA_FLAGS = [
        "tím môi", "môi thâm", "mặt tím", "tím tái", "tím ngắt", "tái mét", "móng tay tím"
    ]
    SEVERE_DYSPNEA_FLAGS = [
        "không thở được", "nghẹt thở", "ngạt thở", "ngộp thở", "thở không nổi",
        "không nói nổi", "thều thào", "nói không ra hơi", "hụt hơi liên tục",
        "rút lõm ngực", "ngực thít chặt", "ngừng thở", "sắp ngất"
    ]
    EMERGENCY_CALLS = [
        "cấp cứu", "gọi 115", "115", "đi viện gấp", "cứu với", "nguy kịch", "khẩn cấp"
    ]

    # Mẫu phát hiện thất bại khi cắt cơn (Reliever Refractory / Reliever Failure)
    RELIEVER_FAIL_PATTERNS = [
        r'(?:xịt|hít|dùng)\s*.*?(?:không đỡ|không bớt|vẫn khó thở|càng khó thở|vẫn nghẹt thở|không ăn thua)',
        r'(?:không đỡ|càng nặng|khó thở tăng|không bớt).*?(?:xịt|ventolin|cắt cơn)',
        r'(?:đã xịt|vừa xịt).*?(?:nhưng|mà|vẫn).*?(?:vẫn|không|càng|tức ngực|nghẹt thở)'
    ]

    # Danh mục dấu hiệu hen bùng phát / trở nặng (YELLOW FLAGS)
    YELLOW_FLAGS = [
        "thức giấc ban đêm", "thức giấc nửa đêm", "tỉnh giấc nửa đêm", "thức giấc vì ho",
        "ho nhiều về đêm", "khò khè tăng", "nặng ngực", "tức ngực", "thấy hơi mệt",
        "phải xịt cắt cơn", "cần xịt thuốc", "vùng vàng", "thở khò khè", "nặng ngực khi đi lại"
    ]

    @staticmethod
    def strip_accents(text: str) -> str:
        """Loại bỏ dấu tiếng Việt để đối sánh mềm (fuzzy matching)."""
        text = unicodedata.normalize('NFD', text)
        text = re.sub(r'[\u0300-\u036f]', '', text)
        return text.replace('đ', 'd').replace('Đ', 'D')

    def normalize_text(self, text: str) -> str:
        """Chuẩn hóa văn bản đầu vào: chữ thường, chuẩn hóa teencode phổ biến."""
        t = text.lower().strip()
        # Chuẩn hóa viết tắt thường gặp của bệnh nhân khi hoảng loạn
        replacements = {
            r'\bk\b': 'không',
            r'\bko\b': 'không',
            r'\bkhg\b': 'không',
            r'\bdc\b': 'được',
            r'\btho\b': 'thở',
            r'\bmet\b': 'mệt',
            r'\bcap cuu\b': 'cấp cứu',
            r'\bngat tho\b': 'ngạt thở',
            r'\bnghet tho\b': 'nghẹt thở',
            r'\btim tai\b': 'tím tái'
        }
        for pattern, replacement in replacements.items():
            t = re.sub(pattern, replacement, t)
        return t

    def evaluate(self, input_data: ScreenerInput, profile: Optional[Dict[str, Any]] = None) -> ScreenerResult:
        """Thực thi sàng lọc triệu chứng, trả về mức độ rủi ro và chỉ dẫn hành động."""
        matched_flags: List[str] = []
        matched_reasons: List[str] = []

        # 1. Xác định cấu hình quy tắc (Ưu tiên config_override > profile cá nhân > default)
        cfg = input_data.config_override or ScreenerRuleConfig()
        if profile and not input_data.config_override:
            c_status = profile.get("clinical_status", {})
            cfg.personal_best_pef = c_status.get("personal_best_pef", cfg.personal_best_pef)
            # Nạp ngưỡng tùy biến nếu có trong profile
            if "screener_config" in profile:
                p_cfg = profile["screener_config"]
                cfg.red_spo2_threshold = p_cfg.get("red_spo2_threshold", cfg.red_spo2_threshold)
                cfg.yellow_spo2_threshold = p_cfg.get("yellow_spo2_threshold", cfg.yellow_spo2_threshold)

        red_pef = int(cfg.personal_best_pef * cfg.red_pef_ratio)
        yellow_pef = int(cfg.personal_best_pef * cfg.yellow_pef_ratio)

        # 2. ĐÁNH GIÁ CHỈ SỐ SINH HIỆU CÓ CẤU TRÚC (STRUCTURED VITALS)
        pef_val = input_data.pef_value
        spo2_val = input_data.spo2

        # 3. TRÍCH XUẤT CHỈ SỐ TỪ VĂN BẢN TỰ DO NẾU CHƯA CÓ DỮ LIỆU CẤU TRÚC
        norm_text = ""
        if input_data.free_text:
            norm_text = self.normalize_text(input_data.free_text)
            if pef_val is None:
                pef_match = re.search(r'(?:pef|lưu lượng đỉnh)[^\d]{0,20}(\d+)', norm_text)
                if pef_match:
                    pef_val = int(pef_match.group(1))
            if spo2_val is None:
                spo2_match = re.search(r'(?:spo2|oxy|oxi)[^\d]{0,20}(\d+)', norm_text)
                if spo2_match:
                    spo2_val = int(spo2_match.group(1))

        # --- A. Kiểm tra chỉ số PEF ---
        if pef_val is not None:
            if pef_val < red_pef:
                matched_flags.append("pef_critical")
                matched_reasons.append(
                    f"Chỉ số PEF ({pef_val} L/min) tụt dưới 60% mức chuẩn tốt nhất ({cfg.personal_best_pef} L/min)."
                )
            elif pef_val < yellow_pef:
                matched_flags.append("pef_warning")
                matched_reasons.append(
                    f"Chỉ số PEF ({pef_val} L/min) giảm trong khoảng 60% - 80% mức chuẩn tốt nhất ({cfg.personal_best_pef} L/min)."
                )

        # --- B. Kiểm tra chỉ số SpO2 ---
        if spo2_val is not None:
            if spo2_val < cfg.red_spo2_threshold:
                matched_flags.append("spo2_critical")
                matched_reasons.append(f"Độ bão hòa oxy SpO2 ({spo2_val}%) ở mức nguy hiểm (< {cfg.red_spo2_threshold}%).")
            elif spo2_val < cfg.yellow_spo2_threshold:
                matched_flags.append("spo2_warning")
                matched_reasons.append(f"Độ bão hòa oxy SpO2 ({spo2_val}%) ở mức cảnh báo ({cfg.red_spo2_threshold}% - {cfg.yellow_spo2_threshold}%).")

        # --- C. Kiểm tra tần suất dùng thuốc cắt cơn ---
        if input_data.reliever_puffs and input_data.reliever_puffs > cfg.max_reliever_puffs_24h:
            matched_flags.append("reliever_overuse")
            matched_reasons.append(
                f"Đã sử dụng thuốc cắt cơn {input_data.reliever_puffs} nhát trong 24h qua (vượt mức an toàn {cfg.max_reliever_puffs_24h} nhát)."
            )

        # 4. ĐÁNH GIÁ TRIỆU CHỨNG LÂM SÀNG VĂN BẢN & CHECKLIST (UNSTRUCTURED / CHECKLIST)
        is_red_text = False
        is_yellow_text = False

        if norm_text:
            unaccented_text = self.strip_accents(norm_text)

            # Kiểm tra Cờ đỏ trong text
            all_red_keywords = (
                self.CONSCIOUSNESS_FLAGS + self.HYPOXIA_FLAGS + 
                self.SEVERE_DYSPNEA_FLAGS + self.EMERGENCY_CALLS + 
                cfg.custom_red_keywords
            )
            for kw in all_red_keywords:
                if kw in norm_text or self.strip_accents(kw) in unaccented_text:
                    matched_flags.append(f"red_flag_keyword:{kw}")
                    matched_reasons.append(f"Xuất hiện dấu hiệu khẩn cấp trong phản ánh: '{kw}'.")
                    is_red_text = True
                    break

            # Kiểm tra mẫu xịt thuốc không đỡ
            for pat in self.RELIEVER_FAIL_PATTERNS:
                if re.search(pat, norm_text):
                    matched_flags.append("reliever_refractory")
                    matched_reasons.append("Tình trạng khó thở không thuyên giảm hoặc tăng nặng sau khi đã dùng thuốc cắt cơn.")
                    is_red_text = True
                    break

            # Kiểm tra Cờ vàng trong text (nếu chưa bị đỏ)
            if not is_red_text:
                all_yellow_keywords = self.YELLOW_FLAGS + cfg.custom_yellow_keywords
                for kw in all_yellow_keywords:
                    if kw in norm_text or self.strip_accents(kw) in unaccented_text:
                        matched_flags.append(f"yellow_flag_keyword:{kw}")
                        matched_reasons.append(f"Ghi nhận triệu chứng hen bùng phát / kiểm soát kém: '{kw}'.")
                        is_yellow_text = True
                        break

        # Kiểm tra checklist triệu chứng được chọn sẵn
        if "night_waking" in input_data.selected_symptoms:
            matched_flags.append("symptom:night_waking")
            matched_reasons.append("Thức giấc nửa đêm do ho hoặc khó thở.")
            is_yellow_text = True
        if "chest_tightness" in input_data.selected_symptoms:
            matched_flags.append("symptom:chest_tightness")
            matched_reasons.append("Cảm giác nặng ngực hoặc tức ngực tăng dần.")
            is_yellow_text = True
        if "severe_cyanosis" in input_data.selected_symptoms or "unresponsive" in input_data.selected_symptoms:
            matched_flags.append("symptom:severe_red_flag")
            matched_reasons.append("Bệnh nhân có dấu hiệu tím tái hoặc tri giác lơ mơ.")
            is_red_text = True

        # 5. TRÌNH PHÁN QUYẾT TỐI HẬU (WORST-CASE ARBITER)
        has_red = (
            "pef_critical" in matched_flags or 
            "spo2_critical" in matched_flags or 
            "reliever_refractory" in matched_flags or 
            is_red_text
        )

        has_yellow = (
            "pef_warning" in matched_flags or 
            "spo2_warning" in matched_flags or 
            "reliever_overuse" in matched_flags or 
            is_yellow_text
        )

        # Lấy thông tin điều trị cá nhân hóa nếu có profile
        p_name = profile.get("patient_info", {}).get("full_name", "Bác/Bạn") if profile else "Bác/Bạn"
        meds = profile.get("current_medications", {}) if profile else {}
        reliever_med = meds.get("reliever_med", "thuốc cắt cơn tác dụng nhanh")
        plan_rules = profile.get("action_plan_rules", {}) if profile else {}
        hospital = profile.get("follow_up", {}).get("hospital", "cơ sở y tế gần nhất") if profile else "cơ sở y tế gần nhất"

        if has_red:
            plan_red = plan_rules.get("red_zone", "Dùng ngay 2-4 nhát thuốc cắt cơn. Lặp lại sau 5-10 phút nếu cần.")
            action_text = (
                f"🚨 CẢNH BÁO CỜ ĐỎ CẤP CỨU: {p_name} đang có các dấu hiệu nguy kịch cần hỗ trợ y tế khẩn cấp!\n\n"
                f"1. DÙNG THUỐC CẮT CƠN KHẨN CẤP: Dùng ngay {reliever_med} theo kế hoạch: {plan_red}\n"
                f"2. TƯ THẾ HỖ TRỢ ĐƯỜNG THỞ: Ngồi thẳng lưng, hơi cúi người ra phía trước, thở chúm môi chậm rãi. TUYỆT ĐỐI KHÔNG NẰM NGỬA!\n"
                f"3. CẤP CỨU KHẨN CẤP: Nhờ người nhà gọi ngay Cấp cứu 115 hoặc khẩn trương di chuyển tới {hospital}!"
            )
            return ScreenerResult(
                risk_level="RED_ZONE",
                matched_flags=matched_flags,
                matched_reasons=matched_reasons,
                action_instructions=action_text,
                escalate_to_staff=True,
                suggested_follow_up_minutes=10
            )

        if has_yellow:
            plan_yellow = plan_rules.get("yellow_zone", "Dùng ngay 2 nhát thuốc cắt cơn và nghỉ ngơi.")
            action_text = (
                f"⚠️ CẢNH BÁO HEN TRỞ NẶNG (VÙNG VÀNG): {p_name} có dấu hiệu hen bùng phát hoặc kiểm soát kém.\n\n"
                f"1. SỬ DỤNG THUỐC CẮT CƠN: Dùng {reliever_med} theo đúng chỉ dẫn Vùng Vàng: {plan_yellow}\n"
                f"2. NGHỈ NGƠI TẠI CHỖ: Tránh xa khói bụi, máy lạnh nhiệt độ thấp hoặc môi trường có mùi dị nguyên.\n"
                f"3. THEO DÕI ĐÁNH GIÁ LẠI: Sau 20-30 phút nếu cơn khó thở không thuyên giảm hoặc xuất hiện dấu hiệu nguy cấp, cần liên hệ cơ sở y tế ({hospital}) ngay."
            )
            return ScreenerResult(
                risk_level="YELLOW_ZONE",
                matched_flags=matched_flags,
                matched_reasons=matched_reasons,
                action_instructions=action_text,
                escalate_to_staff=True,
                suggested_follow_up_minutes=30
            )

        # Trạng thái an toàn bình thường (NORMAL)
        action_text = (
            f"✅ TÌNH TRẠNG HIỆN TẠI ỔN ĐỊNH: Các chỉ số và triệu chứng của {p_name} đều nằm trong vùng an toàn (Vùng Xanh).\n\n"
            f"• Tiếp tục duy trì xịt thuốc kiểm soát định kỳ đúng liều lượng.\n"
            f"• Giữ ấm đường thở, uống đủ nước ấm và theo dõi chỉ số PEF hàng ngày."
        )
        return ScreenerResult(
            risk_level="NORMAL",
            matched_flags=[],
            matched_reasons=["Các chỉ số sinh hiệu và triệu chứng ghi nhận đều trong giới hạn an toàn bình thường."],
            action_instructions=action_text,
            escalate_to_staff=False,
            suggested_follow_up_minutes=None
        )
