from fastapi import APIRouter, File, status, UploadFile

from app.schemas.document import DocumentUploadResponse
from app.services.ingestion import DocumentIngestionService

router = APIRouter()
ingestion_service = DocumentIngestionService()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF or Image Document",
)
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts a PDF or image file (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`).
    
    1. Reads raw file bytes asynchronously from the request.
    2. Passes bytes to `DocumentIngestionService`.
    3. Returns document metadata, page count, and unique document ID.
    """
    # 1. Read bytes from the uploaded file
    file_bytes = await file.read()

    # 2. Process bytes through your Ingestion Service
    # (returns tuple: response_model, list_of_pil_images)
    response_schema, _ = ingestion_service.process_file_bytes(
        file_bytes=file_bytes, 
        filename=file.filename
    )

    # 3. Return the Pydantic schema (FastAPI serializes this to JSON)
    return response_schema