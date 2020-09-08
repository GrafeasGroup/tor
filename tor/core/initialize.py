import logging

from bugsnag.handlers import BugsnagHandler  # type: ignore

from tor.core.config import Config
from tor.core.helpers import clean_list, get_wiki_page

# Use a logger local to this module
log = logging.getLogger()


def configure_logging(cfg: Config, log_name="transcribersofreddit.log") -> None:
    # Set formatting and logging level.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
        filename=log_name,
    )

    if cfg.bugsnag_api_key:
        # will intercept anything error level or above
        bs_handler = BugsnagHandler()
        bs_handler.setLevel(logging.ERROR)
        logging.getLogger().addHandler(bs_handler)
        log.info('Bugsnag is successfully enabled!')
    else:
        log.info("No Bugsnag API Key found. Not running with Bugsnag!")

    log.info("*" * 50)
    log.info("Logging configured. Starting program!")
    log.info("*" * 50)


def populate_header(cfg: Config) -> None:
    cfg.header = get_wiki_page('format/header', cfg)


def populate_formatting(cfg: Config) -> None:
    """
    Grabs the contents of the three wiki pages that contain the
    formatting examples and stores them in the cfg object.

    :return: None.
    """
    cfg.audio_formatting = get_wiki_page('format/audio', cfg)
    cfg.video_formatting = get_wiki_page('format/video', cfg)
    cfg.image_formatting = get_wiki_page('format/images', cfg)
    cfg.other_formatting = get_wiki_page('format/other', cfg)


def populate_domain_lists(cfg: Config) -> None:
    """
    Loads the approved content domains into the config object from the
    wiki page.

    :return: None.
    """

    domain_string = get_wiki_page('domains', cfg)
    domains = ''.join(domain_string.splitlines()).split('---')

    for domainset in domains:
        domain_list = domainset[domainset.index('['):].strip('[]').split(', ')
        current_domain_list = []
        if domainset.startswith('video'):
            current_domain_list = cfg.video_domains
        elif domainset.startswith('audio'):
            current_domain_list = cfg.audio_domains
        elif domainset.startswith('images'):
            current_domain_list = cfg.image_domains

        current_domain_list += domain_list
        # [current_domain_list.append(x) for x in domain_list]
        log.debug(f'Domain list populated: {current_domain_list}')


def populate_subreddit_lists(cfg: Config) -> None:
    """
    Gets the list of subreddits to monitor and loads it into memory.

    :return: None.
    """

    cfg.subreddits_to_check = get_wiki_page('subreddits', cfg).splitlines()
    cfg.subreddits_to_check = clean_list(cfg.subreddits_to_check)
    log.debug(f'Created list of subreddits from wiki: {cfg.subreddits_to_check}')

    for line in get_wiki_page('subreddits/upvote-filtered', cfg).splitlines():
        if ',' in line:
            sub, threshold = line.split(',')
            cfg.upvote_filter_subs[sub] = int(threshold)

    log.debug(f'Retrieved subreddits subject to the upvote filter: {cfg.upvote_filter_subs}')

    cfg.subreddits_domain_filter_bypass = clean_list(
        get_wiki_page('subreddits/domain-filter-bypass', cfg).splitlines())
    log.debug(f'Retrieved subreddits that bypass the domain filter: {cfg.subreddits_domain_filter_bypass}')

    cfg.no_link_header_subs = clean_list(
        get_wiki_page('subreddits/no-link-header', cfg).splitlines())
    log.debug(f'Retrieved subreddits subject to the upvote filter: {cfg.no_link_header_subs}')


def populate_gifs(cfg: Config) -> None:
    cfg.no_gifs = get_wiki_page('usefulgifs/no', cfg).splitlines()


def initialize(cfg: Config) -> None:
    populate_domain_lists(cfg)
    log.debug('Domains loaded.')
    populate_subreddit_lists(cfg)
    log.debug('Subreddits loaded.')
    populate_formatting(cfg)
    log.debug('Formatting loaded.')
    populate_header(cfg)
    log.debug('Header loaded.')
    # this call returns a full list rather than a generator. Praw is weird.
    cfg.tor_mods = cfg.tor.moderator()
    log.debug('Mod list loaded.')
    populate_gifs(cfg)
    log.debug('Gifs loaded.')
