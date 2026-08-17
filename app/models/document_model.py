import enum
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base

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

    page_ocr_results: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationship back to the document
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="pages",
    )
    
    #Relationship back to parent document
    document = relationship("Document", back_populates="pages")