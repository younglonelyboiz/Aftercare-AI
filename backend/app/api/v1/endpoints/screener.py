from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from backend.app.schemas.screener import ScreenerInput, ScreenerResult
from backend.app.clinical_agents.screener.symptom_screener import SymptomScreenerEngine
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import current_user, ensure_patient_access
from backend.app.models.identity import User
from backend.app.services.patient_context import clinical_context

router = APIRouter()
screener_engine = SymptomScreenerEngine()

@router.post("/evaluate", response_model=ScreenerResult)
async def evaluate_symptoms(request: ScreenerInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Sàng lọc triệu chứng, chỉ số sinh hiệu và phân tầng nguy cơ lâm sàng.
    
    Quy tắc nghiệp vụ:
      - Tuyệt đối không chẩn đoán tên bệnh lý (Zero Clinical Diagnosis).
      - Chỉ định hướng xử trí theo phác đồ cá nhân và điều phối cấp cứu.
    """
    pid = request.patient_id or user.patient_id
    if pid:
        ensure_patient_access(db, user, pid)
    try:
        profile: Optional[Dict[str, Any]] = None
        if pid:
            try:
                profile = clinical_context(db, pid)
            except ValueError:
                # Nếu không tìm thấy profile, engine vẫn chạy dựa trên ngưỡng chuẩn mặc định
                profile = None

        result = screener_engine.evaluate(input_data=request, profile=profile)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi thực thi sàng lọc triệu chứng: {str(e)}")
