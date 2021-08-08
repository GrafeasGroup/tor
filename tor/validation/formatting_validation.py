import re
from typing import Optional, Set

from tor.validation.formatting_issues import FormattingIssue
from tor.validation.helpers import format_as_sections
from tor.strings import translation

i18n = translation()

FOOTER = "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
"for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;"
"like&#32;more&#32;information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;"
"we&#32;do&#32;it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)"

# Regex to recognize headers that have been made bold instead of italic.
# Example:
#
# **Image Transcription: Tumblr**
BOLD_HEADER_PATTERN = re.compile(r"^\s*\*\*(Image|Video|Audio) Transcription:?.*\*\*")

# Regex to recognize correctly formed separators.
# Separators are three dashes (---), potentially with spaces in-between.
# They need to be surrounded by empty lines (which can contain spaces)
# The separator line (---) can start with up to three spaces and end with arbitrary spaces.
PROPER_SEPARATORS_PATTERN = re.compile(r"\n[ ]*\n[ ]{,3}([-][ ]*){3,}[ ]*\n[ ]*\n")

# Regex to recognize a separator (---) being misused as heading.
# This happens when they empty line before the separator is missing.
# The following example will display as heading and not as separator:
#
# Heading
# ---
#
# The separator line can start with up to three spaces and contain spaces in-between.
HEADING_WITH_DASHES_PATTERN = re.compile(r"[\w][:*_ ]*\n[ ]{,3}([-][ ]*){3,}\n")

# Regex to recognize fenced code blocks, i.e. code blocks surrounded by three backticks.
# Example:
#
# ```
# int x = 0;
# ```
FENCED_CODE_BLOCK_PATTERN = re.compile("```.*```", re.DOTALL)

# Regex to recognize unescaped hashtags which may render as headers.
# Example:
#
# #Hashtag
UNESCAPED_HEADING_PATTERN = re.compile(r"(\n[ ]*\n[ ]{,3}|^)#[^ ]")


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
        if len(PROPER_SEPARATORS_PATTERN.findall(transcription)) < 2
        else None
    )


def check_for_heading_with_dashes(transcription: str) -> Optional[FormattingIssue]:
    """Check if the transcription has headings created with dashes.

    In markdown, you can make headings by putting three dashes on the next line.
    Almost always, these dashes were intended to be separators instead.

    Heading
    ---

    Will be a level 2 heading.
    """
    return (
        FormattingIssue.HEADING_WITH_DASHES
        if HEADING_WITH_DASHES_PATTERN.search(transcription)
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


def check_for_unescaped_heading(transcription: str) -> Optional[FormattingIssue]:
    """Check if the transcription contains an unescaped hashtag. Actual backslash in example swapped for (backslash) to
    avoid invalid escape sequence warning

    Valid: (backslash)#Text
    Valid: # Test
    Invalid: #Test
    """
    return (
        FormattingIssue.UNESCAPED_HEADING
        if UNESCAPED_HEADING_PATTERN.search(transcription) is not None
        else None
    )


def check_for_formatting_issues(transcription: str) -> Set[FormattingIssue]:
    """Check the transcription for common formatting issues."""
    return set(
        issue
        for issue in [
            check_for_bold_header(transcription),
            check_for_malformed_footer(transcription),
            check_for_heading_with_dashes(transcription),
            check_for_missing_separators(transcription),
            check_for_fenced_code_block(transcription),
        ]
        if issue is not None
    )


def get_formatting_issue_message(errors: Set[FormattingIssue]) -> str:
    """Get a message containing instructions for each formatting issue."""
    error_messages = [i18n["formatting_issues"][error.value] for error in errors]
    error_list = format_as_sections(error_messages)
    return i18n["formatting_issues"]["message"].format(error_list=error_list)
