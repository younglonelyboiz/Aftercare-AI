from fastapi import APIRouter
from backend.app.api.v1.endpoints import chat, patients, documents, care_plans

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["Medical Chat"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(care_plans.router, prefix="/care-tracker", tags=["Asthma Care Tracker"])
