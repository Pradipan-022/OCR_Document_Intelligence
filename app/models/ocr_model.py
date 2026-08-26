import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document_model import DocumentPage


class OCREngineResultModel(Base):
    """Stores OCR output produced by one OCR engine for a document page."""

    __tablename__ = "ocr_engine_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    page_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    engine_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    engine_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    profile_used: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    average_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    execution_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    page: Mapped["DocumentPage"] = relationship(
        "DocumentPage",
        back_populates="ocr_results",
    )

    blocks: Mapped[list["OCRBlockModel"]] = relationship(
        "OCRBlockModel",
        back_populates="engine_result",
        cascade="all, delete-orphan",
    )


class OCRBlockModel(Base):
    """Stores a text block detected by an OCR engine."""

    __tablename__ = "ocr_blocks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    engine_result_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ocr_engine_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    x_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    y_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    x_max: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    y_max: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    engine_result: Mapped["OCREngineResultModel"] = relationship(
        "OCREngineResultModel",
        back_populates="blocks",
    )

    words: Mapped[list["OCRWordModel"]] = relationship(
        "OCRWordModel",
        back_populates="block",
        cascade="all, delete-orphan",
    )


class OCRWordModel(Base):
    """Stores an individual OCR-recognized word."""

    __tablename__ = "ocr_words"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    block_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ocr_blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    text: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    is_low_confidence: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    x_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    y_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    x_max: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    y_max: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    block: Mapped["OCRBlockModel"] = relationship(
        "OCRBlockModel",
        back_populates="words",
    )