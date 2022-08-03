import pytest

from tor.helpers.flair import (
    FLAIR_DATA,
    _get_flair_css,
    generate_promotion_message,
    check_promotion,
)
from tor.strings import translation


i18n = translation()


@pytest.mark.parametrize(
    "transcription_count,name",
    [
        (250, "grafeas-purple"),
        (1000, "grafeas-diamond"),
        (111, "grafeas-teal"),
        (1, "grafeas"),
        (100000000, "grafeas-sapphire"),
    ],
)
def test_get_flair_css(transcription_count: int, name: str) -> None:
    assert _get_flair_css(transcription_count) == name


@pytest.mark.parametrize(
    "transcription_count,name",
    [
        (0, "grafeas"),
        (-1, "grafeas"),
        (-0.3, "grafeas"),
    ],  # noqa:E231
)
def test_get_flair_css_invalid_options(transcription_count: int, name: str) -> None:
    assert _get_flair_css(0) == "grafeas"
    assert _get_flair_css(-1) == "grafeas"


@pytest.mark.parametrize(
    "value,expected_return",
    [
        (0, False),
        (25, True),
        (100, True),
        (11, False),
        (999, False),
        (1000, True),
    ],
)
def test_check_promotion(value: int, expected_return: bool) -> None:
    assert check_promotion(value) == expected_return


def test_generate_promotion_message() -> None:
    result = generate_promotion_message(100)
    assert "Teal" in result  # current rank
    assert "Purple" in result  # next rank
    assert "250" in result  # value for next rank


def test_generate_promotion_message_with_invalid_value() -> None:
    with pytest.raises(IndexError):
        generate_promotion_message(99)


def test_generate_promotion_message_first_transcription() -> None:
    result = generate_promotion_message(1)
    assert "Pink" in result
    assert i18n["responses"]["done"]["promotion_text"]["first_rank"] in result


def test_generate_promotion_message_top_rank() -> None:
    result = generate_promotion_message(max(FLAIR_DATA.keys()))
    assert i18n["responses"]["done"]["promotion_text"]["highest_rank"] in result
