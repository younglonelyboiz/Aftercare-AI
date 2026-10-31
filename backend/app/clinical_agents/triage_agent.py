from typing import Dict, Any, Optional
from backend.app.schemas.screener import ScreenerInput, ScreenerResult
from backend.app.clinical_agents.screener.symptom_screener import SymptomScreenerEngine

class TriageAgent:
    """Agent phân loại mức độ an toàn y tế và thực thi Rule-based Guardrail.
    
    Ủy quyền toàn bộ logic sàng lọc triệu chứng và phân tầng nguy cơ
    sang SymptomScreenerEngine (Single Source of Truth).
    """
    def __init__(self, gemini_client=None):
        self.client = gemini_client
        self.screener = SymptomScreenerEngine()

    def evaluate_risk(self, user_query: str, profile: Dict[str, Any]) -> str:
        """Đánh giá nguy cơ từ câu chat tự do, trả về risk_level (RED_ZONE | YELLOW_ZONE | NORMAL)."""
        screener_input = ScreenerInput(
            patient_id=profile.get("patient_info", {}).get("patient_id"),
            free_text=user_query
        )
        result: ScreenerResult = self.screener.evaluate(screener_input, profile=profile)
        return result.risk_level

    def evaluate_full(self, screener_input: ScreenerInput, profile: Optional[Dict[str, Any]] = None) -> ScreenerResult:
        """Đánh giá đầy đủ (trả về ScreenerResult gồm chỉ dẫn, cờ rủi ro và lý do)."""
        return self.screener.evaluate(screener_input, profile=profile)

