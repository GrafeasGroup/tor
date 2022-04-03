import re
from typing import Optional


HEADER_REGEX = re.compile(
    r"\s*\*(?P<format>\S+)[ ]+(?P<tr_text>Transcription)"
    r"(?::(?:[ ]+(?P<type>[^\n*]+))?\*|\*:)"
    r"(?:\s*\n[ ]{0,3}(?P<separator>---)[ ]*\n)",
    re.IGNORECASE,
)

VALID_FORMATS = ["Image", "Video", "Audio"]
LOWERCASE_VALID_FORMATS = [ft.casefold() for ft in VALID_FORMATS]


def check_header_errors(transcription: str) -> Optional[str]:
    """Check if the header of the transcription has any formatting errors."""
    header_match = HEADER_REGEX.search(transcription)

    if header_match is None:
        return "No header found!"

    header_format = header_match.group("format")
    header_tr_text = header_match.group("type")
    header_separator = header_match.group("separator")

    if header_match.start() != 0:
        return "Please place the header at the top of your transcription!"
    if header_format.casefold() not in LOWERCASE_VALID_FORMATS:
        return "Invalid format!"
    if header_format.casefold() not in VALID_FORMATS:
        return "Format not capitalized correctly!"
    if header_tr_text != "Transcription":
        return "Transcription text not capitalized correctly!"
    if header_separator is None:
        return "Header separator missing!"
