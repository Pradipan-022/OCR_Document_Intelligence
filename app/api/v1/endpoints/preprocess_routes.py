from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.quality_schema import (
    BatchPreprocessingResponse,
    DocumentPageQualitySchema,
    PreprocessPageRequest,
)
from app.services.validation.document_service import document_service
from app.services.preprocessing.preprocess_service import preprocessing_service

router = APIRouter()


@router.post(
    "/documents/{document_id}/pages/{page_number}",
    response_model=DocumentPageQualitySchema,
    status_code=status.HTTP_200_OK,
    summary="Preprocess a single page",
)
def preprocess_page(
    document_id: str,
    page_number: int,
    payload: Optional[PreprocessPageRequest] = None,
    db: Session = Depends(get_db),
):
    """Runs quality assessment and preprocessing on a single page, supporting optional manual overrides."""
    page = document_service.get_document_page(
        db=db, document_id=document_id, page_number=page_number
    )
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} for document '{document_id}' not found.",
        )

    override_profile = payload.override_profile if payload else None
    
    # Unpacks tuple to get the ORM object containing id and page_id
    quality_record, _ = preprocessing_service.process_page(
        db=db,
        page=page,
        override_profile=override_profile,
    )

    return quality_record


@router.post(
    "/documents/{document_id}",
    response_model=BatchPreprocessingResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch preprocess all document pages",
)
def preprocess_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Executes quality assessment and recommended preprocessing across all pages of a document."""
    doc = document_service.get_document_by_id(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    processed_records = []
    for page in doc.pages:
        quality_record, _ = preprocessing_service.process_page(db=db, page=page)
        processed_records.append(quality_record)

    return BatchPreprocessingResponse(
        document_id=document_id,
        processed_pages=processed_records,
    )


@router.get(
    "/documents/{document_id}/pages/{page_number}/quality",
    response_model=DocumentPageQualitySchema,
    status_code=status.HTTP_200_OK,
    summary="Get page quality report",
)
def get_page_quality_report(
    document_id: str,
    page_number: int,
    db: Session = Depends(get_db),
):
    """Retrieves stored quality metrics and profile choices for a page."""
    page = document_service.get_document_page(
        db=db, document_id=document_id, page_number=page_number
    )
    if not page or not page.quality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality report not found for this page. Please run preprocessing first.",
        )

    return page.quality


@router.get(
    "/documents/{document_id}/pages/{page_number}/processed-image",
    summary="Serve processed PNG image file",
)
def get_processed_page_image(
    document_id: str,
    page_number: int,
    db: Session = Depends(get_db),
):
    """Serves the enhanced preprocessed image file for side-by-side frontend viewing."""
    page = document_service.get_document_page(
        db=db, document_id=document_id, page_number=page_number
    )
    if not page or not page.quality or not page.quality.processed_image_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preprocessed image file not found. Run preprocessing first.",
        )

    return FileResponse(page.quality.processed_image_path, media_type="image/png")


