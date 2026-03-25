import asyncio
from fastapi import WebSocket, WebSocketDisconnect


# Cap max WebSocket connections to prevent unbounded memory growth
MAX_WS_CONNECTIONS = 20


class LogManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        # Reject new connections if at capacity
        if len(self.connections) >= MAX_WS_CONNECTIONS:
            try:
                oldest = self.connections.pop(0)
                await oldest.close()
            except Exception:
                pass
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        try:
            self.connections.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, message: str):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self.connections.remove(ws)
            except ValueError:
                pass


log_manager = LogManager()
