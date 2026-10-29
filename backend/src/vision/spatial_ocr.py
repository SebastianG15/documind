from dataclasses import dataclass
from typing import Sequence, Union
import numpy as np
import torch


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


class SpatialOCREngine:
    def __init__(
        self,
        languages: list[str] | None = None,
        use_gpu: bool | None = None,
        min_confidence: float = 0.15,
        text_threshold: float = 0.5,
        link_threshold: float = 0.35,
        low_text: float = 0.35,
        mag_ratio: float = 1.0,
    ) -> None:
        self.languages = languages or ["es", "en"]
        self.use_gpu = torch.cuda.is_available() if use_gpu is None else use_gpu
        self.min_confidence = min_confidence
        self.text_threshold = text_threshold
        self.link_threshold = link_threshold
        self.low_text = low_text
        self.mag_ratio = mag_ratio
        self._reader = None

    @property
    def reader(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(self.languages, gpu=self.use_gpu)
        return self._reader

    def extract_tokens(
        self,
        image: np.ndarray,
        page_number: int = 1,
    ) -> OCRResult:
        if image is None or image.size == 0:
            raise ValueError("La imagen proporcionada para OCR está vacía o es inválida.")

        h, w = image.shape[:2]
        raw_results = self.reader.readtext(
            image,
            text_threshold=self.text_threshold,
            link_threshold=self.link_threshold,
            low_text=self.low_text,
            mag_ratio=self.mag_ratio,
        )

        tokens: list[SpatialToken] = []
        full_text_parts: list[str] = []

        for bbox_pts, text, confidence in raw_results:
            clean_text = str(text).strip()
            if not clean_text or float(confidence) < self.min_confidence:
                continue

            int_pts = [[int(pt[0]), int(pt[1])] for pt in bbox_pts]
            normalized = normalize_bbox(int_pts, img_width=w, img_height=h)

            token = SpatialToken(
                text=clean_text,
                confidence=float(confidence),
                bbox=normalized,
                raw_box=int_pts,
            )
            tokens.append(token)
            full_text_parts.append(clean_text)

        return OCRResult(
            page_number=page_number,
            tokens=tokens,
            full_text=" ".join(full_text_parts),
            width=w,
            height=h,
        )
