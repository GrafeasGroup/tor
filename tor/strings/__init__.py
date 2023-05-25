"""Translations for the project."""
import os
from typing import Any

import yaml


def translation(lang: str = "en_US") -> Any:
    """Generate translation data for the project."""
    with open(os.path.join(os.path.dirname(__file__), f"{lang}.yml"), "r") as f:
        return yaml.safe_load(f)
