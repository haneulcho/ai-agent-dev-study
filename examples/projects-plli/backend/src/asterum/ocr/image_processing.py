"""OCR 전에 반복해서 사용하는 이미지 입출력과 전처리 함수.

Pillow는 파일 형식·EXIF 방향·crop·저장을 맡고, OpenCV는 명암 보정과
이진화를 맡는다. 함수가 명령행 인자를 알지 않으므로 API와 학습 코드에서 재사용할 수 있다.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

# 정규화 crop 좌표의 순서는 x, y, width, height다. 모든 값은 0~1 범위다.
type NormalizedBox = tuple[float, float, float, float]
type UInt8Image = NDArray[np.uint8]

# Pillow가 기본 지원하지 않는 HEIC/HEIF 파일도 Image.open으로 읽을 수 있게 등록한다.
register_heif_opener()


class PreprocessVariant(StrEnum):
    """강의에서 원본과 비교할 세 가지 전처리 방식."""

    GRAYSCALE = "grayscale"
    CONTRAST = "contrast"
    BINARY = "binary"


def load_rgb_image(path: Path) -> Image.Image:
    """이미지를 열고 촬영 방향을 보정한 뒤 RGB 색상 형식으로 통일한다.

    스마트폰 사진은 픽셀을 돌리지 않고 EXIF에 방향만 기록할 수 있다. 이 값을 먼저
    적용해야 이후 crop 좌표가 화면에서 본 방향과 일치한다.
    """

    if not path.is_file():
        raise FileNotFoundError(path)

    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).convert("RGB")


def crop_normalized(image: Image.Image, box: NormalizedBox) -> Image.Image:
    """해상도에 독립적인 0~1 좌표를 실제 픽셀 좌표로 바꿔 이미지를 자른다.

    예를 들어 ``(0, 0, 0.5, 1)``은 이미지 크기와 관계없이 왼쪽 절반을 뜻한다.
    """

    x, y, width, height = box
    if not all(0.0 <= value <= 1.0 for value in box):
        raise ValueError("normalized crop values must be between 0 and 1")
    if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValueError("normalized crop box must have a positive size inside the image")

    # Pillow의 crop은 (왼쪽, 위, 오른쪽, 아래) 픽셀 좌표를 사용한다.
    left = round(image.width * x)
    top = round(image.height * y)
    right = round(image.width * (x + width))
    bottom = round(image.height * (y + height))
    if right <= left or bottom <= top:
        raise ValueError("crop box resolves to an empty pixel region")
    return image.crop((left, top, right, bottom))


def resize_max_side(image: Image.Image, max_side: int | None) -> Image.Image:
    """가로세로 비율을 유지하면서 긴 변만 지정 크기 이하로 줄인다.

    작은 이미지는 억지로 확대하지 않는다. 확대는 새로운 정보를 만들지 못하고 글자 경계만
    흐릴 수 있기 때문이다.
    """

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
    """RGB 이미지를 OCR 비교용 grayscale, contrast 또는 binary 이미지로 바꾼다.

    - ``grayscale``: 색상만 제거한 기본 비교본
    - ``contrast``: CLAHE로 영역별 명암 차이를 보강한 비교본
    - ``binary``: 대비 보정 후 글자와 배경을 흑백 두 값으로 나눈 비교본
    """

    # OpenCV가 처리할 수 있도록 Pillow 이미지를 NumPy 배열로 바꾼다.
    resized = resize_max_side(image.convert("RGB"), max_side)
    rgb: UInt8Image = np.asarray(resized, dtype=np.uint8)
    grayscale = cast(UInt8Image, cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY))

    if variant is PreprocessVariant.GRAYSCALE:
        result = grayscale
    else:
        # CLAHE는 사진 일부가 어둡거나 밝아도 작은 영역별로 대비를 보정한다.
        contrast = cast(
            UInt8Image,
            cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(grayscale),
        )
        if variant is PreprocessVariant.CONTRAST:
            result = contrast
        else:
            # 약한 blur로 점 노이즈를 줄인 뒤 Otsu 방식이 흑백 경계값을 자동 결정한다.
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
    """출력 폴더를 만들고 PNG로 저장하되 기본적으로 기존 파일을 보호한다."""

    if path.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
