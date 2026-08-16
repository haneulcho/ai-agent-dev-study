"""학습용 원본 이미지를 crop하거나 OCR 전처리 이미지로 만드는 CLI.

이 파일은 명령행 인자와 작업 순서를 담당한다. 실제 이미지 변환 알고리즘은
``asterum.ocr.image_processing``에 두어 API나 학습 코드에서도 재사용할 수 있게 한다.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from asterum.data.files import sha256_file
from asterum.ocr.image_processing import (
    PreprocessVariant,
    crop_normalized,
    load_rgb_image,
    preprocess_image,
    save_png,
)

SUPPORTED_IMAGE_SUFFIXES = {".heic", ".heif", ".jpeg", ".jpg", ".png", ".webp"}


class CropTarget(BaseModel):
    """원본 이미지에서 잘라낼 영역 하나와 저장 경로."""

    model_config = ConfigDict(extra="forbid")

    output: Path
    box: tuple[
        float,
        float,
        float,
        float,
    ] = Field(description="Normalized x, y, width, height")

    @model_validator(mode="after")
    def validate_box(self) -> CropTarget:
        """정규화 좌표가 원본 이미지 바깥으로 나가지 않는지 확인한다."""

        x, y, width, height = self.box
        if not all(0.0 <= value <= 1.0 for value in self.box):
            raise ValueError("crop values must be between 0 and 1")
        if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ValueError("crop box must have a positive size inside the image")
        return self


class CropJob(BaseModel):
    """원본 이미지 하나와 그 이미지에서 만들 crop 목록."""

    model_config = ConfigDict(extra="forbid")

    source: Path
    targets: list[CropTarget] = Field(min_length=1)


class CropRecipe(BaseModel):
    """여러 원본의 crop 작업을 한 번에 재현하는 versioned 설정."""

    model_config = ConfigDict(extra="forbid")

    version: str
    jobs: list[CropJob] = Field(min_length=1)


def _inside_root(path: Path, root: Path) -> Path:
    """recipe가 프로젝트 밖의 파일을 읽거나 쓰지 못하게 경로를 제한한다."""

    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path must stay inside project root: {path}")
    return resolved


def _load_recipe(path: Path) -> CropRecipe:
    """JSON recipe를 읽고 누락·오타·잘못된 좌표를 Pydantic으로 검증한다."""

    with path.open(encoding="utf-8") as file:
        return CropRecipe.model_validate(json.load(file))


def _image_files(paths: Sequence[Path]) -> list[Path]:
    """파일과 디렉터리 입력을 실제 처리할 이미지 파일 목록으로 펼친다."""

    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                candidate
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
            )
        elif path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
            files.append(path)
        else:
            raise ValueError(f"unsupported image path: {path}")
    return files


def _report(items: Iterable[dict[str, object]]) -> None:
    """사람과 후속 스크립트가 모두 읽을 수 있도록 결과를 JSON으로 출력한다."""

    print(json.dumps({"items": list(items)}, ensure_ascii=False, indent=2))


def crop_command(args: argparse.Namespace) -> None:
    """crop recipe를 순서대로 실행하고 각 결과의 크기와 checksum을 보고한다."""

    root = args.project_root.resolve()
    recipe = _load_recipe(args.recipe.resolve())
    items: list[dict[str, object]] = []

    for job in recipe.jobs:
        # 같은 원본에서 여러 영역을 자를 수 있으므로 원본은 작업당 한 번만 연다.
        source_path = _inside_root(root / job.source, root)
        source = load_rgb_image(source_path)
        for target in job.targets:
            output_path = _inside_root(root / target.output, root)
            cropped = crop_normalized(source, target.box)
            item: dict[str, object] = {
                "source": str(job.source),
                "output": str(target.output),
                "width": cropped.width,
                "height": cropped.height,
                "status": "validated" if args.dry_run else "written",
            }
            # dry-run은 실제 파일을 만들지 않고 경로와 crop 크기까지만 검증한다.
            if not args.dry_run:
                save_png(cropped, output_path, overwrite=args.overwrite)
                item["sha256"] = sha256_file(output_path)
            items.append(item)

    _report(items)


def preprocess_command(args: argparse.Namespace) -> None:
    """한 개 이상의 입력을 선택한 OCR 전처리 방식으로 변환한다."""

    output_dir = args.output_dir.resolve()
    variant = PreprocessVariant(args.variant)
    items: list[dict[str, object]] = []

    for source_path in _image_files(args.input):
        # 원본 파일은 그대로 두고 출력 디렉터리에 variant 이름이 붙은 PNG를 만든다.
        image = load_rgb_image(source_path.resolve())
        processed = preprocess_image(image, variant, max_side=args.max_side)
        output_path = output_dir / f"{source_path.stem}.{variant.value}.png"
        save_png(processed, output_path, overwrite=args.overwrite)
        items.append(
            {
                "source": str(source_path),
                "output": str(output_path),
                "variant": variant.value,
                "width": processed.width,
                "height": processed.height,
                "sha256": sha256_file(output_path),
            }
        )

    _report(items)


def build_parser() -> argparse.ArgumentParser:
    """``crop``과 ``preprocess`` 하위 명령의 사용법을 정의한다."""

    parser = argparse.ArgumentParser(
        description="Crop and preprocess Asterum OCR dataset images without changing originals"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # crop 명령: 사람이 검토한 좌표를 recipe로 반복 적용한다.
    crop_parser = subparsers.add_parser("crop", help="Apply a versioned crop recipe")
    crop_parser.add_argument("--recipe", type=Path, required=True)
    crop_parser.add_argument("--project-root", type=Path, default=Path.cwd())
    crop_parser.add_argument("--dry-run", action="store_true")
    crop_parser.add_argument("--overwrite", action="store_true")
    crop_parser.set_defaults(handler=crop_command)

    # preprocess 명령: OCR에서 비교할 흑백·대비·이진화 이미지를 생성한다.
    preprocess_parser = subparsers.add_parser(
        "preprocess", help="Create an OCR preprocessing variant"
    )
    preprocess_parser.add_argument("--input", type=Path, nargs="+", required=True)
    preprocess_parser.add_argument("--output-dir", type=Path, required=True)
    preprocess_parser.add_argument(
        "--variant",
        choices=[variant.value for variant in PreprocessVariant],
        default=PreprocessVariant.CONTRAST.value,
    )
    preprocess_parser.add_argument("--max-side", type=int, default=2000)
    preprocess_parser.add_argument("--overwrite", action="store_true")
    preprocess_parser.set_defaults(handler=preprocess_command)
    return parser


def main() -> None:
    """CLI를 실행하고 예상 가능한 사용자 입력 오류를 짧은 메시지로 바꾼다."""

    parser = build_parser()
    args = parser.parse_args()
    try:
        args.handler(args)
    except (FileExistsError, FileNotFoundError, OSError, ValueError, ValidationError) as error:
        # 긴 traceback 대신 바로 수정할 수 있는 원인만 보여 준다.
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
