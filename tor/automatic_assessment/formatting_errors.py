from enum import Enum


class FormattingError(Enum):
    FANCY_PANTS = 1
    MISSING_SEPARATORS = 2
    SEPARATOR_HEADINGS = 3
    MALFORMED_FOOTER = 4
    FENCED_CODE_BLOCK = 5
