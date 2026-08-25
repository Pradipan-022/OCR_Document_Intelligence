import uuid
from typing import Any, Optional
from PIL import Image
from sqlalchemy.orm import Session

from app.models.document_model import DocumentPage, DocumentPageQuality
from app.services.preprocessing.quality import quality_assessor
from app.services.preprocessing.pipeline import preprocessing_pipeline
from app.services.storage import storage_service


class PreprocessingService:
    """Coordinates document quality analysis, image transformation, storage, and DB persistence."""

    # --- Single-Task Internal Helpers ---

    def _load_page_image(self, image_path: str) -> Image.Image:
        """Task: Load original page image from disk into memory."""
        return Image.open(image_path)

    def _determine_profile(
        self, recommended_profile: str, override_profile: Optional[str] = None
    ) -> str:
        """Task: Resolve target preprocessing profile (User override takes precedence)."""
        return override_profile or recommended_profile

    def _extract_user_id(self, page: DocumentPage) -> Optional[str]:
        """Task: Safely extract owner_id from parent document for user folder isolation."""
        if hasattr(page, "document") and hasattr(page.document, "owner_id"):
            return page.document.owner_id
        return None

    def _save_processed_image(
        self,
        page: DocumentPage,
        processed_pil: Image.Image,
        applied_profile: str,
    ) -> str:
        """Task: Save preprocessed image to storage and return disk file path."""
        user_id = self._extract_user_id(page)
        return storage_service.save_processed_page_image(
            document_id=page.document_id,
            page_number=page.page_number,
            image=processed_pil,
            profile_name=applied_profile,
            user_id=user_id,
        )

    def _get_val(self, obj: Any, key: str, default: Any = None) -> Any:
        """Task: Extract value safely whether quality_report is a dict or a Pydantic object."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _merge_quality_payload(
            self,
            page_id: str,
            quality_report: Any,
            applied_profile: str,
            processed_image_path: str,
            record_id: Optional[str] = None,
        ) -> dict:
            """Combines quality assessor metrics with database identifiers into a unified schema payload."""
            # Convert Pydantic object to dict if necessary
            data = (
                quality_report.model_dump()
                if hasattr(quality_report, "model_dump")
                else dict(quality_report)
            )
    
            # Inject required keys expected by DocumentPageQualitySchema
            data["id"] = record_id or str(uuid.uuid4())
            data["page_id"] = page_id
            data["applied_profile"] = applied_profile
            data["processed_image_path"] = processed_image_path
    
            return data
        
    def _save_or_update_quality_record(
        self,
        db: Session,
        page_id: str,
        quality_report: Any,
        applied_profile: str,
        processed_image_path: str,
    ) -> DocumentPageQuality:
        """Upsert the DocumentPageQuality database record using merged metrics."""
        quality_record = (
            db.query(DocumentPageQuality)
            .filter(DocumentPageQuality.page_id == page_id)
            .first()
        )

        existing_id = quality_record.id if quality_record else str(uuid.uuid4())

        # Combine raw report metrics with missing DB IDs
        payload = self._merge_quality_payload(
            page_id=page_id,
            quality_report=quality_report,
            applied_profile=applied_profile,
            processed_image_path=processed_image_path,
            record_id=existing_id,
        )

        if not quality_record:
            quality_record = DocumentPageQuality(id=payload["id"], page_id=payload["page_id"])
            db.add(quality_record)

        # Map combined fields directly
        quality_record.blur_score = payload.get("blur_score", 0.0)
        quality_record.brightness_score = payload.get("brightness_score", 0.0)
        quality_record.contrast_score = payload.get("contrast_score", 0.0)
        quality_record.skew_angle = payload.get("skew_angle", 0.0)
        quality_record.estimated_dpi = payload.get("estimated_dpi", 72)
        quality_record.has_document_boundary = payload.get("has_document_boundary", False)
        quality_record.resolution_warning = payload.get("resolution_warning", False)
        quality_record.resolution_critical = payload.get("resolution_critical", False)
        quality_record.quality_label = payload.get("quality_label", "Unknown")
        quality_record.recommended_profile = payload.get("recommended_profile", "basic")
        quality_record.applied_profile = payload.get("applied_profile")
        quality_record.processed_image_path = payload.get("processed_image_path")

        db.commit()
        db.refresh(quality_record)
        return quality_record

    

    # --- Main Orchestrator Method ---

    def process_page(
        self,
        db: Session,
        page: DocumentPage,
        override_profile: Optional[str] = None,
    ) -> tuple[DocumentPageQuality, Image.Image]:
        """Task: High-level pipeline controller delegating page processing step-by-step."""
        # 1. Load image asset from disk
        original_pil = self._load_page_image(page.image_path)

        # 2. Analyze visual & physical quality metrics
        quality_report = quality_assessor.analyze(original_pil)

        # Extract recommended profile safely
        rec_profile = self._get_val(quality_report, "recommended_profile", "basic")

        # 3. Determine active preprocessing profile
        selected_profile = self._determine_profile(
            recommended_profile=rec_profile,
            override_profile=override_profile,
        )

        # 4. Apply image transformations via pipeline
        processed_pil, applied_profile = preprocessing_pipeline.process(
            pil_image=original_pil,
            profile_name=selected_profile,
        )

        # 5. Persist transformed image file to storage disk
        processed_image_path = self._save_processed_image(
            page=page,
            processed_pil=processed_pil,
            applied_profile=applied_profile,
        )

        # 6. Upsert DocumentPageQuality DB record
        quality_record = self._save_or_update_quality_record(
            db=db,
            page_id=page.id,  # Explicitly passes document_pages primary key
            quality_report=quality_report,
            applied_profile=applied_profile,
            processed_image_path=processed_image_path,
        )

        return quality_record, processed_pil


preprocessing_service = PreprocessingService()