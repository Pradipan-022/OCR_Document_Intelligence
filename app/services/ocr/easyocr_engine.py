import time
from typing import Optional

import cv2
import easyocr
import numpy as np

from app.core.config import settings
from app.schemas.ocr_schema import(
    BoundingBox,
    OCRBlock,
    OCREngineResult,
    OCRWord,
)
from app.services.ocr.base import BaseOCREngine

class EasyOCREngine(BaseOCREngine):
    """
    EasyOCR engine adapter.

    Uses CPU by default, lazy-loads the EasyOCR Reader,
    preserves EasyOCR polygon coordinates, and normalizes
    confidence scores to the application's 0-100 scale.
    """
    
    def __init__(
        self,
        languages: Optional[list[str]] = None,
        gpu:bool = False,
        ):
        self._languages = languages or ["en"]
        self._gpu = gpu
        self._reader: Optional[easyocr.Reader] = None
        
    @property
    def name(self) -> str:
        return "easyocr"
    
    @property
    def reader(self) -> easyocr.Reader:
        """
        Lazily initialize the EasyOCR Reader.

        The Reader loads the detection and recognition models,
        so it should only be initialized once and reused.
        """
        if self._reader is None:
            self._reader = easyocr.Reader(
                self._languages,
                gpu=self._gpu
            )
        return self._reader
    
    def get_version(self) -> str:
        """Return the installed EasyOCR version."""
        try:
            return str(easyocr.__version__)
        except AttributeError:
            return "unknown"
    
    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        """Convert raw image bytes into an OpenCV image."""
        nparr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(
            nparr,
            cv2.IMREAD_COLOR,
        )
        
    def _parse_results(
        self,
        raw_results: list,
    ) -> tuple[list[OCRWord], list[float], list[str]]:
        """
        Convert EasyOCR results into application OCRWord objects.

        EasyOCR returns:
            (polygon, text, confidence)

        EasyOCR confidence is normalized from:
            0.0 - 1.0

        Application confidence:
            0.0 - 100.0
        """
        
        words: list[OCRWord] = []
        confidences: list[float] = []
        texts: list[str] = []
        
        for polygon_points, text, raw_confidence in raw_results:
            clean_text = text.strip()
            if not clean_text:
                continue
            
            #   EasyOCR confidence: 0.0 -> 1.0
            # Application confidence: 0.0 -> 100.0   
            normalized_confidence = max(
                0.0, min(100.0, float(raw_confidence) * 100.0)
            )
            is_low_confidence = (
                normalized_confidence < settings.LOW_CONFIDENCE_THRESHOLD
            )
            polygon = [
                [int(point[0]), int(point[1])]
                for point in polygon_points
            ]
            xs = [point[0] for point in polygon]
            ys = [point[1] for point in polygon]
            
            bbox = BoundingBox(
                x_min=min(xs),
                y_min=min(ys),
                x_max=max(xs),
                y_max=max(ys),
                polygon=polygon,
            )
            
            word = OCRWord(
                text=clean_text,
                confidence=round(normalized_confidence, 2),
                bbox=bbox,
                is_low_confidence=is_low_confidence,
            )
            
            words.append(word)
            confidences.append(normalized_confidence)
            texts.append(clean_text)
            
        return words, confidences, texts
    
    def _build_ocr_block(
        self,
        words: list[OCRWord],
    ) -> list[OCRBlock]:
        
        if not words:
            return []
        
        # Sort roughly top-to-bottom, then left-to-right
        sorted_words = sorted(
            words,
            key=lambda word: (
                word.bbox.y_min,
                word.bbox.x_min,    
            ),
        )
        
        lines: list[list[OCRWord]] = []
        
        for word in sorted_words:
            placed = False
            word_y = word.bbox.y_min
            
            for line in lines:
                line_y = np.mean(
                    [w.bbox.y_min for w in line]
                )
                
                if abs(word_y - line_y) < 15:
                    line.append(word)
                    placed = True
                    break
            if not placed:
                lines.append([word])
                
        blocks: list[OCRBlock] = []
        
        for line_words in lines:
            line_words.sort(
                key=lambda word: word.bbox.x_min
            )
            
            text = " ".join(
                word.text for word in line_words
            )
            
            confidence = float(
                np.mean([word.confidence for word in line_words])
            )
            bbox = BoundingBox(
                x_min=min(
                    w.bbox.x_min for w in line_words
                ),
                y_min=min(
                    w.bbox.y_min for w in line_words
                ),
                x_max=max(
                    w.bbox.x_max for w in line_words
                ),
                y_max=max(
                    w.bbox.y_max for w in line_words
            ),
            )
            
            blocks.append(
                OCRBlock(
                    text=text,
                    confidence=round(confidence, 2),
                    bbox=bbox,
                    words=line_words,
                )
            )
        return blocks
    
    def extract(
        self,
        image_bytes: bytes,
        profile_name: str = "basic",
    ) -> OCREngineResult:
        """
        Execute EasyOCR on an image and return standardized OCR output.
        """

        start_time = time.perf_counter()
        version_str = self.get_version()

        try:
            image = self._decode_image(image_bytes)

            raw_results = self.reader.readtext(
                image,
                detail=1,
            )

            words, confidences, texts = self._parse_results(
                raw_results
            )

            average_confidence = (
                float(np.mean(confidences))
                if confidences
                else 0.0
            )

            blocks = self._build_ocr_blocks(words)

            elapsed_ms = (
                time.perf_counter() - start_time
            ) * 1000

            return OCREngineResult(
                engine_name=self.name,
                engine_version=version_str,
                profile_used=profile_name,
                raw_text=" ".join(texts),
                average_confidence=round(
                    average_confidence,
                    2,
                ),
                execution_time_ms=round(
                    elapsed_ms,
                    2,
                ),
                status="success",
                blocks=blocks,
            )

        except Exception as exc:
            elapsed_ms = (
                time.perf_counter() - start_time
            ) * 1000

            return OCREngineResult(
                engine_name=self.name,
                engine_version=version_str,
                profile_used=profile_name,
                raw_text="",
                average_confidence=0.0,
                execution_time_ms=round(
                    elapsed_ms,
                    2,
                ),
                status="failed",
                error_message=str(exc),
                blocks=[],
            )
            