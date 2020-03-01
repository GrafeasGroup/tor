import logging
import re
import signal
import sys
import time
from typing import List

from praw.exceptions import APIException  # type: ignore
from praw.models import Comment, Submission, Subreddit  # type: ignore
from prawcore.exceptions import RequestException, ServerError, Forbidden, NotFound  # type: ignore

import tor.core
from tor.core import __version__
from tor.core.config import Config
from tor.strings import translation


log = logging.getLogger(__name__)

subreddit_regex = re.compile(
    r'reddit.com\/r\/([a-z0-9\-\_\+]+)',
    flags=re.IGNORECASE
)
i18n = translation()


class flair(object):
    unclaimed = 'Unclaimed'
    summoned_unclaimed = 'Summoned - Unclaimed'
    completed = 'Completed!'
    in_progress = 'In Progress'
    meta = 'Meta'
    disregard = 'Disregard'


class reports(object):
    original_post_deleted_or_locked = 'Original post has been deleted or locked'
    post_should_be_marked_nsfw = 'Post should be marked as NSFW'
    no_bot_accounts = 'No bot accounts but our own'
    post_violates_rules = 'Post Violates Rules on Partner Subreddit'


# error message for an API timeout
_pattern = re.compile(r'again in (?P<number>[0-9]+) (?P<unit>\w+)s?\.$',
                      re.IGNORECASE)


def _(message: str) -> str:
    """
    Message formatter. Returns the message and the disclaimer for the
    footer.

    :param message: string. The message to be displayed.
    :return: string. The original message plus the footer.
    """
    return i18n['responses']['bot_footer'].format(message, version=__version__)


def clean_list(items: List[str]) -> List[str]:
    """
    Takes a list and removes entries that are only newlines.

    :param items: List.
    :return: List, sans newlines
    """
    return list([item.strip() for item in items if item.strip()])


def send_to_modchat(message: str, cfg: Config, channel='general') -> None:
    """
    Sends a message to the ToR mod chat.

    :param message: String; the message that is to be encoded
    :param cfg: the global config dict.
    :param channel: String; the name of the channel to send to. '#' optional.
    :return: None.
    """
    if cfg.modchat:
        try:
            cfg.modchat.api_call(
                'chat.postMessage',
                channel=channel,
                text=message
            )
        except Exception as e:
            log.error(f'Failed to send message to modchat #{channel}: '
                      f'\'{message}\'')
            log.error(e)


def is_our_subreddit(subreddit_name: str, cfg: Config) -> bool:
    """
    Compares given subreddit to the one we're operating out of

    :param subreddit_name: String; the questioned subreddit
    :param cfg: the global config object
    :return: Boolean for if they are the same subreddit
    """
    # We're referring to `cfg.tor.name` in case of testing environment, and
    # using `.casefold()` to provide cross-characterset, case-insensitive
    # string comparisons.
    # @see https://docs.python.org/3/library/stdtypes.html#str.casefold
    return str(subreddit_name).casefold() == str(cfg.tor.name).casefold()


def clean_id(post_id: str) -> str:
    """
    Fixes the Reddit ID so that it can be used to get a new object.

    By default, the Reddit ID is prefixed with something like `t1_` or
    `t3_`, but this doesn't always work for getting a new object. This
    method removes those prefixes and returns the rest.

    :param post_id: String. Post fullname (ID)
    :return: String. Post fullname minus the first three characters.
    """
    return post_id[post_id.index('_') + 1:]


def get_parent_post_id(post: Comment, subreddit: Subreddit) -> Submission:
    """
    Takes any given comment object and returns the object of the
    original post, no matter how far up the chain it is. This is
    a very time-intensive function because of how Reddit handles
    rate limiting and the fact that you can't just request the
    top parent -- you have to just loop your way to the top.

    :param post: comment object
    :param r: the instantiated reddit object
    :return: submission object of the top post.
    """
    if not post.is_root:
        parent = subreddit.comment(id=clean_id(post.parent_id))
        return get_parent_post_id(parent, subreddit)
    else:
        return subreddit.submission(id=clean_id(post.parent_id))


def get_wiki_page(pagename: str, cfg: Config) -> str:
    """
    Return the contents of a given wiki page.

    :param pagename: String. The name of the page to be requested.
    :param cfg: Dict. Global config object.
    :param return_on_fail: Any value to return when nothing is found
        at the requested page. This allows us to specify returns for
        easier work in debug mode.
    :param subreddit: Object. A specific PRAW Subreddit object if we
        want to interact with a different sub.
    :return: String or None. The content of the requested page if
        present else None.
    """
    log.debug(f'Retrieving wiki page {pagename}')
    try:
        return cfg.tor.wiki[pagename].content_md
    except NotFound:
        return ''


def handle_rate_limit(exc: APIException) -> None:
    time_map = {
        'second': 1,
        'minute': 60,
        'hour': 60 * 60,
    }
    matches = re.search(_pattern, exc.message)
    if not matches:
        log.error(f'Unable to parse rate limit message {exc.message!r}')
        return
    delay = matches[0] * time_map[matches[1]]
    time.sleep(delay + 1)


def run_until_dead(func, cfg: Config):
    """
    The official method that replaces all that ugly boilerplate required to
    start up a bot under the TranscribersOfReddit umbrella. This method handles
    communication issues with Reddit, timeouts, and handles CTRL+C and
    unexpected crashes.

    :param func: The function that you want to run; this will automatically be
        passed the config object. Historically, this is the only thing needed
        to start a bot.
    :param exceptions: A tuple of exception classes to guard against. These are
        a set of PRAW connection errors (timeouts and general connection
        issues) but they can be overridden with a passed-in set.
    :return: None.
    """

    def double_ctrl_c_handler(*args, **kwargs) -> None:
        if not tor.core.is_running:
            log.critical('User pressed CTRL+C twice!!! Killing!')
            sys.exit(1)

        log.info(
            '\rUser triggered command line shutdown. Will terminate after current loop.'
        )
        tor.core.is_running = False

    # handler for CTRL+C
    signal.signal(signal.SIGINT, double_ctrl_c_handler)

    try:
        while tor.core.is_running:
            try:
                func(cfg)
            except APIException as e:
                if e.error_type == 'RATELIMIT':
                    log.warning(
                        'Ratelimit - artificially limited by Reddit. Sleeping'
                        ' for requested time!'
                    )
                    handle_rate_limit(e)
            except (RequestException, ServerError, Forbidden) as e:
                log.warning(f'{e} - Issue communicating with Reddit. Sleeping for 60s!')
                time.sleep(60)

        log.info('User triggered shutdown. Shutting down.')
        sys.exit(0)

    except Exception as e:
        log.error(e)
        sys.exit(1)
