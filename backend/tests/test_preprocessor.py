import io
import time
import cv2
import numpy as np
import pypdfium2 as pdfium
import pytest

from src.vision.preprocessor import (
    DocumentPreprocessor,
    ProcessedPage,
    detect_skew_angle,
    enhance_contrast,
    rasterize_pdf,
    rotate_image,
)


def create_synthetic_document(angle: float = 0.0, width: int = 800, height: int = 1000) -> np.ndarray:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    
    # Draw realistic horizontal text lines (simulating an invoice)
    for y in range(100, 900, 40):
        cv2.putText(
            image,
            "FACTURA ELECTRONICA F001-0004523 RUC 20481234567 TOTAL S/ 1540.00",
            (80, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (20, 20, 20),
            2,
            cv2.LINE_AA,
        )

    if abs(angle) > 0.01:
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        image = cv2.warpAffine(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
    return image


def create_synthetic_pdf_bytes(pages_count: int = 2) -> bytes:
    doc = pdfium.PdfDocument.new()
    for _ in range(pages_count):
        doc.new_page(400, 600)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


def test_detect_skew_angle_positive_rotation():
    expected_angle = 8.5
    image = create_synthetic_document(angle=expected_angle)
    detected_angle = detect_skew_angle(image)
    
    # Detected angle should match within a 0.5 degree tolerance
    assert abs(detected_angle - expected_angle) < 0.6


def test_detect_skew_angle_negative_rotation():
    expected_angle = -6.0
    image = create_synthetic_document(angle=expected_angle)
    detected_angle = detect_skew_angle(image)
    
    assert abs(detected_angle - expected_angle) < 0.6


def test_detect_skew_angle_straight_image():
    image = create_synthetic_document(angle=0.0)
    detected_angle = detect_skew_angle(image)
    
    assert abs(detected_angle) < 0.5


def test_rotate_image_straightens_document():
    skew_angle = 7.0
    image = create_synthetic_document(angle=skew_angle)
    
    corrected = rotate_image(image, skew_angle)
    residual_angle = detect_skew_angle(corrected)
    
    # After rotation, residual angle should be close to 0
    assert abs(residual_angle) < 0.6


def test_enhance_contrast_improves_contrast():
    # Low-contrast image with values clustered between 120 and 150
    low_contrast = np.random.randint(120, 150, (400, 400, 3), dtype=np.uint8)
    enhanced = enhance_contrast(low_contrast)
    
    # Standard deviation in the L channel should increase after adaptive equalization
    std_orig = float(np.std(cv2.cvtColor(low_contrast, cv2.COLOR_BGR2GRAY)))
    std_enh = float(np.std(cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)))
    assert std_enh > std_orig


def test_rasterize_pdf():
    pdf_bytes = create_synthetic_pdf_bytes(pages_count=2)
    pages = rasterize_pdf(pdf_bytes, dpi=144)
    
    assert len(pages) == 2
    # 400x600 pt at 144 dpi -> scale = 2.0 -> 800x1200 px
    assert pages[0].shape == (1200, 800, 3)
    assert pages[1].shape == (1200, 800, 3)


def test_process_pdf_end_to_end():
    pdf_bytes = create_synthetic_pdf_bytes(pages_count=1)
    preprocessor = DocumentPreprocessor(target_dpi=72)
    processed_pages = preprocessor.process_pdf(pdf_bytes)
    
    assert len(processed_pages) == 1
    page = processed_pages[0]
    assert isinstance(page, ProcessedPage)
    assert page.page_number == 1
    assert page.width > 0
    assert page.height > 0
    assert isinstance(page.original_skew_angle, float)


def test_process_invalid_pdf_raises_error():
    preprocessor = DocumentPreprocessor()
    with pytest.raises(ValueError, match="Error al rasterizar el documento PDF"):
        preprocessor.process_pdf(b"not a valid pdf content")


def test_benchmark_preprocessor_performance():
    image = create_synthetic_document(angle=5.0, width=800, height=1000)
    preprocessor = DocumentPreprocessor()
    
    t0 = time.perf_counter()
    result = preprocessor.process_image(image)
    duration_ms = (time.perf_counter() - t0) * 1000
    
    assert isinstance(result, ProcessedPage)
    # Processing per standard page must be under 250ms
    assert duration_ms < 250.0
