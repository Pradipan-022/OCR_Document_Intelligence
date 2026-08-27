import asyncio
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document_model import Document, StatusEnum
from app.models.ocr_model import OCREngineResultModel, OCRBlockModel, OCRWordModel
from app.services.ocr.tesseract_engine import TesseractEngine
from app.services.ocr.easyocr_engine import EasyOCREngine
from app.services.ocr.paddle_engine import PaddleEngine
from app.services.ocr.consensus import OCRConsensusEngine
from app.services.extraction.extractor import MetadataAndTableExtractor
from app.services.extraction.business_rules import BusinessValidationEngine

class DocumentPipelineOrchestrator:
    def __init__(self):
        self.tesseract = TesseractEngine()
        self.easyocr = EasyOCREngine()
        self.paddle = PaddleEngine()
        self.consensus_engine = OCRConsensusEngine()
        self.extractor = MetadataAndTableExtractor()
        self.validator = BusinessValidationEngine()

    def _run_single_engine(self, engine, image_path: str) -> dict:
        """Helper to run an individual OCR engine on disk image."""
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            result = engine.extract(image_bytes)
            
            return {
                "text": result.raw_text,
                "avg_confidence": result.average_confidence,
                "duration_seconds": result.execution_time_ms / 1000.0,
                "blocks": [block.model_dump() if hasattr(block, 'model_dump') else block.dict() for block in result.blocks],
                "status": result.status,
                "error": result.error_message
            }
        except Exception as e:
            return {"text": "", "avg_confidence": 0.0, "duration_seconds": 0.0, "error": str(e), "blocks": []}
        
    def _update_progress(self, db: Session, doc: Document, percent: int, step_description: str):
        doc.ocr_results = {
            "progress": percent,
            "current_step": step_description
        }
        db.commit()

    def execute_pipeline(self, document_id: str):
        """Main background job executing end-to-end processing and database persistence."""
        db: Session = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return

            doc.status = StatusEnum.PROCESSING
            db.commit()
            self._update_progress(db, doc, 15, "Analyzing image quality & running preprocessing")

            all_page_results = []
            full_document_text = ""
            primary_tokens = []

            for page in doc.pages:
                # 1. Parallel OCR Execution
                with ThreadPoolExecutor(max_workers=3) as executor:
                    f_tess = executor.submit(self._run_single_engine, self.tesseract, page.image_path)
                    f_easy = executor.submit(self._run_single_engine, self.easyocr, page.image_path)
                    f_pad  = executor.submit(self._run_single_engine, self.paddle, page.image_path)

                    raw_ocr = {
                        "tesseract": f_tess.result(),
                        "easyocr": f_easy.result(),
                        "paddle": f_pad.result()
                    }

                # 2. Consensus Engine
                consensus_output = self.consensus_engine.select_best_and_merge(raw_ocr)
                
                # Update DocumentPage quality score
                page.quality_score = consensus_output["engine_scores"][consensus_output["recommended_engine"]]
                
                # 3. Relational Database Persistence for OCR Engine Results, Blocks, & Words
                for engine_name, engine_data in raw_ocr.items():
                    engine_row = OCREngineResultModel(
                        page_id=page.id,
                        engine_name=engine_name,
                        profile_used=page.quality.applied_profile if page.quality else None,
                        raw_text=engine_data.get("text", ""),
                        average_confidence=engine_data.get("avg_confidence", 0.0),
                        execution_time_ms=engine_data.get("duration_seconds", 0.0) * 1000.0,
                        status=engine_data.get("status", "SUCCESS"),
                        error_message=engine_data.get("error")
                    )
                    db.add(engine_row)
                    db.flush()  # Generate engine_row.id for child FKs

                    for block in engine_data.get("blocks", []):
                        bbox = block.get("bbox", {}) if isinstance(block.get("bbox"), dict) else {}
                        block_row = OCRBlockModel(
                            engine_result_id=engine_row.id,
                            text=block.get("text", ""),
                            confidence=block.get("confidence", 0.0),
                            x_min=bbox.get("x_min", block.get("x_min", 0)),
                            y_min=bbox.get("y_min", block.get("y_min", 0)),
                            x_max=bbox.get("x_max", block.get("x_max", 0)),
                            y_max=bbox.get("y_max", block.get("y_max", 0))
                        )
                        db.add(block_row)
                        db.flush()  # Generate block_row.id for word FKs

                        for word in block.get("words", []):
                            w_bbox = word.get("bbox", {}) if isinstance(word.get("bbox"), dict) else {}
                            confidence_val = word.get("confidence", 0.0)
                            word_row = OCRWordModel(
                                block_id=block_row.id,
                                text=word.get("text", ""),
                                confidence=confidence_val,
                                is_low_confidence=confidence_val < 0.60,
                                x_min=w_bbox.get("x_min", word.get("x_min", 0)),
                                y_min=w_bbox.get("y_min", word.get("y_min", 0)),
                                x_max=w_bbox.get("x_max", word.get("x_max", 0)),
                                y_max=w_bbox.get("y_max", word.get("y_max", 0))
                            )
                            db.add(word_row)

                            # Collect tokens from recommended engine on page 1 for table extraction
                            if engine_name == consensus_output["recommended_engine"] and page.page_number == 1:
                                primary_tokens.append({
                                    "text": word.get("text", ""),
                                    "bbox": [
                                        w_bbox.get("x_min", word.get("x_min", 0)),
                                        w_bbox.get("y_min", word.get("y_min", 0)),
                                        w_bbox.get("x_max", word.get("x_max", 0)),
                                        w_bbox.get("y_max", word.get("y_max", 0))
                                    ]
                                })

                full_document_text += "\n" + consensus_output["merged_text"]
                all_page_results.append(consensus_output)

            self._update_progress(db, doc, 60, "Running parallel OCR engines (Tesseract, EasyOCR, Paddle)")
            # 4. Key-Value & Line-Item Extraction
            extracted_fields = self.extractor.extract_key_values(full_document_text)
            line_items = self.extractor.extract_line_item_table(primary_tokens)

            self._update_progress(db, doc, 85, "Extracting line items and validating business rules")
            # 5. Business Rules & Math Validation
            validation_report = self.validator.validate_document(extracted_fields, line_items)

            # 6. Aggregated JSON payload directly into Document model
            doc.ocr_results = {
                "pages": all_page_results,
                "extracted_fields": extracted_fields,
                "line_items": line_items,
                "validation": validation_report,
                "audit_trail": []
            }
            doc.status = StatusEnum.COMPLETED
            db.commit()

        except Exception as err:
            db.rollback()
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = StatusEnum.FAILED
                db.commit()
            raise err
        finally:
            db.close()