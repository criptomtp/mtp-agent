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
    weasyprint_ok = False
    weasyprint_err = ""
    try:
        from weasyprint import HTML
        import tempfile, os
        tmp = os.path.join(tempfile.gettempdir(), "test.pdf")
        HTML(string="<h1>test</h1>").write_pdf(tmp)
        weasyprint_ok = os.path.exists(tmp) and os.path.getsize(tmp) > 0
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception as e:
        weasyprint_err = str(e)[:200]
    return {
        "status": "ok",
        "storage_ready": bool(settings.SUPABASE_SERVICE_KEY),
        "weasyprint_ok": weasyprint_ok,
        "weasyprint_err": weasyprint_err or None,
    }



@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await log_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(ws)
