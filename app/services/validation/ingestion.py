import base64
import io
import uuid
from pathlib import Path
import pymupdf  # PyMuPDF
from PIL import Image, ImageOps

from app.core.config import settings
from app.schemas.document_schema import DocumentUploadResponse, PageMetadata


class DocumentIngestionService:
    """Handles document validation, PDF rendering, Base64 serialization,
    and converting uploads into PIL Images for downstream processing.
    """

    @staticmethod
    def validate_file(filename: str, file_size: int) -> str:
        """Validates file extension and size constraints.

        Returns file extension on success or raises ValueError.
        """
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(
                f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_MB}MB."
            )

        return ext

    @staticmethod
    def validate_batch(file_count: int) -> None:
        """Ensures the uploaded batch does not exceed limits."""
        if file_count > settings.MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size exceeds maximum limit of {settings.MAX_BATCH_SIZE} files."
            )

    @staticmethod
    def pil_to_base64(
        image: Image.Image, image_format: str = "PNG"
    ) -> str:
        """Converts a PIL Image object to a Base64 string for JSON API responses."""
        buffer = io.BytesIO()
        image.save(buffer, format=image_format)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/{image_format.lower()};base64,{encoded}"

    @staticmethod
    def base64_to_pil(base64_str: str) -> Image.Image:
        """Converts a Base64 string back into a PIL Image."""
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        image_data = base64.b64decode(base64_str)
        return Image.open(io.BytesIO(image_data))

    def _pdf_bytes_to_pil(self, pdf_bytes: bytes) -> list[Image.Image]:
        """Task: Render PDF pages into a list of PIL Images."""
        pil_images: list[Image.Image] = []
        pdf_doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap(dpi=settings.PDF_RENDER_DPI)
            pil_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            pil_images.append(ImageOps.exif_transpose(pil_img))

        pdf_doc.close()
        return pil_images

    def _image_bytes_to_pil(self, image_bytes: bytes) -> list[Image.Image]:
        """Task: Load single image bytes into a PIL Image list."""
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return [ImageOps.exif_transpose(pil_img)]

    def _bytes_to_pil_images(
        self, file_bytes: bytes, ext: str
    ) -> list[Image.Image]:
        """Acts as a traffic controller. It checks whether the uploaded file is a PDF or a regular image, 
        and passes the bytes to either _pdf_bytes_to_pil or _image_bytes_to_pil"""
        if ext == ".pdf":
            return self._pdf_bytes_to_pil(file_bytes)
        return self._image_bytes_to_pil(file_bytes)

    def _build_page_metadata(
        self, pil_images: list[Image.Image]
    ) -> list[PageMetadata]:
        """Task: Create PageMetadata schemas with dimensions and Base64 strings."""
        pages_metadata: list[PageMetadata] = []

        for index, img in enumerate(pil_images, start=1):
            pages_metadata.append(
                PageMetadata(
                    page_number=index,
                    width=img.width,
                    height=img.height,
                    image_base64=self.pil_to_base64(img),
                )
            )

        return pages_metadata

    def _build_upload_response(
        self,
        document_id: str,
        filename: str,
        ext: str,
        pages_metadata: list[PageMetadata],
    ) -> DocumentUploadResponse:
        """Task: Instantiate the final DocumentUploadResponse Pydantic schema."""
        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            file_type=ext.lstrip("."),
            page_count=len(pages_metadata),
            status="PENDING",
            pages=pages_metadata,
        )

    # --- Orchestrator Method ---

    def process_file_bytes(
        self, file_bytes: bytes, filename: str
    ) -> tuple[DocumentUploadResponse, list[Image.Image]]:
        """Task: High-level pipeline coordinator delegating tasks step-by-step."""
        # 1. Validate file constraints
        ext = self.validate_file(filename, len(file_bytes))

        # 2. Parse file bytes into PIL images
        pil_images = self._bytes_to_pil_images(file_bytes, ext)

        # 3. Generate page metadata & Base64 strings
        pages_metadata = self._build_page_metadata(pil_images)

        # 4. Construct response object
        response = self._build_upload_response(
            document_id=str(uuid.uuid4()),
            filename=filename,
            ext=ext,
            pages_metadata=pages_metadata,
        )

        return response, pil_images

ingestion_service = DocumentIngestionService()