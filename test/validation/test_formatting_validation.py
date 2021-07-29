from typing import List

import pytest

from tor.validation.formatting_validation import (
    check_for_fenced_code_block,
    check_for_missing_separators,
    check_for_formatting_issues,
    check_for_separator_heading,
    check_for_malformed_footer,
    check_for_bold_header,
    PROPER_SEPARATORS_PATTERN,
)
from tor.validation.formatting_issues import FormattingIssue

# We need trailing whitespaces for some tests.
# Because they are within a multiline string,
# I couldn't disable them via a line comment.
# flake8: noqa: W291


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("\n\n---\n\n", True),  # "Normal" separator
        ("\n\n-------\n\n", True),  # More dashes are allowed
        ("\n  \n---\n  \n", True),  # Spaces on the empty lines are allowed
        ("Word\n\n---\n\nWord", True),  # Separator with surrounding text
        ("\n\n   ---\n\n", True),  # Separator can start with up to three spaces
        ("\n\n---      \n\n", True),  # Separator can have trailing spaces
        ("\n\n-  -  -\n\n", True),  # Separator can have spaces in-between
        ("Word\n---\n\n", False),  # Only one linebreak makes a heading
        ("\n\n--\n\n", False),  # Not enough dashes
        ("\n\n    ---\n\n", False),  # Four leading spaces makes a code block
    ],
)
def test_proper_separator_pattern(test_input: str, should_match: bool) -> None:
    """Test if horizontal separators are recognized correctly."""
    actual = PROPER_SEPARATORS_PATTERN.search(test_input) is not None
    assert actual == should_match


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("**Image Transcription: Tumblr**", True),
        ("**Image Transcription:**", True),
        ("**Image Transcription**", True),
        ("**Video Transcription:**", True),
        ("*Image Transcription: Tumblr*", False),
        ("*Image Transcription:*", False),
        ("*Image Transcription*", False),
        (
            "*Image Transcription: Tumblr*\n\n---\n\n**Image Transcription: Tumblr**",
            False,
        ),
    ],
)
def test_check_for_bold_header(test_input: str, should_match: bool) -> None:
    """Test if bold headers are detected."""
    actual = check_for_bold_header(test_input)
    expected = FormattingIssue.BOLD_HEADER if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("This is a text", True),
        ("This is a\n\n---\n\ntext", True),
        ("This\n\n---\n\nis a\n\n---\n\ntext", False),
        ("This\n\n---\n\nis\n\n---\n\na\n\n---\n\ntext", False),
        ("This\n  \n   ---  \n \nis\n  \n---    \n \n  a text", False),
        (
            """*Image Transcription: Meme*

---  

[*An image of Robin from "Stranger Things" wearing a Scoops Ahoy uniform. She is holding a whiteboard in front of her and looking off-camera with a condescending expression. The whiteboard reads:*]

If you can force people and draft them to go to war, you can force people to get vaccines.

---

"""
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
            "for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;"
            "like&#32;more&#32;information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;"
            "we&#32;do&#32;it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            False,
        ),
    ],
)
def test_check_for_missing_separators(test_input: str, should_match: bool) -> None:
    """Test if missing separators are detected."""
    actual = check_for_missing_separators(test_input)
    expected = FormattingIssue.MISSING_SEPARATORS if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("Heading\n---", True),
        ("Heading with Spaces\n---", True),
        ("Heading    \n---", True),
        ("Not Heading\n\n---", False),
        ("Just text\nand\nstuff", False),
    ],
)
def test_check_for_separator_headings(test_input: str, should_match: bool) -> None:
    """Test if separators misused as headings are detected."""
    actual = check_for_separator_heading(test_input)
    expected = FormattingIssue.SEPARATOR_HEADINGS if should_match else None
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
    """Test if malformed footers are detected."""
    actual = check_for_malformed_footer(test_input)
    expected = FormattingIssue.MALFORMED_FOOTER if should_match else None
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
    """Test if fenced code blocks are detected."""
    actual = check_for_fenced_code_block(test_input)
    expected = FormattingIssue.FENCED_CODE_BLOCK if should_match else None
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
            [FormattingIssue.MISSING_SEPARATORS],
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
            [FormattingIssue.FENCED_CODE_BLOCK],
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
            [FormattingIssue.FENCED_CODE_BLOCK, FormattingIssue.MISSING_SEPARATORS],
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
        (
            """*Image Transcription: Meme*

---  

[*An image of Robin from "Stranger Things" wearing a Scoops Ahoy uniform. She is holding a whiteboard in front of her and looking off-camera with a condescending expression. The whiteboard reads:*]

If you can force people and draft them to go to war, you can force people to get vaccines.

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
def test_check_for_formatting_issues(
    test_input: str, expected: List[FormattingIssue]
) -> None:
    """Test if formatting issues are detected correctly"""
    actual = check_for_formatting_issues(test_input)
    assert actual == set(expected)
