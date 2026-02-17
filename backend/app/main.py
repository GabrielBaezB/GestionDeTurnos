from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.init_auth import init_db_data
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and Default Data
    init_db_data()
    yield

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

# Static Files
# Path relative to backend/app/main.py -> ../../../frontend
# Wait, main.py is in backend/app. so .. is backend, .. is root. 
# frontend is in root/frontend.
# So relative path from main.py is ../../frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def read_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/kiosk")
    async def read_kiosk():
        return FileResponse(os.path.join(frontend_path, "kiosk.html"))

    @app.get("/monitor")
    async def read_monitor():
        return FileResponse(os.path.join(frontend_path, "monitor.html"))

    @app.get("/clerk")
    async def read_clerk():
        return FileResponse(os.path.join(frontend_path, "clerk.html"))

    @app.get("/admin")
    async def read_admin():
        return FileResponse(os.path.join(frontend_path, "admin.html"))

@app.get("/health")
def health_check():
    return {"status": "ok", "system": "ZeroQrobo Notaría Online (Frontend Ready)"}
