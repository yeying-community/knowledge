# api/main.py

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from api.routers.health import router as health_router
from api.routers.query import router as query_router
from api.app_register import router as app_register_router
from api.routers.memory import router as memory_router
from api.routers.kb import router as kb_router
from api.routers.stores import router as stores_router
from api.routers.ingestion import router as ingestion_router
from api.routers.ingestion_jobs import router as ingestion_jobs_router
from api.routers.resume import router as resume_router
from api.routers.jd import router as jd_router
from api.routers.private_dbs import router as private_db_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Service",
        version="2.1.0",
    )

    origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Common APIs (platform capabilities)
    common_router = APIRouter()
    common_router.include_router(health_router)
    common_router.include_router(app_register_router)
    common_router.include_router(kb_router)
    common_router.include_router(stores_router)
    common_router.include_router(ingestion_router)
    common_router.include_router(ingestion_jobs_router)
    common_router.include_router(memory_router)
    common_router.include_router(private_db_router)

    # Business APIs (workflow-specific)
    biz_router = APIRouter()
    biz_router.include_router(query_router)
    biz_router.include_router(resume_router)
    biz_router.include_router(jd_router)

    app.include_router(common_router)
    app.include_router(biz_router)

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.exists():
        app.mount("/console", StaticFiles(directory=str(frontend_dir), html=True), name="console")

    return app


app = create_app()
