"""아스테룸 글리프와 한글 자모를 연결하는 JSON 매핑 계약."""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CharacterDefinition(BaseModel):
    """아스테룸 문자 한 개의 식별자, SVG, 한글 자모와 checksum."""

    model_config = ConfigDict(extra="forbid")

    glyph_id: str = Field(pattern=r"^ast_[a-z0-9_]+$")
    source_svg: str = Field(min_length=1)
    ko_jamo: str = Field(min_length=1, max_length=1)
    kind: Literal["consonant", "vowel"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_jamo(self) -> Self:
        """같아 보이는 한글이 서로 다른 유니코드 배열로 저장되지 않게 한다."""

        if unicodedata.normalize("NFC", self.ko_jamo) != self.ko_jamo:
            raise ValueError("ko_jamo must be NFC-normalized")
        return self


class AsterumMapping(BaseModel):
    """한 버전에서 사용하는 전체 문자 목록."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    characters: list[CharacterDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_uniqueness(self) -> Self:
        """문자·SVG·자모의 역매핑이 모호해지지 않도록 중복을 막는다."""

        for field_name in ("glyph_id", "source_svg", "ko_jamo"):
            values = [getattr(character, field_name) for character in self.characters]
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {field_name}")
        return self


def load_mapping(path: Path) -> AsterumMapping:
    """JSON 파일을 읽고 모든 매핑 규칙을 검증해 객체로 반환한다."""

    return AsterumMapping.model_validate_json(path.read_text(encoding="utf-8"))
