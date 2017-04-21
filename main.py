import logging
import sys
import time

# noinspection PyUnresolvedReferences
import better_exceptions
import redis
from praw import Reddit

from helpers import _
from helpers import flair
from helpers import flair_post
from helpers import get_wiki_page
from helpers import is_valid
from helpers import log_header
from helpers import update_wiki_page
from processing import process_claim
from processing import process_done
from processing import process_mention
from processing import process_post
from strings import id_already_handled_in_db


class Context(object):
    """
    Support object for the bot -- holds data that doesn't have
    anywhere else to go.
    """
    video_domains = []
    audio_domains = []
    image_domains = []

    video_formatting = ''
    audio_formatting = ''
    image_formatting = ''
    header = ''

    subreddits_to_check = []
    # subreddits that we're only getting 100 posts at a time from
    # instead of jump-starting it with 500
    subreddit_members = []

    perform_header_check = False
    debug_sleep = False


def populate_header():
    Context.header = ''

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
    Context.header = ' '.join(temp)


def populate_formatting():
    """
    Grabs the contents of the three wiki pages that contain the
    formatting examples and stores them in the Context object.
    
    :return: None.
    """
    # zero out everything so we can reinitialize later
    Context.audio_formatting = ''
    Context.video_formatting = ''
    Context.image_formatting = ''

    Context.audio_formatting = get_wiki_page('format/audio', tor=tor)
    Context.video_formatting = get_wiki_page('format/video', tor=tor)
    Context.image_formatting = get_wiki_page('format/images', tor=tor)


def populate_domain_lists():
    """
    Loads the approved content domains into the Context object from the
    wiki page.
    
    :return: None.
    """

    Context.video_domains = []
    Context.image_domains = []
    Context.audio_domains = []

    domains = get_wiki_page('domains', tor=tor)
    domains = ''.join(domains.splitlines()).split('---')

    for domainset in domains:
        domain_list = domainset[domainset.index('['):].strip('[]').split(', ')
        current_domain_list = []
        if domainset.startswith('video'):
            current_domain_list = Context.video_domains
        elif domainset.startswith('audio'):
            current_domain_list = Context.audio_domains
        elif domainset.startswith('images'):
            current_domain_list = Context.image_domains
        [current_domain_list.append(x) for x in domain_list]
        logging.debug('Domain list populated: {}'.format(current_domain_list))


def populate_subreddit_lists():
    """
    Gets the list of subreddits to monitor and loads it into memory.
    
    :return: None.
    """

    Context.subreddits_to_check = []
    Context.subreddit_members = []

    Context.subreddits_to_check = get_wiki_page('subreddits', tor=tor).split('\r\n')
    logging.debug(
        'Created list of subreddits from wiki: {}'.format(
            Context.subreddits_to_check
        )
    )
    Context.subreddit_members = get_wiki_page('subreddits/members', tor=tor).split('\r\n')
    logging.debug(
        'Created list of subreddits from wiki: {}'.format(
            Context.subreddit_members
        )
    )


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


def respond_to_thanks(mention):
    """
    An easter egg; it posts a reply to anything that includes the word
    'thank'. It's very rudimentary but should be a little nugget of fun.
    
    :param mention: The Comment object.
    :return: None.
    """
    logging.info(
        'Responding to a Thank You comment, ID {}'.format(mention)
    )
    mention.reply(_('You\'re very welcome! I\'m just doing my job!'))


def check_inbox():
    """
    Goes through all the unread messages in the inbox. It has two
    loops within this section, each one dealing with a different type
    of mail. Also deliberately leaves mail which does not fit into
    either category so that it can be read manually at a later point.
    
    The first loop handles username mentions.
    The second loop sorts out and handles comments that include 'claim'
        and 'done'. 
    :return: None.
    """
    # first we do mentions, then comment replies
    mentions = []
    # grab all of our messages and filter
    for item in r.inbox.unread(limit=None):
        if item.subject == 'username mention':
            mentions.append(item)
            item.mark_read()

    # sort them and create posts where necessary
    for mention in mentions:
        logging.info('Received mention! ID {}'.format(mention))

        if not is_valid(mention.parent_id, redis_server):
            # Do our check here to make sure we can actually work on this one and
            # that we haven't already posted about it. We use the full ID here
            # instead of the cleaned one, just in case.
            logging.info(id_already_handled_in_db.format(mention.parent_id))
            continue

        process_mention(mention, r, tor, redis_server, Context)

    # comment replies
    replies = []
    for item in r.inbox.unread(limit=None):
        if item.subject == 'comment reply':
            replies.append(item)
            item.mark_read()

    for reply in replies:
        # if 'thank' in reply.body.lower():
        #     respond_to_thanks(reply)
        #     continue
        if 'claim' in reply.body.lower():
            process_claim(reply, r)
        if 'done' in reply.body.lower():
            process_done(reply, r, tor, Context)


def check_submissions(subreddit, Context):
    """
    Loops through all of the subreddits that have opted in and pulls
    the 100 newest submissions. It checks the domain of the submission
    against the domain lists and hands off the post to process_post()
    for formatting and posting on ToR.
    
    :param subreddit: String. A valid subreddit name.
    :param Context: the Context object.
    :return: None.
    """
    if subreddit in Context.subreddit_members:
        sr = r.subreddit(subreddit).new(limit=100)
    else:
        sr = r.subreddit(subreddit).new(limit=500)
        Context.subreddit_members.append(subreddit)
        update_wiki_page(
            'subreddits/members',
            '\r\n'.join(Context.subreddit_members),
            tor)

    for post in sr:
        if (
            post.domain in Context.image_domains or
            post.domain in Context.audio_domains or
            post.domain in Context.video_domains
        ):
            process_post(post, tor, redis_server, Context)


def set_meta_flair_on_other_posts(transcribersofreddit):
    """
    Loops through the 25 newest posts on ToR and sets the flair to
    'Meta' for any post that is not authored by the bot or any of
    the moderators.
    
    :param transcribersofreddit: The Subreddit object for ToR.
    :return: None.
    """
    for post in transcribersofreddit.new(limit=25):
        # this one returns a full list rather than a generator. It's weird.
        moderators = transcribersofreddit.moderator()
        if (
            post.author != r.redditor('transcribersofreddit') and
            post.author not in moderators
        ):
            logging.info(
                'Flairing post {} by author {} with Meta.'.format(
                    post.fullname, post.author
                )
            )
            flair_post(post, flair.meta)


def initialize():
    populate_domain_lists()
    logging.info('Domains loaded.')
    populate_subreddit_lists()
    logging.info('Subreddits loaded.')
    populate_formatting()
    logging.info('Formatting loaded.')
    populate_header()
    logging.info('Header loaded.')

    logging.info('Initialization complete.')


if __name__ == '__main__':
    r = Reddit('bot')  # load from config file
    configure_logging()
    try:
        redis_server = redis.StrictRedis(host='localhost', port=6379, db=0)
        redis_server.ping()
    except redis.exceptions.ConnectionError:
        logging.error("Redis server is not running! Exiting!")
        sys.exit(1)
    tor = r.subreddit('transcribersofreddit')
    initialize()

    try:
        # primary loop
        while True:
            check_inbox()
            for sub in Context.subreddits_to_check:
                check_submissions(sub, Context)
            set_meta_flair_on_other_posts(tor)
            logging.debug('Looping!')
            if Context.debug_sleep:
                time.sleep(60)

    except KeyboardInterrupt:
        logging.error('User triggered shutdown. Shutting down.')
