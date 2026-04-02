from __future__ import annotations

import io

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import HealthResponse
from app.services.ocr_service import process_image_to_pdf
from app.utils.file_utils import validate_image_upload

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


def _validate_langs(langs_param: str | None) -> list[str]:
    supported = {"en", "hi", "mr"}
    if not langs_param:
        return settings.lang_list

    requested = [c.strip().lower() for c in langs_param.split(",") if c.strip()]
    invalid = set(requested) - supported
    if invalid:
        from app.core.exceptions import UnsupportedFileTypeError
        raise UnsupportedFileTypeError(f"Unsupported language codes: {invalid}")
    return requested


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")


@router.post("/ocr/extract", tags=["ocr"])
async def extract(
    request: Request,
    file: UploadFile,
    langs: str | None = None,
) -> StreamingResponse:
    request_id = request.state.request_id
    lang_list = _validate_langs(langs)
    content = await file.read()
    filename = file.filename or "upload"

    logger.info(
        "ocr_request_received",
        request_id=request_id,
        filename=filename,
        langs=lang_list,
    )

    # 1. Validation
    validate_image_upload(filename, content)

    # 2. Orchestration (Processing -> OCR -> PDF)
    pdf_bytes, ocr_result = process_image_to_pdf(
        image_content=content,
        reader=request.app.state.ocr_reader,
        settings=settings,
    )

    # 3. Stream result
    stem = filename.rsplit(".", 1)[0]
    output_filename = f"{stem}_ocr.pdf"

    logger.info(
        "ocr_request_complete",
        request_id=request_id,
        words_found=len(ocr_result.words),
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"',
            "X-Request-Id": request_id,
        },
    )
