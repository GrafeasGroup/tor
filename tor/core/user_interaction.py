import logging

from tor.core.validation import verified_posted_transcript
from tor.helpers.flair import flair
from tor.helpers.flair import flair_post
from tor.helpers.flair import update_user_flair
from tor.helpers.misc import _
from tor.helpers.wiki import get_wiki_page
from tor.helpers.reddit_ids import get_parent_post_id
from tor.strings.responses import already_claimed
from tor.strings.responses import claim_already_complete
from tor.strings.responses import claim_success
from tor.strings.responses import done_cannot_find_transcript
from tor.strings.responses import done_completed_transcript
from tor.strings.responses import done_still_unclaimed
from tor.strings.responses import please_accept_coc


def coc_accepted(post, config):
    """
    Verifies that the user is in the Redis set "accepted_CoC".
    
    :param post: the Comment object containing the claim.
    :param config: the global config dict.
    :return: True if the user has accepted the Code of Conduct, False if they
        haven't.
    """
    return config.redis.sismember('accepted_CoC', post.author.name) == 1


def process_coc(post, r, tor, config):
    """
    Adds the username of the redditor to the db as accepting the code of
    conduct.
    
    :param post: The Comment object containing the claim.
    :param r: Active Reddit object.
    :param tor: the TranscribersOfReddit Subreddit helper object.
    :param config: the global config dict.
    :return: None.
    """
    config.redis.sadd('accepted_CoC', post.author.name)
    process_claim(post, r, tor, config)


def process_claim(post, r, tor, config):
    """
    Handles comment replies containing the word 'claim' and routes
    based on a basic decision tree.

    :param post: The Comment object containing the claim.
    :param r: Active Reddit object.
    :param tor: the TranscribersOfReddit Subreddit helper object.
    :param config: the global config dict.
    :return: None.
    """
    top_parent = get_parent_post_id(post, r)

    # WAIT! Do we actually own this post?
    if top_parent.author.name != 'transcribersofreddit':
        logging.debug('Received `claim` on post we do not own. Ignoring.')
        return

    if not coc_accepted(post, config):
        # do not cache this page. We want to get it every time.
        post.reply(_(
            please_accept_coc.format(get_wiki_page('codeofconduct', tor))
        ))
        return

    if flair.unclaimed in top_parent.link_flair_text:
        # need to get that "Summoned - Unclaimed" in there too
        post.reply(_(claim_success))
        flair_post(top_parent, flair.in_progress)
        logging.info(
            'Claim on ID {} by {} successful'.format(
                top_parent.fullname, post.author
            )
        )
    # can't claim something that's already claimed
    elif top_parent.link_flair_text == flair.in_progress:
        post.reply(_(already_claimed))
    elif top_parent.link_flair_text == flair.completed:
        post.reply(_(claim_already_complete))


def process_done(post, r, tor, config, override=False):
    """
    Handles comments where the user says they've completed a post.
    Also includes a basic decision tree to enable verification of
    the posts to try and make sure they actually posted a
    transcription.

    :param post: the Comment object which contains the string 'done'.
    :param r: Active Reddit object.
    :param tor: Shortcut; a Subreddit object for ToR.
    :param config: the global config object.
    :param override: A parameter that can only come from process_override()
        and skips the validation check.
    :return: None.
    """

    top_parent = get_parent_post_id(post, r)

    # WAIT! Do we actually own this post?
    if top_parent.author.name != 'transcribersofreddit':
        logging.debug('Received `done` on post we do not own. Ignoring.')
        return

    if flair.unclaimed in top_parent.link_flair_text:
        post.reply(_(done_still_unclaimed))
    elif top_parent.link_flair_text == flair.in_progress:
        if not override:
            if not verified_posted_transcript(post, r, config):
                # we need to double-check these things to keep people
                # from gaming the system
                logging.info(
                    'Post {} does not appear to have a post by claimant {}. '
                    'Hrm...'.format(
                        top_parent.fullname, post.author
                    )
                )
                post.reply(_(done_cannot_find_transcript))
                return
        # Control flow:
        # If we have an override, we end up here to complete.
        # If there is no override, we go into the validation above.
        # If the validation fails, post the apology and return.
        # If the validation succeeds, come down here.
        post.reply(_(done_completed_transcript))
        flair_post(top_parent, flair.completed)
        update_user_flair(post, tor, r)
        if override:
            logging.info('Moderator override triggered!')
        logging.info(
            'Post {} completed by {}!'.format(
                top_parent.fullname, post.author
            )
        )
        config.redis.incr('total_completed', amount=1)
