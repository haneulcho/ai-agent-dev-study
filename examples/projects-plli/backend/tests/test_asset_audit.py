from pathlib import Path

from asterum.data.asset_audit import audit_assets
from asterum.data.characters import CHARACTER_SPECS
from asterum.data.import_characters import import_characters

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = PROJECT_ROOT / "assets/asterum"


def test_repository_assets_pass_audit() -> None:
    report = audit_assets(ASSET_ROOT / "mapping/asterum.mapping.v1.json")

    assert report.ok, report.model_dump()
    assert report.character_count == 28


def test_character_import_is_reproducible(tmp_path: Path) -> None:
    source_dir = ASSET_ROOT / "characters/svg"
    imported_root = tmp_path / "asterum"

    mapping_path = import_characters(source_dir, imported_root)
    report = audit_assets(mapping_path)

    assert report.ok, report.model_dump()
    assert report.character_count == len(CHARACTER_SPECS)
