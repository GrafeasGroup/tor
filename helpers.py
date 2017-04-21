import logging

import prawcore
from addict import Dict

from setup import __version__
from strings import bot_footer

flair = Dict()
flair.unclaimed = 'Unclaimed'
flair.summoned_unclaimed = 'Summoned - Unclaimed'
flair.completed = 'Completed!'
flair.in_progress = 'In Progress'
flair.meta = 'Meta'


def add_complete_post_id(post_id, redis_server):
    """
    Adds the post id to the complete_post_ids set in Redis. This is used
    to make sure that we didn't break halfway through working on this post.
    
    NOTE: This does not keep track of *transcribed* posts. This is only
    used to track the actual posting process, from grabbing new posts
    to actually creating the post with the "Unclaimed" tag.
    
    :param post_id: string. The comment / post ID.
    :param redis_server: The active Redis instance.
    :return: None.
    """
    redis_server.sadd('complete_post_ids', post_id)


def is_valid(post_id, redis_server):
    """
    Returns true or false based on whether the parent id is in a set of IDs.
    It determines this by attempting to insert the value into the DB and
    returning the result. If the result is already in the set, we check the
    completed id set as well to make sure that it's actually been done. If
    it's in the post_ids set and *not* the complete_post_ids set, we assume
    something went horribly wrong and we try again.

    :param post_id: string. The comment / post ID.
    :param redis_server: The active Redis instance.
    :return: True if the ID is successfully inserted into the set; False if
        it's already there.
    """
    result = redis_server.sadd('post_ids', post_id)

    if result == 1:
        # the post id was submitted successfully and it's good to work on.
        return True

    else:
        # The post is already in post_ids, which is triggered when we start
        # the process. Let's see if we ever completed it.
        member = redis_server.sismember('complete_post_ids', post_id)
        if member != 1:
            # It's in post_ids, which means we started it, but it's not
            # in complete_post_ids, which means we never finished it for
            # some reason. Let's try it again.
            logging.warning('Incomplete post found! ID: {}'.format(post_id))
            return True

        else:
            # it *is* in complete_post_ids, which means we've already
            # worked on it. Therefore, the post generally is not valid
            # to work on because it's already been successfully completed.
            return False


def _(message):
    """
    Message formatter. Returns the message and the disclaimer for the
    footer.
    
    :param message: string. The message to be displayed.
    :return: string. The original message plus the footer.
    """
    return bot_footer.format(message, version=__version__)


def get_wiki_page(pagename, tor):
    """
    Return the contents of a given wiki page.
    
    :param pagename: String. The name of the page to be requested.
    :param tor: Active ToR instance.
    :return: String or None. The content of the requested page if
        present else None.
    """
    logging.debug('Retrieving wiki page {}'.format(pagename))
    try:
        return tor.wiki[pagename].content_md
    except prawcore.exceptions.NotFound:
        return None


def update_wiki_page(pagename, content, tor):
    """
    Sends new content to the requested wiki page.
    
    :param pagename: String. The name of the page to be edited.
    :param content: String. New content for the wiki page.
    :param tor: Active ToR instance.
    :return: None.
    """
    logging.debug('Updating wiki page {}'.format(pagename))
    return tor.wiki[pagename].edit(content)


def log_header(message):
    logging.info('*'*50)
    logging.info(message)
    logging.info('*' * 50)


def clean_id(post_id):
    """
    Fixes the Reddit ID so that it can be used to get a new object.
    
    By default, the Reddit ID is prefixed with something like `t1_` or
    `t3_`, but this doesn't always work for getting a new object. This
    method removes those prefixes and returns the rest.
    
    :param post_id: String. Post fullname (ID)
    :return: String. Post fullname minus the first three characters.
    """
    return post_id[post_id.index('_')+1:]


def flair_post(post, text):
    """
    Sets the requested flair on a given post. Must provide a string
    which matches an already-available flair template.
    
    :param post: A Submission object on ToR.
    :param text: String. The name of the flair template to apply.
    :return: None.
    """
    # Flair looks like this:
    # {
    #   'flair_css_class': 'unclaimed-flair',
    #   'flair_template_id': 'fe9d6950-142a-11e7-901e-0ecc947f9ff4',
    #   'flair_text_editable': False,
    #   'flair_position': 'left',
    #   'flair_text': 'Unclaimed'
    # }
    for choice in post.flair.choices():
        if choice['flair_text'] == text:
            post.flair.select(
                flair_template_id=choice['flair_template_id']
            )


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


def update_user_flair(post, tor, reddit):
    """
    On a successful transcription, this takes the user's current flair,
    increments the counter by one, and stores it back to the subreddit.
    
    :param post: The post which holds the author information.
    :param tor: A shortcut for the Subreddit object for ToR.
    :param reddit: Active Reddit instance.
    :return: None.
    """
    flair_text = '0 Γ - Beta Tester'

    try:
        # The post object is technically an inbox mention, even though it's
        # a Comment object. In order to get the flair, we have to take the
        # ID of our post object and re-request it from Reddit in order to
        # get the *actual* object, even though they have the same ID. It's
        # weird.
        user_flair = reddit.comment(id=clean_id(post.fullname)).author_flair_text
    except AttributeError:
        user_flair = flair_text

    if user_flair is None:
        user_flair = flair_text

    if 'Γ' in user_flair:
        # take their current flair and add one to it
        new_flair_count = int(user_flair[:user_flair.index('Γ') - 1])
        # if there's anything special in their flair string, let's save it
        additional_flair_text = user_flair[user_flair.index('Γ') + 1:]
        user_flair = '{} Γ'.format(new_flair_count + 1)
        # add in that special flair bit back in to keep their flair intact
        user_flair += additional_flair_text
        tor.flair.set(post.author, text=user_flair, css_class='grafeas')
        logging.info('Setting flair for {}'.format(post.author))
    else:
        # they're bot or a mod and have custom flair. Leave it alone.
        return
