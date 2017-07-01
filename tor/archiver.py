import sys
import logging

import prawcore
from praw import Reddit

from tor import config
from tor.core.initialize import configure_logging
from tor.core.initialize import configure_tor
from tor.helpers.misc import explode_gracefully, subreddit_from_url

from tor.strings.urls import reddit_url

from time import sleep
from datetime import datetime


def run(tor, config, archive):
    # TODO the bot will now check ALL posts on the subreddit.
    # when we remove old transcription requests, there aren't too many left.
    # but we should make it stop after a certain amount of time anyway
    # eg. if it encounters a post >36 hours old, it will break the loop

    # TODO we can use .submissions(end=unixtime) apparently

    for post in tor.new():
        # [META] - do nothing
        # [UNCLAIMED] - remove
        # [COMPLETED] - remove and x-post to r/tor_archive
        # [IN PROGRESS] - do nothing (should discuss)
        flair = post.link_flair_css_class

        if flair not in ('unclaimed', 'transcriptioncomplete'):
            continue

        # find the original post subreddit
        # take it in lowercase so the config is case insensitive
        post_subreddit = subreddit_from_url(post.url).lower()

        # hours until a post from this subreddit should be archived
        hours = config.archive_time_subreddits.get(
            post_subreddit, config.archive_time_default)

        # time since this post was made
        date = datetime.utcfromtimestamp(post.created_utc)
        seconds = (date - datetime.utcnow()).seconds

        if seconds > hours * 3600:
            logging.info(
                'Post "{}" is older than maximum age, removing.'.format(
                    post.title)
            )

            post.mod.remove()

            if flair == 'completed':
                logging.info('Archiving completed post...')
                archive.submit(
                    post.title,
                    url=reddit_url.format(post.url))


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

    except (
            prawcore.exceptions.RequestException,
            prawcore.exceptions.ServerError,
            prawcore.exceptions.Forbidden
    ) as e:
        logging.warning(
            '{} - Issue communicating with Reddit. Sleeping for 60s!'
            ''.format(e)
        )
        time.sleep(60)

    except Exception as e:
        explode_gracefully('archiver bot', e, tor)
