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
    """Temporary endpoint to verify env vars and files on Railway."""
    import os, glob
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    results_dir = os.path.join(project_root, "results")
    result_files = []
    if os.path.exists(results_dir):
        for root, dirs, files in os.walk(results_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), project_root)
                result_files.append(rel)
    return {
        "SUPABASE_SERVICE_KEY_set": bool(service_key),
        "SUPABASE_SERVICE_KEY_len": len(service_key),
        "SUPABASE_URL_set": bool(os.getenv("SUPABASE_URL", "")),
        "SUPABASE_KEY_set": bool(os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")),
        "project_root": project_root,
        "results_dir_exists": os.path.exists(results_dir),
        "cwd": os.getcwd(),
        "result_files": result_files[:50],
    }


@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await log_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(ws)
