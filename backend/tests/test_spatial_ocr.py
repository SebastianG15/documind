import cv2
import numpy as np
import pytest

from src.vision.spatial_ocr import (
    OCRResult,
    SpatialOCREngine,
    SpatialToken,
    normalize_bbox,
)


def test_normalize_bbox_standard_polygon():
    raw_polygon = [[100, 200], [300, 200], [300, 400], [100, 400]]
    width = 1000
    height = 2000

    ymin, xmin, ymax, xmax = normalize_bbox(raw_polygon, width, height)

    assert ymin == 100
    assert xmin == 100
    assert ymax == 200
    assert xmax == 300
    assert 0 <= ymin <= ymax <= 1000
    assert 0 <= xmin <= xmax <= 1000


def test_normalize_bbox_clamps_out_of_bounds():
    raw_polygon = [[-50, -20], [1200, -20], [1200, 2500], [-50, 2500]]
    width = 1000
    height = 2000

    ymin, xmin, ymax, xmax = normalize_bbox(raw_polygon, width, height)

    assert ymin == 0
    assert xmin == 0
    assert ymax == 1000
    assert xmax == 1000


def test_spatial_token_and_ocr_result_dataclasses():
    token = SpatialToken(
        text="20481234567",
        confidence=0.985,
        bbox=(150, 200, 190, 450),
        raw_box=[[200, 150], [450, 150], [450, 190], [200, 190]],
    )
    assert token.text == "20481234567"
    assert token.confidence == 0.985
    assert token.bbox == (150, 200, 190, 450)

    ocr_result = OCRResult(
        page_number=1,
        tokens=[token],
        full_text="20481234567",
        width=1000,
        height=2000,
    )
    assert ocr_result.page_number == 1
    assert len(ocr_result.tokens) == 1
    assert ocr_result.full_text == "20481234567"


def test_spatial_ocr_extracts_tokens_from_image():
    # Create synthetic invoice crop with clear printed text
    image = np.full((300, 800, 3), 255, dtype=np.uint8)
    cv2.putText(
        image,
        "FACTURA F001-4920",
        (50, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (0, 0, 0),
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        "TOTAL 1500.00",
        (50, 200),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (0, 0, 0),
        3,
        cv2.LINE_AA,
    )

    ocr_engine = SpatialOCREngine(min_confidence=0.2)
    result = ocr_engine.extract_tokens(image, page_number=1)

    assert isinstance(result, OCRResult)
    assert result.page_number == 1
    assert result.width == 800
    assert result.height == 300
    assert len(result.tokens) >= 2

    # Verify all bounding boxes are within [0, 1000] and valid
    for token in result.tokens:
        ymin, xmin, ymax, xmax = token.bbox
        assert 0 <= ymin <= ymax <= 1000
        assert 0 <= xmin <= xmax <= 1000

    assert "FACTURA" in result.full_text.upper() or "TOTAL" in result.full_text.upper()


def test_spatial_ocr_empty_image_raises_error():
    ocr_engine = SpatialOCREngine()
    empty_image = np.zeros((0, 0, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="La imagen proporcionada para OCR está vacía o es inválida"):
        ocr_engine.extract_tokens(empty_image)
