import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from backend.config import settings
from backend.routers import dashboard, leads, runs, settings as settings_router
from backend.ws.logs import log_manager

app = FastAPI(title="MTP Fulfillment Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(leads.router)
app.include_router(runs.router)
app.include_router(settings_router.router)


@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "storage_ready": bool(settings.SUPABASE_SERVICE_KEY),
    }


@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await log_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(ws)
