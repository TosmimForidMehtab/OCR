from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class OCRWord(BaseModel):

    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[list[float]]


class OCRResult(BaseModel):

    words: list[OCRWord]
    image_width: int
    image_height: int
    processed_width: int
    processed_height: int
