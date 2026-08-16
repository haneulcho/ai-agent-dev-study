import pytest
from asterum.domain.composition import compose_jamo


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (("ㄱ", "ㅑ", "ㅇ", "ㅗ", "ㅐ"), "갸왜"),
        (("ㅎ", "ㅏ", "ㄴ", "ㄱ", "ㅡ", "ㄹ"), "한글"),
        (("ㄱ", "ㅏ", "ㄱ", "ㅅ"), "갃"),
    ],
)
def test_compose_jamo(tokens: tuple[str, ...], expected: str) -> None:
    result = compose_jamo(tokens)

    assert result.ok
    assert result.text == expected


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (("ㄱ", "ㄱ", "ㅏ"), "까"),
        (("ㄷ", "ㄷ", "ㅏ"), "따"),
        (("ㅂ", "ㅂ", "ㅏ"), "빠"),
        (("ㅅ", "ㅅ", "ㅏ"), "싸"),
        (("ㅈ", "ㅈ", "ㅏ"), "짜"),
    ],
)
def test_compose_jamo_combines_tense_initials(tokens: tuple[str, ...], expected: str) -> None:
    result = compose_jamo(tokens)

    assert result.ok
    assert result.text == expected


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (("ㄷ", "ㄷ", "ㅡ", "ㅅ"), "뜻"),
        (("ㅂ", "ㅏ", "ㄱ", "ㄱ"), "밖"),
        (("ㅇ", "ㅣ", "ㅅ", "ㅅ"), "있"),
    ],
)
def test_compose_jamo_combines_double_consonants(tokens: tuple[str, ...], expected: str) -> None:
    result = compose_jamo(tokens)

    assert result.ok
    assert result.text == expected


def test_compose_jamo_does_not_guess_ambiguous_syllable_boundary() -> None:
    result = compose_jamo(("ㅇ", "ㅏ", "ㄱ", "ㄱ", "ㅏ"))

    assert not result.ok
    assert result.text == "악가"
    assert [issue.code for issue in result.issues] == ["AMBIGUOUS_SYLLABLE_BOUNDARY"]
    assert result.issues[0].position == 2
    assert result.issues[0].token == "".join(("ㄱ", "ㄱ"))


def test_compose_jamo_reports_incomplete_syllable() -> None:
    result = compose_jamo(("ㅏ", "ㄱ"))

    assert not result.ok
    assert result.text == ""
    assert [issue.code for issue in result.issues] == [
        "EXPECTED_INITIAL_CONSONANT",
        "EXPECTED_MEDIAL_VOWEL",
    ]
