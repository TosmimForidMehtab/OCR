from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SUPPORTED_LANGS = {"en", "hi", "mr"}
_BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = False

    # OCR Tuning
    ocr_default_langs: str = "en"
    ocr_confidence_threshold: float = 0.4
    ocr_gpu: bool = False
    ocr_line_group_ratio: float = 0.015
    ocr_min_dimension: int = 1000
    ocr_deskew_limit: int = 45

    # PDF Output
    pdf_font_name: str = "NotoSans"
    pdf_font_size: int = 11
    pdf_text_opacity: float = 0.0

    # File handling
    max_upload_size_mb: int = 10
    temp_dir: Path = Path("/tmp/ocr_uploads")

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Derived — not set from env
    assets_dir: Path = _BASE_DIR / "assets"
    fonts_dir: Path = _BASE_DIR / "assets" / "fonts"

    @field_validator("ocr_default_langs")
    @classmethod
    def validate_langs(cls, value: str) -> str:
        langs = [lang.strip() for lang in value.split(",") if lang.strip()]
        if not langs:
            raise ValueError("ocr_default_langs must contain at least one language code.")
        unsupported = set(langs) - _SUPPORTED_LANGS
        if unsupported:
            raise ValueError(
                f"Unsupported language code(s): {unsupported}. "
                f"Supported: {_SUPPORTED_LANGS}"
            )
        return ",".join(langs)

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, value: str) -> str:
        if value not in {"json", "text"}:
            raise ValueError("log_format must be 'json' or 'text'.")
        return value

    @property
    def lang_list(self) -> list[str]:
        return [lang.strip() for lang in self.ocr_default_langs.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
