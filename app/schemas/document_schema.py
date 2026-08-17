from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class PageMetadata(BaseModel):
    page_number: int
    width: int
    height: int
    image_base64: Optional[str] = None  # Populated when returning JSON payloads


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