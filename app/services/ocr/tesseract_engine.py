import time
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from typing import Any

from app.schemas.ocr_schema import BoundingBox, OCRBlock, OCRWord, OCREngineResult
from app.services.ocr.base import BaseOCREngine
from app.core.config import settings

class TesseractEngine(BaseOCREngine):
    
    @property
    def name(self) -> str:
        return "tesseract"
    
    def get_version(self) -> str:
        """Retrieves installed Tesseract binary version."""
        try:
            return str(pytesseract.get_tesseract_version())
        except Exception:
            return "unknown"
    
    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        """Helper 1: Decodes raw image byte streams into an OpenCV array."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image bytes for Tesseract engine.")
        return img
    
    def _parse_words_by_block(
        self, data: dict[str, Any]     
    ) -> tuple[dict[int, list[OCRWord]], list[float], list[str]]:
        """Helper 2: Parses pytesseract output dict into structured OCRWord instances

        grouped by block_num.
        """
        grouped_blocks: dict[int, list[OCRWord]] = {}
        all_confidences: list[float] = []
        all_texts: list[str] = []

        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if not text:
                continue

            raw_conf = float(data["conf"][i])
            normalized_conf = max(0.0, raw_conf)
            is_low = raw_conf < settings.LOW_CONFIDENCE_THRESHOLD

            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i],
                data["height"][i],
            )
            bbox = BoundingBox(x_min=x, y_min=y, x_max=x + w, y_max=y + h)

            word_obj = OCRWord(
                text=text,
                confidence=round(normalized_conf, 2),
                bbox=bbox,
                is_low_confidence=is_low,
            )

            block_num = data["block_num"][i]
            if block_num not in grouped_blocks:
                grouped_blocks[block_num] = []

            grouped_blocks[block_num].append(word_obj)
            all_confidences.append(normalized_conf)
            all_texts.append(text)

        return grouped_blocks, all_confidences, all_texts

    def _build_ocr_blocks(
        self, grouped_blocks: dict[int, list[OCRWord]]
    ) -> list[OCRBlock]:
        """Helper 3: Aggregates grouped words into bounding OCRBlocks."""
        blocks: list[OCRBlock] = []
        for words in grouped_blocks.values():
            if not words:
                continue

            block_text = " ".join(w.text for w in words)
            block_conf = float(np.mean([w.confidence for w in words]))
            block_bbox = BoundingBox(
                x_min=min(w.bbox.x_min for w in words),
                y_min=min(w.bbox.y_min for w in words),
                x_max=max(w.bbox.x_max for w in words),
                y_max=max(w.bbox.y_max for w in words),
            )
            blocks.append(
                OCRBlock(
                    text=block_text,
                    confidence=round(block_conf, 2),
                    bbox=block_bbox,
                    words=words,
                )
            )
        return blocks

    def extract(
        self, image_bytes: bytes, profile_name: str = "basic"
    ) -> OCREngineResult:
        """Extracts OCR tokens from raw image bytes and returns structured schema results."""
        start_time = time.perf_counter()
        version_str = self.get_version()

        try:
            img = self._decode_image(image_bytes)
            data = pytesseract.image_to_data(img, output_type=Output.DICT)
            grouped_blocks, confidences, texts = self._parse_words_by_block(data)
            blocks = self._build_ocr_blocks(grouped_blocks)

            avg_conf = float(np.mean(confidences)) if confidences else 0.0
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return OCREngineResult(
                engine_name=self.name,
                engine_version=version_str,
                profile_used=profile_name,
                raw_text=" ".join(texts),
                average_confidence=round(avg_conf, 2),
                execution_time_ms=round(elapsed_ms, 2),
                status="success",
                blocks=blocks,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return OCREngineResult(
                engine_name=self.name,
                engine_version=version_str,
                profile_used=profile_name,
                raw_text="",
                average_confidence=0.0,
                execution_time_ms=round(elapsed_ms, 2),
                status="failed",
                error_message=str(exc),
                blocks=[],
            )