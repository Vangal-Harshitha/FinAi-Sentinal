"""
main.py  —  FinAI FastAPI Application Entry Point (Phase 9 Integrated)
"""
import traceback

try:
    print("STARTING APP...")
except Exception as e:
    print("EARLY ERROR:", e)
    traceback.print_exc()
    raise e
import sys, time
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import traceback

try:
    from fastapi import FastAPI, Request, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from loguru import logger

    from api.routes import ai, auth, goals, receipts, transactions, voice, fraud
    from core.config import get_settings
    from db.database import engine
    from models.orm import Base

except Exception as e:
    print("IMPORT ERROR:", e)
    traceback.print_exc()
    raise e
try:
    settings = get_settings()
except Exception as e:
    print("CONFIG ERROR:", e)
    traceback.print_exc()
    raise e

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ Database tables verified")

    try:
        from services.ml_registry import model_registry
        await model_registry.load_all()
        logger.info("🤖 ML models loaded")
    except Exception as e:
        logger.warning(f"⚠️ ML models not fully loaded: {e}")

    yield

    logger.info("🛑 Shutting down")
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FinAI – Intelligent Personal Finance Management System (Phase 9)",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({ms}ms)")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)},
    )


PREFIX = "/api/v1"
app.include_router(auth.router,         prefix=PREFIX)
app.include_router(transactions.router, prefix=PREFIX)
app.include_router(receipts.router,     prefix=PREFIX)
app.include_router(voice.router,        prefix=PREFIX)
app.include_router(goals.router,        prefix=PREFIX)
app.include_router(ai.router,           prefix=PREFIX)
app.include_router(fraud.router,        prefix=PREFIX)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API", "docs": "/docs"}
