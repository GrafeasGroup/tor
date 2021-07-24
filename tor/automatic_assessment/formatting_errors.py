from enum import Enum


class FormattingError(Enum):
    FANCY_PANTS = 1
    MISSING_SEPARATORS = 2
    FENCED_CODE_BLOCK = 3
