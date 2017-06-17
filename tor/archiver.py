import sys
import logging

from praw import Reddit

from tor import config
from tor.core.initialize import configure_logging
from tor.core.initialize import configure_tor
from tor.helpers.misc import explode_gracefully
from tor.helpers.reddit_ids import clean_id

from time import sleep
from datetime import datetime


def run(tor, config, archive):
    # TODO the bot will now check ALL posts on the subreddit.
    # when we remove old transcription requests, there aren't too many left.
    # but we should make it stop after a certain amount of time anyway
    # eg. if it encounters a post >36 hours old, it will break the loop

    # TODO we can use .submissions(end=unixtime) apparently

    for post in tor.new():
        date = datetime.utcfromtimestamp(post.created_utc)
        seconds = (date - datetime.utcnow()).seconds

        # TODO retrieve max ages from config
        if seconds > 18 * 3600:
            # [META] - do nothing
            # [UNCLAIMED] - remove
            # [COMPLETED] - remove and x-post to r/tor_archive
            # [IN PROGRESS] - do nothing (should discuss)
            flair = post.link_flair_css_class

            if flair not in ('unclaimed', 'completed'):
                continue

            logging.info(
                'Post "{}" is older than maximum age, removing.'.format(
                    post.title)
            )

            post.mod.remove()

            if flair == 'completed':
                logging.info('Archiving completed post...')
                archive.submit(
                    post.title,
                    url='http://redd.it/' + clean_id(post.link_id))


if __name__ == '__main__':
    r = Reddit('bot_archiver')

    configure_logging(config)
    logging.basicConfig(filename='archiver.log')

    tor = configure_tor(r, config)

    archive = r.subreddit('ToR_Archive')

    try:
        while True:
            run(tor, config, archive)
            sleep(300)  # 5 minutes

    except KeyboardInterrupt:
        logging.info('Received keyboard interrupt! Shutting down!')
        sys.exit(0)

    except Exception as e:
        explode_gracefully('archiver bot', e, tor)
