"""Entrypoint FastAPI da demo Manutenção Veicular."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .bootstrap import init_database_async, seed_all_async
from .config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
log = logging.getLogger("manutencao")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Boot: criando tabelas + seed...")
    try:
        await init_database_async()
        await seed_all_async()
    except Exception as e:
        log.exception("Boot inicial falhou: %s", e)
    try:
        from .jobs.alertas_preventivas import start_scheduler
        start_scheduler()
    except Exception as e:
        log.warning("Scheduler não iniciou: %s", e)
    yield
    log.info("Shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Idempotency-Key"],
)

# ---------- Routers ----------
from .routers import (admin, alertas, auth_routes, dashboard, health, oficinas,
                      ordem_servico, planos, timeline, upload, veiculos)

API = "/api"
app.include_router(health.router, prefix=API)
app.include_router(auth_routes.router, prefix=API)
app.include_router(veiculos.router, prefix=API)
app.include_router(oficinas.router, prefix=API)
app.include_router(planos.router, prefix=API)
app.include_router(ordem_servico.router, prefix=API)
app.include_router(timeline.router, prefix=API)
app.include_router(dashboard.router, prefix=API)
app.include_router(alertas.router, prefix=API)
app.include_router(upload.router, prefix=API)
app.include_router(admin.router, prefix=API)


# ---------- Frontend estático (build do Vite) ----------
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend_dist"

if settings.SERVE_FRONTEND and FRONTEND_DIST.exists():
    @app.get("/", include_in_schema=False)
    def root_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        path = FRONTEND_DIST / "manifest.webmanifest"
        if not path.exists():
            path = FRONTEND_DIST / "manifest.json"
        return FileResponse(path, media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        path = FRONTEND_DIST / "sw.js"
        if path.exists():
            return FileResponse(path, media_type="application/javascript")
        return {"detail": "no service worker"}

    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    # Servir TODOS os arquivos estáticos do dist na raiz (registerSW.js, workbox-*.js,
    # pwa-*.png, favicon, etc.) — ANTES do fallback SPA
    app.mount("/static-root", StaticFiles(directory=str(FRONTEND_DIST)), name="static-root")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        from fastapi import HTTPException
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        # Se o path tem extensão de arquivo estático, tenta servir do dist
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        # Caso contrário, SPA fallback (rotas client-side React Router)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    log.warning("SERVE_FRONTEND=false ou dist ausente em %s", FRONTEND_DIST)

    @app.get("/")
    def root_api_only():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/api/docs",
            "health": "/api/health",
        }
