from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from asterum.data.asset_audit import audit_assets, sha256_file
from asterum.data.characters import CHARACTER_SPECS

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ASSET_ROOT = PROJECT_ROOT / "assets/asterum"


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as temporary_file:
        json.dump(payload, temporary_file, ensure_ascii=False, indent=2)
        temporary_file.write("\n")
        temporary_path = Path(temporary_file.name)
    os.replace(temporary_path, path)


def import_characters(source_dir: Path, asset_root: Path, *, force: bool = False) -> Path:
    source_dir = source_dir.resolve()
    target_dir = asset_root / "characters/svg"
    mapping_path = asset_root / "mapping/asterum.mapping.v1.json"
    target_dir.mkdir(parents=True, exist_ok=True)

    character_records: list[dict[str, str]] = []
    for spec in CHARACTER_SPECS:
        source_path = source_dir / f"{spec.ko_jamo}.svg"
        if not source_path.is_file():
            raise FileNotFoundError(f"missing source SVG: {source_path}")

        target_path = target_dir / source_path.name
        if (
            target_path.exists()
            and not force
            and sha256_file(source_path) != sha256_file(target_path)
        ):
            raise FileExistsError(f"target differs; rerun with --force after review: {target_path}")
        shutil.copy2(source_path, target_path)
        character_records.append(
            {
                "glyph_id": spec.glyph_id,
                "source_svg": f"../characters/svg/{source_path.name}",
                "ko_jamo": spec.ko_jamo,
                "kind": spec.kind,
                "sha256": sha256_file(target_path),
            }
        )

    _atomic_write_json(mapping_path, {"version": "1.0.0", "characters": character_records})
    report = audit_assets(mapping_path)
    if not report.ok:
        issue_codes = ", ".join(issue.code for issue in report.issues)
        raise ValueError(f"imported assets failed audit: {issue_codes}")
    return mapping_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the 28 reviewed Asterum SVG files")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    mapping_path = import_characters(args.source, args.asset_root.resolve(), force=args.force)
    print(mapping_path)


if __name__ == "__main__":
    main()
