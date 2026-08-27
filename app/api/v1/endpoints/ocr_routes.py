import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.document_model import Document, StatusEnum
from app.services.orchestrator import DocumentPipelineOrchestrator
from app.services.export_services import ExportService

router = APIRouter()
orchestrator = DocumentPipelineOrchestrator()

@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
def process_document(id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    background_tasks.add_task(orchestrator.execute_pipeline, document_id=id)
    return {"message": "Document processing started asynchronously", "document_id": id, "status": "PROCESSING"}

@router.get("/{document_id}/status")
def get_document_status(id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": id, "status": doc.status}

@router.get("/{document_id}/result")
def get_document_result(id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc or doc.status != StatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Results not ready or processing failed")
    return doc.ocr_results

@router.put("/{document_id}/review")
def save_human_review(id: str, payload: dict, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
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

@router.get("/{id}/export")
def export_document_data(
    id: str, 
    format: str = "json", 
    page_number: int = 1, 
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc or not doc.ocr_results:
        raise HTTPException(status_code=400, detail="Document incomplete or not found")

    fmt = format.lower()

    if fmt == "json":
        json_data = ExportService.to_json(doc.ocr_results)
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={id}.json"}
        )

    elif fmt == "csv":
        line_items = doc.ocr_results.get("line_items", [])
        csv_data = ExportService.to_csv(line_items)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={id}.csv"}
        )

    elif fmt in ["image", "png"]:
        # Find specified page
        target_page = next((p for p in doc.pages if p.page_number == page_number), None)
        if not target_page or not os.path.exists(target_page.image_path):
            raise HTTPException(status_code=44, detail=f"Page {page_number} image file not found")

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
            headers={"Content-Disposition": f"inline; filename={id}_page_{page_number}_annotated.png"}
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