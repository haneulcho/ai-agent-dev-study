"""인식된 한글 자모 순서를 완성형 한글 음절로 조합한다.

OCR은 아스테룸 글리프를 ``ㄱ``, ``ㅏ`` 같은 자모로 분류한다. 이 모듈은 그 순서를
유니코드 한글 음절로 바꾸며, 누락된 글자를 임의로 추측하지 않는다.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

# 유니코드 한글 음절 계산식에서 사용하는 초성·중성·종성의 공식 순서다.
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

# 두 개의 기본 모음이나 받침이 연이어 나왔을 때 하나로 합칠 수 있는 조합이다.
COMPOUND_VOWELS = {
    ("ㅗ", "ㅏ"): "ㅘ",
    ("ㅗ", "ㅐ"): "ㅙ",
    ("ㅗ", "ㅣ"): "ㅚ",
    ("ㅜ", "ㅓ"): "ㅝ",
    ("ㅜ", "ㅔ"): "ㅞ",
    ("ㅜ", "ㅣ"): "ㅟ",
    ("ㅡ", "ㅣ"): "ㅢ",
}

# 아스테룸 기본 문자에는 별도의 쌍자음 글리프가 없다. 따라서 음절 시작에서
# 같은 기본 자음 두 개가 연속되고 그 다음에 모음이 오면 된소리 초성으로 합친다.
TENSE_INITIALS = {
    ("ㄱ", "ㄱ"): "ㄲ",
    ("ㄷ", "ㄷ"): "ㄸ",
    ("ㅂ", "ㅂ"): "ㅃ",
    ("ㅅ", "ㅅ"): "ㅆ",
    ("ㅈ", "ㅈ"): "ㅉ",
}

COMPOUND_FINALS = {
    ("ㄱ", "ㄱ"): "ㄲ",
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
    ("ㅅ", "ㅅ"): "ㅆ",
}

CONSONANTS = frozenset(CHOSEONG) | (frozenset(JONGSEONG) - {""})
VOWELS = frozenset(JUNGSEONG)


class CompositionIssue(BaseModel):
    """조합할 수 없는 자모의 위치와 이유."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    position: int
    token: str
    message: str


class CompositionResult(BaseModel):
    """완성된 문자열과 사람이 확인해야 할 문제 목록."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    issues: tuple[CompositionIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.issues


def _compose_syllable(initial: str, medial: str, final: str = "") -> str:
    """초성·중성·종성의 순번으로 유니코드 한글 한 글자를 계산한다."""

    initial_index = CHOSEONG.index(initial)
    medial_index = JUNGSEONG.index(medial)
    final_index = JONGSEONG.index(final)
    return chr(0xAC00 + ((initial_index * 21) + medial_index) * 28 + final_index)


def compose_jamo(tokens: Sequence[str]) -> CompositionResult:
    """읽기 순서의 자모를 한글로 조합하고 잘못된 위치는 issue로 남긴다.

    처리 순서는 ``초성 → 중성 → 선택적 종성``이다. 다음 자모가 모음이면 현재 자음을
    받침으로 쓰지 않고 다음 음절의 초성으로 넘긴다.
    """

    output: list[str] = []
    issues: list[CompositionIssue] = []
    position = 0

    while position < len(tokens):
        # 한 음절은 반드시 자음(초성)으로 시작한다.
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

        # 예: ㄷ+ㄷ+ㅡ는 ㄸ+ㅡ로 읽어 '뜨'를 만든다. 세 번째 token이 모음일
        # 때만 합치므로 단순히 같은 자음이 이어졌다는 이유로 추측하지 않는다.
        medial_position = position + 1
        if position + 2 < len(tokens):
            tense_initial = TENSE_INITIALS.get((initial, tokens[position + 1]))
            if tense_initial is not None and tokens[position + 2] in VOWELS:
                initial = tense_initial
                medial_position = position + 2

        if medial_position >= len(tokens) or tokens[medial_position] not in VOWELS:
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

        # 기본 모음 두 개가 ㅗ+ㅏ처럼 들어오면 ㅘ 한 글자로 합친다.
        medial = tokens[medial_position]
        next_position = medial_position + 1
        if next_position < len(tokens):
            compound_medial = COMPOUND_VOWELS.get((medial, tokens[next_position]))
            if compound_medial is not None:
                medial = compound_medial
                next_position += 1

        # 다음 자음이 받침인지 다음 음절의 초성인지 뒤의 모음까지 살펴 결정한다.
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
                    # ㄱ+ㄱ처럼 된소리 초성으로도 읽을 수 있는 두 자음 뒤에 모음이
                    # 오면 음절 경계만으로는 답을 하나로 확정할 수 없다. 기존의
                    # 왼쪽 우선 결과는 유지하되 사람이 확인할 수 있도록 문제를 남긴다.
                    if (first_final, following) in TENSE_INITIALS and after_following in VOWELS:
                        issues.append(
                            CompositionIssue(
                                code="AMBIGUOUS_SYLLABLE_BOUNDARY",
                                position=next_position,
                                token=f"{first_final}{following}",
                                message=(
                                    "앞 자음을 받침으로 읽는 경우와 두 자음을 "
                                    "된소리 초성으로 읽는 경우가 모두 가능하다"
                                ),
                            )
                        )
                    final = first_final
                    next_position += 1

        output.append(_compose_syllable(initial, medial, final))
        position = next_position

    return CompositionResult(text="".join(output), issues=tuple(issues))
