import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pathlib import Path
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter
from app.models.base import Base, engine
from app.api.public import router as public_router
from app.api.admin import router as admin_router
from app.views.pages import router as pages_router
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.environment == "production" and not settings.encryption_master_key:
        logger.warning(
            "ENCRYPTION_MASTER_KEY not set — falling back to ADMIN_SESSION_SECRET derivation. "
            "Set an explicit key in production for stronger security."
        )
    yield


app = FastAPI(title="Odoo Pulse", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

app.include_router(pages_router)
app.include_router(public_router)
app.include_router(admin_router)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "No encontrado"})


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})
