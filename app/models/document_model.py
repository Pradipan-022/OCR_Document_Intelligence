import enum
import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base
if TYPE_CHECKING:
    from app.models.user_model import User
if TYPE_CHECKING:
    from app.models.ocr_model import OCREngineResultModel

class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(Base):
    """Represents an uploaded document (PDF or single image) in the database."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    owner_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="documents"
    )

    filename: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum),
        default=StatusEnum.PENDING,
        nullable=False,
    )

    page_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Aggregated results and analytics
    overall_quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    ocr_results: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Timestamps (stored in UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to individual pages
    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentPage(Base):
    """Represents an individual page within a multi-page document."""

    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    image_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Per-page assessment and OCR data
    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    ocr_results: Mapped[list["OCREngineResultModel"]] = relationship(
        "OCREngineResultModel",
        back_populates="page",
        cascade="all, delete-orphan",
    )

    # Relationship back to the parent document
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="pages",
    )
    
    #One-to-one relationship with quality report
    quality: Mapped[Optional["DocumentPageQuality"]] = relationship(
        "DocumentPageQuality",
        back_populates="page",
        uselist=False,
        cascade="all, delete-orphan",
    )

class DocumentPageQuality(Base):
    """Stores physical quality assessment metrics and preprocessing choices for a page."""

    __tablename__ = "document_page_quality"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Unique foreign key enforces a true one-to-one relationship
    page_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Visual and physical scores
    blur_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    brightness_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    contrast_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    skew_angle: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    estimated_dpi: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Quality flags
    has_document_boundary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    resolution_warning: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    resolution_critical: Mapped[bool] = mapped_column(
            Boolean,
            default=False,
            nullable=False,
        )

    # Classification and pipeline routing
    quality_label: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    recommended_profile: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    applied_profile: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    processed_image_path: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True,
    )

    # Relationship back to DocumentPage
    page: Mapped["DocumentPage"] = relationship(
        "DocumentPage",
        back_populates="quality",
    )