import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import magic

from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError

_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def validate_image_upload(filename: str, content: bytes) -> None:
    """
    Validate that the uploaded file is an allowed image type and within
    the configured size limit. Raises domain exceptions on failure.
    """
    settings = get_settings()

    # Size check
    size = len(content)
    if size > settings.max_upload_size_bytes:
        limit_mb = settings.max_upload_size_mb
        raise FileTooLargeError(
            f"File size {size / 1_048_576:.1f} MB exceeds the {limit_mb} MB limit."
        )

    # Extension check
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"File extension '{suffix}' is not supported. "
            f"Accepted: {sorted(_ALLOWED_EXTENSIONS)}"
        )

    
    mime = magic.from_buffer(content, mime=True)
    if mime not in _ALLOWED_MIME_TYPES:
        raise UnsupportedFileTypeError(
            f"Detected MIME type '{mime}' is not supported. "
            f"Accepted: {sorted(_ALLOWED_MIME_TYPES)}"
        )


@contextmanager
def temp_image_file(content: bytes, suffix: str = ".png") -> Generator[Path, None, None]:
    """
    Write image bytes to a named temp file and yield its Path.
    The file is deleted automatically when the context exits, even on error.
    """
    settings = get_settings()
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        dir=settings.temp_dir,
        suffix=suffix,
        delete=True,
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        yield Path(tmp.name)
