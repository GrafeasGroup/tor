import logging
import os

from tor import __version__
from tor.cli._base import MyParser
from tor.core.config import config  # type: ignore
from tor.core.initialize import build_bot  # type: ignore
from tor.core.users import User
from tor.helpers.flair import _parse_existing_flair


def run(cfg):
    for flair_obj in config.tor.flair(limit=None):
        username = str(flair_obj["user"])
        logging.info(f"Backing up transcription count for {username}")
        u = User(username, redis_conn=config.redis)
        count, flair_css = _parse_existing_flair(flair_obj["flair_text"])
        u.update("transcriptions", count)
        u.save()


def get_args():
    p = MyParser()
    p.add_argument(
        "--version",
        "-v",
        action="version",
        help="Prints the program version and exits",
        version=f"%(prog)s {__version__}",
    )

    p.add_argument(
        "--debug",
        action="store_true",
        dest="debug_mode",
        default=os.getenv("DEBUG_MODE", False),
        help="Enter a sandbox mode so it will not affect production",
    )
    p.add_argument(
        "--bot-name",
        action="store",
        dest="bot_name",
        default=os.getenv("BOT_NAME", "bot"),
        help="Name of the PRAW config section to use for the Reddit API client",
    )

    p.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="A safe, no write way of running the bot",
    )

    return p.parse_args()


def main():
    opts = get_args()
    config.debug_mode = opts.debug_mode

    if config.debug_mode:
        bot_name = "debug"
    else:
        bot_name = opts.bot_name

    build_bot(bot_name, __version__, full_name="u/ToR")
    config.perform_header_check = True

    if not opts.dry_run:
        run(config)
