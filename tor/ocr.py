import logging
import os
import sys
import time
import traceback

import prawcore
import wget
from praw import Reddit
from tesserocr import PyTessBaseAPI

from tor import context as base_context
from tor.core.initialize import configure_logging
from tor.core.initialize import configure_redis
from tor.core.initialize import configure_tor
from tor.helpers.misc import _
from tor.helpers.reddit_ids import clean_id
from tor.strings.ocr import base_comment

"""
General notes for implementation.

Process:

u/transcribersofreddit identifies an image
  redis_server.rpush('ocr_ids', 'ocr::{}'.format(post.fullname))
  redis_server.set('ocr::{}'.format(post.fullname), result.fullname)
  
...where result.fullname is the post that u/transcribersofreddit makes about the image.

Bot:
  every interval (variable):
    thingy = redis_server.lpop('ocr_ids')
    u_tor_post_id = redis_server.get(thingy)
    
    get image from thingy
    download it
    ...OCR magic on thingy...
    save magic
    delete image
    
    u_tor_post_id.reply(ocr_magic)
"""

class context(base_context):
    """
    OCR dependent configuration items. Inherits from the regular bot context
    object.
    """
    ocr_delay = 10


def process_image(local_file):
    with PyTessBaseAPI() as api:
        api.SetImageFile(local_file)
        text = api.GetUTF8Text()

        confidences = api.AllWordConfidences()
        logging.info(confidences)
        logging.info('Average of confidences: {}'.format(
            sum(confidences) / len(confidences))
        )

        # If you feed it a regular image with no text, you'll get newlines
        # and spaces back. We strip those out to see if we actually got
        # anything of substance.
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
        yield s[start:start+n]


def main(context, redis_server):
    while True:
        try:
            time.sleep(context.ocr_delay)
            new_post = redis_server.lpop('ocr_ids').decode('utf-8')
            if new_post is None:
                # nothing new in the queue. Wait and try again.
                continue

            # We got something!
            image_post = r.submission(id=clean_id(new_post))

            # download image for processing
            filename = wget.download(image_post.url)
            result = process_image(filename)
            # delete the image; we don't want to clutter up the hdd
            os.remove(filename)

            if not result:
                # we don't want orphan entries
                redis_server.delete(new_post)
                continue

            tor_post = r.submission(
                id=clean_id(
                    redis_server.get(new_post).decode('utf-8')
                )
            )

            thing_to_reply_to = tor_post.reply(_(base_comment))
            for chunk in chunks(result, 9000):
                # end goal: if something is over 9000 characters long, we
                # should post a top level comment, then keep replying to
                # the comments we make until we run out of chunks.
                thing_to_reply_to = thing_to_reply_to.reply(_(base_comment.format(chunk)))

            redis_server.delete(new_post)

        except (
            prawcore.exceptions.RequestException,
            prawcore.exceptions.ServerError
        ) as e:
            logging.error(e)
            logging.error(
                'PRAW encountered an error communicating with Reddit.'
            )
            logging.error(
                'Sleeping for 60 seconds and trying program loop again.'
            )
            time.sleep(60)


if __name__ == '__main__':
    r = Reddit('bot_ocr')  # loaded from local praw.ini config file
    configure_logging()

    redis_server = configure_redis()

    # the subreddit object shortcut for TranscribersOfReddit
    tor = configure_tor(r, context)

    try:
        main(context, redis_server)
    except Exception as e:
        # try to raise one last flag as it goes down
        tor.message('OCR Exploded :(', traceback.format_exc())
        logging.error(traceback.format_exc())
        sys.exit(1)