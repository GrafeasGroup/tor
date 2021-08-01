from typing import List

import pytest

from tor.validation.helpers import format_as_sections


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (["Item 1"], "Item 1"),
        (["This is\na test"], "This is\na test"),
        (["Item 1", "Item 2", "Item 3"], "Item 1\n\n---\n\nItem 2\n\n---\n\nItem 3"),
        (
            ["Item 1\nwith other stuff", "Item 2", "Item 3\nand so on"],
            "Item 1\nwith other stuff\n\n---\n\nItem 2\n\n---\n\nItem 3\nand so on",
        ),
    ],
)
def test_format_as_sections(test_input: List[str], expected: str) -> None:
    """Test if sections are formatted correctly."""
    actual = format_as_sections(test_input)
    assert actual == expected
