"""
IPTV Panel - Main Application
Equivalent to XC_VM: Full IPTV management panel with Xtream Codes compatible API.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from src.core.config import settings
from src.core.database import init_db, engine, Base
from src.core.cache.redis_cache import cache
from src.core.logging.logger import logger
from src.domain import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    from src.core.database import SessionLocal
    from src.domain.user.service import UserService
    db = SessionLocal()
    try:
        svc = UserService(db)
        admin = svc.get_by_username("admin")
        if not admin:
            svc.create({
                "username": "admin",
                "password": "admin",
                "is_admin": True,
                "enabled": True,
                "max_connections": 1,
            })
            logger.info("Default admin user created (admin/admin)")
    finally:
        db.close()

    try:
        await cache.connect()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Running without cache.")

    from src.core.module.loader import ModuleLoader
    modules_dir = os.path.join(os.path.dirname(__file__), "modules")
    module_loader = ModuleLoader(modules_dir)
    loaded = module_loader.load_all()
    for name, mod in loaded.items():
        mod.boot(app)
        logger.info(f"Module '{name}' v{mod.get_version()} booted")

    yield

    try:
        await cache.disconnect()
    except Exception:
        pass
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="IPTV Panel - Open Source IPTV Management Platform with Xtream Codes Compatible API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "public", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates_dir = os.path.join(os.path.dirname(__file__), "public", "views")
templates = Jinja2Templates(directory=templates_dir) if os.path.exists(templates_dir) else None

# --- Admin API Routes ---
from src.public.controllers.admin.auth_routes import router as admin_auth_router
from src.public.controllers.admin.stream_routes import router as admin_stream_router
from src.public.controllers.admin.user_routes import router as admin_user_router
from src.public.controllers.admin.vod_routes import router as admin_vod_router
from src.public.controllers.admin.category_routes import router as admin_category_router
from src.public.controllers.admin.bouquet_routes import router as admin_bouquet_router
from src.public.controllers.admin.server_routes import router as admin_server_router
from src.public.controllers.admin.epg_routes import router as admin_epg_router
from src.public.controllers.admin.settings_routes import router as admin_settings_router
from src.public.controllers.admin.line_routes import router as admin_line_router
from src.public.controllers.admin.reseller_routes import router as admin_reseller_router
from src.public.controllers.admin.dashboard_routes import router as admin_dashboard_router

app.include_router(admin_auth_router, prefix="/api/admin")
app.include_router(admin_dashboard_router, prefix="/api/admin")
app.include_router(admin_stream_router, prefix="/api/admin")
app.include_router(admin_user_router, prefix="/api/admin")
app.include_router(admin_vod_router, prefix="/api/admin")
app.include_router(admin_category_router, prefix="/api/admin")
app.include_router(admin_bouquet_router, prefix="/api/admin")
app.include_router(admin_server_router, prefix="/api/admin")
app.include_router(admin_epg_router, prefix="/api/admin")
app.include_router(admin_settings_router, prefix="/api/admin")
app.include_router(admin_line_router, prefix="/api/admin")
app.include_router(admin_reseller_router, prefix="/api/admin")

# --- Player / Xtream Codes Compatible API ---
from src.public.controllers.api.player_api import router as player_api_router
from src.public.controllers.api.mag_api import router as mag_api_router
from src.public.controllers.api.enigma2_api import router as enigma2_api_router
from src.public.controllers.api.xplugin_api import router as xplugin_api_router

app.include_router(player_api_router)
app.include_router(mag_api_router)
app.include_router(enigma2_api_router)
app.include_router(xplugin_api_router)

# --- Reseller API ---
from src.public.controllers.reseller.reseller_api import router as reseller_api_router
app.include_router(reseller_api_router, prefix="/api/reseller")

# --- Streaming Routes ---
from src.public.controllers.api.streaming_routes import router as streaming_router
from src.public.controllers.api.internal_api import router as internal_router

app.include_router(streaming_router)
app.include_router(internal_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/panel/")


@app.get("/panel/{path:path}", response_class=HTMLResponse)
async def admin_panel(request: Request, path: str = ""):
    if templates:
        return templates.TemplateResponse("admin/index.html", {"request": request, "settings": settings})
    return HTMLResponse(content="<h1>IPTV Panel</h1><p>Admin UI available at /panel/</p>")


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
