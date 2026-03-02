from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.database import init_db, get_session
from backend.app.init_auth import init_db_data
import os
import asyncio

# ─── Background Task: Reclaim Abandoned Tickets ───
ABANDONED_TIMEOUT_MINUTES = 30

async def reclaim_abandoned_tickets():
    """Every 5 min, return tickets stuck in SERVING for > 30 min back to WAITING."""
    from backend.app.models.ticket import Ticket, TicketStatus
    from sqlmodel import select
    from datetime import datetime, timedelta
    
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        try:
            session = next(get_session())
            cutoff = datetime.now() - timedelta(minutes=ABANDONED_TIMEOUT_MINUTES)
            abandoned = session.exec(
                select(Ticket)
                .where(Ticket.status == TicketStatus.SERVING)
                .where(Ticket.updated_at < cutoff)
            ).all()
            
            if abandoned:
                for ticket in abandoned:
                    ticket.status = TicketStatus.WAITING
                    ticket.served_by_module_id = None
                    ticket.served_by_operator_id = None
                    ticket.updated_at = datetime.now()
                    session.add(ticket)
                session.commit()
                
                # Broadcast update so monitor refreshes
                from backend.app.core.events import event_manager
                from backend.app.api.v1.endpoints.tickets import _monitor_snapshot
                snapshot = _monitor_snapshot(session)
                event_manager.broadcast("tickets_reclaimed", snapshot)
                
                print(f"♻️ Reclaimed {len(abandoned)} abandoned ticket(s)")
            session.close()
        except Exception as e:
            print(f"❌ Error reclaiming tickets: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and Default Data
    print(f"🚀 STARTUP CONFIG CHECK:")
    print(f"   - PROJECT_NAME: '{settings.PROJECT_NAME}'")
    print(f"   - COMPANY_NAME: '{settings.COMPANY_NAME}'")
    print(f"   - THEME_COLOR:  '{settings.THEME_COLOR}'")
    
    init_db_data()
    
    # Start background task
    task = asyncio.create_task(reclaim_abandoned_tickets())
    print(f"⏱️ Abandoned ticket reclaimer started (timeout: {ABANDONED_TIMEOUT_MINUTES} min)")
    
    yield
    
    # Cleanup on shutdown
    task.cancel()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# Static Files & Templates
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    templates = Jinja2Templates(directory=frontend_path)

    # Helper for common context
    def get_context(request: Request):
        return {
            "request": request,
            "project_name": settings.PROJECT_NAME,
            "company_name": settings.COMPANY_NAME,
            "logo_url": settings.LOGO_URL,
            "theme_color": settings.THEME_COLOR,
            "api_v1_str": settings.API_V1_STR
        }

    @app.get("/", response_class=HTMLResponse)
    async def read_index(request: Request):
        return templates.TemplateResponse("index.html", get_context(request))

    @app.get("/kiosk", response_class=HTMLResponse)
    async def read_kiosk(request: Request):
        return templates.TemplateResponse("kiosk.html", get_context(request))

    @app.get("/monitor", response_class=HTMLResponse)
    async def read_monitor(request: Request):
        return templates.TemplateResponse("monitor.html", get_context(request))

    @app.get("/clerk", response_class=HTMLResponse)
    async def read_clerk(request: Request):
        return templates.TemplateResponse("clerk.html", get_context(request))

    @app.get("/admin", response_class=HTMLResponse)
    async def read_admin(request: Request):
        return templates.TemplateResponse("admin.html", get_context(request))

    @app.get("/reports", response_class=HTMLResponse)
    async def read_reports(request: Request):
        return templates.TemplateResponse("reports.html", get_context(request))

    # Service Worker must be served from root for full scope
    @app.get("/sw.js")
    async def service_worker():
        sw_path = os.path.join(frontend_path, "sw.js")
        from fastapi.responses import FileResponse
        return FileResponse(sw_path, media_type="application/javascript")

@app.get("/health")
def health_check():
    return {"status": "ok", "system": f"{settings.PROJECT_NAME} — Sistema de Gestión de Filas"}
