from sqlalchemy.orm import Session, selectinload
from typing import Optional

from app.models.document_model import Document, DocumentPage, StatusEnum
from app.schemas.document_schema import DocumentUploadResponse
from app.models.user_model import User


class DocumentService:
    """Handles database CRUD operations for Document and DocumentPage models."""

    def create_document_with_pages(
        self,
        db: Session,
        upload_schema: DocumentUploadResponse,
        raw_file_path: str,
        page_image_paths: list[str],
        owner_id: Optional[str] = None,

    ) -> Document:
        """Creates parent Document and child DocumentPage records in SQLite."""
        db_doc = Document(
            id=upload_schema.document_id,
            filename=upload_schema.filename,
            file_path=raw_file_path,
            file_type=upload_schema.file_type,
            status=StatusEnum.PENDING,
            page_count=upload_schema.page_count,
            owner_id = owner_id,
        )
        db.add(db_doc)

        for page_meta, image_path in zip(upload_schema.pages, page_image_paths):
            db_page = DocumentPage(
                document_id=db_doc.id,
                page_number=page_meta.page_number,
                image_path=image_path,
                width=page_meta.width,
                height=page_meta.height,
            )
            db.add(db_page)

        db.commit()
        db.refresh(db_doc)
        return db_doc

    def get_document_by_id(self, db: Session, document_id: str) -> Document | None:
        """Fetches a document record by its primary key."""
        return db.query(Document).filter(Document.id == document_id).first()

    def list_documents(
        self,
        db: Session,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Document]:
        """Retrieves documents with eager-loaded page quality relations, filtered by UUID or username."""
        query = db.query(Document).options(
            selectinload(Document.pages).selectinload(DocumentPage.quality)
        )

        if user_id:
            query = query.outerjoin(User, Document.owner_id == User.id).filter(
                (Document.owner_id == user_id) | (User.username == user_id)
            )

        return (
            query.order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_document_page(
        self, db: Session, document_id: str, page_number: int
    ) -> DocumentPage | None:
        """Fetches a specific page record for a given document."""
        return (
            db.query(DocumentPage)
            .filter(
                DocumentPage.document_id == document_id,
                DocumentPage.page_number == page_number,
            )
            .first()
        )


document_service = DocumentService()