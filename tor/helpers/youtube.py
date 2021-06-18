import logging
from urllib.parse import parse_qs, urlparse

import requests
from requests.exceptions import HTTPError

from tor.strings import translation

i18n = translation()


def get_yt_video_id(url: str) -> str:
    """
    Returns Video_ID extracting from the given url of Youtube

    Examples of URLs:
      Valid:
        'http://youtu.be/_lOT2p_FCvA',
        'www.youtube.com/watch?v=_lOT2p_FCvA&feature=feedu',
        'http://www.youtube.com/embed/_lOT2p_FCvA',
        'http://www.youtube.com/v/_lOT2p_FCvA?version=3&amp;hl=en_US',
        'https://www.youtube.com/watch?v=rTHlyTphWP0&index=6&list=PLjeDyYvG6-40qawYNR4juzvSOg-ezZ2a6',
        'youtube.com/watch?v=_lOT2p_FCvA',

      Invalid:
        'youtu.be/watch?v=_lOT2p_FCvA',
    """
    # initial version: http://stackoverflow.com/a/7936523/617185
    # by Mikhail Kashkin (http://stackoverflow.com/users/85739/mikhail-kashkin)

    if url.startswith(('youtu', 'www')):
        url = 'http://' + url

    query = urlparse(url)

    if 'youtube' in str(query.hostname):
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        elif query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    elif 'youtu.be' in str(query.hostname):
        return query.path[1:]

    return ''


def has_youtube_transcript(url: str) -> bool:
    try:
        video_id = get_yt_video_id(url)
        if not video_id:
            return False

        result = requests.get(i18n['urls']['yt_transcript_url'].format(video_id))
        result.raise_for_status()

        if result.text.startswith('<?xml version="1.0" encoding="utf-8" ?><transcript><text'):
            return True

        return False
    except HTTPError as e:
        logging.error(f'{e} - Cannot retrieve transcript for {url}')
        return False


def is_youtube_url(url: str) -> bool:
    if url.startswith(('youtu', 'www')):
        url = 'http://' + url

    query = urlparse(url)

    if 'youtube' in str(query.hostname):
        return True
    if 'youtu.be' in str(query.hostname):
        return True
    return False


def is_transcribable_youtube_video(url: str) -> bool:
    """
    We don't want to process channels or user accounts, so we'll filter
    those out here.

    :param url: the YouTube URL we need to check.
    :return: True if it's a video; false if it's a channel,
    user, or playlist.
    """
    if not is_youtube_url(url):
        return False

    return not any(keyword in url for keyword in ['user', 'channel', 'playlist'])
