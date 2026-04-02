import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class OCRBackendError(Exception):

    http_status: int = 500
    error_code: str = "InternalError"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedFileTypeError(OCRBackendError):
    http_status = 422
    error_code = "UnsupportedFileTypeError"


class FileTooLargeError(OCRBackendError):
    http_status = 413
    error_code = "FileTooLargeError"


class OCRProcessingError(OCRBackendError):
    http_status = 500
    error_code = "OCRProcessingError"


class PDFGenerationError(OCRBackendError):
    http_status = 500
    error_code = "PDFGenerationError"



def _error_response(request: Request, exc: OCRBackendError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "request_id": request.state.request_id,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnsupportedFileTypeError)
    async def handle_unsupported_file(
        request: Request, exc: UnsupportedFileTypeError
    ) -> JSONResponse:
        return _error_response(request, exc)

    @app.exception_handler(FileTooLargeError)
    async def handle_file_too_large(
        request: Request, exc: FileTooLargeError
    ) -> JSONResponse:
        return _error_response(request, exc)

    @app.exception_handler(OCRProcessingError)
    async def handle_ocr_error(
        request: Request, exc: OCRProcessingError
    ) -> JSONResponse:
        return _error_response(request, exc)

    @app.exception_handler(PDFGenerationError)
    async def handle_pdf_error(
        request: Request, exc: PDFGenerationError
    ) -> JSONResponse:
        return _error_response(request, exc)

    @app.exception_handler(OCRBackendError)
    async def handle_generic(
        request: Request, exc: OCRBackendError
    ) -> JSONResponse:
        return _error_response(request, exc)
