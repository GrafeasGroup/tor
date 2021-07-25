from enum import Enum


class FormattingError(Enum):
    BOLD_HEADER = "bold_header"
    MISSING_SEPARATORS = "missing_separators"
    SEPARATOR_HEADINGS = "separator_headings"
    MALFORMED_FOOTER = "malformed_footer"
    FENCED_CODE_BLOCK = "fenced_code_block"
