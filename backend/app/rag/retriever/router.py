from typing import List
import re

# Từ khóa định tuyến phân hệ 2 kho tri thức
EMERGENCY_KEYWORDS = [
    "cấp cứu", "115", "nguy kịch", "đe dọa tính mạng", "ngủ gà", "lơ mơ", 
    "lồng ngực im lặng", "im phăng phắc", "ngồi chồm", "ngồi cúi", "nói từng từ",
    "vùng đỏ", "pef dưới 60", "tụt sâu", "ngừng thở", "cắt cơn cấp tốc", "nửa đêm",
    "prednisolone", "viên prednisolone", "đợt cấp"
]

CARE_KEYWORDS = [
    "duy trì", "ngưng bình", "dừng thuốc", "súc miệng", "rát họng", "nấm", "khàn", 
    "run tay", "buồng đệm", "spacer", "tập gym", "chạy bộ", "gắng sức", "vắc xin", "vắc-xin",
    "tiêm phòng", "mang thai", "em bé", "aspirin", "ibuprofen", "dạ dày", "ợ chua",
    "tái khám", "cốp xe", "bảo quản", "viêm mũi", "copd", "chó mèo", "khói thuốc"
]

class QueryRouter:
    """Định tuyến câu hỏi của bệnh nhân vào phân kho tri thức thích hợp."""

    @staticmethod
    def route_query_store(query_text: str) -> str:
        q = query_text.lower()
        match_emergency = sum(1 for kw in EMERGENCY_KEYWORDS if kw in q)
        match_care = sum(1 for kw in CARE_KEYWORDS if kw in q)

        if match_emergency > 0 and match_care > 0:
            return "ALL"
        if match_emergency == 0 and match_care == 0:
            return "ALL"
        if match_emergency > 0:
            return "KHO_1_CANH_BAO_CO_DO_CAP_CUU"
        else:
            return "KHO_2_CHAM_SOC_HOI_PHUC_THEO_DOI"
