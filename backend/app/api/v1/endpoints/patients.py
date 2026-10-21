from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json
from pathlib import Path

router = APIRouter()
PROFILES_DIR = Path(__file__).resolve().parents[5] / "Data" / "patient_profiles"

@router.get("/", response_model=List[Dict[str, Any]])
def list_patients():
    """Lấy danh sách tóm tắt tất cả các bệnh nhân mẫu."""
    patients = []
    if not PROFILES_DIR.exists():
        return patients
        
    for p_file in sorted(PROFILES_DIR.glob("*.json")):
        with open(p_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            patients.append({
                "patient_id": data["patient_info"]["patient_id"],
                "full_name": data["patient_info"]["full_name"],
                "age": data["patient_info"]["age"],
                "gender": data["patient_info"]["gender"],
                "diagnosis": data["clinical_status"]["diagnosis"],
                "personal_best_pef": data["clinical_status"]["personal_best_pef"],
                "baseline_spo2": data["clinical_status"]["baseline_spo2"],
                "file_name": p_file.name
            })
    return patients

@router.get("/{patient_id}", response_model=Dict[str, Any])
def get_patient_detail(patient_id: str):
    """Lấy toàn bộ hồ sơ chi tiết của bệnh nhân theo ID."""
    if not PROFILES_DIR.exists():
        raise HTTPException(status_code=404, detail="Thư mục hồ sơ không tồn tại.")
        
    for p_file in PROFILES_DIR.glob("*.json"):
        with open(p_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("patient_info", {}).get("patient_id") == patient_id:
                return data
                
    raise HTTPException(status_code=404, detail=f"Không tìm thấy bệnh nhân có mã: {patient_id}")
