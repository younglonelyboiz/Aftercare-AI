import logging
import json
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("NurseWebSocketManager")

class NurseWebSocketManager:
    """Quản lý kết nối WebSocket thời gian thực giữa Backend và Trạm trực Điều dưỡng (Nurse Station)."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_tokens = {}

    async def connect(self, websocket: WebSocket, token: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_tokens[websocket] = token
        logger.info(f"Trạm điều dưỡng mới đã kết nối. Tổng số kết nối: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.connection_tokens.pop(websocket, None)
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Trạm điều dưỡng đã ngắt kết nối. Còn lại: {len(self.active_connections)}")

    async def broadcast_json(self, message: Dict[str, Any]):
        """Bắn gói tin JSON tới tất cả các trạm điều dưỡng đang trực tuyến."""
        dead_connections = []
        from backend.app.core.database import SessionLocal
        from backend.app.core.security import session_user, allowed_patient_ids
        for connection in list(self.active_connections):
            try:
                with SessionLocal() as db:
                    user = session_user(db, self.connection_tokens.get(connection))
                    if not user or user.role not in {"admin", "nurse"}:
                        await connection.close(code=1008)
                        dead_connections.append(connection)
                        continue
                    allowed = allowed_patient_ids(db, user)
                    pid = message.get("patient_id") or message.get("ticket", {}).get("patient_id")
                    if allowed is not None and (not pid or pid not in allowed):
                        continue
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Lỗi gửi tin tới kết nối: {str(e)}")
                dead_connections.append(connection)

        # Dọn dẹp kết nối chết
        for dead in dead_connections:
            self.disconnect(dead)

    async def send_personal_json(self, websocket: WebSocket, message: Dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Lỗi gửi tin cá nhân: {str(e)}")

# Singleton instance dùng chung toàn hệ thống
nurse_ws_manager = NurseWebSocketManager()

