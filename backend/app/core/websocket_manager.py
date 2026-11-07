import logging
import json
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("NurseWebSocketManager")

class NurseWebSocketManager:
    """Quản lý kết nối WebSocket thời gian thực giữa Backend và Trạm trực Điều dưỡng (Nurse Station)."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Trạm điều dưỡng mới đã kết nối. Tổng số kết nối: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Trạm điều dưỡng đã ngắt kết nối. Còn lại: {len(self.active_connections)}")

    async def broadcast_json(self, message: Dict[str, Any]):
        """Bắn gói tin JSON tới tất cả các trạm điều dưỡng đang trực tuyến."""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Lỗi gửi tin tới kết nối: {str(e)}")
                dead_connections.append(connection)

        # Dọn dẹp kết nối chết
        for dead in dead_connections:
            if dead in self.active_connections:
                self.active_connections.remove(dead)

    async def send_personal_json(self, websocket: WebSocket, message: Dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Lỗi gửi tin cá nhân: {str(e)}")

# Singleton instance dùng chung toàn hệ thống
nurse_ws_manager = NurseWebSocketManager()

