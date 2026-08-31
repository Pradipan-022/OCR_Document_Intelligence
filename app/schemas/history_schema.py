from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PageMetadata(BaseModel):
    page_number: int
    width: int
    height: int
    image_base64: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    page_count: int
    status: str = "PENDING"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    pages: list[PageMetadata] = []


class HistoryPageItem(BaseModel):
    page_id: str
    page_number: int
    image_url: str
    processed_image_url: Optional[str] = None
    is_preprocessed: bool = False
    applied_profile: Optional[str] = None
    recommended_profile: Optional[str] = None
    quality_label: Optional[str] = None
    quality_metrics: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class HistoryDocumentItem(BaseModel):
    document_id: str
    filename: str
    file_type: str
    page_count: int
    status: str
    user_id: Optional[str] = None
    created_at: datetime
    pages: list[HistoryPageItem] = []

    model_config = ConfigDict(from_attributes=True)