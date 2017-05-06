import logging
import sys

import redis

from tor.helpers.misc import log_header
from tor.helpers.wiki import get_wiki_page


def configure_tor(r, context):
    """
    Assembles the tor object based on whether or not we've enabled debug mode
    and returns it. There's really no reason to put together a Subreddit
    object dedicated to our subreddit -- it just makes some future lines
    a little easier to type.
    
    :param r: the active Reddit object.
    :param context: the global context object.
    :return: the Subreddit object for the chosen subreddit.
    """
    if context.debug_mode:
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
        logging.error("Redis server is not running! Exiting!")
        sys.exit(1)

    return redis_server


def configure_logging():
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
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    log_header('Starting!')


def populate_header(tor, context):
    context.header = ''

    result = get_wiki_page('format/header', tor=tor)
    result = result.split('\r\n')
    temp = []
    for part in result:
        part = part.lstrip().rstrip()
        if part == '':
            continue
        if part == '---':
            continue
        temp.append(part)
    context.header = ' '.join(temp)


def populate_formatting(tor, context):
    """
    Grabs the contents of the three wiki pages that contain the
    formatting examples and stores them in the context object.

    :return: None.
    """
    # zero out everything so we can reinitialize later
    context.audio_formatting = ''
    context.video_formatting = ''
    context.image_formatting = ''

    context.audio_formatting = get_wiki_page('format/audio', tor=tor)
    context.video_formatting = get_wiki_page('format/video', tor=tor)
    context.image_formatting = get_wiki_page('format/images', tor=tor)


def populate_domain_lists(tor, context):
    """
    Loads the approved content domains into the context object from the
    wiki page.

    :return: None.
    """

    context.video_domains = []
    context.image_domains = []
    context.audio_domains = []

    domains = get_wiki_page('domains', tor=tor)
    domains = ''.join(domains.splitlines()).split('---')

    for domainset in domains:
        domain_list = domainset[domainset.index('['):].strip('[]').split(', ')
        current_domain_list = []
        if domainset.startswith('video'):
            current_domain_list = context.video_domains
        elif domainset.startswith('audio'):
            current_domain_list = context.audio_domains
        elif domainset.startswith('images'):
            current_domain_list = context.image_domains
        [current_domain_list.append(x) for x in domain_list]
        logging.debug('Domain list populated: {}'.format(current_domain_list))


def populate_moderators(tor, context):
    # Praw doesn't cache this information, so it requests it every damn time
    # we ask about the moderators. Let's cache this so we can drastically cut
    # down on the number of calls for the mod list.

    # nuke the existing list
    context.tor_mods = []

    # this call returns a full list rather than a generator. Praw is weird.
    context.tor_mods = tor.moderator()


def populate_subreddit_lists(tor, context):
    """
    Gets the list of subreddits to monitor and loads it into memory.

    :return: None.
    """

    context.subreddits_to_check = []

    context.subreddits_to_check = get_wiki_page('subreddits', tor=tor).split('\r\n')
    logging.debug(
        'Created list of subreddits from wiki: {}'.format(
            context.subreddits_to_check
        )
    )


def populate_gifs(tor, context):
    # zero it out so we can load more
    context.no_gifs = []
    context.no_gifs = get_wiki_page('usefulgifs/no', tor=tor).split('\r\n')


def initialize(tor, context):
    populate_domain_lists(tor, context)
    logging.debug('Domains loaded.')
    populate_subreddit_lists(tor, context)
    logging.debug('Subreddits loaded.')
    populate_formatting(tor, context)
    logging.debug('Formatting loaded.')
    populate_header(tor, context)
    logging.debug('Header loaded.')
    populate_moderators(tor, context)
    logging.debug('Mod list loaded.')
    populate_gifs(tor, context)
    logging.debug('Gifs loaded.')
