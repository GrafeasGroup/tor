import logging
import sys
import time
import traceback

# noinspection PyUnresolvedReferences
import better_exceptions
import prawcore
from praw import Reddit

from tor import context
from tor.core.inbox import check_inbox
from tor.core.initialize import configure_logging
from tor.core.initialize import configure_redis
from tor.core.initialize import configure_tor
from tor.core.initialize import initialize
from tor.core.posts import check_submissions
from tor.helpers.misc import set_meta_flair_on_other_posts

# This program is dedicated to Aramanthe and Icon For Hire, whose music
# has served as the soundtrack for much of its continued development.
# praw.exceptions.APIException

if __name__ == '__main__':
    r = Reddit('bot')  # loaded from local praw.ini config file
    configure_logging()

    redis_server = configure_redis()

    # the subreddit object shortcut for TranscribersOfReddit
    tor = configure_tor(r, context)

    initialize(tor, context)
    logging.info('Initialization complete.')

    try:
        while True:
            try:
                check_inbox(r, tor, redis_server, context)

                for sub in context.subreddits_to_check:
                    # check_submissions(sub, r, tor, redis_server, context)
                    pass

                set_meta_flair_on_other_posts(r, tor, context)

                if context.debug_mode:
                    time.sleep(60)

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

    except KeyboardInterrupt:
        logging.error('User triggered shutdown. Shutting down.')
        sys.exit(0)

    except Exception as e:
        # try to raise one last flag as it goes down
        tor.message('I BROKE', traceback.format_exc())
        logging.error(traceback.format_exc())
        sys.exit(1)
