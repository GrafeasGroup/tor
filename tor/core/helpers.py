import logging
import re
import signal
import sys
import time

import praw
import prawcore

from tor import __version__
from tor.core.config import config
from tor.core.heartbeat import stop_heartbeat_server
from tor.core.strings import bot_footer


class Object(object):
    pass


semaphores = {}


subreddit_regex = re.compile("reddit.com\/r\/([a-z0-9\-\_\+]+)", flags=re.IGNORECASE)

default_exceptions = (
    prawcore.exceptions.RequestException,
    prawcore.exceptions.ServerError,
    prawcore.exceptions.Forbidden,
)

flair = Object()
flair.unclaimed = "Unclaimed"
flair.summoned_unclaimed = "Summoned - Unclaimed"
flair.completed = "Completed!"
flair.in_progress = "In Progress"
flair.meta = "Meta"
flair.disregard = "Disregard"

css_flair = Object()
css_flair.unclaimed = "unclaimed"
css_flair.completed = "transcriptioncomplete"
css_flair.in_progress = "inprogress"
css_flair.meta = "meta"
css_flair.disregard = "disregard"

reports = Object()
reports.original_post_deleted_or_locked = "Original post has been deleted or locked"
reports.post_should_be_marked_nsfw = "Post should be marked as NSFW"
reports.no_bot_accounts = "No bot accounts but our own"
reports.post_violates_rules = "Post Violates Rules on Partner Subreddit"

# error message for an API timeout
_pattern = re.compile("again in (?P<number>[0-9]+) (?P<unit>\w+)s?\.$", re.IGNORECASE)

# CTRL+C handler variable
running = True


def _(message):
    """
    Message formatter. Returns the message and the disclaimer for the
    footer.

    :param message: string. The message to be displayed.
    :return: string. The original message plus the footer.
    """
    return bot_footer.format(message, version=__version__)


def log_header(message):
    logging.info("*" * 50)
    logging.info(message)
    logging.info("*" * 50)


def clean_list(items):
    """
    Takes a list and removes entries that are only newlines.

    :param items: List.
    :return: List, sans newlines
    """
    cleaned = []
    for item in items:
        if item.strip() != "":
            cleaned.append(item)

    return cleaned


def send_to_modchat(message, config, channel="general"):
    """
    Sends a message to the ToR mod chat.

    :param message: String; the message that is to be encoded
    :param config: the global config dict.
    :param channel: String; the name of the channel to send to. '#' optional.
    :return: None.
    """
    if config.modchat:
        try:
            config.modchat.api_call("chat.postMessage", channel=channel, text=message)
        except Exception as e:
            logging.error(
                f"Failed to send message to modchat #{channel}: " f"'{message}'"
            )
            logging.error(e)
    else:
        if "modchat_warning" not in semaphores:
            logging.warning("Modchat not configured")
            semaphores["modchat_warning"] = True

        logging.debug(
            "Modchat Message ({channel}): {msg}".format(msg=message, channel=channel)
        )


def explode_gracefully(error, config):
    """
    A last-ditch effort to try to raise a few more flags as it goes down.
    Only call in times of dire need.

    :param bot_name: string; the name of the bot calling the method.
    :param error: an exception object.
    :param tor: the r/ToR helper object
    :return: Nothing. Everything dies here.
    """
    logging.error(error)
    sys.exit(1)


def subreddit_from_url(url):
    """
    Returns the subreddit a post was made in, based on its reddit URL
    """
    m = subreddit_regex.search(url)
    if m is not None:
        return m.group(1)
    return None


def clean_id(post_id):
    """
    Fixes the Reddit ID so that it can be used to get a new object.

    By default, the Reddit ID is prefixed with something like `t1_` or
    `t3_`, but this doesn't always work for getting a new object. This
    method removes those prefixes and returns the rest.

    :param post_id: String. Post fullname (ID)
    :return: String. Post fullname minus the first three characters.
    """
    return post_id[post_id.index("_") + 1 :]


