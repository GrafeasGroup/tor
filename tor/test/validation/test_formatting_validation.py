import datetime
from typing import List

import pytest

from tor.test.validation.helpers import (
    load_all_valid_transcriptions,
    load_invalid_transcription_from_file,
    load_valid_transcription_from_file,
)
from tor.validation.formatting_validation import (
    check_for_fenced_code_block,
    check_for_incorrect_line_break,
    check_for_missing_separators,
    check_for_formatting_issues,
    check_for_heading_with_dashes,
    check_for_malformed_footer,
    check_for_bold_header,
    check_for_unescaped_heading,
    check_for_invalid_header,
    check_for_reference_links,
    PROPER_SEPARATORS_PATTERN,
    HEADING_WITH_DASHES_PATTERN,
    UNESCAPED_USERNAME_PATTERN,
    check_for_unescaped_username,
    check_for_unescaped_subreddit,
    UNESCAPED_SUBREDDIT_PATTERN,
    is_april_fools,
    FOOTER_PATTERN_APRIL_FOOLS,
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
        ("Heading\n---\n", True),  # "Classical" heading with dashes
        ("Heading\n-------\n", True),  # More dashes are allowed
        ("Heading   \n---\n", True),  # Trailing spaces after word are allowed
        ("*Heading*\n---\n", True),  # Formatting characters in heading are allowed
        ("Heading\n   ---\n", True),  # Dashes can start with up to three spaces
        ("Heading\n-  -  -\n", True),  # Dashes can have spaces in-between
        ("Heading\n---    \n", True),  # Dashes can have trailing spaces
        ("Heading\n---asd\n", False),  # Dashes can't have words after them
        ("Heading\n\n---\n\n", False),  # That's a separator
        ("   \n   \n---\n\n", False),  # That's a separator
    ],
)
def test_heading_with_dashes_pattern(test_input: str, should_match: bool) -> None:
    """Test if headings made with dashes are recognized correctly."""
    actual = HEADING_WITH_DASHES_PATTERN.search(test_input) is not None
    assert actual == should_match


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("u/username", True),  # Username with one slash
        ("Text u/username Text", True),  # Username in text
        ("**u/username**", True),  # Username bolded
        ("/u/username", True),  # Username with two slashes
        ("u/123456", True),  # Username with numbers
        ("u/_username_", True),  # Username with underscores
        ("u/-username-", True),  # Username with dashes
        (r"u\/username", False),  # Escaped username with one slash
        (r"\/u/username", False),  # Escaped username with first slash escaped
        (r"/u\/username", False),  # Escaped username with second slash escaped
        (r"\/u\/username", False),  # Escaped username with both slashes escaped
        (r"https://www.reddit.com/u/username", False),  # Link to user
        (r"r/subreddit", False),  # Subreddit name with one slash
        (r"/r/subreddit", False),  # Subreddit name with two slashes
    ],
)
def test_unescaped_username_pattern(test_input: str, should_match: bool) -> None:
    """Test if headings made with dashes are recognized correctly."""
    actual = UNESCAPED_USERNAME_PATTERN.search(test_input) is not None
    assert actual == should_match


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("r/subreddit", True),  # Subreddit with one slash
        ("Text r/subreddit Text", True),  # Subreddit in text
        ("**r/subreddit**", True),  # Subreddit bolded
        ("/r/subreddit", True),  # Subreddit with two slashes
        ("r/123456", True),  # Subreddit with numbers
        ("r/subreddit", True),  # Subreddit with underscores
        ("r/-subreddit-", True),  # Subreddit with dashes
        (r"r\/subreddit", False),  # Escaped subreddit with one slash
        (r"\/r/subreddit", False),  # Escaped subreddit with first slash escaped
        (r"/r\/subreddit", False),  # Escaped subreddit with second slash escaped
        (r"\/r\/subreddit", False),  # Escaped subreddit with both slashes escaped
        (r"https://www.reddit.com/r/subreddit", False),  # Link to subreddit
        (r"u/username", False),  # Username with one slash
        (r"/u/username", False),  # Username with two slashes
    ],
)
def test_unescaped_subreddit_pattern(test_input: str, should_match: bool) -> None:
    """Test if headings made with dashes are recognized correctly."""
    actual = UNESCAPED_SUBREDDIT_PATTERN.search(test_input) is not None
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
        (
            load_invalid_transcription_from_file("bold-header_heading-with-dashes.txt"),
            True,
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
        (load_invalid_transcription_from_file("missing-separators.txt"), True),
        (load_valid_transcription_from_file("190177.txt"), False),
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
        ("Heading\n---\n", True),
        ("Heading with Spaces\n---\n", True),
        ("Heading    \n---\n", True),
        ("Not Heading\n\n---\n", False),
        ("Just text\nand\nstuff\n", False),
        (load_invalid_transcription_from_file("heading-with-dashes.txt"), True),
        (load_valid_transcription_from_file("190177.txt"), False),
    ],
)
def test_check_for_heading_with_dashes(test_input: str, should_match: bool) -> None:
    """Test if separators misused as headings are detected."""
    actual = check_for_heading_with_dashes(test_input)
    expected = FormattingIssue.HEADING_WITH_DASHES if should_match else None
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
        # Old footer (with "for Reddit")
        # TODO: We probably want to disallow this one at some point
        (
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;for&#32;Reddit&#32;and&#32;"
            "you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;like&#32;more&#32;information&#32;"
            "on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;it,&#32;click&#32;here!]"
            "(https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            False,
        ),
        # New footer (without "for Reddit")
        (
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;and&#32;"
            "you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;like&#32;more&#32;information&#32;"
            "on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;it,&#32;click&#32;here!]"
            "(https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            False,
        ),
        (load_invalid_transcription_from_file("malformed-footer.txt"), True),
        (load_valid_transcription_from_file("190177.txt"), False),
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
    "test_input,should_match",
    [
        ("This is a line  \nThis is another line", True),
        ("This is a line\\\nThis is another line", True),
        ("This is a line\n\nThis is another line", False),
        ("*Word*  \n_Word_", True),  # Line break after formatting characters
        ("Word    \nWord", True),  # Line break with more than two spaces
        (
            "Word\n  \n---  \n\nWord",
            False,
        ),  # Spaces within paragraph line breaks (often happens when transcribing)
        ("Word \nWord", False),  # Only one space at the end
    ],
)
def test_check_for_incorrect_line_break(test_input: str, should_match: bool) -> None:
    """Test if incorrect line breaks are detected."""
    actual = check_for_incorrect_line_break(test_input)
    expected = FormattingIssue.INCORRECT_LINE_BREAK if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("u/username", True),
        ("/u/username", True),
        (r"u\/username", False),
        (r"\/u/username", False),
        (r"\/u\/username", False),
        (
            load_invalid_transcription_from_file("unescaped_username_subreddit.txt"),
            True,
        ),
    ],
)
def test_check_for_unescaped_username(test_input: str, should_match: bool) -> None:
    """Test if unescaped usernames are detected."""
    actual = check_for_unescaped_username(test_input)
    expected = FormattingIssue.UNESCAPED_USERNAME if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("r/subreddit", True),
        ("/r/subreddit", True),
        (r"r\/subreddit", False),
        (r"\/r/subreddit", False),
        (r"\/r\/subreddit", False),
        (
            load_invalid_transcription_from_file("unescaped_username_subreddit.txt"),
            True,
        ),
    ],
)
def test_check_for_unescaped_subreddit(test_input: str, should_match: bool) -> None:
    """Test if unescaped subreddit names are detected."""
    actual = check_for_unescaped_subreddit(test_input)
    expected = FormattingIssue.UNESCAPED_SUBREDDIT if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("#This is an unescaped heading", True),
        (r"\#This is properly escaped", False),
        ("# This is meant to render as a heading", False),
        ("\n     \n   #heading", True),
        ("\n\n\\#hashtag1 #hashtag2", False),
        ("\n\n*#hashtag1 #hashtag2*", False),
        ("## test", False),
    ],
)
def test_check_for_unescaped_heading(test_input: str, should_match: bool) -> None:
    """Test if unescaped hashtags are detected."""
    actual = check_for_unescaped_heading(test_input)
    expected = FormattingIssue.UNESCAPED_HEADING if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        ("*Image Transcription: Test*", False),
        ("*Image Transcription*", False),
        ("*Audio Transcription*", False),
        ("*Video Transcription*", False),
        ("*Invalid Header*", True),
        ("*Invalid Header*\n\n---\n\nBlah", True),
        ("*Image Transcription: Test*\n\n---\n\nBlah", False),
        ("Blah *Image Transcription: Test*", True),
        (
            "**Image Transcription: Test**",
            False,
        ),  # There is a separate check for this, so it shouldn't be checked here
        ("Image Transcription: Test*", True),
        ("    *Image Transcription: Test*", False),
    ],
)
def test_check_for_invalid_header(test_input: str, should_match: bool) -> None:
    """Test if invalid headers are detected."""
    actual = check_for_invalid_header(test_input)
    expected = FormattingIssue.INVALID_HEADER if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,should_match",
    [
        (
            '[lance]: https://en.wikipedia.org/wiki/Holy_Lance "Holy Lance - Wikipedia"',
            True,
        ),
        ("[*Redacted*]: Oh man i think i just ran out of pain", True),
        (
            "something something something [*Redacted*]: Oh man i think i just ran out of pain",
            True,
        ),
        ("[*Redacted*]:Oh man i think i just ran out of pain", True),
        (r"\[*Redacted*]: Oh man i think i just ran out of pain", False),
        ("[*The tor bot happily smiles as the entire queue is cleared in CTQ*]", False),
    ],
)
def test_check_for_reference_links(test_input: str, should_match: str) -> None:
    """Test if reference links are detected"""
    actual = check_for_reference_links(test_input)
    expected = FormattingIssue.REFERENCE_LINK if should_match else None
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            load_invalid_transcription_from_file("missing-separators.txt"),
            [FormattingIssue.MISSING_SEPARATORS],
        ),
        (
            load_invalid_transcription_from_file("fenced-code-block.txt"),
            [FormattingIssue.FENCED_CODE_BLOCK],
        ),
        (
            load_invalid_transcription_from_file(
                "fenced-code-block_missing-separators.txt"
            ),
            [FormattingIssue.FENCED_CODE_BLOCK, FormattingIssue.MISSING_SEPARATORS],
        ),
        (
            load_invalid_transcription_from_file("unescaped_username_subreddit.txt"),
            [FormattingIssue.UNESCAPED_USERNAME, FormattingIssue.UNESCAPED_SUBREDDIT],
        ),
        (
            load_invalid_transcription_from_file("bold-header_heading-with-dashes.txt"),
            [
                FormattingIssue.BOLD_HEADER,
                FormattingIssue.HEADING_WITH_DASHES,
                FormattingIssue.MISSING_SEPARATORS,
            ],
        ),
        (
            load_invalid_transcription_from_file("unescaped-heading.txt"),
            [FormattingIssue.UNESCAPED_HEADING],
        ),
    ],
)
def test_check_for_formatting_issues_invalid_transcriptions(
    test_input: str, expected: List[FormattingIssue]
) -> None:
    """Test if formatting issues are detected correctly."""
    actual = check_for_formatting_issues(test_input)
    assert actual == set(expected)


