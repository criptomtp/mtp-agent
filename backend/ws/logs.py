import asyncio
from fastapi import WebSocket, WebSocketDisconnect


class LogManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, message: str):
        for ws in self.connections[:]:
            try:
                await ws.send_text(message)
            except Exception:
                self.connections.remove(ws)


log_manager = LogManager()
