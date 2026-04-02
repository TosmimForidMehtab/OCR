import math

import cv2
import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def deskew_pil_image(pil_image: Image.Image) -> Image.Image:
    settings = get_settings()
    limit = settings.ocr_deskew_limit

    # Convert to grayscale for edge detection
    img = _to_rgb(pil_image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=100,
        maxLineGap=10,
    )

    if lines is None:
        return pil_image

    angles: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 != x1:
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(angle) < limit:
                angles.append(angle)

    if not angles:
        return pil_image

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return pil_image

    logger.debug("image_deskewed_pil", angle_degrees=round(median_angle, 2))
    
    return pil_image.rotate(
        median_angle, 
        resample=Image.Resampling.BICUBIC, 
        expand=True, 
        fillcolor=(255, 255, 255)
    )


def preprocess(pil_image: Image.Image) -> np.ndarray:
    settings = get_settings()

    img = _to_rgb(pil_image)
    img = _upscale_if_small(img, settings.ocr_min_dimension)

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # gray = _binarise(gray)
    
    gray = _denoise(gray)

    logger.debug(
        "image_preprocessed",
        shape=gray.shape,
        dtype=str(gray.dtype),
    )
    return gray

def _to_rgb(image: Image.Image) -> np.ndarray:
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    return np.array(image, dtype=np.uint8)


def _upscale_if_small(img: np.ndarray, min_dim: int) -> np.ndarray:
    h, w = img.shape[:2]
    shorter = min(h, w)
    if shorter >= min_dim:
        return img

    scale = min_dim / shorter
    new_w, new_h = int(w * scale), int(h * scale)
    upscaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    logger.debug("image_upscaled", original=(w, h), resized=(new_w, new_h))
    return upscaled


def _binarise(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def _denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)