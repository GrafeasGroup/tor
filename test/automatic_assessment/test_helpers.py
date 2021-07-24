from typing import List

import pytest

from tor.automatic_assessment.helpers import (
    format_as_markdown_list_item,
    format_as_markdown_list,
)


@pytest.mark.parametrize(
    "test_input,expected",
    [("Item 1", "- Item 1"), ("This is\na test", "- This is\n  a test")],
)
def test_format_as_markdown_list_item(test_input: str, expected: str) -> None:
    """Test if list items are formatted correctly."""
    actual = format_as_markdown_list_item(test_input)
    assert actual == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (["Item 1"], "- Item 1"),
        (["This is\na test"], "- This is\n  a test"),
        (["Item 1", "Item 2", "Item 3"], "- Item 1\n- Item 2\n- Item 3"),
        (
            ["Item 1\nwith other stuff", "Item 2", "Item 3\nand so on"],
            "- Item 1\n  with other stuff\n- Item 2\n- Item 3\n  and so on",
        ),
    ],
)
def test_format_as_markdown_list(test_input: List[str], expected: str) -> None:
    """Test if lists are formatted correctly."""
    actual = format_as_markdown_list(test_input)
    assert actual == expected
