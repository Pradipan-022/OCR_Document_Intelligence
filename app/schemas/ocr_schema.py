from typing import List, Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    """Normalized spatial coordinates for detected text tokens."""
    
    x_min: int = Field(..., description="Top-left X coordinate in pixels")
    y_min: int = Field(..., description="Top-left Y coordinate in pixels")
    x_max: int = Field(..., description="Bottom-right X coordinate in pixels")
    y_max: int = Field(..., description="Bottom-right Y coordinate in pixels")
    
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
    words: List[OCRWord] = []


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
    blocks: List[OCRBlock] = []


class DocumentPageOCRResponse(BaseModel):
    """Aggregated OCR execution payload for a single page."""

    page_id: str
    document_id: str
    page_number: int
    selected_engine: Optional[str] = None
    engine_results: List[OCREngineResult] = []