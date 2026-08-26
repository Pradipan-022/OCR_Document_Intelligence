import time
from typing import Any, Optional

import cv2
import numpy as np
from paddleocr import PaddleOCR

from app.core.config import settings
from app.schemas.ocr_schema import (
    BoundingBox,
    OCRBlock,
    OCREngineResult,
    OCRWord,
)
from app.services.ocr.base import BaseOCREngine


class PaddleEngine(BaseOCREngine):
    """
    PaddleOCR 3.x engine adapter using native paddle inference runtime.
    """

    def __init__(
        self,
        lang: str = "en",
        device: str = "cpu",
    ):
        self._lang = lang
        self._device = device
        self._engine: Optional[PaddleOCR] = None

    @property
    def name(self) -> str:
        return "paddleocr"

    @property
    def engine(self) -> PaddleOCR:
        if self._engine is None:
            self._engine = PaddleOCR(
                lang=self._lang,
                device=self._device,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                engine="paddle",  # Directs inference to pure Paddle runtime
            )
        return self._engine

    def get_version(self) -> str:
        try:
            import paddleocr

            return str(getattr(paddleocr, "__version__", "unknown"))
        except Exception:
            return "unknown"

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode image bytes for PaddleOCR engine.")
        return image

    def _extract_result_value(self, result: Any, key: str) -> Any:
        try:
            if isinstance(result, dict):
                return result.get(key)
            return result[key]
        except (KeyError, TypeError, IndexError):
            pass
        return getattr(result, key, None)

    def _parse_results(
        self,
        raw_results: Any,
    ) -> tuple[list[OCRWord], list[float], list[str]]:
        words: list[OCRWord] = []
        confidences: list[float] = []
        texts: list[str] = []

        if raw_results is None:
            return words, confidences, texts

        try:
            results = list(raw_results)
        except TypeError:
            results = [raw_results]

        for result in results:
            rec_texts = self._extract_result_value(result, "rec_texts")
            rec_scores = self._extract_result_value(result, "rec_scores")
            rec_polys = self._extract_result_value(result, "rec_polys")

            if rec_texts is None or rec_scores is None:
                continue

            rec_polys = rec_polys if rec_polys is not None else []

            for index, text in enumerate(rec_texts):
                clean_text = str(text).strip()
                if not clean_text or index >= len(rec_scores):
                    continue

                raw_confidence = float(rec_scores[index])
                normalized_confidence = max(
                    0.0, min(100.0, raw_confidence * 100.0)
                )

                if index >= len(rec_polys) or rec_polys[index] is None:
                    continue

                polygon = [
                    [int(point[0]), int(point[1])]
                    for point in rec_polys[index]
                ]

                if len(polygon) < 4:
                    continue

                xs = [point[0] for point in polygon]
                ys = [point[1] for point in polygon]

                bbox = BoundingBox(
                    x_min=min(xs),
                    y_min=min(ys),
                    x_max=max(xs),
                    y_max=max(ys),
                    polygon=polygon,
                )

                is_low_confidence = (
                    normalized_confidence < settings.LOW_CONFIDENCE_THRESHOLD
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

    def _build_ocr_blocks(
        self,
        words: list[OCRWord],
    ) -> list[OCRBlock]:
        if not words:
            return []

        sorted_words = sorted(
            words,
            key=lambda word: (word.bbox.y_min, word.bbox.x_min),
        )

        lines: list[list[OCRWord]] = []

        for word in sorted_words:
            placed = False
            word_y = word.bbox.y_min

            for line in lines:
                line_y = float(np.mean([w.bbox.y_min for w in line]))
                if abs(word_y - line_y) < 15:
                    line.append(word)
                    placed = True
                    break

            if not placed:
                lines.append([word])

        blocks: list[OCRBlock] = []

        for line_words in lines:
            line_words.sort(key=lambda word: word.bbox.x_min)
            text = " ".join(word.text for word in line_words)
            confidence = float(
                np.mean([word.confidence for word in line_words])
            )

            bbox = BoundingBox(
                x_min=min(w.bbox.x_min for w in line_words),
                y_min=min(w.bbox.y_min for w in line_words),
                x_max=max(w.bbox.x_max for w in line_words),
                y_max=max(w.bbox.y_max for w in line_words),
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
        start_time = time.perf_counter()
        version_str = self.get_version()

        try:
            image = self._decode_image(image_bytes)

            if hasattr(self.engine, "predict"):
                raw_results = self.engine.predict(image)
            else:
                raw_results = self.engine.ocr(image)

            words, confidences, texts = self._parse_results(raw_results)
            average_confidence = (
                float(np.mean(confidences)) if confidences else 0.0
            )

            blocks = self._build_ocr_blocks(words)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return OCREngineResult(
                engine_name=self.name,
                engine_version=version_str,
                profile_used=profile_name,
                raw_text=" ".join(texts),
                average_confidence=round(average_confidence, 2),
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