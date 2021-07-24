from typing import List

import pytest

from tor.automatic_assessment.automatic_assessment import (
    check_for_fenced_code_block,
    check_for_missing_separators,
    check_transcription,
    check_for_separator_heading,
    check_for_malformed_footer,
)
from tor.automatic_assessment.formatting_errors import FormattingError


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("This is a text", True),
        ("This is a\n\n---\n\ntext", True),
        ("This\n\n---\n\nis a\n\n---\n\ntext", False),
        ("This\n\n---\n\nis\n\n---\n\na\n\n---\n\ntext", False),
    ],
)
def test_check_for_missing_separators(test_input: str, should_match: bool) -> None:
    """Test if fenced code blocks are detected"""
    actual = check_for_missing_separators(test_input)
    expected = FormattingError.MISSING_SEPARATORS if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("Heading\n---", True),
        ("Heading with Spaces\n---", True),
        ("Not Heading\n\n---", False),
        ("Just text\nand\nstuff", False),
    ],
)
def test_check_for_separator_headings(test_input: str, should_match: bool) -> None:
    """Test if fenced code blocks are detected"""
    actual = check_for_separator_heading(test_input)
    expected = FormattingError.SEPARATOR_HEADINGS if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("Text without footer", True),
        (
            "^(I'm a human volunteer content transcriber for Reddit and you could be too!) "
            "[^(If you'd like more information on what we do and why we do it, click here!)]"
            "(https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            True,
        ),
        (
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;for&#32;and&#32;"
            "you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;like&#32;more&#32;information&#32;"
            "on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;it,&#32;click&#32;here!]"
            "(https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            False,
        ),
    ],
)
def test_check_for_malformed_footer(test_input: str, should_match: bool) -> None:
    """Test if malformed footers are detected correctly."""
    actual = check_for_malformed_footer(test_input)
    expected = FormattingError.MALFORMED_FOOTER if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("```\nCode\n```", True),
        ("Word\n```\nint x = 1\n```Word", True),
        ("This is just normal text", False),
        ("Word\n    int x = 1\nWord", False),
    ],
)
def test_check_for_fenced_code_block(test_input: str, should_match: bool) -> None:
    """Test if fenced code blocks are detected"""
    actual = check_for_fenced_code_block(test_input)
    expected = FormattingError.FENCED_CODE_BLOCK if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            """*Image Transcription:*

[*Description of Image.*]

"""
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
            "for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;"
            "like&#32;more&#32;information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;"
            "we&#32;do&#32;it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            [FormattingError.MISSING_SEPARATORS],
        ),
        (
            """*Image Transcription:*

---

```
function foo(x: int) {
    return bar;
}
```

---

"""
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
            "for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;"
            "like&#32;more&#32;information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;"
            "we&#32;do&#32;it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            [FormattingError.FENCED_CODE_BLOCK],
        ),
        (
            """*Image Transcription:*

```
function foo(x: int) {
    return bar;
}
```

"""
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
            "for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;"
            "like&#32;more&#32;information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;"
            "we&#32;do&#32;it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            [FormattingError.FENCED_CODE_BLOCK, FormattingError.MISSING_SEPARATORS],
        ),
        (
            """*Image Transcription:*

---

[*Description of Image.*]

---

"""
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
            "for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;"
            "like&#32;more&#32;information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;"
            "we&#32;do&#32;it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            [],
        ),
    ],
)
def test_check_transcription(test_input: str, expected: List[FormattingError]) -> None:
    """Test if formatting errors are detected correctly"""
    print(test_input)
    actual = check_transcription(test_input)
    assert actual == set(expected)
