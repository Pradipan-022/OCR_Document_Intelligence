from typing import Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    """Normalized spatial coordinates for detected text tokens."""
    
    x_min: int = Field(..., description="Top-left X coordinate in pixels")
    y_min: int = Field(..., description="Top-left Y coordinate in pixels")
    x_max: int = Field(..., description="Bottom-right X coordinate in pixels")
    y_max: int = Field(..., description="Bottom-right Y coordinate in pixels")
    polygon: Optional[list[list[int]]] = Field(
        None,
        description="4-corner polygon points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] from EasyOCR/PaddleOCR.",
    )
    
class OCRWord(BaseModel):
    """Single extracted word token with confidence and position."""

    text: str
    confidence: float = Field(..., ge=0.0, le=100.0)
    bbox: BoundingBox
    is_low_confidence: bool = False
    
class OCRBlock(BaseModel):
    """Grouped text line or paragraph with spatial bounds."""

    text: str
    confidence: float
    bbox: BoundingBox
    words: list[OCRWord] = Field(default_factory=list)

class OCREngineResult(BaseModel):
    """Standardized output produced by a single OCR engine execution."""
    engine_name: str
    engine_version: str = "unknown"
    profile_used: Optional[str] = "basic"
    raw_text: str
    average_confidence: float
    execution_time_ms: float
    status: str = "success"  # "success" or "failed"
    error_message: Optional[str] = None
    blocks: list[OCRBlock] = Field(default_factory=list)


class EngineScoreBreakdown(BaseModel):
    """Transparent scoring breakdown based on: Score = 0.40C + 0.20T + 0.20A + 0.10S + 0.10V."""

    engine_name: str
    confidence_score: float  # C: normalized confidence (0-100)
    text_completeness_score: float  # T: non-empty token ratio
    agreement_score: float  # A: cross-engine text match ratio
    speed_score: float  # S: latency performance score
    validation_readiness_score: float  # V: key pattern matching score
    final_score: float
    
class DocumentPageOCRResponse(BaseModel):
    """Aggregated OCR execution payload for a single page."""

    page_id: str
    document_id: str
    page_number: int
    recommended_engine: Optional[str] = None
    engine_scores: list[EngineScoreBreakdown] = []
    consensus_text: Optional[str] = None
    engine_results: list[OCREngineResult] = []