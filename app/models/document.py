import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base

class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(Base):
    """Represents an uploaded document (PDF or single image) in the database."""
    
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False) # Path to stored file on disk
    file_type = Column(String, nullable=False) # e.g., 'pdf', 'png', 'jpg'
    status = Column(Enum(StatusEnum), default=0, nullable=False)
    page_count = Column(Integer, default=0, nullable=False)
    
    #Aggregated results and analytics
    overall_quality_score = Column(Float, nullable=True) #Calculated quality rating
    ocr_results = Column(JSON, nullable=True)
    
    #Timestamps (Stored in UTC)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.noew(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    #Relationship to individual pages
    pages = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
        
    )   
    
class DocumentPage(Base):
    #Represents an individual page within a multi-page document.
    
    __tablename__ = "document_pages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))    
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String, nullable=False) #Disk path to rendered PNG page
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    
    #Per page assessment and OCR data
    quality_score = Column(Float, nullable=True)
    page_ocr_results = Column(JSON, nullable=True)
    
    #Relationship back to parent document
    document = relationship("Document", back_populates="pages")