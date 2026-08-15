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


def test_compose_jamo_reports_incomplete_syllable() -> None:
    result = compose_jamo(("ㅏ", "ㄱ"))

    assert not result.ok
    assert result.text == ""
    assert [issue.code for issue in result.issues] == [
        "EXPECTED_INITIAL_CONSONANT",
        "EXPECTED_MEDIAL_VOWEL",
    ]
