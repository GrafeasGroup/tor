from urllib.parse import urlparse

from tor.strings import translation

i18n = translation()


def is_youtube_url(url: str) -> bool:
    if url.startswith(("youtu", "www")):
        url = "http://" + url

    query = urlparse(url)

    if "youtube" in str(query.hostname):
        return True
    if "youtu.be" in str(query.hostname):
        return True
    return False


def is_transcribable_youtube_video(url: str) -> bool:
    """We don't want to process channels or user accounts, so we'll filter
    those out here.

    :param url: the YouTube URL we need to check.
    :return: True if it's a video; false if it's a channel,
    user, or playlist.
    """
    return not any(keyword in url for keyword in ["user", "channel", "playlist"])
