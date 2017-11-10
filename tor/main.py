import os
import time

from tor_core.config import config
from tor_core.helpers import run_until_dead
from tor_core.initialize import build_bot

from tor import __version__
from tor.core.inbox import check_inbox
from tor.core.posts import check_submissions
from tor.helpers.flair import set_meta_flair_on_other_posts


# Musical Dedications:
#
# This program is dedicated to the below artists; their music has
# served as the soundtrack for the continued development of u/ToR.
# List is in alphabetical order.
#
# Aramanthe
# Caravan Palace
# Hiromi
# Girl Talk
# Icon for Hire
# Lady Gaga
#
# Streams:
# https://www.youtube.com/watch?v=hX3j0sQ7ot8


def run(config):
    """
    Primary routine.

    :param config: Global config dict, supplied by tor_core.
    :return: None.
    """
    check_inbox(config)

    for sub in config.subreddits_to_check:
        check_submissions(sub, config)

    set_meta_flair_on_other_posts(config)

    if config.debug_mode:
        time.sleep(60)


def main():
    config.debug_mode = bool(os.environ.get('DEBUG_MODE', False))
    bot_name = 'debug' if config.debug_mode \
        else os.environ.get('BOT_NAME', 'bot')
    build_bot(bot_name, __version__, full_name='u/ToR')
    config.perform_header_check = True
    run_until_dead(run)


if __name__ == '__main__':
    main()
