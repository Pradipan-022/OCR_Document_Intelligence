from pydantic import BaseModel, ConfigDict, Field


class DocumentQualityReportSchema(BaseModel):
    """Pydantic schema representing document quality metrics and pipeline recommendations."""

    width: int = Field(..., description="Width of the image in pixels.")
    height: int = Field(..., description="Height of the image in pixels.")
    estimated_dpi: int = Field(..., description="Calculated or EXIF metadata DPI.")
    blur_score: float = Field(..., description="Variance of Laplacian focus score.")
    brightness_score: float = Field(..., description="Mean grayscale intensity (0-255).")
    contrast_score: float = Field(..., description="Standard deviation of pixel intensity.")
    skew_angle: float = Field(..., description="Detected rotation angle in degrees.")
    has_document_boundary: bool = Field(..., description="True if a 4-corner document contour is found.")
    resolution_warning: bool = Field(..., description="True if resolution is below optimal threshold.")
    quality_label: str = Field(..., description="'Good', 'Acceptable', 'Poor', or 'Needs manual review'.")
    recommended_profile: str = Field(..., description="Suggested preprocessing profile.")

    model_config = ConfigDict(from_attributes=True)