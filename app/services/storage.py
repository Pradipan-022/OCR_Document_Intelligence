import json
from pathlib import Path
from typing import Any, Optional
from PIL import Image
from app.core.config import settings


class StorageService:
    """Encapsulates all physical disk reading, writing, and path resolution for raw uploads,

    preprocessed images, and OCR JSON artifacts.
    """

    def __init__(self, upload_dir: Path = settings.UPLOAD_DIR):
        self.upload_dir = upload_dir

    def get_document_dir(
        self, document_id: str, user_id: Optional[str] = None
    ) -> Path:
        """Creates and returns tenant-isolated directory: uploads/{user_id}/{document_id} or uploads/guest/{document_id}."""
        user_folder = user_id if user_id else "guest"
        doc_dir = self.upload_dir / user_folder / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir

    def save_raw_file(
        self, doc_dir: Path, filename: str, file_bytes: bytes
    ) -> str:
        """Saves original raw upload file (PDF or Image) to disk."""
        raw_file_path = doc_dir / f"raw_{filename}"
        with open(raw_file_path, "wb") as f:
            f.write(file_bytes)
        return str(raw_file_path)

    def save_page_images(
        self, doc_dir: Path, pil_images: list[Image.Image]
    ) -> list[str]:
        """Saves rendered page PIL images as PNGs to disk."""
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
        """Orchestrates saving raw uploads and converted page images."""
        doc_dir = self.get_document_dir(
            document_id=document_id, user_id=user_id
        )
        raw_path = self.save_raw_file(doc_dir, filename, file_bytes)
        page_paths = self.save_page_images(doc_dir, pil_images)
        return raw_path, page_paths

    def save_processed_page_image(
        self,
        document_id: str,
        page_number: int,
        image: Image.Image,
        profile_name: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Saves a preprocessed/enhanced page image to disk."""
        doc_dir = self.get_document_dir(
            document_id=document_id, user_id=user_id
        )
        processed_path = (
            doc_dir / f"processed_page_{page_number}_{profile_name}.png"
        )
        image.save(processed_path, format="PNG")
        return str(processed_path)

    def save_ocr_result(
        self,
        document_id: str,
        page_number: int,
        ocr_payload: dict[str, Any],
        user_id: Optional[str] = None,
    ) -> str:
        """Saves standardized OCR JSON output for a page to disk."""
        doc_dir = self.get_document_dir(
            document_id=document_id, user_id=user_id
        )
        ocr_path = doc_dir / f"ocr_page_{page_number}.json"
        with open(ocr_path, "w", encoding="utf-8") as f:
            json.dump(ocr_payload, f, indent=2, ensure_ascii=False)
        return str(ocr_path)


storage_service = StorageService()