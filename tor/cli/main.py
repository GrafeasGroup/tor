import argparse
import os
import time
import logging

from praw import Reddit  # type: ignore
from dotenv import load_dotenv

# The `import tor` lines is necessary because `tor.__SELF_NAME__` is
# set here. Reason: https://gist.github.com/TheLonelyGhost/9dbe810c42d8f2edcf3388a8b19519e1
import tor
from tor import __version__
from tor.core.config import config
from tor.core.helpers import run_until_dead
from tor.core.inbox import check_inbox
from tor.core.initialize import configure_logging, initialize
from tor.helpers.flair import set_meta_flair_on_other_posts
from tor.helpers.threaded_worker import threaded_check_submissions

##############################
NOOP_MODE = bool(os.getenv('NOOP_MODE', ''))
DEBUG_MODE = bool(os.getenv('DEBUG_MODE', ''))
##############################

# Patreon Dedications:
#
# Through our work supported by Grafeas Group Ltd., some people see
# fit to help us keep the lights on. Of those helpful souls, even
# fewer gift $50 or more and they have earned their place in the
# following list. For reference, the link can be found here:
# https://www.patreon.com/grafeasgroup
# List is in date order.
#
# Jake L (2017-11-17)
# Michael W (2017-11-27)
# Luke Abby (2019-07-02)

# Musical Dedications:
#
# This program is dedicated to the below artists; their music has
# served as the soundtrack for the continued development of u/ToR.
# List is in alphabetical order. Anyone who contributes to this
# codebase is invited to add their tunes!
#
# Alec Benjamin
# Alison Wonderland
# Apashe
# Aramanthe
# Betty Who
# blink-182
# Braxton Burks
# Caravan Palace
# Daft Punk
# David Bowie
# Dorothy
# Hiromi
# Girl Talk
# Green Day
# Icon for Hire
# Inverness
# John Williams
# K-391
# Lady Gaga
# Neon Hitch
# Rage Against the Machine
# The Beatles
# The Killers
# Two Door Cinema Club
#
#
# Streams:
# https://www.youtube.com/watch?v=hX3j0sQ7ot8  # he's dead, Jim

log = logging.getLogger()
load_dotenv()


def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '--debug',
        action='store_true',
        default=DEBUG_MODE,
        help='Puts bot in dev-mode using non-prod credentials'
    )
    parser.add_argument(
        '--noop',
        action='store_true',
        default=NOOP_MODE,
        help=(
            'Just run the daemon, but take no action (helpful for testing infrastructure'
            ' changes)'
        )
    )

    return parser.parse_args()


def noop(cfg):
    pass


def run(cfg):
    """
    Primary routine.

    :param cfg: Global config dict, supplied by tor_core.
    :return: None.
    """
    check_inbox(cfg)

    threaded_check_submissions(cfg)

    set_meta_flair_on_other_posts(cfg)

    if cfg.debug_mode:
        time.sleep(15)


def main():
    configure_logging(config)
    config.debug_mode = DEBUG_MODE

    if config.debug_mode:
        bot_name = "debug"
    else:
        bot_name = os.environ.get("BOT_NAME", "bot")

    log.info(f"Connecting to Reddit as {bot_name}.")
    config.r = Reddit(
        user_agent=bot_name,
        client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
        client_secret=os.environ.get("REDDIT_SECRET", ""),
        username=os.environ.get("REDDIT_USERNAME", ""),
        password=os.environ.get("REDDIT_PASSWORD", "")
    )
    initialize(config)
    config.perform_header_check = True
    log.info("Bot built and initialized")

    tor.__SELF_NAME__ = config.r.user.me().name
    if tor.__SELF_NAME__ not in tor.__BOT_NAMES__:
        tor.__BOT_NAMES__.append(tor.__SELF_NAME__)

    if NOOP_MODE:
        run_until_dead(noop)
    else:
        run_until_dead(run)


if __name__ == "__main__":
    main()
