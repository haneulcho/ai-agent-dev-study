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
        x, y, width, height = self.box
        if not all(0.0 <= value <= 1.0 for value in self.box):
            raise ValueError("crop values must be between 0 and 1")
        if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ValueError("crop box must have a positive size inside the image")
        return self


class CropJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Path
    targets: list[CropTarget] = Field(min_length=1)


class CropRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    jobs: list[CropJob] = Field(min_length=1)


def _inside_root(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path must stay inside project root: {path}")
    return resolved


def _load_recipe(path: Path) -> CropRecipe:
    with path.open(encoding="utf-8") as file:
        return CropRecipe.model_validate(json.load(file))


def _image_files(paths: Sequence[Path]) -> list[Path]:
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
    print(json.dumps({"items": list(items)}, ensure_ascii=False, indent=2))


def crop_command(args: argparse.Namespace) -> None:
    root = args.project_root.resolve()
    recipe = _load_recipe(args.recipe.resolve())
    items: list[dict[str, object]] = []

    for job in recipe.jobs:
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
            if not args.dry_run:
                save_png(cropped, output_path, overwrite=args.overwrite)
                item["sha256"] = sha256_file(output_path)
            items.append(item)

    _report(items)


def preprocess_command(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.resolve()
    variant = PreprocessVariant(args.variant)
    items: list[dict[str, object]] = []

    for source_path in _image_files(args.input):
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
    parser = argparse.ArgumentParser(
        description="Crop and preprocess Asterum OCR dataset images without changing originals"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    crop_parser = subparsers.add_parser("crop", help="Apply a versioned crop recipe")
    crop_parser.add_argument("--recipe", type=Path, required=True)
    crop_parser.add_argument("--project-root", type=Path, default=Path.cwd())
    crop_parser.add_argument("--dry-run", action="store_true")
    crop_parser.add_argument("--overwrite", action="store_true")
    crop_parser.set_defaults(handler=crop_command)

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
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.handler(args)
    except (FileExistsError, FileNotFoundError, OSError, ValueError, ValidationError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
