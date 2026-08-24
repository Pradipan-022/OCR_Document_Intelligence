from typing import Optional
from PIL import Image
from sqlalchemy.orm import Session

from app.models.document_model import DocumentPage, DocumentPageQuality
from app.services.preprocessing.quality import quality_assessor
from app.services.preprocessing.pipeline import preprocessing_pipeline
from app.services.storage import storage_service


class PreprocessingService:
    """Coordinates page quality analysis, image transformation, and disk/DB persistence."""

    def process_page(
        self,
        db: Session,
        page: DocumentPage,
        override_profile: Optional[str] = None,
    ) -> tuple[DocumentPageQuality, Image.Image]:
        """Task: High-level orchestration for analyzing, transforming, and persisting page data."""
        # 1. Load original page image from disk
        original_pil = Image.open(page.image_path)

        # 2. Analyze image quality metrics
        quality_report = quality_assessor.analyze(original_pil)

        # 3. Determine selected profile (User override takes precedence)
        selected_profile = override_profile or quality_report.recommended_profile

        # 4. Apply image preprocessing pipeline
        processed_pil, applied_profile = preprocessing_pipeline.process(
            pil_image=original_pil,
            profile_name=selected_profile,
        )

        # 5. Extract user owner_id from document for folder isolation
        user_id = page.document.owner_id if hasattr(page.document, "owner_id") else None

        # 6. Save preprocessed image file to disk storage
        processed_image_path = storage_service.save_processed_page_image(
            document_id=page.document_id,
            page_number=page.page_number,
            image=processed_pil,
            profile_name=applied_profile,
            user_id=user_id,
        )

        # 7. Upsert DocumentPageQuality DB record with metrics & processed file path
        quality_record = self._save_or_update_quality_record(
            db=db,
            page_id=page.id,
            quality_report=quality_report,
            applied_profile=applied_profile,
            processed_image_path=processed_image_path,
        )

        return quality_record, processed_pil

    def _save_or_update_quality_record(
        self,
        db: Session,
        page_id: str,
        quality_report,
        applied_profile: str,
        processed_image_path: str,
    ) -> DocumentPageQuality:
        """Task: Upsert the DocumentPageQuality record in the database."""
        existing_record = (
            db.query(DocumentPageQuality)
            .filter(DocumentPageQuality.page_id == page_id)
            .first()
        )

        if existing_record:
            existing_record.blur_score = quality_report.blur_score
            existing_record.brightness_score = quality_report.brightness_score
            existing_record.contrast_score = quality_report.contrast_score
            existing_record.skew_angle = quality_report.skew_angle
            existing_record.estimated_dpi = quality_report.estimated_dpi
            existing_record.has_document_boundary = quality_report.has_document_boundary
            existing_record.resolution_warning = quality_report.resolution_warning
            existing_record.quality_label = quality_report.quality_label
            existing_record.recommended_profile = quality_report.recommended_profile
            existing_record.applied_profile = applied_profile
            existing_record.processed_image_path = processed_image_path
            quality_record = existing_record
        else:
            quality_record = DocumentPageQuality(
                page_id=page_id,
                blur_score=quality_report.blur_score,
                brightness_score=quality_report.brightness_score,
                contrast_score=quality_report.contrast_score,
                skew_angle=quality_report.skew_angle,
                estimated_dpi=quality_report.estimated_dpi,
                has_document_boundary=quality_report.has_document_boundary,
                resolution_warning=quality_report.resolution_warning,
                quality_label=quality_report.quality_label,
                recommended_profile=quality_report.recommended_profile,
                applied_profile=applied_profile,
                processed_image_path=processed_image_path,
            )
            db.add(quality_record)

        db.commit()
        db.refresh(quality_record)
        return quality_record


preprocessing_service = PreprocessingService()