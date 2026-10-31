from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from backend.app.schemas.screener import ScreenerInput, ScreenerResult
from backend.app.clinical_agents.screener.symptom_screener import SymptomScreenerEngine
from backend.app.rag.service import AftercareRAGService

router = APIRouter()
screener_engine = SymptomScreenerEngine()
rag_service = AftercareRAGService()

@router.post("/evaluate", response_model=ScreenerResult)
async def evaluate_symptoms(request: ScreenerInput):
    """Sàng lọc triệu chứng, chỉ số sinh hiệu và phân tầng nguy cơ lâm sàng.
    
    Quy tắc nghiệp vụ:
      - Tuyệt đối không chẩn đoán tên bệnh lý (Zero Clinical Diagnosis).
      - Chỉ định hướng xử trí theo phác đồ cá nhân và điều phối cấp cứu.
    """
    try:
        profile: Optional[Dict[str, Any]] = None
        if request.patient_id:
            try:
                profile = rag_service.get_patient_profile(request.patient_id)
            except ValueError:
                # Nếu không tìm thấy profile, engine vẫn chạy dựa trên ngưỡng chuẩn mặc định
                profile = None

        result = screener_engine.evaluate(input_data=request, profile=profile)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi thực thi sàng lọc triệu chứng: {str(e)}")
