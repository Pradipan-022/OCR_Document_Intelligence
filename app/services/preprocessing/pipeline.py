import cv2
import numpy as np
from PIL import Image


class ImagePreprocessingPipeline:
    """Executes targeted OpenCV image transformations based on selected quality profiles."""

    # --- Single-Task Format Converters ---

    def _pil_to_cv2(self, pil_image: Image.Image) -> np.ndarray:
        """Task: Convert PIL Image to OpenCV BGR NumPy array."""
        rgb_np = np.array(pil_image.convert("RGB"))
        return cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR)

    def _cv2_to_pil(self, cv_image: np.ndarray) -> Image.Image:
        """Task: Convert OpenCV NumPy array back to PIL Image (RGB or Grayscale)."""
        if len(cv_image.shape) == 2:  # Grayscale
            return Image.fromarray(cv_image)
        rgb_np = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_np)

    # --- Single-Task Preprocessing Profile Implementations ---

    def _profile_original(self, cv_image: np.ndarray) -> np.ndarray:
        """Task: Return copy of image without modification."""
        return cv_image.copy()

    def _profile_basic(self, cv_image: np.ndarray) -> np.ndarray:
        """Task: Standard conversion to grayscale and bilateral denoising."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        # Bilateral filter reduces noise while preserving strong text edges
        return cv2.bilateralFilter(gray, d=9, sigmaColor=30, sigmaSpace=30)

    def _profile_low_light(self, cv_image: np.ndarray) -> np.ndarray:
        """Task: Enhance underexposed text using CLAHE and adaptive thresholding."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        # CLAHE redistributes local contrast across tiles
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        # Convert to binary high-contrast text layout
        return cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )
    
    def _profile_overexposed(self, cv_image: np.ndarray) -> np.ndarray:
        """Task: Recover text from bright/glare images via gamma compression and adaptive thresholding."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Gamma correction (gamma=2.0) darkens overexposed regions to recover text contrast
        gamma = 2.0
        lookup_table = np.array(
            [((i / 255.0) ** gamma) * 255 for i in np.arange(0, 256)]
        ).astype("uint8")
        darkened = cv2.LUT(gray, lookup_table)

        # Apply wider window adaptive thresholding for washed out backgrounds
        return cv2.adaptiveThreshold(
            darkened,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,
            4,
        )

    def _profile_skewed(self, cv_image: np.ndarray) -> np.ndarray:
        """Task: Rotate and deskew text contours back to horizontal orientation."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        pts = cv2.findNonZero(thresh)

        if pts is None or len(pts) == 0:
            return cv_image

        angle = cv2.minAreaRect(pts)[-1]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        # Calculate rotation matrix around image center
        h, w = cv_image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        return cv2.warpAffine(
            cv_image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _profile_noisy_scan(self, cv_image: np.ndarray) -> np.ndarray:
        """Task: Remove background speckles using median filtering and morphology."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        # Median blur removes salt-and-pepper scanner noise
        median = cv2.medianBlur(gray, 3)
        # Morphological opening (erosion -> dilation) clears tiny artifacts
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        return cv2.morphologyEx(median, cv2.MORPH_OPEN, kernel)

    def _profile_small_text(self, cv_image: np.ndarray) -> np.ndarray:
        """Task: Upscale image 2x and apply unsharp masking sharpening."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        # Upscale dimensions using Bicubic interpolation
        upscaled = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        # Unsharp mask formula: Output = Original + (Original - GaussianBlur) * Weight
        blurred = cv2.GaussianBlur(upscaled, (0, 0), 3.0)
        return cv2.addWeighted(upscaled, 1.5, blurred, -0.5, 0)

    # --- Master Orchestrator Method ---

    def process(
        self, pil_image: Image.Image, profile_name: str = "basic"
    ) -> tuple[Image.Image, str]:
        """Task: Route PIL Image to the requested profile (supports user overrides)."""
        profile_map = {
            "original": self._profile_original,
            "basic": self._profile_basic,
            "low_light": self._profile_low_light,
            "overexposed": self._profile_overexposed,
            "skewed": self._profile_skewed,
            "noisy_scan": self._profile_noisy_scan,
            "small_text": self._profile_small_text,
        }

        # Fallback to 'basic' if profile is invalid
        selected_profile = profile_name if profile_name in profile_map else "basic"
        transform_func = profile_map[selected_profile]

        cv_img = self._pil_to_cv2(pil_image)
        transformed_cv = transform_func(cv_img)
        processed_pil = self._cv2_to_pil(transformed_cv)

        return processed_pil, selected_profile


preprocessing_pipeline = ImagePreprocessingPipeline()