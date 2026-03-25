import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from backend.config import settings
from backend.routers import analytics, dashboard, leads, outreach, proposals, runs, settings as settings_router
from backend.ws.logs import log_manager

app = FastAPI(title="MTP Fulfillment Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router)
app.include_router(dashboard.router)
app.include_router(leads.router)
app.include_router(runs.router)
app.include_router(proposals.router)
app.include_router(outreach.router)
app.include_router(settings_router.router)


@app.get("/health")
@app.get("/api/health")
def health():
    import os
    mem_mb = None
    mem_percent = None
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info()
        mem_mb = round(mem.rss / 1024 / 1024, 1)
        mem_percent = round(process.memory_percent(), 1)
    except Exception:
        # Fallback if psutil not available
        try:
            import resource
            mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if os.uname().sysname == "Darwin":
                mem_mb = round(mem_kb / 1024 / 1024, 1)
            else:
                mem_mb = round(mem_kb / 1024, 1)
        except Exception:
            pass
    return {
        "status": "ok",
        "storage_ready": bool(settings.SUPABASE_SERVICE_KEY),
        "memory_mb": mem_mb,
        "memory_percent": mem_percent,
    }



@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await log_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(ws)
