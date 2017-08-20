import logging
import os
import sys
import time
import urllib
from tesserocr import PyTessBaseAPI

import prawcore
import wget
from praw import Reddit

from tor.core.config import config
from tor.core.initialize import configure_logging
from tor.core.initialize import configure_redis
from tor.core.initialize import configure_tor
from tor.helpers.misc import _
from tor.helpers.misc import explode_gracefully
from tor.helpers.reddit_ids import clean_id
from tor.strings.ocr import base_comment

"""
General notes for implementation.

Process:

u/transcribersofreddit identifies an image
  config.redis.rpush('ocr_ids', 'ocr::{}'.format(post.fullname))
  config.redis.set('ocr::{}'.format(post.fullname), result.fullname)

...where result.fullname is the post that u/transcribersofreddit makes about
the image.

Bot:
  every interval (variable):
    thingy = config.redis.lpop('ocr_ids')
    u_tor_post_id = config.redis.get(thingy)

    get image from thingy
    download it
    ...OCR magic on thingy...
    save magic
    delete image

    u_tor_post_id.reply(ocr_magic)
"""


def process_image(local_file):
    with PyTessBaseAPI() as api:
        api.SetImageFile(local_file)
        text = api.GetUTF8Text()

        confidences = api.AllWordConfidences()
        if not confidences or len(confidences) == 0:
            # we have an image, but it *really* couldn't find anything, not
            # even false positives.
            return None

        logging.debug('Average of confidences: {}'.format(
            sum(confidences) / len(confidences))
        )

        # If you feed it a regular image with no text, more often than not
        # you'll get newlines and spaces back. We strip those out to see if
        # we actually got anything of substance.
        if text.strip() != '':
            return text
        else:
            return None


def chunks(s, n):
    """
    Produce n-character chunks from s.
    :param s: incoming string.
    :param n: number of characters to cut the chunk at.
    """
    for start in range(0, len(s), n):
        yield s[start:(start + n)]


def run(config):
    while True:
        try:
            time.sleep(config.ocr_delay)
            new_post = config.redis.lpop('ocr_ids')
            if new_post is None:
                logging.debug('No post found. Sleeping.')
                # nothing new in the queue. Wait and try again.
                continue

            # We got something!
            new_post = new_post.decode('utf-8')
            logging.info(
                'Found a new post, ID {}'.format(new_post)
            )
            image_post = config.r.submission(id=clean_id(new_post))

            # download image for processing
            # noinspection PyUnresolvedReferences
            try:
                filename = wget.download(image_post.url)
            except urllib.error.HTTPError:
                # what if the post has been deleted? Ignore it and continue.
                continue

            try:
                result = process_image(filename)
            except RuntimeError:
                logging.warning(
                    'Either we hit an imgur album or no text was returned.'
                )
                os.remove(filename)
                continue

            logging.debug('result: {}'.format(result))

            # delete the image; we don't want to clutter up the hdd
            os.remove(filename)

            if not result:
                logging.info('Result was none! Skipping!')
                # we don't want orphan entries
                config.redis.delete(new_post)
                continue

            tor_post_id = config.redis.get(new_post).decode('utf-8')

            logging.info(
                'posting transcription attempt for {} on {}'.format(
                    new_post, tor_post_id
                )
            )

            tor_post = config.r.submission(id=clean_id(tor_post_id))

            thing_to_reply_to = tor_post.reply(_(base_comment))
            for chunk in chunks(result, 9000):
                # end goal: if something is over 9000 characters long, we
                # should post a top level comment, then keep replying to
                # the comments we make until we run out of chunks.
                thing_to_reply_to = thing_to_reply_to.reply(_(chunk))

            config.redis.delete(new_post)

        except (
            prawcore.exceptions.RequestException,
            prawcore.exceptions.ServerError
        ) as e:
            logging.warning(
                '{} - Issue communicating with Reddit. Sleeping for 60s!'
                ''.format(e)
            )
            time.sleep(60)


def main():
    '''
    Console scripts entry point for OCR Bot
    '''
    config.ocr_delay = 10
    config.r = Reddit('bot_ocr')  # loaded from local praw.ini config file
    configure_logging(config, log_name='ocr.log')
    logging.basicConfig(
        filename='ocr.log'
    )

    config.redis = configure_redis()

    # the subreddit object shortcut for TranscribersOfReddit
    tor = configure_tor(config.r, config)

    try:
        run(config)

    except KeyboardInterrupt:
        logging.info('Received keyboard interrupt! Shutting down!')
        sys.exit(0)

    except Exception as e:
        explode_gracefully('u/transcribot', e, tor)


if __name__ == '__main__':
    main()
