from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

CHOSEONG = (
    "ㄱ",
    "ㄲ",
    "ㄴ",
    "ㄷ",
    "ㄸ",
    "ㄹ",
    "ㅁ",
    "ㅂ",
    "ㅃ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅉ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
)
JUNGSEONG = (
    "ㅏ",
    "ㅐ",
    "ㅑ",
    "ㅒ",
    "ㅓ",
    "ㅔ",
    "ㅕ",
    "ㅖ",
    "ㅗ",
    "ㅘ",
    "ㅙ",
    "ㅚ",
    "ㅛ",
    "ㅜ",
    "ㅝ",
    "ㅞ",
    "ㅟ",
    "ㅠ",
    "ㅡ",
    "ㅢ",
    "ㅣ",
)
JONGSEONG = (
    "",
    "ㄱ",
    "ㄲ",
    "ㄳ",
    "ㄴ",
    "ㄵ",
    "ㄶ",
    "ㄷ",
    "ㄹ",
    "ㄺ",
    "ㄻ",
    "ㄼ",
    "ㄽ",
    "ㄾ",
    "ㄿ",
    "ㅀ",
    "ㅁ",
    "ㅂ",
    "ㅄ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
)

COMPOUND_VOWELS = {
    ("ㅗ", "ㅏ"): "ㅘ",
    ("ㅗ", "ㅐ"): "ㅙ",
    ("ㅗ", "ㅣ"): "ㅚ",
    ("ㅜ", "ㅓ"): "ㅝ",
    ("ㅜ", "ㅔ"): "ㅞ",
    ("ㅜ", "ㅣ"): "ㅟ",
    ("ㅡ", "ㅣ"): "ㅢ",
}
COMPOUND_FINALS = {
    ("ㄱ", "ㅅ"): "ㄳ",
    ("ㄴ", "ㅈ"): "ㄵ",
    ("ㄴ", "ㅎ"): "ㄶ",
    ("ㄹ", "ㄱ"): "ㄺ",
    ("ㄹ", "ㅁ"): "ㄻ",
    ("ㄹ", "ㅂ"): "ㄼ",
    ("ㄹ", "ㅅ"): "ㄽ",
    ("ㄹ", "ㅌ"): "ㄾ",
    ("ㄹ", "ㅍ"): "ㄿ",
    ("ㄹ", "ㅎ"): "ㅀ",
    ("ㅂ", "ㅅ"): "ㅄ",
}

CONSONANTS = frozenset(CHOSEONG) | (frozenset(JONGSEONG) - {""})
VOWELS = frozenset(JUNGSEONG)


class CompositionIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    position: int
    token: str
    message: str


class CompositionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    issues: tuple[CompositionIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.issues


def _compose_syllable(initial: str, medial: str, final: str = "") -> str:
    initial_index = CHOSEONG.index(initial)
    medial_index = JUNGSEONG.index(medial)
    final_index = JONGSEONG.index(final)
    return chr(0xAC00 + ((initial_index * 21) + medial_index) * 28 + final_index)


def compose_jamo(tokens: Sequence[str]) -> CompositionResult:
    """Compose ordered compatibility jamo without guessing missing syllable boundaries."""

    output: list[str] = []
    issues: list[CompositionIssue] = []
    position = 0

    while position < len(tokens):
        initial = tokens[position]
        if initial not in CHOSEONG:
            issues.append(
                CompositionIssue(
                    code="EXPECTED_INITIAL_CONSONANT",
                    position=position,
                    token=initial,
                    message="음절은 초성 자음으로 시작해야 한다",
                )
            )
            position += 1
            continue

        if position + 1 >= len(tokens) or tokens[position + 1] not in VOWELS:
            issues.append(
                CompositionIssue(
                    code="EXPECTED_MEDIAL_VOWEL",
                    position=position,
                    token=initial,
                    message="초성 다음에 중성 모음이 필요하다",
                )
            )
            position += 1
            continue

        medial = tokens[position + 1]
        next_position = position + 2
        if next_position < len(tokens):
            compound_medial = COMPOUND_VOWELS.get((medial, tokens[next_position]))
            if compound_medial is not None:
                medial = compound_medial
                next_position += 1

        final = ""
        if next_position < len(tokens) and tokens[next_position] in CONSONANTS:
            first_final = tokens[next_position]
            following = tokens[next_position + 1] if next_position + 1 < len(tokens) else None

            if following is None:
                final = first_final
                next_position += 1
            elif following in VOWELS:
                pass
            elif following in CONSONANTS:
                after_following = (
                    tokens[next_position + 2] if next_position + 2 < len(tokens) else None
                )
                compound_final = COMPOUND_FINALS.get((first_final, following))
                if compound_final is not None and after_following not in VOWELS:
                    final = compound_final
                    next_position += 2
                else:
                    final = first_final
                    next_position += 1

        output.append(_compose_syllable(initial, medial, final))
        position = next_position

    return CompositionResult(text="".join(output), issues=tuple(issues))
