import time

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
#
# Aramanthe
# Caravan Palace
# Icon for Hire
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
    build_bot('bot', __version__, full_name='u/ToR')
    run_until_dead(run)

if __name__ == '__main__':
    main()
