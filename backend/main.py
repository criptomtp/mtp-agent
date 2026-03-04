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
    return {"status": "ok"}


@app.get("/api/debug/env")
def debug_env():
    """Temporary endpoint to verify env vars on Railway. Remove after debugging."""
    import os
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    return {
        "SUPABASE_SERVICE_KEY_set": bool(service_key),
        "SUPABASE_SERVICE_KEY_len": len(service_key),
        "SUPABASE_SERVICE_KEY_prefix": service_key[:20] + "..." if len(service_key) > 20 else service_key,
        "SUPABASE_URL_set": bool(os.getenv("SUPABASE_URL", "")),
        "SUPABASE_KEY_set": bool(os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")),
    }


@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await log_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(ws)
