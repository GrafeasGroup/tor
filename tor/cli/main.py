import atexit
import logging
import os
import pathlib
import sys
import time

import beeline
import click
from click.core import Context
from dotenv import load_dotenv
from praw import Reddit
from shiv.bootstrap import current_zipfile  # type: ignore

# The `import tor` lines is necessary because `tor.__SELF_NAME__` is
# set here. Reason: https://gist.github.com/TheLonelyGhost/9dbe810c42d8f2edcf3388a8b19519e1
import tor
from tor import __version__
from tor.core.config import config
from tor.core.helpers import run_until_dead
from tor.core.inbox import check_inbox
from tor.core.initialize import initialize
from tor.helpers.flair import set_meta_flair_on_other_posts
from tor.helpers.threaded_worker import threaded_check_submissions

##############################
NOOP_MODE = bool(os.getenv("NOOP_MODE", ""))
DEBUG_MODE = bool(os.getenv("DEBUG_MODE", ""))
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
# David G (2021-06-14)
# Jason H (2021-07-01)

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
# DIAMANTE
# Dorothy
# Flyleaf
# Halestorm
# Hiromi
# Girl Talk
# Green Day
# Icon for Hire
# Inverness
# John Williams
# K-391
# Lady Gaga
# Neon Hitch
# Queen
# Rage Against the Machine
# Rita Ora
# The Beatles
# The Killers
# The Pretty Reckless
# Two Door Cinema Club
#
#
# Streams:
# https://www.youtube.com/watch?v=hX3j0sQ7ot8  # he's dead, Jim

log = logging.getLogger()

with current_zipfile() as archive:
    dotenv_path: str | None
    if archive:
        # if archive is none, we're not in the zipfile and are probably
        # in development mode right now.
        dotenv_path = str(pathlib.Path(archive.filename).parent / ".env")
    else:
        dotenv_path = None
load_dotenv(dotenv_path=dotenv_path)


def run_noop(cfg):
    pass


@beeline.traced(name="run")
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


@click.group(
    context_settings=dict(help_option_names=["-h", "--help", "--halp"]),
    invoke_without_command=True,
)
@click.pass_context
@click.option(
    "-d",
    "--debug",
    "debug",
    is_flag=True,
    default=DEBUG_MODE,
    help="Puts bot in dev-mode using non-prod credentials",
)
@click.option(
    "-n",
    "--noop",
    "noop",
    is_flag=True,
    default=NOOP_MODE,
    help="Just run the daemon, but take no action (helpful for testing infrastructure changes)",
)
@click.version_option(version=__version__, prog_name=tor.__SELF_NAME__)
def main(ctx: Context, debug: bool, noop: bool):
    """Run ToR."""
    if ctx.invoked_subcommand:
        # If we asked for a specific command, don't run the bot. Instead, pass control
        # directly to the subcommand.
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    honeycomb_key = os.getenv("HONEYCOMB_KEY", "")

    # if no api key, do not send data and instead print what would be sent to stderr
    # if we have a key, pass data to honeycomb.io
    args = {
        "writekey": honeycomb_key,
        "dataset": "transcribersofreddit",
        "service_name": "tor_moderator",
        "debug": True if len(honeycomb_key) == 0 else False,
        "sample_rate": 10,
    }
    beeline.init(**args)
    atexit.register(beeline.close)

    config.debug_mode = debug

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
        password=os.environ.get("REDDIT_PASSWORD", ""),
    )
    initialize(config)
    config.perform_header_check = True
    log.info("Bot built and initialized")

    tor.__SELF_NAME__ = config.r.user.me().name
    if tor.__SELF_NAME__ not in tor.__BOT_NAMES__:
        tor.__BOT_NAMES__.append(tor.__SELF_NAME__)

    if noop:
        run_until_dead(run_noop)
    else:
        run_until_dead(run)


@main.command()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show Pytest output instead of running quietly.",
)
def selfcheck(verbose: bool) -> None:
    """
    Verify the binary passes all tests internally.

    Add any other self-check related code here.
    """
    import pytest

    import tor.test

    # -x is 'exit immediately if a test fails'
    # We need to get the path because the file is actually inside the extracted
    # environment maintained by shiv, not physically inside the archive at the
    # time of running.
    args = ["-x", str(pathlib.Path(tor.test.__file__).parent)]
    if not verbose:
        args.append("-qq")
    # pytest will return an exit code that we can check on the command line
    sys.exit(pytest.main(args))


BANNER = r"""
___________   __________
\__    ___/___\______   \
  |    | /  _ \|       _/
  |    |(  <_> )    |   \
  |____| \____/|____|_  /
                      \/
"""


@main.command()
def shell() -> None:
    """Create a Python REPL inside the environment."""
    import code

    code.interact(local=globals(), banner=BANNER)


if __name__ == "__main__":
    main()
