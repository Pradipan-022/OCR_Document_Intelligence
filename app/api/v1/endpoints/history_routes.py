from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.history_schema import HistoryDocumentItem, HistoryPageItem
from app.services.validation.document_service import document_service

router = APIRouter()


@router.get("", response_model=list[HistoryDocumentItem], status_code=status.HTTP_200_OK)
@router.get("/history", response_model=list[HistoryDocumentItem], status_code=status.HTTP_200_OK)
def get_document_history(
    user_id: Optional[str] = Query(None, description="Filter history by user ID or username"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Retrieves document history grouped with page-level thumbnail links and preprocessing status."""
    docs = document_service.list_documents(db=db, user_id=user_id, skip=skip, limit=limit)
    history_list = []

    for doc in docs:
        page_items = []
        sorted_pages = sorted(doc.pages, key=lambda p: p.page_number)

        for page in sorted_pages:
            quality = page.quality
            has_quality = quality is not None
            
            page_items.append(
                HistoryPageItem(
                    page_id=page.id,
                    page_number=page.page_number,
                    image_url=f"/api/v1/documents/{doc.id}/pages/{page.page_number}/image",
                    processed_image_url=(
                        f"/api/v1/preprocessing/documents/{doc.id}/pages/{page.page_number}/processed-image"
                        if has_quality and quality.processed_image_path
                        else None
                    ),
                    is_preprocessed=has_quality and bool(quality.applied_profile),
                    applied_profile=quality.applied_profile if has_quality else None,
                    recommended_profile=quality.recommended_profile if has_quality else None,
                    quality_label=quality.quality_label if has_quality else "Pending",
                    quality_metrics={
                        "blur_score": quality.blur_score,
                        "brightness_score": quality.brightness_score,
                        "contrast_score": quality.contrast_score,
                        "skew_angle": quality.skew_angle,
                        "estimated_dpi": quality.estimated_dpi,
                        "has_document_boundary": quality.has_document_boundary,
                        "resolution_warning": quality.resolution_warning,
                    } if has_quality else {}
                )
            )

        status_str = doc.status.value if hasattr(doc.status, "value") else (doc.status or "UPLOADED")

        history_list.append(
            HistoryDocumentItem(
                document_id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type or "unknown",
                page_count=doc.page_count or len(page_items),
                status=status_str,
                owner_id=doc.owner_id,
                created_at=doc.created_at,
                pages=page_items
            )
        )

    return history_list