def get_parent_post_id(post, r):
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
    while True:
        if not post.is_root:
            post = r.comment(id=clean_id(post.parent_id))
        else:
            return r.submission(id=clean_id(post.parent_id))


def get_wiki_page(pagename, config, return_on_fail=None, subreddit=None):
    """
    Return the contents of a given wiki page.

    :param pagename: String. The name of the page to be requested.
    :param config: Dict. Global config object.
    :param return_on_fail: Any value to return when nothing is found
        at the requested page. This allows us to specify returns for
        easier work in debug mode.
    :param subreddit: Object. A specific PRAW Subreddit object if we
        want to interact with a different sub.
    :return: String or None. The content of the requested page if
        present else None.
    """
    if not subreddit:
        subreddit = config.tor
    logging.debug(f"Retrieving wiki page {pagename}")
    try:
        result = subreddit.wiki[pagename].content_md
        return result if result != "" else return_on_fail
    except prawcore.exceptions.NotFound:
        return return_on_fail


def update_wiki_page(pagename, content, config, subreddit=None):
    """
    Sends new content to the requested wiki page.

    :param pagename: String. The name of the page to be edited.
    :param content: String. New content for the wiki page.
    :param config: Dict. Global config object.
    :param subreddit: Object. A specific PRAW Subreddit object if we
        want to interact with a different sub.
    :return: None.
    """

    logging.debug(f"Updating wiki page {pagename}")

    if not subreddit:
        subreddit = config.tor

    try:
        return subreddit.wiki[pagename].edit(content)
    except prawcore.exceptions.NotFound as e:
        logging.error(f"{e} - Requested wiki page {pagename} not found. Cannot update.")


def deactivate_heartbeat_port(port):
    """
    This isn't used as part of the normal functions; when a port is created,
    it gets used again and again. The point of this function is to deregister
    the port that the status page checks, but would probably only be used by
    the command line.

    :param port: int, the port number
    :return: None
    """
    config.redis.srem("active_heartbeat_ports", port)
    logging.info("Removed port from set of heartbeats.")


def stop_heartbeat(config):
    """
    Any logic that goes along with stopping the cherrypy heartbeat server goes
    here. This is called on exit of `run_until_dead()`, either through keyboard
    or crash. The heartbeat server will terminate if the process dies anyway,
    but this allows for a clean shutdown.

    :param config: the global config object
    :return: None
    """
    stop_heartbeat_server()
    logging.info("Stopped heartbeat!")


def handle_rate_limit(exc):
    time_map = {"second": 1, "minute": 60, "hour": 60 * 60}
    matches = re.search(_pattern, exc.message)
    delay = matches[0] * time_map[matches[1]]
    time.sleep(delay + 1)


def signal_handler(signal, frame):
    """
    This is the SIGINT handler that allows us to intercept CTRL+C.
    When this is triggered, it will wait until the primary loop ends
    the current iteration before ending. Press CTRL+C twice to kill
    immediately.

    :param signal: Unused.
    :param frame: Unused.
    :return: None.
    """
    global running

    if not running:
        logging.critical("User pressed CTRL+C twice!!! Killing!")
        stop_heartbeat(config)
        sys.exit(1)

    logging.info(
        "\rUser triggered command line shutdown. Will terminate after current loop."
    )
    running = False


def run_until_dead(func, exceptions=default_exceptions):
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
    # handler for CTRL+C
    signal.signal(signal.SIGINT, signal_handler)

    try:
        while running:
            try:
                func(config)
            except praw.exceptions.APIException as e:
                if e.error_type == "RATELIMIT":
                    logging.warning(
                        "Ratelimit - artificially limited by Reddit. Sleeping"
                        " for requested time!"
                    )
                    handle_rate_limit(e)
            except exceptions as e:
                logging.warning(
                    f"{e} - Issue communicating with Reddit. Sleeping for 60s!"
                )
                time.sleep(60)

        logging.info("User triggered shutdown. Shutting down.")
        stop_heartbeat(config)
        sys.exit(0)

    except Exception as e:
        stop_heartbeat(config)
        explode_gracefully(e, config)
