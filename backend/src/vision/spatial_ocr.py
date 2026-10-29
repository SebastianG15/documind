from dataclasses import dataclass
from typing import Sequence, Union


@dataclass
class SpatialToken:
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (ymin, xmin, ymax, xmax) normalized to [0, 1000]
    raw_box: list[list[int]]


@dataclass
class OCRResult:
    page_number: int
    tokens: list[SpatialToken]
    full_text: str
    width: int
    height: int


def normalize_bbox(
    box_points: Sequence[Sequence[Union[int, float]]],
    img_width: int,
    img_height: int,
    target_scale: int = 1000,
) -> tuple[int, int, int, int]:
    if img_width <= 0 or img_height <= 0:
        return (0, 0, 0, 0)

    xs = [pt[0] for pt in box_points]
    ys = [pt[1] for pt in box_points]

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)

    xmin = int(round(max(0.0, min(float(min_x), float(img_width))) / img_width * target_scale))
    xmax = int(round(max(0.0, min(float(max_x), float(img_width))) / img_width * target_scale))
    ymin = int(round(max(0.0, min(float(min_y), float(img_height))) / img_height * target_scale))
    ymax = int(round(max(0.0, min(float(max_y), float(img_height))) / img_height * target_scale))

    xmin = max(0, min(target_scale, xmin))
    xmax = max(0, min(target_scale, xmax))
    ymin = max(0, min(target_scale, ymin))
    ymax = max(0, min(target_scale, ymax))

    return (ymin, xmin, ymax, xmax)