@pytest.mark.parametrize("transcription", load_all_valid_transcriptions())
def test_check_for_formatting_issues_valid_transcription(transcription: str) -> None:
    """Make sure that valid transcriptions don't generate formatting issues."""
    actual = check_for_formatting_issues(transcription)
    assert actual == set([])


def test_april_fools():
    target = datetime.datetime(2020, 4, 1, 12, 36)  # midday on April 1
    assert is_april_fools(target)


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
        # Old footer (with "for Reddit")
        # TODO: We probably want to disallow this one at some point
        (
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;for&#32;Reddit&#32;and&#32;"
            "you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;like&#32;more&#32;information&#32;"
            "on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;it,&#32;click&#32;here!]"
            "(https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            False,
        ),
        # New footer (without "for Reddit")
        (
            "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;and&#32;"
            "you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;like&#32;more&#32;information&#32;"
            "on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;it,&#32;click&#32;here!]"
            "(https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            False,
        ),
        # April fool's footer (without "for Reddit")
        (
            "^^I'm&#32;a&#32;pterodactly&#32;and&#32;"
            "you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;like&#32;more&#32;information&#32;"
            "on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;we&#32;do&#32;it,&#32;click&#32;here!]"
            "(https://www.reddit.com/r/TranscribersOfReddit/wiki/index)",
            False,
        ),
        (load_invalid_transcription_from_file("malformed-footer.txt"), True),
        (load_valid_transcription_from_file("190177.txt"), False),
    ],
)
def test_april_fools_footer(test_input, should_match):
    has_errors = not FOOTER_PATTERN_APRIL_FOOLS.search(test_input)
    assert has_errors == should_match
