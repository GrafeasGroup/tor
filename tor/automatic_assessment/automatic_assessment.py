import re
from typing import Optional, List, Set

from tor.automatic_assessment.formatting_errors import FormattingError

MISSING_SEPARATORS_PATTERN = re.compile("---")
FENCED_CODE_BLOCK_PATTERN = re.compile("```.*```", re.DOTALL)


def check_for_missing_separators(transcription: str) -> Optional[FormattingError]:
    """Check if the transcription is missing the horizontal separators."""
    return (
        FormattingError.MISSING_SEPARATORS
        if len(MISSING_SEPARATORS_PATTERN.findall(transcription)) < 2
        else None
    )


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
