"""사용자가 검토한 28개 SVG를 프로젝트 자산과 매핑 파일로 가져온다."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from asterum.data.asset_audit import audit_assets
from asterum.data.characters import CHARACTER_SPECS
from asterum.data.files import sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ASSET_ROOT = PROJECT_ROOT / "assets/asterum"


def _atomic_write_json(path: Path, payload: object) -> None:
    """작성 도중 실패해도 기존 JSON이 깨지지 않도록 임시 파일을 완성한 뒤 교체한다."""

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
    """28개 SVG를 복사하고 각 파일의 checksum이 들어간 매핑 JSON을 생성한다."""

    source_dir = source_dir.resolve()
    target_dir = asset_root / "characters/svg"
    mapping_path = asset_root / "mapping/asterum.mapping.v1.json"
    target_dir.mkdir(parents=True, exist_ok=True)

    character_records: list[dict[str, str]] = []
    for spec in CHARACTER_SPECS:
        # 파일명에 있는 한글 자모는 최초 반입 때만 대응 관계를 찾는 데 사용한다.
        source_path = source_dir / f"{spec.ko_jamo}.svg"
        if not source_path.is_file():
            raise FileNotFoundError(f"missing source SVG: {source_path}")

        target_path = target_dir / source_path.name
        # 이미 있는 승인본과 내용이 다르면 실수로 덮어쓰지 않도록 기본 동작을 중단한다.
        if (
            target_path.exists()
            and not force
            and sha256_file(source_path) != sha256_file(target_path)
        ):
            raise FileExistsError(f"target differs; rerun with --force after review: {target_path}")
        shutil.copy2(source_path, target_path)
        # 매핑에는 원본 변경을 확인할 수 있도록 복사한 파일의 checksum도 함께 저장한다.
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
    # 파일 생성에 성공해도 구조나 개수가 틀릴 수 있으므로 같은 작업에서 다시 검증한다.
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
