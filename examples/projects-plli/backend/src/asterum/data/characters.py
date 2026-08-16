"""프로젝트가 공식적으로 지원하는 아스테룸 문자 28개의 기준 목록."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CharacterSpec:
    """안정적인 문자 ID와 대응 한글 자모의 최소 정보."""

    glyph_id: str
    ko_jamo: str
    kind: Literal["consonant", "vowel"]


# 순서는 매핑을 새로 만들 때도 일정하게 유지해 사람이 diff를 읽기 쉽게 한다.
CHARACTER_SPECS = (
    CharacterSpec("ast_giyeok", "ㄱ", "consonant"),
    CharacterSpec("ast_nieun", "ㄴ", "consonant"),
    CharacterSpec("ast_digeut", "ㄷ", "consonant"),
    CharacterSpec("ast_rieul", "ㄹ", "consonant"),
    CharacterSpec("ast_mieum", "ㅁ", "consonant"),
    CharacterSpec("ast_bieup", "ㅂ", "consonant"),
    CharacterSpec("ast_siot", "ㅅ", "consonant"),
    CharacterSpec("ast_ieung", "ㅇ", "consonant"),
    CharacterSpec("ast_jieut", "ㅈ", "consonant"),
    CharacterSpec("ast_chieut", "ㅊ", "consonant"),
    CharacterSpec("ast_kieuk", "ㅋ", "consonant"),
    CharacterSpec("ast_tieut", "ㅌ", "consonant"),
    CharacterSpec("ast_pieup", "ㅍ", "consonant"),
    CharacterSpec("ast_hieut", "ㅎ", "consonant"),
    CharacterSpec("ast_a", "ㅏ", "vowel"),
    CharacterSpec("ast_ae", "ㅐ", "vowel"),
    CharacterSpec("ast_ya", "ㅑ", "vowel"),
    CharacterSpec("ast_yae", "ㅒ", "vowel"),
    CharacterSpec("ast_eo", "ㅓ", "vowel"),
    CharacterSpec("ast_e", "ㅔ", "vowel"),
    CharacterSpec("ast_yeo", "ㅕ", "vowel"),
    CharacterSpec("ast_ye", "ㅖ", "vowel"),
    CharacterSpec("ast_o", "ㅗ", "vowel"),
    CharacterSpec("ast_yo", "ㅛ", "vowel"),
    CharacterSpec("ast_u", "ㅜ", "vowel"),
    CharacterSpec("ast_yu", "ㅠ", "vowel"),
    CharacterSpec("ast_eu", "ㅡ", "vowel"),
    CharacterSpec("ast_i", "ㅣ", "vowel"),
)

EXPECTED_JAMO = frozenset(spec.ko_jamo for spec in CHARACTER_SPECS)
