from tor.core.helpers import cleanup_post_title


def test_cleanup_post_title() -> None:
    """Verify that the post title is cleaned up correctly."""
    title = "Test &amp; other stuff &lt;3 1 &gt; 2 abc"
    expected = "Test & other stuff <3 1 > 2 abc"
    actual = cleanup_post_title(title)
    assert actual == expected
