from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.document_schema import DocumentUploadResponse
from app.services.document_service import document_service
from app.services.ingestion import ingestion_service
from app.services.storage import storage_service

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    # 1. Byte validation & image extraction
    file_bytes = await file.read()
    upload_schema, pil_images = ingestion_service.process_file_bytes(
        file_bytes, file.filename
    )

    # 2. Disk file writing
    raw_path, page_paths = storage_service.save_document_files(
        document_id=upload_schema.document_id,
        filename=file.filename,
        file_bytes=file_bytes,
        pil_images=pil_images,
    )

    # 3. Database persistence
    document_service.create_document_with_pages(
        db=db,
        upload_schema=upload_schema,
        raw_file_path=raw_path,
        page_image_paths=page_paths,
    )

    return upload_schema


@router.get("/")
def list_documents(
    skip: int = 0, limit: int = 10, db: Session = Depends(get_db)
):
    return document_service.list_documents(db=db, skip=skip, limit=limit)


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = document_service.get_document_by_id(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/pages/{page_number}/image")
def get_page_image(
    document_id: str, page_number: int, db: Session = Depends(get_db)
):
    page = document_service.get_document_page(
        db=db, document_id=document_id, page_number=page_number
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page image not found")

    return FileResponse(page.image_path, media_type="image/png")