from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

type NormalizedBox = tuple[float, float, float, float]
type UInt8Image = NDArray[np.uint8]

register_heif_opener()


class PreprocessVariant(StrEnum):
    GRAYSCALE = "grayscale"
    CONTRAST = "contrast"
    BINARY = "binary"


def load_rgb_image(path: Path) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(path)

    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).convert("RGB")


def crop_normalized(image: Image.Image, box: NormalizedBox) -> Image.Image:
    x, y, width, height = box
    if not all(0.0 <= value <= 1.0 for value in box):
        raise ValueError("normalized crop values must be between 0 and 1")
    if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValueError("normalized crop box must have a positive size inside the image")

    left = round(image.width * x)
    top = round(image.height * y)
    right = round(image.width * (x + width))
    bottom = round(image.height * (y + height))
    if right <= left or bottom <= top:
        raise ValueError("crop box resolves to an empty pixel region")
    return image.crop((left, top, right, bottom))


def resize_max_side(image: Image.Image, max_side: int | None) -> Image.Image:
    if max_side is None:
        return image.copy()
    if max_side <= 0:
        raise ValueError("max_side must be positive")

    largest_side = max(image.size)
    if largest_side <= max_side:
        return image.copy()

    scale = max_side / largest_side
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def preprocess_image(
    image: Image.Image,
    variant: PreprocessVariant,
    *,
    max_side: int | None = None,
) -> Image.Image:
    resized = resize_max_side(image.convert("RGB"), max_side)
    rgb: UInt8Image = np.asarray(resized, dtype=np.uint8)
    grayscale = cast(UInt8Image, cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY))

    if variant is PreprocessVariant.GRAYSCALE:
        result = grayscale
    else:
        contrast = cast(
            UInt8Image,
            cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(grayscale),
        )
        if variant is PreprocessVariant.CONTRAST:
            result = contrast
        else:
            blurred = cast(UInt8Image, cv2.GaussianBlur(contrast, (3, 3), 0))
            result = cast(
                UInt8Image,
                cv2.threshold(
                    blurred,
                    0,
                    255,
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU,
                )[1],
            )

    return Image.fromarray(result, mode="L")


def save_png(image: Image.Image, path: Path, *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
