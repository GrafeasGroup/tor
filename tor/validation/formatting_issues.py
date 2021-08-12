from enum import Enum


class FormattingIssue(Enum):
    BOLD_HEADER = "bold_header"
    MISSING_SEPARATORS = "missing_separators"
    HEADING_WITH_DASHES = "heading_with_dashes"
    MALFORMED_FOOTER = "malformed_footer"
    FENCED_CODE_BLOCK = "fenced_code_block"
    UNESCAPED_HEADING = "unescaped_heading"
