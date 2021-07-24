import re
from typing import Optional, List, Set

from tor.automatic_assessment.formatting_errors import FormattingError

FOOTER = "^^I'm&#32;a&#32;human&#32;volunteer&#32;content&#32;transcriber&#32;"
"for&#32;Reddit&#32;and&#32;you&#32;could&#32;be&#32;too!&#32;[If&#32;you'd&#32;"
"like&#32;more&#32;information&#32;on&#32;what&#32;we&#32;do&#32;and&#32;why&#32;"
"we&#32;do&#32;it,&#32;click&#32;here!](https://www.reddit.com/r/TranscribersOfReddit/wiki/index)"

MISSING_SEPARATORS_PATTERN = re.compile(r"\n\n---+\n\n")
SEPARATOR_HEADING_PATTERN = re.compile(r"\S+\n---+")
FENCED_CODE_BLOCK_PATTERN = re.compile("```.*```", re.DOTALL)


def check_for_missing_separators(transcription: str) -> Optional[FormattingError]:
    """Check if the transcription is missing the horizontal separators."""
    return (
        FormattingError.MISSING_SEPARATORS
        if len(MISSING_SEPARATORS_PATTERN.findall(transcription)) < 2
        else None
    )


def check_for_separator_heading(transcription: str) -> Optional[FormattingError]:
    """Check if the transcription has headings that were meant to be separators."""
    return (
        FormattingError.SEPARATOR_HEADINGS
        if SEPARATOR_HEADING_PATTERN.search(transcription) is not None
        else None
    )


def check_for_malformed_footer(transcription: str) -> Optional[FormattingError]:
    """Check if the transcription doesn't contain the correct footer."""
    return FormattingError.MALFORMED_FOOTER if FOOTER not in transcription else None


def check_for_fenced_code_block(transcription: str) -> Optional[FormattingError]:
    """Check if the transcription contains a fenced code block.

    Fenced code blocks look like this:
    ```
    Code Line 1
    Code Line 2
    ```
    They don't display correctly on all devices.
    """
    return (
        FormattingError.FENCED_CODE_BLOCK
        if FENCED_CODE_BLOCK_PATTERN.search(transcription) is not None
        else None
    )


def check_transcription(transcription: str) -> Set[FormattingError]:
    """Check the transcription for common formatting errors."""
    return set(
        error
        for error in [
            check_for_missing_separators(transcription),
            check_for_fenced_code_block(transcription),
        ]
        if error is not None
    )
