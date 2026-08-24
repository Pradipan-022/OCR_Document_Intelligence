from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class DocumentPageQualitySchema(BaseModel):
    """Pydantic schema representing document quality metrics and pipeline recommendations."""

    id: str = Field(..., description="Unique identifier of the quality report.")
    page_id: str = Field(..., description="ID of the document page associated with this quality report.")
    blur_score: float = Field(..., description="Variance of Laplacian focus score.")
    brightness_score: float = Field(..., description="Mean grayscale intensity (0-255).")
    contrast_score: float = Field(..., description="Standard deviation of pixel intensity.")
    skew_angle: float = Field(..., description="Detected rotation angle in degrees.")
    estimated_dpi: int = Field(..., description="Calculated or EXIF metadata DPI.")
    has_document_boundary: bool = Field(..., description="True if a 4-corner document contour is found.")
    resolution_warning: bool = Field(..., description="True if resolution is below optimal threshold.")
    quality_label: str = Field(..., description="Overall quality classification of the document page.")
    recommended_profile: str = Field(..., description="Suggested preprocessing profile.")
    applied_profile: Optional[str] = Field(
        None,
        description="Preprocessing profile that was actually applied to the page."
    )
    processed_image_path: Optional[str] = Field(
        None,
        description="File path to the processed page image stored on disk."
    )

    model_config = ConfigDict(from_attributes=True)
    
class PreprocessPageRequest(BaseModel):
    """Payload for manual profile overrides."""

    override_profile: Optional[str] = Field(
        None,
        description="Optional profile override: 'original', 'basic', 'low_light', 'skewed', 'noisy_scan', 'small_text'",
    )


class BatchPreprocessingResponse(BaseModel):
    """Response returned when processing all pages of a document."""

    document_id: str
    processed_pages: list[DocumentPageQualitySchema]