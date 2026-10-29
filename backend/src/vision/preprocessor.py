from dataclasses import dataclass
from pathlib import Path
from typing import Union
import cv2
import numpy as np
import pypdfium2 as pdfium


@dataclass
class ProcessedPage:
    page_number: int
    image: np.ndarray
    original_skew_angle: float
    width: int
    height: int


def detect_skew_angle(image: np.ndarray, max_angle: float = 45.0) -> float:
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Otsu thresholding with text inverted to foreground (white text on black background)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Horizontal dilation to merge individual letters into continuous text lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 3))
    dilated = cv2.dilate(binary, kernel, iterations=2)

    # Detect horizontal lines using probabilistic Hough Transform
    edges = cv2.Canny(dilated, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=80,
        maxLineGap=20,
    )

    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line.flatten()
            if x2 == x1:
                continue
            angle = -np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) <= max_angle:
                angles.append(angle)

    if not angles:
        # Fallback to minimum area bounding rectangles on text contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) < 100:
                continue
            rect = cv2.minAreaRect(cnt)
            (w, h) = rect[1]
            angle = rect[2]
            if w < h:
                angle = angle - 90.0 if angle > 0 else angle + 90.0
            if abs(angle) <= max_angle:
                angles.append(angle)

    if not angles:
        return 0.0

    return float(np.median(angles))


def rotate_image(
    image: np.ndarray,
    angle: float,
    border_color: tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    if abs(angle) < 0.05:
        return image.copy()

    h, w = image.shape[:2]
    center = (w / 2.0, h / 2.0)

    # Negative angle counter-rotates the skewed document to upright orientation
    rotation_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)

    cos_val = abs(rotation_matrix[0, 0])
    sin_val = abs(rotation_matrix[0, 1])

    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))

    rotation_matrix[0, 2] += (new_w / 2.0) - center[0]
    rotation_matrix[1, 2] += (new_h / 2.0) - center[1]

    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_color,
    )
    return rotated


def enhance_contrast(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        cl = clahe.apply(l_channel)
        merged = cv2.merge((cl, a_channel, b_channel))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(image)


def rasterize_pdf(
    pdf_source: Union[str, Path, bytes],
    dpi: int = 300,
) -> list[np.ndarray]:
    try:
        if isinstance(pdf_source, (str, Path)):
            pdf = pdfium.PdfDocument(str(pdf_source))
        elif isinstance(pdf_source, bytes):
            pdf = pdfium.PdfDocument(pdf_source)
        else:
            raise ValueError("El origen del PDF debe ser una ruta válida o una secuencia de bytes.")
    except Exception as exc:
        raise ValueError(f"Error al rasterizar el documento PDF: {exc}") from exc

    scale = dpi / 72.0
    pages: list[np.ndarray] = []
    try:
        for page in pdf:
            bitmap = page.render(scale=scale)
            arr = bitmap.to_numpy().copy()
            pages.append(arr)
    finally:
        pdf.close()

    return pages


class DocumentPreprocessor:
    def __init__(
        self,
        target_dpi: int = 300,
        max_skew_angle: float = 45.0,
        enable_clahe: bool = True,
    ) -> None:
        self.target_dpi = target_dpi
        self.max_skew_angle = max_skew_angle
        self.enable_clahe = enable_clahe

    def process_image(self, image: np.ndarray, page_number: int = 1) -> ProcessedPage:
        skew_angle = detect_skew_angle(image, max_angle=self.max_skew_angle)
        deskewed = rotate_image(image, skew_angle)

        if self.enable_clahe:
            enhanced = enhance_contrast(deskewed)
        else:
            enhanced = deskewed

        h, w = enhanced.shape[:2]
        return ProcessedPage(
            page_number=page_number,
            image=enhanced,
            original_skew_angle=skew_angle,
            width=w,
            height=h,
        )

    def process_pdf(self, pdf_source: Union[str, Path, bytes]) -> list[ProcessedPage]:
        raw_pages = rasterize_pdf(pdf_source, dpi=self.target_dpi)
        processed: list[ProcessedPage] = []
        for idx, page_img in enumerate(raw_pages, start=1):
            processed.append(self.process_image(page_img, page_number=idx))
        return processed

    def process_file(self, file_path: Union[str, Path]) -> list[ProcessedPage]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        if path.suffix.lower() == ".pdf":
            return self.process_pdf(path)

        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"No se pudo cargar la imagen desde: {file_path}")

        return [self.process_image(image, page_number=1)]
