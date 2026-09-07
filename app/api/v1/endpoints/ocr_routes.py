import os
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.document_model import Document, StatusEnum, DocumentPage
from app.models.ocr_model import OCREngineResultModel, OCRBlockModel, OCRWordModel
from app.services.orchestrator import DocumentPipelineOrchestrator
from app.services.export_services import ExportService
from app.services.extraction.extractor import MetadataAndTableExtractor

router = APIRouter()
orchestrator = DocumentPipelineOrchestrator()
extractor = MetadataAndTableExtractor()

class ExtractionRequest(BaseModel):
    merged_text: str
    bounding_box_tokens: list[dict[str, Any]]

@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
def process_document(document_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    background_tasks.add_task(orchestrator.execute_pipeline, document_id=document_id)
    return {"message": "Document processing started asynchronously", "document_id": document_id, "status": "PROCESSING"}

@router.get("/{document_id}/status")
def get_document_status(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    status_str = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
    res = {
        "document_id": document_id,
        "status": status_str,
        "total_pages": doc.page_count or len(doc.pages) or 1
    }
    if doc.ocr_results and isinstance(doc.ocr_results, dict):
        res["progress"] = doc.ocr_results.get("progress", 0)
        res["current_step"] = doc.ocr_results.get("current_step", "")
        res["current_page"] = doc.ocr_results.get("current_page", 1)
        if "total_pages" in doc.ocr_results:
            res["total_pages"] = doc.ocr_results["total_pages"]
    return res

@router.get("/{document_id}/result")
def get_document_result(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != StatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Results not ready or processing failed")
    
    res = dict(doc.ocr_results or {})
    res["document_id"] = doc.id
    res["status"] = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
    res["total_pages"] = doc.page_count or len(doc.pages) or len(res.get("pages", [])) or 1
    return res

@router.put("/{document_id}/review")
def save_human_review(document_id: str, payload: dict, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or not doc.ocr_results:
        raise HTTPException(status_code=404, detail="Document not found")

    results = dict(doc.ocr_results)
    field = payload.get("field")
    new_val = payload.get("new_value")

    if field in results.get("extracted_fields", {}):
        results["extracted_fields"][field] = new_val

    audit_entry = {
        "field": field,
        "original_value": payload.get("old_value"),
        "new_value": new_val,
        "reviewer_id": payload.get("reviewer", "anonymous"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    results.setdefault("audit_trail", []).append(audit_entry)

    doc.ocr_results = results
    db.commit()
    return {"message": "Review state saved", "audit_trail": results["audit_trail"]}

@router.get("/{document_id}/export")
def export_document_data(
    document_id: str, 
    format: str = "json", 
    page_number: int = 1, 
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or not doc.ocr_results:
        raise HTTPException(status_code=400, detail="Document incomplete or not found")

    fmt = format.lower()

    if fmt == "json":
        json_data = ExportService.to_json(doc.ocr_results)
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={document_id}.json"}
        )

    elif fmt == "csv":
        line_items = doc.ocr_results.get("line_items", [])
        csv_data = ExportService.to_csv(line_items)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={document_id}.csv"}
        )

    elif fmt in ["image", "png"]:
        # Find specified page
        target_page = next((p for p in doc.pages if p.page_number == page_number), None)
        if not target_page or not os.path.exists(target_page.image_path):
            raise HTTPException(status_code=404, detail=f"Page {page_number} image file not found")

        # Read page image bytes from disk
        with open(target_page.image_path, "rb") as f:
            image_bytes = f.read()

        # Extract blocks for recommended engine on this page
        pages_payload = doc.ocr_results.get("pages", [])
        page_idx = page_number - 1
        blocks = []
        
        if 0 <= page_idx < len(pages_payload):
            page_data = pages_payload[page_idx]
            rec_engine = page_data.get("recommended_engine")
            blocks = page_data.get("raw_engine_data", {}).get(rec_engine, {}).get("blocks", [])

        # Draw bounding boxes and generate PNG bytes
        annotated_bytes = ExportService.generate_annotated_image(image_bytes, blocks)

        return Response(
            content=annotated_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename={document_id}_page_{page_number}_annotated.png"}
        )

    else:
        raise HTTPException(
            status_code=400, 
            detail="Unsupported format requested. Choose 'json', 'csv', or 'image'."
        )
    
@router.get("/metrics/summary")
def get_metrics_summary(db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.status == StatusEnum.COMPLETED).all()

    total_docs = len(docs)
    engine_wins = {"tesseract": 0, "easyocr": 0, "paddle": 0}
    engine_scores = {"tesseract": [], "easyocr": [], "paddle": []}
    validation_failures = 0

    for doc in docs:
        if not doc.ocr_results:
            continue
        
        # Aggregate page-level engine performance
        pages = doc.ocr_results.get("pages", [])
        for page in pages:
            rec = page.get("recommended_engine")
            if rec in engine_wins:
                engine_wins[rec] += 1
            
            scores = page.get("engine_scores", {})
            for engine, score in scores.items():
                if engine in engine_scores:
                    engine_scores[engine].append(score)

        # Count documents with validation flags
        validation = doc.ocr_results.get("validation", {})
        if validation.get("is_valid") is False or len(validation.get("anomalies", [])) > 0:
            validation_failures += 1

    avg_confidence = {
        eng: round(sum(scores) / len(scores), 3) if scores else 0.0
        for eng, scores in engine_scores.items()
    }

    return {
        "total_completed_documents": total_docs,
        "recommended_engine_distribution": engine_wins,
        "average_engine_confidence": avg_confidence,
        "validation_flagged_count": validation_failures
    }

def _normalize_tokens_from_raw(raw_data: dict[str, Any]) -> tuple[str, list]:
    """Helper to pull full text and token bboxes from raw OCR JSON payloads."""
    merged_text = raw_data.get("merged_text", raw_data.get("raw_text", ""))
    tokens = []
    
    # Check for recommended engine output or fallback blocks
    rec_engine = raw_data.get("recommended_engine")
    engine_data = raw_data.get("raw_engine_data", {}).get(rec_engine, {}) if rec_engine else {}
    blocks = engine_data.get("blocks", raw_data.get("blocks", []))

    for block in blocks:
        words = block.get("words", [block])
        for word in words:
            bbox = word.get("bbox", {}) if isinstance(word.get("bbox"), dict) else {}
            tokens.append({
                "text": word.get("text", ""),
                "bbox": [
                    bbox.get("x_min", word.get("x_min", 0)),
                    bbox.get("y_min", word.get("y_min", 0)),
                    bbox.get("x_max", word.get("x_max", 0)),
                    bbox.get("y_max", word.get("y_max", 0))
                ]
            })
            
    return merged_text, tokens

@router.post("/extract/raw")
def extract_from_raw_payload(payload: dict[str, Any]):
    """Option 2: Paste any raw OCR engine output JSON as-is without formatting bbox fields."""
    try:
        merged_text, tokens = _normalize_tokens_from_raw(payload)
        return {
            "status": "success",
            "data": {
                "fields": extractor.extract_key_values(merged_text),
                "line_items": extractor.extract_line_item_table(tokens)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse raw OCR payload: {str(e)}")
    
@router.post("/documents/{document_id}/extract")
def extract_by_document_id(
    document_id: str, 
    page_number: int = 1, 
    db: Session = Depends(get_db)
):
    """Option 1: Zero input needed. Fetches raw_json directly from DB page record."""
    page = db.query(DocumentPage).filter(
        DocumentPage.document_id == document_id,
        DocumentPage.page_number == page_number
    ).first()

    if not page or not page.raw_json:
        raise HTTPException(status_code=404, detail="Page OCR results not found in DB.")

    merged_text, tokens = _normalize_tokens_from_raw(page.raw_json)

    return {
        "status": "success",
        "document_id": document_id,
        "page_number": page_number,
        "data": {
            "fields": extractor.extract_key_values(merged_text),
            "line_items": extractor.extract_line_item_table(tokens)
        }
    }


def _cluster_tokens_into_lines(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Spatially groups OCR tokens into visual reading lines based on bounding box vertical overlap."""
    if not tokens:
        return []

    valid_tokens = [t for t in tokens if t.get("text")]
    sorted_tokens = sorted(
        valid_tokens,
        key=lambda t: (
            t.get("bbox", {}).get("y_min", t.get("y0", 0)),
            t.get("bbox", {}).get("x_min", t.get("x0", 0))
        )
    )

    lines: list[dict[str, Any]] = []
    for token in sorted_tokens:
        bbox = token.get("bbox") or {
            "x_min": token.get("x_min", token.get("x0", 0)),
            "y_min": token.get("y_min", token.get("y0", 0)),
            "x_max": token.get("x_max", token.get("x1", 0)),
            "y_max": token.get("y_max", token.get("y1", 0))
        }
        t_ymin = bbox.get("y_min", 0)
        t_ymax = bbox.get("y_max", 0)
        t_height = max(t_ymax - t_ymin, 1)

        matched_line = None
        for line in lines:
            line_ymin = line["bbox"]["y_min"]
            line_ymax = line["bbox"]["y_max"]
            line_height = max(line_ymax - line_ymin, 1)
            tolerance = min(t_height, line_height) * 0.5

            if abs(t_ymin - line_ymin) <= tolerance or (t_ymin >= line_ymin and t_ymin <= line_ymax):
                matched_line = line
                break

        if matched_line:
            matched_line["tokens"].append(token)
            matched_line["bbox"]["x_min"] = min(matched_line["bbox"]["x_min"], bbox.get("x_min", 0))
            matched_line["bbox"]["y_min"] = min(matched_line["bbox"]["y_min"], bbox.get("y_min", 0))
            matched_line["bbox"]["x_max"] = max(matched_line["bbox"]["x_max"], bbox.get("x_max", 0))
            matched_line["bbox"]["y_max"] = max(matched_line["bbox"]["y_max"], bbox.get("y_max", 0))
        else:
            lines.append({
                "line_id": len(lines) + 1,
                "tokens": [token],
                "bbox": {
                    "x_min": bbox.get("x_min", 0),
                    "y_min": bbox.get("y_min", 0),
                    "x_max": bbox.get("x_max", 0),
                    "y_max": bbox.get("y_max", 0)
                }
            })

    formatted_lines = []
    for line in lines:
        line["tokens"].sort(key=lambda t: (t.get("bbox", {}).get("x_min", t.get("x0", 0))))
        line_text = " ".join([t.get("text", "") for t in line["tokens"] if t.get("text")])
        confidences = [
            t.get("confidence", 1.0)
            for t in line["tokens"]
            if t.get("confidence") is not None
        ]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        formatted_lines.append({
            "line_id": line["line_id"],
            "text": line_text,
            "confidence": round(avg_conf, 4),
            "bbox": line["bbox"],
            "word_count": len(line["tokens"]),
            "tokens": line["tokens"]
        })

    return formatted_lines


def _normalize_engine_name(name: str) -> str:
    n = name.lower()
    if "paddle" in n:
        return "paddle"
    if "easy" in n:
        return "easyocr"
    if "tess" in n:
        return "tesseract"
    return n


@router.get("/{document_id}/structured-text")
@router.get("/documents/{document_id}/structured-text")
def get_document_structured_text(
    document_id: str,
    page_number: int = Query(1, ge=1, description="Page number to inspect"),
    engine: Optional[str] = Query(None, description="Filter by engine (tesseract, easyocr, paddle)"),
    granularity: str = Query("word", description="Granularity: word, line, or block"),
    min_confidence: float = Query(0.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db)
):
    """
    Returns structured OCR text organized spatially with bounding box (bbox) coordinates
    generated by each OCR engine for frontend rendering.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    target_page = next((p for p in doc.pages if p.page_number == page_number), None)
    if not target_page:
        raise HTTPException(status_code=404, detail=f"Page {page_number} not found for document {document_id}")

    # Determine recommended engine from doc.ocr_results if available
    recommended_engine = "tesseract"
    ocr_results_payload = doc.ocr_results or {}
    pages_payload = ocr_results_payload.get("pages", [])
    page_json_data = {}

    if isinstance(pages_payload, list) and 0 <= (page_number - 1) < len(pages_payload):
        page_json_data = pages_payload[page_number - 1]
    elif isinstance(pages_payload, dict):
        page_json_data = pages_payload.get(str(page_number), {})

    if isinstance(page_json_data, dict):
        recommended_engine = page_json_data.get("recommended_engine", recommended_engine)

    engines_data: dict[str, Any] = {}
    engine_boxes_map: dict[str, list[dict[str, Any]]] = {}

    # 1. Attempt to fetch relational DB engine records
    db_engine_results = db.query(OCREngineResultModel).filter(
        OCREngineResultModel.page_id == target_page.id
    ).all()

    filtered_target_engine = _normalize_engine_name(engine) if engine else None

    if db_engine_results:
        for db_res in db_engine_results:
            eng_key = _normalize_engine_name(db_res.engine_name)
            if filtered_target_engine and eng_key != filtered_target_engine:
                continue

            tokens = []
            blocks_data = []

            for block in db_res.blocks:
                b_dict = {
                    "id": block.id,
                    "text": block.text,
                    "confidence": block.confidence,
                    "bbox": {
                        "x_min": block.x_min,
                        "y_min": block.y_min,
                        "x_max": block.x_max,
                        "y_max": block.y_max
                    }
                }
                words_data = []
                for w in block.words:
                    conf = w.confidence
                    if min_confidence > 0 and (conf < min_confidence and conf * 100 < min_confidence):
                        continue

                    w_bbox = {
                        "x_min": w.x_min,
                        "y_min": w.y_min,
                        "x_max": w.x_max,
                        "y_max": w.y_max
                    }
                    token_item = {
                        "id": w.id,
                        "text": w.text,
                        "confidence": w.confidence,
                        "is_low_confidence": w.is_low_confidence,
                        "bbox": w_bbox,
                        "block_id": block.id
                    }
                    tokens.append(token_item)
                    words_data.append(token_item)

                b_dict["words"] = words_data
                blocks_data.append(b_dict)

            lines = _cluster_tokens_into_lines(tokens)

            svg_boxes = [
                {
                    "x0": t["bbox"]["x_min"],
                    "y0": t["bbox"]["y_min"],
                    "x1": t["bbox"]["x_max"],
                    "y1": t["bbox"]["y_max"],
                    "text": t["text"],
                    "confidence": t["confidence"],
                    "label": f"Word #{idx + 1}"
                }
                for idx, t in enumerate(tokens)
            ]

            engines_data[eng_key] = {
                "engine_name": eng_key,
                "raw_text": db_res.raw_text,
                "average_confidence": db_res.average_confidence,
                "execution_time_ms": db_res.execution_time_ms,
                "status": db_res.status,
                "total_tokens": len(tokens),
                "tokens": tokens,
                "structured_lines": lines,
                "blocks": blocks_data
            }
            engine_boxes_map[eng_key] = svg_boxes

    # 2. Fallback to doc.ocr_results JSON payload if relational records are missing or empty
    if not engines_data and isinstance(page_json_data, dict):
        raw_map = page_json_data.get("raw_engine_data") or page_json_data.get("engines") or {}
        for eng_name, eng_info in raw_map.items():
            eng_key = _normalize_engine_name(eng_name)
            if filtered_target_engine and eng_key != filtered_target_engine:
                continue

            if not isinstance(eng_info, dict):
                continue

            raw_blocks = eng_info.get("blocks", [])
            tokens = []
            parsed_blocks = []

            for b_idx, block in enumerate(raw_blocks):
                if not isinstance(block, dict):
                    continue
                words = block.get("words", [block])
                parsed_words = []
                for w in words:
                    if not isinstance(w, dict):
                        continue
                    w_text = w.get("text") or w.get("word") or ""
                    if not w_text:
                        continue
                    w_conf = w.get("confidence") or w.get("score") or w.get("conf") or 1.0
                    if min_confidence > 0 and (w_conf < min_confidence and w_conf * 100 < min_confidence):
                        continue

                    b_val = w.get("bbox") or block.get("bbox") or {}
                    if isinstance(b_val, dict):
                        x0 = b_val.get("x_min", w.get("x0", 0))
                        y0 = b_val.get("y_min", w.get("y0", 0))
                        x1 = b_val.get("x_max", w.get("x1", 0))
                        y1 = b_val.get("y_max", w.get("y1", 0))
                    elif isinstance(b_val, (list, tuple)) and len(b_val) >= 4:
                        x0, y0, x1, y1 = b_val[0], b_val[1], b_val[2], b_val[3]
                    else:
                        x0 = w.get("x_min", w.get("x0", 0))
                        y0 = w.get("y_min", w.get("y0", 0))
                        x1 = w.get("x_max", w.get("x1", 0))
                        y1 = w.get("y_max", w.get("y1", 0))

                    t_item = {
                        "text": w_text,
                        "confidence": float(w_conf),
                        "is_low_confidence": float(w_conf) < 0.60 if float(w_conf) <= 1.0 else float(w_conf) < 60.0,
                        "bbox": {"x_min": x0, "y_min": y0, "x_max": x1, "y_max": y1},
                        "block_id": b_idx + 1
                    }
                    tokens.append(t_item)
                    parsed_words.append(t_item)

                parsed_blocks.append({
                    "id": b_idx + 1,
                    "text": block.get("text", ""),
                    "confidence": block.get("confidence", 1.0),
                    "words": parsed_words
                })

            lines = _cluster_tokens_into_lines(tokens)
            svg_boxes = [
                {
                    "x0": t["bbox"]["x_min"],
                    "y0": t["bbox"]["y_min"],
                    "x1": t["bbox"]["x_max"],
                    "y1": t["bbox"]["y_max"],
                    "text": t["text"],
                    "confidence": t["confidence"],
                    "label": f"Token #{idx + 1}"
                }
                for idx, t in enumerate(tokens)
            ]

            engines_data[eng_key] = {
                "engine_name": eng_key,
                "raw_text": eng_info.get("text", ""),
                "average_confidence": eng_info.get("avg_confidence", 0.0),
                "execution_time_ms": eng_info.get("duration_seconds", 0.0) * 1000.0,
                "status": eng_info.get("status", "SUCCESS"),
                "total_tokens": len(tokens),
                "tokens": tokens,
                "structured_lines": lines,
                "blocks": parsed_blocks
            }
            engine_boxes_map[eng_key] = svg_boxes

    # Format structured_text_blocks depending on granularity
    structured_blocks_response = []
    active_engine_name = filtered_target_engine or recommended_engine
    active_data = engines_data.get(active_engine_name) or next(iter(engines_data.values()), {})

    if granularity == "line":
        for line in active_data.get("structured_lines", []):
            structured_blocks_response.append({
                "label": f"Line #{line['line_id']}",
                "text": line["text"],
                "confidence": line["confidence"],
                "bbox": line["bbox"],
                "tokens": line["tokens"]
            })
    elif granularity == "block":
        for b in active_data.get("blocks", []):
            structured_blocks_response.append({
                "label": f"Block #{b['id']}",
                "text": b["text"],
                "confidence": b.get("confidence", 1.0),
                "bbox": b.get("bbox", {}),
                "words": b.get("words", [])
            })
    else:  # "word" granularity default
        for idx, t in enumerate(active_data.get("tokens", []), start=1):
            structured_blocks_response.append({
                "label": f"Token #{idx}",
                "text": t["text"],
                "confidence": t["confidence"],
                "bbox": t["bbox"]
            })

    return {
        "status": "success",
        "document_id": document_id,
        "page_number": page_number,
        "total_pages": doc.page_count or len(doc.pages) or 1,
        "recommended_engine": recommended_engine,
        "granularity": granularity,
        "engines": engines_data,
        "engine_boxes": engine_boxes_map,
        "structured_text_blocks": structured_blocks_response
    }