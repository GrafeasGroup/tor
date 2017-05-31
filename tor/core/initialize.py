import logging
import sys

import redis
from bugsnag.handlers import BugsnagHandler

from tor.helpers.misc import log_header
from tor.helpers.misc import clean_list
from tor.helpers.wiki import get_wiki_page


def configure_tor(r, config):
    """
    Assembles the tor object based on whether or not we've enabled debug mode
    and returns it. There's really no reason to put together a Subreddit
    object dedicated to our subreddit -- it just makes some future lines
    a little easier to type.
    
    :param r: the active Reddit object.
    :param config: the global config object.
    :return: the Subreddit object for the chosen subreddit.
    """
    if config.debug_mode:
        tor = r.subreddit('ModsOfToR')
    else:
        # normal operation, our primary subreddit
        tor = r.subreddit('transcribersofreddit')

    return tor


def configure_redis():
    """
    Creates a connection to the local Redis server, then returns the active
    connection.
    
    :return: object: the active Redis object.
    """
    try:
        redis_server = redis.StrictRedis(host='localhost', port=6379, db=0)
        redis_server.ping()
    except redis.exceptions.ConnectionError:
        logging.fatal("Redis server is not running! Exiting!")
        sys.exit(1)

    return redis_server


def configure_logging(config):
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] - [%(levelname)s] - [%(funcName)s] - %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        filename='transcribersofreddit.log'
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] - [%(funcName)s] - %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)

    # add the handlers to the root logger
    logging.getLogger('').addHandler(console)
    # will intercept anything error level or above
    if config.bs_api_key:
        bs_handler = BugsnagHandler()
        bs_handler.setLevel(logging.ERROR)
        logging.getLogger('').addHandler(bs_handler)

    if config.bs_api_key:
        logging.info('Bugsnag enabled!')
    else:
        logging.info('Not running with Bugsnag!')

    log_header('Starting!')


def populate_header(tor, config):
    config.header = ''
    config.header = get_wiki_page('format/header', tor=tor)


def populate_formatting(tor, config):
    """
    Grabs the contents of the three wiki pages that contain the
    formatting examples and stores them in the config object.

    :return: None.
    """
    # zero out everything so we can reinitialize later
    config.audio_formatting = ''
    config.video_formatting = ''
    config.image_formatting = ''

    config.audio_formatting = get_wiki_page('format/audio', tor=tor)
    config.video_formatting = get_wiki_page('format/video', tor=tor)
    config.image_formatting = get_wiki_page('format/images', tor=tor)


def populate_domain_lists(tor, config):
    """
    Loads the approved content domains into the config object from the
    wiki page.

    :return: None.
    """

    config.video_domains = []
    config.image_domains = []
    config.audio_domains = []

    domains = get_wiki_page('domains', tor=tor)
    domains = ''.join(domains.splitlines()).split('---')

    for domainset in domains:
        domain_list = domainset[domainset.index('['):].strip('[]').split(', ')
        current_domain_list = []
        if domainset.startswith('video'):
            current_domain_list = config.video_domains
        elif domainset.startswith('audio'):
            current_domain_list = config.audio_domains
        elif domainset.startswith('images'):
            current_domain_list = config.image_domains
        [current_domain_list.append(x) for x in domain_list]
        logging.debug('Domain list populated: {}'.format(current_domain_list))


def populate_moderators(tor, config):
    # Praw doesn't cache this information, so it requests it every damn time
    # we ask about the moderators. Let's cache this so we can drastically cut
    # down on the number of calls for the mod list.

    # nuke the existing list
    config.tor_mods = []

    # this call returns a full list rather than a generator. Praw is weird.
    config.tor_mods = tor.moderator()


def populate_subreddit_lists(tor, config):
    """
    Gets the list of subreddits to monitor and loads it into memory.

    :return: None.
    """

    config.subreddits_to_check = []
    config.upvote_filter_subs = []
    config.no_link_header_subs = []

    config.subreddits_to_check = get_wiki_page('subreddits', tor=tor).split('\r\n')
    config.subreddits_to_check = clean_list(config.subreddits_to_check)
    logging.debug(
        'Created list of subreddits from wiki: {}'.format(
            config.subreddits_to_check
        )
    )

    config.upvote_filter_subs = get_wiki_page(
        'subreddits/upvote-filtered', tor=tor
    ).split('\r\n')
    config.upvote_filter_subs = clean_list(config.upvote_filter_subs)
    logging.debug(
        'Retrieved subreddits subject to the upvote filter: {}'.format(
            config.upvote_filter_subs
        )
    )

    config.no_link_header_subs = get_wiki_page(
        'subreddits/no-link-header', tor=tor
    ).split('\r\n')
    config.no_link_header_subs = clean_list(config.no_link_header_subs)
    logging.debug(
        'Retrieved subreddits subject to the upvote filter: {}'.format(
            config.no_link_header_subs
        )
    )

    config.upvote_filter_threshold = get_wiki_page(
        'subreddits/upvote-filtered/filter', tor=tor
    )
    logging.debug(
        'Retrieved upvote filter number: {}'.format(
            config.upvote_filter_threshold
        )
    )


def populate_gifs(tor, config):
    # zero it out so we can load more
    config.no_gifs = []
    config.no_gifs = get_wiki_page('usefulgifs/no', tor=tor).split('\r\n')


def initialize(tor, config):
    populate_domain_lists(tor, config)
    logging.debug('Domains loaded.')
    populate_subreddit_lists(tor, config)
    logging.debug('Subreddits loaded.')
    populate_formatting(tor, config)
    logging.debug('Formatting loaded.')
    populate_header(tor, config)
    logging.debug('Header loaded.')
    populate_moderators(tor, config)
    logging.debug('Mod list loaded.')
    populate_gifs(tor, config)
    logging.debug('Gifs loaded.')
