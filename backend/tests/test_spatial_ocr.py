import pytest
from src.vision.spatial_ocr import SpatialToken, OCRResult, normalize_bbox


def test_normalize_bbox_standard_polygon():
    # Polygon with 4 corners in pixel space (1000x2000 image)
    raw_polygon = [[100, 200], [300, 200], [300, 400], [100, 400]]
    width = 1000
    height = 2000

    # In pixels: x is [100, 300], y is [200, 400]
    # In normalized [0, 1000]:
    # xmin = 100 / 1000 * 1000 = 100
    # xmax = 300 / 1000 * 1000 = 300
    # ymin = 200 / 2000 * 1000 = 100
    # ymax = 400 / 2000 * 1000 = 200
    ymin, xmin, ymax, xmax = normalize_bbox(raw_polygon, width, height)

    assert ymin == 100
    assert xmin == 100
    assert ymax == 200
    assert xmax == 300
    assert 0 <= ymin <= ymax <= 1000
    assert 0 <= xmin <= xmax <= 1000


def test_normalize_bbox_clamps_out_of_bounds():
    # Polygon with coordinates exceeding image bounds
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
