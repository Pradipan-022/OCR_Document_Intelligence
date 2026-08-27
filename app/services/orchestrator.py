import asyncio
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document_model import Document, StatusEnum
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
            # 1. Read file as bytes
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            # 2. Call the correct interface
            result = engine.extract(image_bytes)
            
            # 3. Map the OCREngineResult Pydantic model to the dict expected by OCRConsensusEngine
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

    def execute_pipeline(self, document_id: str):
        """Main background job executing end-to-end processing."""
        db: Session = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return

            doc.status = StatusEnum.PROCESSING
            db.commit()

            all_page_results = []
            full_document_text = ""

            for page in doc.pages:
                # 1. Parallel OCR Execution via ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=3) as executor:
                    f_tess = executor.submit(self._run_single_engine, self.tesseract, page.image_path)
                    f_easy = executor.submit(self._run_single_engine, self.easyocr, page.image_path)
                    f_pad  = executor.submit(self._run_single_engine, self.paddle, page.image_path)

                    raw_ocr = {
                        "tesseract": f_tess.result(),
                        "easyocr": f_easy.result(),
                        "paddle": f_pad.result()
                    }

                # 2. Consensus & Engine Scoring
                consensus_output = self.consensus_engine.select_best_and_merge(raw_ocr)
                
                # Update page record with OCR metrics
                page.quality_score = consensus_output["engine_scores"][consensus_output["recommended_engine"]]
                page.page_ocr_results = consensus_output
                
                full_document_text += "\n" + consensus_output["merged_text"]
                all_page_results.append(consensus_output)

            # 3. Key-Value Metadata & Line-Item Table Extraction
            extracted_fields = self.extractor.extract_key_values(full_document_text)
            
            # Extract line items using tokens from best engine on page 1
            best_engine_data = all_page_results[0]["raw_engine_data"][all_page_results[0]["recommended_engine"]]
            
            # Flatten blocks/words into the simple dictionary format expected by the extractor
            primary_tokens = []
            for block in best_engine_data.get("blocks", []):
                for word in block.get("words", []):
                    primary_tokens.append({
                        "text": word["text"],
                        "bbox": [
                            word["bbox"]["x_min"],
                            word["bbox"]["y_min"],
                            word["bbox"]["x_max"],
                            word["bbox"]["y_max"]
                        ]
                    })

            line_items = self.extractor.extract_line_item_table(primary_tokens)

            # 4. Business Rule & Math Validation
            validation_report = self.validator.validate_document(extracted_fields, line_items)

            # 5. Persist Output Payload to Document DB Model
            doc.ocr_results = {
                "pages": all_page_results,
                "extracted_fields": extracted_fields,
                "line_items": line_items,
                "validation": validation_report,
                "audit_trail": []  # Empty initial review log
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