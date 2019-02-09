import argparse
import os
import sys
import time

from tor import __version__
from tor.core.config import config
from tor.core.helpers import run_until_dead
from tor.core.inbox import check_inbox
from tor.core.initialize import build_bot
from tor.helpers.flair import set_meta_flair_on_other_posts
from tor.helpers.threaded_worker import threaded_check_submissions


def parse_arguments():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--debug', action='store_true', default=bool(os.environ.get('DEBUG_MODE', False)), help='Puts bot in dev-mode using non-prod credentials')
    parser.add_argument('--noop', action='store_true', default=False, help='Just run the daemon, but take no action (helpful for testing infrastructure changes)')

    return parser.parse_args()


def run(cfg):
    """
    Primary routine.

    :param config: Global config dict, supplied by tor_core.
    :return: None.
    """
    check_inbox(config)

    threaded_check_submissions(config)

    set_meta_flair_on_other_posts(config)

    if config.debug_mode:
        time.sleep(60)


def noop(cfg):
    pass


def main():
    opt = parse_arguments()
    config.debug_mode = opt.debug

    if config.debug_mode:
        bot_name = 'debug'
    else:
        bot_name = os.environ.get('BOT_NAME', 'bot')

    if not opt.noop:
        build_bot(bot_name, __version__, full_name='u/ToR')
        config.perform_header_check = True

        sys.stderr.write('Starting ToR bot\n')
        run_until_dead(run)
    else:
        sys.stderr.write('Starting ToR bot (noop mode)\n')
        run_until_dead(noop)


if __name__ == '__main__':
    main()
