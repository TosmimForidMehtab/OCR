from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup_begin", langs=settings.lang_list)

    # Tesseract does not require a persistent reader object
    app.state.ocr_reader = None

    logger.info("service_ready", langs=settings.lang_list)
    yield

    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="OCR Backend",
        description=(
            "Accepts a JPG/PNG image, extracts text via Tesseract "
            "(English, Hindi, Marathi), and returns a searchable PDF."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())[:8]
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    register_exception_handlers(app)

    from app.api.v1.routes.ocr import router as ocr_router

    app.include_router(ocr_router, prefix="/api/v1")

    return app


app = create_app()
