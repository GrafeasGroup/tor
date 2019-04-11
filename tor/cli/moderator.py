import os
import time

from tor import __version__
from tor.cli._base import MyParser
from tor.core.config import config
from tor.core.helpers import run_until_dead
from tor.core.inbox import check_inbox
from tor.core.initialize import build_bot
from tor.helpers.flair import set_meta_flair_on_other_posts
from tor.helpers.threaded_worker import threaded_check_submissions

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

# Musical Dedications:
#
# This program is dedicated to the below artists; their music has
# served as the soundtrack for the continued development of u/ToR.
# List is in alphabetical order. Anyone who contributes to this
# codebase is invited to add their tunes!
#
# Alison Wonderland
# Aramanthe
# Braxton Burks
# Caravan Palace
# David Bowie
# Hiromi
# Girl Talk
# Icon for Hire
# Inverness
# K-391
# Lady Gaga
# Neon Hitch
# The Beatles
# The Killers
# Two Door Cinema Club
#
#
# Streams:
# https://www.youtube.com/watch?v=hX3j0sQ7ot8  # he's dead, Jim


def run(config):
    """
    Primary routine.

    :param config: Global config dict, supplied by tor.core.
    :return: None.
    """
    check_inbox(config)

    threaded_check_submissions(config)

    set_meta_flair_on_other_posts(config)

    if config.debug_mode:
        time.sleep(60)


def get_args():
    p = MyParser()
    p.add_argument('--version', '-v', action='version', help='Prints the program version and exits', version=f'%(prog)s {__version__}')

    p.add_argument('--debug', action='store_true', dest='debug_mode', default=os.getenv('DEBUG_MODE', False), help='Enter a sandbox mode so it will not affect production')
    p.add_argument('--bot-name', action='store', dest='bot_name', default=os.getenv('BOT_NAME', 'bot'), help='Name of the PRAW config section to use for the Reddit API client')

    return p.parse_args()


def main():
    opts = get_args()
    config.debug_mode = opts.debug_mode

    if config.debug_mode:
        bot_name = 'debug'
    else:
        bot_name = opts.bot_name

    build_bot(bot_name, __version__, full_name='u/ToR')
    config.perform_header_check = True
    run_until_dead(run)
