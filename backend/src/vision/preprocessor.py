import cv2
import numpy as np


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

    # Calculate bounding box dimensions of the rotated image to avoid clipping corners
    cos_val = abs(rotation_matrix[0, 0])
    sin_val = abs(rotation_matrix[0, 1])

    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))

    # Adjust transformation matrix to account for translation
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
