from typing import List


def format_as_markdown_list_item(item: str) -> str:
    """Formats the string as a markdown list item.

    This adds the markdown list item indicator to the first line
    and indents the other lines with two spaces, like this:

    - This is an example
      list item with some
      text and stuff.
    """
    lines = item.splitlines()
    # includes lots of extra spaces to get Reddit to parse it correctly
    return "\n".join([f"- {lines[0]}"] + [f"    {line}" for line in lines[1:]])


def format_as_markdown_list(items: List[str]) -> str:
    """Format the given items as a markdown list.

    It will look like this:

    - Item 1
      with more text
    - Item 2
    - Item 3
    """
    return "\n".join([format_as_markdown_list_item(item) for item in items])
