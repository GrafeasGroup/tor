from typing import List


def format_as_sections(items: List[str]) -> str:
    """Format the given items as sections, divided by horizontal separators.

    It will look like this:

    Item 1

    ---

    Item 2
    """
    return "\n\n---\n\n".join(items)
