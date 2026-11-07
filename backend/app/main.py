import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.v1.router import api_router
from backend.app.workers.non_response_worker import non_response_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động NonResponseWorker ngầm để quét ca mất liên lạc & 20 phút Vùng Vàng
    worker_task = asyncio.create_task(non_response_worker.run_loop())
    yield
    # Dừng worker an toàn khi ứng dụng tắt
    non_response_worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Hệ thống Trợ lý AI Chăm sóc Sau xuất viện cho Bệnh nhân Hen Phế Quản (Grounding BYT & GINA)",
    lifespan=lifespan
)

# Cấu hình CORS để Frontend (React/Next.js/Vite) gọi API dễ dàng
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
