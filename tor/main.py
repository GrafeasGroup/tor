import logging
import sys
import time

# noinspection PyUnresolvedReferences
import better_exceptions
import prawcore
from praw import Reddit

from tor import config
from tor.core.inbox import check_inbox
from tor.core.initialize import configure_logging
from tor.core.initialize import configure_redis
from tor.core.initialize import configure_tor
from tor.core.initialize import initialize
from tor.core.posts import check_submissions
from tor.helpers.misc import set_meta_flair_on_other_posts

# This program is dedicated to Aramanthe and Icon For Hire, whose music
# has served as the soundtrack for much of its continued development.

if __name__ == '__main__':
    r = Reddit('bot')  # loaded from local praw.ini config file
    configure_logging()

    redis_server = configure_redis()

    # the subreddit object shortcut for TranscribersOfReddit
    tor = configure_tor(r, config)

    initialize(tor, config)
    logging.info('Initialization complete.')

    try:
        while True:
            try:
                check_inbox(r, tor, redis_server, config)

                for sub in config.subreddits_to_check:
                    check_submissions(sub, r, tor, redis_server, config)

                set_meta_flair_on_other_posts(r, tor, config)

                if config.debug_mode:
                    time.sleep(60)

            except (
                prawcore.exceptions.RequestException,
                prawcore.exceptions.ServerError,
                # this will also trigger if we get banned from somewhere.
                # We will need to plan on some jerk banning us without warning,
                # but for now we will treat is as an API error and try again.
                prawcore.exceptions.Forbidden
            ) as e:
                logging.error(
                    '{} - Issue communicating with Reddit. Sleeping for 60s!'
                    ''.format(e), exc_info=1
                )
                time.sleep(60)

    except KeyboardInterrupt:
        logging.info('User triggered shutdown. Shutting down.')
        sys.exit(0)

    except Exception as e:
        # try to raise one last flag as it goes down
        tor.message('{} - I BROKE'.format(e), exc_info=1)
        logging.error(e, exc_info=1)
        sys.exit(1)
