import os
from typing import Any, Dict

import yaml


def translation(lang: str = "en_US") -> Dict[str, Any]:
    """Get the translation strings for the given language."""
    with open(os.path.join(os.path.dirname(__file__), f"{lang}.yml"), "r") as f:
        return yaml.safe_load(f)
