import cv2
import numpy as np
from PIL import Image

from app.schemas.quality_schema import DocumentQualityReportSchema

class DocumentQualityAssessor:
    """Evaluates physical and visual properties of document images.

    Each internal helper function performs exactly one single calculation task."""
    
    MIN_RECOMMENDED_DPI: int = 150
    MIN_RECOMMENDED_DIM: int = 800
    
    # Helper Funcs
    
    def _to_grayscale_array(self, pil_image: Image.Image) -> np.ndarray:
        """Task: Convert PIL Image to an OpenCV grayscale NumPy array."""
        rgb_np = np.array(pil_image.convert("RGB"))
        return cv2.cvtColor(rgb_np, cv2.COLOR_RGB2GRAY)
    
    def _estimate_dpi(self, pil_image: Image.Image) -> int:
        """Task: Read EXIF DPI metadata or estimate DPI using standard A4 dimensions."""
        dpi_tuple = pil_image.info.get("dpi")        
        if dpi_tuple and dpi_tuple[0] > 0:
            return int(dpi_tuple[0])
        
        width, height = pil_image.size
        estimated_dpi = int(min(width,height) / 8.27)
        return max(estimated_dpi, 72)
    
    def _compute_blur_score(self, gray: np.ndarray) -> float:
        """Task: Calculate focus sharpess using Variance of Laplacian."""
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    
    def _compute_brightness(self, gray:np.ndarray) -> float:
        """Task: Calculate mean grayscale pixel intensity."""
        mean_val, _ = cv2.meanStdDev(gray)
        return float(mean_val[0][0])
    
    def _compute_contrast(self, gray: np.ndarray) -> float:
        """Task: Calculate standard deviation of pixel intensities."""
        _, std_dev = cv2.meanStdDev(gray)
        return float(std_dev[0][0])        
    
    def _detect_skew_angle(self, gray: np.ndarray) -> float:
        """Task: Estimate dominant text rotation angle in [-45, 45] degrees range."""
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        pts = cv2.findNonZero(thresh)
        
        if pts is None or len(pts) == 0:
            return 0.0
        
        angle = cv2.minAreaRect(pts)[-1]
        if angle < -45:
            return float(-(90 - angle))
        elif angle > 45:
            return float(90 - angle)
        return float(-angle)
    
    def _detect_document_boundary(self, gray: np.ndarray) -> bool:
        """Task: Check for a closed 4-sided contour occupying >30% of total image area."""
        blurred = cv2.GaussianBlur(gray, (5,5),0)
        edged = cv2.Canny(blurred, 50, 200)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        img_area = gray.shape[0] * gray.shape[1]
        for cnt in contours:
            perimeter = cv2. arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * perimeter, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                if cv2.contourArea(cnt) > 0.30 * img_area:
                    return True
        return False

    def _check_resolution_suitability(self, dpi: int, width: int, height: int)     -> bool:
        """Task: Check if image resolution falls below target processing thresholds."""
        return dpi < self.MIN_RECOMMENDED_DPI or min(width, height) < self.MIN_RECOMMENDED_DIM
    
    def _determine_quality_label(
        self,
        blur_score: float,
        brightness: float,
        contrast: float,
        skew_angle: float,
        has_boundary: bool,
        resolution_warning: bool,
    ) -> str:
        """Task: Evaluate individual metrics to categorize overall document quality."""
        if blur_score < 50.0 or (resolution_warning and not has_boundary):
            return "Needs manual review"

        if (
            abs(skew_angle) > 10.0
            or contrast < 40.0
            or brightness < 60.0
            or brightness > 220.0
        ):
            return "Poor"

        if (
            blur_score < 200.0
            or abs(skew_angle) > 2.0
            or contrast < 55.0
            or resolution_warning
        ):
            return "Acceptable"

        return "Good"

    def _recommend_preprocessing_profile(
        self,
        blur_score: float,
        brightness: float,
        contrast: float,
        skew_angle: float,
        estimated_dpi: int,
        quality_label: str,
    ) -> str:
        """Task: Route metric evaluation to the optimal target transformation profile."""
        if quality_label == "Good":
            return "original"
        if blur_score < 100.0 or estimated_dpi < 150:
            return "small_text"
        if brightness < 80.0 or brightness > 210.0 or contrast < 40.0:
            return "low_light"
        if abs(skew_angle) > 3.0:
            return "skewed"
        if contrast < 55.0:
            return "noisy_scan"
        return "basic"
    
    #Orchestration Method
    def analyze(self, pil_image: Image.Image) -> DocumentQualityReportSchema:
        """Task: Coordinate individual quality checks step-by-step and return structured schema."""
        gray = self._to_grayscale_array(pil_image)
        width, height = pil_image.size
        
        dpi = self._estimate_dpi(pil_image)
        blur = self._compute_blur_score(gray)
        brightness = self._compute_brightness(gray)
        contrast = self._compute_contrast(gray)
        skew = self._detect_skew_angle(gray)
        has_boundary = self._detect_document_boundary(gray)
        res_warning = self._check_resolution_suitability(dpi, width, height)
        
        label = self._determine_quality_label(
            blur_score=blur,
            brightness=brightness,
            contrast=contrast,
            skew_angle=skew,
            has_boundary=has_boundary,
            resolution_warning=res_warning,
        )
        
        profile = self._recommend_preprocessing_profile(
            blur_score=blur,
            brightness=brightness,
            contrast=contrast,
            skew_angle=skew,
            estimated_dpi=dpi,
            quality_label=label,
        )
        
        return DocumentQualityReportSchema(
            width=width,
            height=height,
            estimated_dpi=dpi,
            blur_score=round(blur, 2),
            brightness_score=round(brightness, 2),
            contrast_score=round(contrast, 2),
            skew_angle=round(skew, 2),
            has_document_boundary=has_boundary,
            resolution_warning=res_warning,
            quality_label=label,
            recommended_profile=profile,
        )
        
quality_assessor = DocumentQualityAssessor()