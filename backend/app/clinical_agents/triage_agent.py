import re
from typing import Dict, Any

class TriageAgent:
    """Agent phân loại mức độ an toàn y tế và thực thi Rule-based Guardrail (Python thuần).
    
    Quy tắc 3 vùng màu:
      1. RED_ZONE (Cờ đỏ Cấp cứu): 
         - Bắt từ khóa đe dọa tính mạng: lồng ngực im lặng, nói từng từ, ngồi chồm, tím tái, ngủ gà, lú lẫn, thở ngắt quãng.
         - Hoặc PEF < 60% mức tốt nhất cá nhân, SpO2 < 92%.
      2. YELLOW_ZONE (Cảnh báo hen trở nặng):
         - Bắt từ khóa: thức giấc đêm, xịt nhiều lần, PEF tụt, tức ngực, khò khè tăng.
         - Hoặc PEF từ 60% đến 80% mức tốt nhất cá nhân.
      3. NORMAL (An toàn):
         - Các câu hỏi tư vấn, sinh hoạt, tác dụng phụ, kỹ thuật hít hoặc PEF >= 80%.
    """
    def __init__(self, gemini_client=None):
        self.client = gemini_client

    def evaluate_risk(self, user_query: str, profile: Dict[str, Any]) -> str:
        c_status = profile.get("clinical_status", {})
        best_pef = c_status.get("personal_best_pef", 450)
        red_pef = int(best_pef * 0.6)
        yellow_pef = int(best_pef * 0.8)

        query_lower = user_query.lower()

        # ==============================================================================
        # 1. HARD RULE: TẦNG CỜ ĐỎ CẤP CỨU (RED ZONE)
        # Bệnh nhân thực tế hoặc người nhà nhắn khi hoảng loạn/nguy kịch
        # ==============================================================================
        # Tri giác suy sụp, kiệt sức
        consciousness_flags = [
            "mê man", "lờ đờ", "lả đi", "mệt lả", "ngất", "bất tỉnh",
            "gọi không thưa", "gọi không biết", "không tỉnh táo", "nằm bất động"
        ]
        # Thiếu oxy nghiêm trọng / tím tái
        hypoxia_flags = [
            "tím môi", "môi thâm", "mặt tím", "tím tái", "tím ngắt", "tái mét", "móng tay tím"
        ]
        # Khó thở dữ dội / ngạt thở / không nói nổi
        severe_dyspnea_flags = [
            "không thở được", "nghẹt thở", "ngạt thở", "ngộp thở", "thở không nổi",
            "không nói nổi", "thều thào", "nói không ra hơi", "hụt hơi liên tục",
            "rút lõm ngực", "ngực thít chặt", "ngừng thở", "sắp ngất"
        ]
        # Kêu cứu / Khẩn cấp
        emergency_calls = [
            "cấp cứu", "gọi 115", "115", "đi viện gấp", "cứu với", "nguy kịch"
        ]

        for flag_list in [consciousness_flags, hypoxia_flags, severe_dyspnea_flags, emergency_calls]:
            for kw in flag_list:
                if kw in query_lower:
                    return "RED_ZONE"

        # Tình huống kinh điển: Đã xịt thuốc cắt cơn nhưng không đỡ / xịt liên tục
        reliever_fail_patterns = [
            r'(?:xịt|hít|dùng)\s*(?:\d+|mấy|nhiều)?\s*(?:nhát|lần|liều)?\s*(?:mà|vẫn)?\s*(?:không đỡ|không bớt|vẫn khó thở|càng khó thở)',
            r'(?:không đỡ|càng nặng|khó thở tăng).*?(?:xịt|ventolin|cắt cơn)'
        ]
        for pattern in reliever_fail_patterns:
            if re.search(pattern, query_lower):
                return "RED_ZONE"

        # Kiểm tra chỉ số PEF khách quan (nếu nhập trong tin nhắn)
        pef_match = re.search(r'(?:pef|lưu lượng đỉnh)[^\d]{0,20}(\d+)', query_lower)
        if pef_match:
            val = int(pef_match.group(1))
            if val < red_pef:
                return "RED_ZONE"
            elif val < yellow_pef:
                return "YELLOW_ZONE"

        # Kiểm tra chỉ số SpO2 khách quan (nếu nhập trong tin nhắn)
        spo2_match = re.search(r'(?:spo2|oxy)[^\d]{0,20}(\d+)', query_lower)
        if spo2_match:
            val = int(spo2_match.group(1))
            if val < 92:
                return "RED_ZONE"
            elif val < 95:
                return "YELLOW_ZONE"

        # ==============================================================================
        # 2. RULE: TẦNG CẢNH BÁO HEN TRỞ NẶNG (YELLOW ZONE)
        # Các triệu chứng khởi phát cơn hoặc kiểm soát kém trong 24h
        # ==============================================================================
        yellow_flags = [
            "thức giấc ban đêm", "thức giấc nửa đêm", "tỉnh giấc nửa đêm", "thức giấc vì ho",
            "ho nhiều về đêm", "khò khè tăng", "nặng ngực", "tức ngực", "thấy hơi mệt",
            "phải xịt cắt cơn", "cần xịt thuốc", "vùng vàng"
        ]
        for kw in yellow_flags:
            if kw in query_lower:
                return "YELLOW_ZONE"

        # ==============================================================================
        # 3. NORMAL (AN TOÀN -> ĐƯA VÀO LUỒNG RAG TRI THỨC)
        # ==============================================================================
        return "NORMAL"
