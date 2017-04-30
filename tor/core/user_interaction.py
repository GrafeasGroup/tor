import logging

from tor.core.validation import verified_posted_transcript
from tor.helpers.flair import flair
from tor.helpers.flair import flair_post
from tor.helpers.flair import update_user_flair
from tor.helpers.misc import _
from tor.helpers.reddit_ids import get_parent_post_id
from tor.strings.responses import already_claimed
from tor.strings.responses import claim_already_complete
from tor.strings.responses import claim_success
from tor.strings.responses import done_cannot_find_transcript
from tor.strings.responses import done_completed_transcript
from tor.strings.responses import done_still_unclaimed


def process_claim(post, r):
    """
    Handles comment replies containing the word 'claim' and routes
    based on a basic decision tree.

    :param post: The Comment object containing the claim.
    :param r: Active Reddit object.
    :return: None.
    """
    top_parent = get_parent_post_id(post, r)

    # WAIT! Do we actually own this post?
    if top_parent.author.name != 'transcribersofreddit':
        logging.debug('Received `claim` on post we do not own. Ignoring.')
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


def process_done(post, r, tor, redis_server, Context, override=False):
    """
    Handles comments where the user says they've completed a post.
    Also includes a basic decision tree to enable verification of
    the posts to try and make sure they actually posted a
    transcription.

    :param post: the Comment object which contains the string 'done'.
    :param r: Active Reddit object.
    :param tor: Shortcut; a Subreddit object for ToR.
    :param redis_server: Active Redis instance.
    :param Context: the global context object.
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
            if not verified_posted_transcript(post, r, Context):
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
        redis_server.incr('total_completed', amount=1)


def respond_to_thanks(mention):
    """
    An easter egg; it posts a reply to anything that includes the word
    'thank'. It's very rudimentary but should be a little nugget of fun.
    This is not currently in use, but I'd like to deploy it once we get
    some of the more serious kinks worked out.

    :param mention: The Comment object.
    :return: None.
    """
    logging.info(
        'Responding to a Thank You comment, ID {}'.format(mention)
    )
    mention.reply(_('You\'re very welcome! I\'m just doing my job!'))