from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CharacterDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    glyph_id: str = Field(pattern=r"^ast_[a-z0-9_]+$")
    source_svg: str = Field(min_length=1)
    ko_jamo: str = Field(min_length=1, max_length=1)
    kind: Literal["consonant", "vowel"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_jamo(self) -> Self:
        if unicodedata.normalize("NFC", self.ko_jamo) != self.ko_jamo:
            raise ValueError("ko_jamo must be NFC-normalized")
        return self


class AsterumMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    characters: list[CharacterDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_uniqueness(self) -> Self:
        for field_name in ("glyph_id", "source_svg", "ko_jamo"):
            values = [getattr(character, field_name) for character in self.characters]
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {field_name}")
        return self


def load_mapping(path: Path) -> AsterumMapping:
    return AsterumMapping.model_validate_json(path.read_text(encoding="utf-8"))
