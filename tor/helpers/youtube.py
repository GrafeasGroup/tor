import logging
from urllib.parse import parse_qs, urlparse

import requests
from tor.strings import translation

youtube_transcription_url = translation()['urls']['yt_transcript_url']


def get_yt_video_id(url):
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

    if 'youtube' in query.hostname:
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        elif query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    elif 'youtu.be' in query.hostname:
        return query.path[1:]
    else:
        raise ValueError


def get_yt_transcript(url, yt_transcript_url=youtube_transcription_url):
    """
    Takes a url, formats it, and sends it off to Google to request the
    uploader-provided transcripts. If we get them, we return them;
    if we get nothing or an error, it returns None.

    :param url: the YouTube video URL
    :param yt_transcript_url: the unformatted url to get the transcripts
    :return: string; the transcript if we get it, None if we don't or
        if there's an error.
    """
    try:
        result = requests.get(
            yt_transcript_url.format(
                get_yt_video_id(url)
            )
        )
        result.raise_for_status()
        if result.text.startswith(
                '<?xml version="1.0" encoding="utf-8" ?><transcript><text'
        ):
            return result
        else:
            return None
    except requests.exceptions.HTTPError as e:
        logging.error(
            f'{e} - Cannot retrieve transcript for {url}'
        )
        return None


def valid_youtube_video(url):
    """
    We don't want to process channels or user accounts, so we'll filter
    those out here.

    :param url: the YouTube URL we need to check.
    :return: True if it's a video; false if it's a channel,
    user, or playlist.
    """
    banned_keywords = ['user', 'channel', 'playlist']
    for keyword in banned_keywords:
        if keyword in url:
            return False

    return True
