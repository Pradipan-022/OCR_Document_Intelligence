from abc import ABC, abstractmethod
from app.schemas.ocr_schema import OCREngineResult

class BaseOCREngine(ABC):
    """Abstract interface that all OCR engine wrappers must implement."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def extract(self, image_bytes: bytes) -> OCREngineResult:
        """Extract text, confidence, and bounding boxes from raw image bytes."""
        pass