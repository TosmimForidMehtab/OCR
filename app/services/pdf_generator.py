from __future__ import annotations

import io
import unicodedata
from pathlib import Path

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.core.config import get_settings
from app.core.exceptions import PDFGenerationError
from app.core.logging import get_logger
from app.models.schemas import OCRResult

logger = get_logger(__name__)

_PT = 1.0


def _register_fonts(fonts_dir: Path, font_name: str) -> None:
    if font_name in pdfmetrics.getRegisteredFontNames():
        return

    regular = fonts_dir / f"{font_name}-Regular.ttf"
    if not regular.exists():
        raise PDFGenerationError(
            f"Required font not found: {regular}. "
            f"Please place {font_name}-Regular.ttf in assets/fonts/."
        )

    pdfmetrics.registerFont(TTFont(font_name, str(regular)))
    logger.info("font_registered", font=font_name, path=str(regular))


def generate_searchable_pdf(
    original_image: Image.Image,
    ocr_result: OCRResult,
) -> bytes:
    
    settings = get_settings()

    try:
        _register_fonts(settings.fonts_dir, settings.pdf_font_name)
    except PDFGenerationError:
        raise
    except Exception as exc:
        raise PDFGenerationError(f"Font registration failed: {exc}") from exc

    try:
        return _build_pdf(original_image, ocr_result, settings)
    except PDFGenerationError:
        raise
    except Exception as exc:
        logger.exception("pdf_generation_failed", error=str(exc))
        raise PDFGenerationError(f"PDF generation failed: {exc}") from exc


def _build_pdf(image: Image.Image, ocr_result: OCRResult, settings: any) -> bytes:
    orig_w, orig_h = image.size
    font_name = settings.pdf_font_name

    x_scale = orig_w / ocr_result.processed_width if ocr_result.processed_width else 1.0
    y_scale = (
        orig_h / ocr_result.processed_height if ocr_result.processed_height else 1.0
    )

    page_w = float(orig_w) * _PT
    page_h = float(orig_h) * _PT

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    # 1. Visual Layer: The original image
    img_buffer = io.BytesIO()
    rgb_image = image.convert("RGB") if image.mode != "RGB" else image
    rgb_image.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    c.drawImage(
        ImageReader(img_buffer),
        x=0,
        y=0,
        width=page_w,
        height=page_h,
        preserveAspectRatio=False,
    )

    # 2. Text Layer: Searchable Overlay
    for word in ocr_result.words:
        clean_text = word.text.strip()
        if not clean_text:
            continue

        bbox = word.bbox
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]

        x_min, x_max = min(xs) * x_scale, max(xs) * x_scale
        y_min, y_max = min(ys) * y_scale, max(ys) * y_scale

        box_w = x_max - x_min
        box_h = y_max - y_min

        # Convert top-down image coords to bottom-up PDF coords
        pdf_x = x_min * _PT
        
        # Nudge the baseline up by ~20% to account for font descenders
        pdf_y = (orig_h - y_max) * _PT + (box_h * _PT * 0.2)

        # Dynamically size font to match box height
        font_size = max(4.0, box_h * _PT * 0.85)

        text_obj = c.beginText(pdf_x, pdf_y)
        text_obj.setFont(font_name, font_size)
        text_obj.setTextRenderMode(3)  # Invisible (but searchable/selectable)

        # Calculate actual text width and force horizontal scaling
        text_width = c.stringWidth(clean_text, font_name, font_size)
        if text_width > 0:
            scale_percentage = (box_w * _PT / text_width) * 100.0
            text_obj.setHorizScale(scale_percentage)

        text_obj.textOut(clean_text)
        c.drawText(text_obj)

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes