"""아스테룸 SVG와 문자 매핑이 학습 기준을 만족하는지 검사한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from asterum.data.characters import EXPECTED_JAMO
from asterum.data.files import sha256_file
from asterum.domain.mapping import load_mapping


class AuditIssue(BaseModel):
    """자산 검증에서 발견한 문제 한 건."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    path: str | None = None


class AssetAuditReport(BaseModel):
    """검사한 매핑 정보와 모든 문제를 담는 최종 보고서."""

    model_config = ConfigDict(extra="forbid")

    mapping_path: str
    mapping_version: str | None = None
    character_count: int = 0
    issues: list[AuditIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def _local_name(tag: str) -> str:
    """XML namespace가 붙은 태그에서 실제 태그 이름만 꺼낸다."""

    return tag.rsplit("}", maxsplit=1)[-1]


def audit_svg(path: Path) -> list[AuditIssue]:
    """SVG 한 파일의 기본 구조와 외부 실행 요소 포함 여부를 검사한다."""

    issues: list[AuditIssue] = []
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError, DefusedXmlException) as error:
        return [AuditIssue(code="INVALID_SVG", message=str(error), path=str(path))]
    if root is None:
        return [AuditIssue(code="INVALID_SVG", message="SVG root is missing", path=str(path))]

    if _local_name(root.tag) != "svg":
        issues.append(
            AuditIssue(code="INVALID_SVG_ROOT", message="root element must be svg", path=str(path))
        )

    # viewBox가 있어야 화면 크기와 관계없이 같은 비율로 글리프를 그릴 수 있다.
    view_box = root.attrib.get("viewBox")
    if view_box is None:
        issues.append(
            AuditIssue(code="MISSING_VIEWBOX", message="viewBox is required", path=str(path))
        )
    else:
        try:
            _, _, width, height = (float(value) for value in view_box.split())
            if width <= 0 or height <= 0:
                raise ValueError("viewBox dimensions must be positive")
        except ValueError as error:
            issues.append(AuditIssue(code="INVALID_VIEWBOX", message=str(error), path=str(path)))

    # 학습용 SVG에는 실제 윤곽 path가 있어야 하고 실행 가능한 요소는 없어야 한다.
    element_names = {_local_name(element.tag) for element in root.iter()}
    if "path" not in element_names:
        issues.append(
            AuditIssue(code="MISSING_PATH", message="at least one path is required", path=str(path))
        )
    for forbidden_tag in ("script", "foreignObject"):
        if forbidden_tag in element_names:
            issues.append(
                AuditIssue(
                    code="UNSAFE_SVG_ELEMENT",
                    message=f"{forbidden_tag} is not allowed",
                    path=str(path),
                )
            )

    # 다른 서버나 로컬 파일을 참조하면 결과가 재현되지 않으므로 내부 참조만 허용한다.
    for element in root.iter():
        for attribute_name, value in element.attrib.items():
            if _local_name(attribute_name) == "href" and value and not value.startswith("#"):
                issues.append(
                    AuditIssue(
                        code="EXTERNAL_SVG_REFERENCE",
                        message="external references are not allowed",
                        path=str(path),
                    )
                )
    return issues


def audit_assets(mapping_path: Path) -> AssetAuditReport:
    """매핑 전체와 연결된 28개 SVG의 경로·내용·checksum을 검사한다."""

    report = AssetAuditReport(mapping_path=str(mapping_path))
    try:
        mapping = load_mapping(mapping_path)
    except (OSError, UnicodeError, ValidationError) as error:
        report.issues.append(
            AuditIssue(code="INVALID_MAPPING", message=str(error), path=str(mapping_path))
        )
        return report

    # 먼저 매핑에 필수 자모 28개가 빠짐없이 들어 있는지 확인한다.
    report.mapping_version = mapping.version
    report.character_count = len(mapping.characters)
    actual_jamo = {character.ko_jamo for character in mapping.characters}
    missing_jamo = sorted(EXPECTED_JAMO - actual_jamo)
    unexpected_jamo = sorted(actual_jamo - EXPECTED_JAMO)
    if missing_jamo:
        report.issues.append(AuditIssue(code="MISSING_JAMO", message=", ".join(missing_jamo)))
    if unexpected_jamo:
        report.issues.append(AuditIssue(code="UNEXPECTED_JAMO", message=", ".join(unexpected_jamo)))

    # 각 매핑 항목이 안전한 경로의 실제 SVG를 가리키고 내용도 승인본과 같은지 확인한다.
    asset_root = mapping_path.parent.parent.resolve()
    seen_hashes: dict[str, Path] = {}
    for character in mapping.characters:
        svg_path = (mapping_path.parent / character.source_svg).resolve()
        if not svg_path.is_relative_to(asset_root):
            report.issues.append(
                AuditIssue(
                    code="SVG_PATH_OUTSIDE_ASSET_ROOT",
                    message=character.source_svg,
                    path=str(svg_path),
                )
            )
            continue
        if not svg_path.is_file():
            report.issues.append(
                AuditIssue(code="MISSING_SVG", message=character.ko_jamo, path=str(svg_path))
            )
            continue

        report.issues.extend(audit_svg(svg_path))
        actual_hash = sha256_file(svg_path)
        if actual_hash != character.sha256:
            report.issues.append(
                AuditIssue(
                    code="CHECKSUM_MISMATCH",
                    message=f"expected {character.sha256}, got {actual_hash}",
                    path=str(svg_path),
                )
            )
        if previous_path := seen_hashes.get(actual_hash):
            report.issues.append(
                AuditIssue(
                    code="DUPLICATE_SVG_CONTENT",
                    message=f"same content as {previous_path}",
                    path=str(svg_path),
                )
            )
        else:
            seen_hashes[actual_hash] = svg_path

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Asterum SVG assets and mapping")
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("assets/asterum/mapping/asterum.mapping.v1.json"),
    )
    args = parser.parse_args()
    report = audit_assets(args.mapping.resolve())
    print(json.dumps(report.model_dump() | {"ok": report.ok}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
