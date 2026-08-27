from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.document_model import Document, StatusEnum
from app.services.orchestrator import DocumentPipelineOrchestrator
from app.services.export_services import ExportService

router = APIRouter()
orchestrator = DocumentPipelineOrchestrator()

# Trigger Async Document Processing
@router.post("/{id}/process", status_code=status.HTTP_202_ACCEPTED)
def process_document(id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    background_tasks.add_task(orchestrator.execute_pipeline, document_id=id)
    return {"message": "Document processing started asynchronously", "document_id": id, "status": "PROCESSING"}

# Read Processing Status
@router.get("/{id}/status")
def get_document_status(id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": id, "status": doc.status}

# Fetch Extracted OCR Data & Validation
@router.get("/{id}/result")
def get_document_result(id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc or doc.status != StatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Results not ready or processing failed")
    return doc.ocr_results

# Human Review Endpoint - Saves manual corrections & appends audit trail
@router.put("/{id}/review")
def save_human_review(id: str, payload: dict, db: Session = Depends(get_db)):
    """Payload format: {"field": "subtotal", "old_value": "100.00", "new_value": "120.00", "reviewer": "admin"}"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc or not doc.ocr_results:
        raise HTTPException(status_code=404, detail="Document not found")

    results = dict(doc.ocr_results)
    field = payload.get("field")
    new_val = payload.get("new_value")

    # Update extracted field value
    if field in results.get("extracted_fields", {}):
        results["extracted_fields"][field] = new_val

    # Append to audit trail log
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

# Data Export Endpoint (JSON / CSV / Annotated Image)
@router.get("/{id}/export")
def export_document_data(id: str, format: str = "json", db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc or not doc.ocr_results:
        raise HTTPException(status_code=400, detail="Document incomplete")

    if format.lower() == "json":
        json_data = ExportService.to_json(doc.ocr_results)
        return Response(content=json_data, media_type="application/json", headers={"Content-Disposition": f"attachment; filename={id}.json"})

    elif format.lower() == "csv":
        line_items = doc.ocr_results.get("line_items", [])
        csv_data = ExportService.to_csv(line_items)
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={id}.csv"})

    else:
        raise HTTPException(status_code=400, detail="Unsupported format requested")