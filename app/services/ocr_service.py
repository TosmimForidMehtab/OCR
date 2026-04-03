from __future__ import annotations

import pytesseract
from pytesseract import Output
import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import OCRProcessingError
from app.core.logging import get_logger
from app.models.schemas import OCRResult, OCRWord
from app.services.image_processor import preprocess, deskew_pil_image
from app.services.pdf_generator import generate_searchable_pdf

logger = get_logger(__name__)


def process_image_to_pdf(
    image_content: bytes,
    reader: any = None,
    settings: any = None,
    langs: list[str] | None = None,
) -> tuple[bytes, OCRResult]:
    import io
    from PIL import Image

    # 1. Load image
    pil_image = Image.open(io.BytesIO(image_content))
    pil_image.load()

    # 2. Deskew
    pil_image = deskew_pil_image(pil_image)

    # 3. Run OCR
    ocr_result = run_ocr(pil_image, settings=settings, langs=langs)

    # 4. Generate Searchable PDF
    pdf_bytes = generate_searchable_pdf(pil_image, ocr_result)

    return pdf_bytes, ocr_result


def run_ocr(
    image: Image.Image, 
    settings: any = None, 
    langs: list[str] | None = None
) -> OCRResult:
    if settings is None:
        settings = get_settings()
    
    if langs is None:
        langs = settings.lang_list
    
    original_w, original_h = image.size

    try:
        processed: np.ndarray = preprocess(image)
        # Convert back to PIL for pytesseract if it was processed as numpy
        # Preprocess returns a grayscale or binary image
        processed_pil = Image.fromarray(processed)
        
        tess_langs = "+".join(langs)
        data = pytesseract.image_to_data(
            processed_pil, 
            lang=tess_langs, 
            output_type=Output.DICT
        )
    except Exception as exc:
        logger.exception("ocr_inference_failed", error=str(exc))
        raise OCRProcessingError(f"OCR inference failed: {exc}") from exc

    words: list[OCRWord] = []
    threshold_percent = settings.ocr_confidence_threshold * 100

    n_boxes = len(data["text"])
    for i in range(n_boxes):
        # level 5 is 'word' level
        if int(data["level"][i]) == 5:
            text = data["text"][i].strip()
            confidence = float(data["conf"][i])
            
            if not text or confidence < threshold_percent:
                continue
            
            # Convert tesseract left,top,w,h to EasyOCR-style 4-point bbox
            l, t, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            bbox = [
                [float(l), float(t)],
                [float(l + w), float(t)],
                [float(l + w), float(t + h)],
                [float(l), float(t + h)]
            ]
            
            words.append(OCRWord(
                text=text, 
                confidence=confidence / 100.0, 
                bbox=bbox
            ))

    words = _sort_into_lines(
        words,
        image_height=processed.shape[0],
        group_ratio=settings.ocr_line_group_ratio,
    )

    logger.info(
        "ocr_complete",
        total_detections=n_boxes,
        accepted=len(words),
    )

    processed_h, processed_w = processed.shape[:2]
    return OCRResult(
        words=words,
        image_width=original_w,
        image_height=original_h,
        processed_width=processed_w,
        processed_height=processed_h,
    )


def _bbox_top_left(word: OCRWord) -> tuple[float, float]:
    """Helper to get the anchor point of a word's bounding box."""
    xs = [pt[0] for pt in word.bbox]
    ys = [pt[1] for pt in word.bbox]
    return min(xs), min(ys)


def _sort_into_lines(
    words: list[OCRWord],
    image_height: int,
    group_ratio: float,
) -> list[OCRWord]:
    if not words:
        return words

    line_threshold = image_height * group_ratio

    words.sort(key=lambda w: (_bbox_top_left(w)[1], _bbox_top_left(w)[0]))

    lines: list[list[OCRWord]] = []
    current_line: list[OCRWord] = [words[0]]
    current_y = _bbox_top_left(words[0])[1]

    for word in words[1:]:
        _, y = _bbox_top_left(word)
        if abs(y - current_y) <= line_threshold:
            current_line.append(word)
        else:
            lines.append(sorted(current_line, key=lambda w: _bbox_top_left(w)[0]))
            current_line = [word]
            current_y = y

    lines.append(sorted(current_line, key=lambda w: _bbox_top_left(w)[0]))

    return [word for line in lines for word in line]