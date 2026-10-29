import cv2
import numpy as np
import pytest

from src.vision.preprocessor import detect_skew_angle, rotate_image


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
