from pathlib import Path
from PIL import Image
from typing import Optional
from app.core.config import settings


class StorageService:
    """Handles physical file operations on disk."""

    def __init__(self, upload_dir: Path = settings.UPLOAD_DIR):
        self.upload_dir = upload_dir

    def get_document_dir(self, document_id: str, user_id: Optional[str] = None) -> Path:
        """
        Creates and returns a dedicated folder for a document under user-specific path:
        - With user_id: uploads/{user_id}/{document_id}
        - Without user_id: uploads/guest/{document_id}
        """
        user_folder = user_id if user_id else "guest"
        doc_dir = self.upload_dir / user_folder / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir

    def _save_raw_file(self, doc_dir: Path, filename: str, file_bytes: bytes) -> str:
        """Helper: Saves original raw upload file (PDF or Image) to disk."""
        raw_file_path = doc_dir / f"raw_{filename}"
        with open(raw_file_path, "wb") as f:
            f.write(file_bytes)
        return str(raw_file_path)

    def _save_page_images(
        self, doc_dir: Path, pil_images: list[Image.Image]
    ) -> list[str]:
        """Helper: Saves each converted page PIL Image as a PNG on disk."""
        page_paths: list[str] = []
        for index, img in enumerate(pil_images, start=1):
            page_path = doc_dir / f"page_{index}.png"
            img.save(page_path, format="PNG")
            page_paths.append(str(page_path))
        return page_paths

    def save_document_files(
        self,
        document_id: str,
        filename: str,
        file_bytes: bytes,
        pil_images: list[Image.Image],
        user_id: Optional[str] = None,
    ) -> tuple[str, list[str]]:
        """Orchestrates saving the raw file and page images to disk."""
        doc_dir = self.get_document_dir(document_id=document_id, user_id=user_id)
        raw_path = self._save_raw_file(doc_dir, filename, file_bytes)
        page_paths = self._save_page_images(doc_dir, pil_images)
        return raw_path, page_paths


storage_service = StorageService()