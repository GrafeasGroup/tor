import os
from typing import List


VALID_TRANSCRIPTION_PATH = os.path.join('test', 'validation', 'transcriptions', 'valid')


def load_valid_transcription_from_file(name: str) -> str:
    """Load a transcription from the transcriptions/valid folder."""
    file = open(os.path.join(VALID_TRANSCRIPTION_PATH, name))
    return file.read()


def load_all_valid_transcriptions() -> List[str]:
    """Loads all transcriptions from the transcriptions/valid folder."""
    files = os.listdir(VALID_TRANSCRIPTION_PATH)
    return [load_valid_transcription_from_file(file) for file in files]
