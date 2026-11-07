from fastapi import APIRouter, Depends
from backend.app.api.v1.endpoints import auth, chat, conversations, patients, documents, care_plans, screener, escalations
from backend.app.core.security import current_user

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(auth.admin_router, prefix="/admin", tags=["Administration"])
api_router.include_router(conversations.router, prefix="/chat", tags=["Chat Memory"])
api_router.include_router(chat.router, prefix="/chat", tags=["Medical Chat"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"], dependencies=[Depends(current_user)])
api_router.include_router(care_plans.router, prefix="/care-tracker", tags=["Asthma Care Tracker"])
api_router.include_router(screener.router, prefix="/screener", tags=["Symptom Screener"])
api_router.include_router(escalations.router, prefix="/escalations", tags=["Escalation & Real-Time Alerts"])

