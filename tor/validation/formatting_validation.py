import re
from typing import Optional, Set

from tor.validation.formatting_issues import FormattingIssue
from tor.validation.helpers import format_as_markdown_list
from tor.strings import translation

i18n = translation()

FOOTER = "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
"for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;"
"like&#32;more&#32;information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;"
"we&#32;do&#32;it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)"

BOLD_HEADER_PATTERN = re.compile(r"^\s*\*\*(Image|Video) Transcription:?.*\*\*")
MISSING_SEPARATORS_PATTERN = re.compile(r"\n[ ]*\n[ ]{,3}---+[ ]*\n[ ]*\n")
SEPARATOR_HEADING_PATTERN = re.compile(r"\w+[ ]*\n---+")
FENCED_CODE_BLOCK_PATTERN = re.compile("```.*```", re.DOTALL)


def check_for_bold_header(transcription: str) -> Optional[FormattingIssue]:
    """Check if the transcription has a bold instead of italic header."""
    return (
        FormattingIssue.BOLD_HEADER
        if BOLD_HEADER_PATTERN.search(transcription) is not None
        else None
    )


def check_for_missing_separators(transcription: str) -> Optional[FormattingIssue]:
    """Check if the transcription is missing the horizontal separators.

    Every transcription should have the form

    <header>

    ---

    <content>

    ---

    <footer>

    If a transcription doesn't have at least two headings, that indicates a
    formatting issue.
    """
    return (
        FormattingIssue.MISSING_SEPARATORS
        if len(MISSING_SEPARATORS_PATTERN.findall(transcription)) < 2
        else None
    )


def check_for_separator_heading(transcription: str) -> Optional[FormattingIssue]:
    """Check if the transcription has headings that were meant to be separators.

    When the separators are missing an empty line before them, they make the
    text a heading instead of appearing as a separator:

    Heading
    ---

    Will be a level 2 heading. This is almost always a mistake.
    """
    return (
        FormattingIssue.SEPARATOR_HEADINGS
        if SEPARATOR_HEADING_PATTERN.search(transcription) is not None
        else None
    )


def check_for_malformed_footer(transcription: str) -> Optional[FormattingIssue]:
    """Check if the transcription doesn't contain the correct footer."""
    return FormattingIssue.MALFORMED_FOOTER if FOOTER not in transcription else None


def check_for_fenced_code_block(transcription: str) -> Optional[FormattingIssue]:
    """Check if the transcription contains a fenced code block.

    Fenced code blocks look like this:

    ```
    Code Line 1
    Code Line 2
    ```

    They don't display correctly on all devices.
    """
    return (
        FormattingIssue.FENCED_CODE_BLOCK
        if FENCED_CODE_BLOCK_PATTERN.search(transcription) is not None
        else None
    )


def check_for_formatting_issues(transcription: str) -> Set[FormattingIssue]:
    """Check the transcription for common formatting issues."""
    return set(
        issue
        for issue in [
            check_for_bold_header(transcription),
            check_for_malformed_footer(transcription),
            check_for_separator_heading(transcription),
            check_for_missing_separators(transcription),
            check_for_fenced_code_block(transcription),
        ]
        if issue is not None
    )


def get_formatting_issue_message(errors: Set[FormattingIssue]) -> str:
    """Get a message containing instructions for each formatting issue."""
    error_messages = [i18n["formatting_issues"][error.value] for error in errors]
    error_list = format_as_markdown_list(error_messages)
    return i18n["formatting_issues"]["message"].format(error_list=error_list)
