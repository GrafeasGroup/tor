import logging
import random

import praw
# noinspection PyProtectedMember
from tor_core.helpers import _
from tor_core.helpers import get_parent_post_id
from tor_core.helpers import get_wiki_page
from tor_core.helpers import send_to_slack

from tor.core.validation import verified_posted_transcript
from tor.helpers.flair import flair
from tor.helpers.flair import flair_post
from tor.helpers.flair import update_user_flair
from tor.strings.responses import already_claimed
from tor.strings.responses import claim_already_complete
from tor.strings.responses import claim_success
from tor.strings.responses import done_cannot_find_transcript
from tor.strings.responses import done_completed_transcript
from tor.strings.responses import done_still_unclaimed
from tor.strings.responses import please_accept_coc
from tor.strings.responses import thumbs_up_gifs
from tor.strings.responses import youre_welcome


def coc_accepted(post, config):
    """
    Verifies that the user is in the Redis set "accepted_CoC".

    :param post: the Comment object containing the claim.
    :param config: the global config dict.
    :return: True if the user has accepted the Code of Conduct, False if they
        haven't.
    """
    return config.redis.sismember('accepted_CoC', post.author.name) == 1


def process_coc(post, config):
    """
    Adds the username of the redditor to the db as accepting the code of
    conduct.

    :param post: The Comment object containing the claim.
    :param config: the global config dict.
    :return: None.
    """
    result = config.redis.sadd('accepted_CoC', post.author.name)

    # Have they already been added? If 0, then just act like they said `claim`
    # instead. If they're actually new, then send a message to slack.
    if result == 1:
        send_to_slack(
            f'<http://www.reddit.com/u/{post.author.name}|u/{post.author.name}> has just accepted the CoC!', config
        )
    process_claim(post, config)


def process_claim(post, config):
    """
    Handles comment replies containing the word 'claim' and routes
    based on a basic decision tree.

    :param post: The Comment object containing the claim.
    :param config: the global config dict.
    :return: None.
    """
    top_parent = get_parent_post_id(post, config.r)

    # WAIT! Do we actually own this post?
    if top_parent.author.name != 'transcribersofreddit':
        logging.debug('Received `claim` on post we do not own. Ignoring.')
        return

    try:
        if not coc_accepted(post, config):
            # do not cache this page. We want to get it every time.
            post.reply(_(
                please_accept_coc.format(get_wiki_page('codeofconduct', config))
            ))
            return

        if top_parent.link_flair_text is None:
            # There exists the very small possibility that the post was
            # malformed and doesn't actually have flair on it. In that case,
            # let's set something so the next part doesn't crash.
            flair_post(top_parent, flair.unclaimed)

        if flair.unclaimed in top_parent.link_flair_text:
            # need to get that "Summoned - Unclaimed" in there too
            post.reply(_(claim_success))

            flair_post(top_parent, flair.in_progress)
            logging.info(
                f'Claim on ID {top_parent.fullname} by {post.author} successful'
            )

        # can't claim something that's already claimed
        elif top_parent.link_flair_text == flair.in_progress:
            post.reply(_(already_claimed))
        elif top_parent.link_flair_text == flair.completed:
            post.reply(_(claim_already_complete))

    except praw.exceptions.APIException as e:
        if e.error_type == 'DELETED_COMMENT':
            logging.info(
                f'Comment attempting to claim ID {top_parent.fullname} has been deleted. Back up for grabs!'
            )
            return
        raise  # Re-raise exception if not


def process_done(post, config, override=False):
    """
    Handles comments where the user says they've completed a post.
    Also includes a basic decision tree to enable verification of
    the posts to try and make sure they actually posted a
    transcription.

    :param post: the Comment object which contains the string 'done'.
    :param config: the global config object.
    :param override: A parameter that can only come from process_override()
        and skips the validation check.
    :return: None.
    """

    top_parent = get_parent_post_id(post, config.r)

    # WAIT! Do we actually own this post?
    if top_parent.author.name != 'transcribersofreddit':
        logging.info('Received `done` on post we do not own. Ignoring.')
        return

    try:
        if flair.unclaimed in top_parent.link_flair_text:
            post.reply(_(done_still_unclaimed))
        elif top_parent.link_flair_text == flair.in_progress:
            if not override and not verified_posted_transcript(post, config):
                # we need to double-check these things to keep people
                # from gaming the system
                logging.info(
                    f'Post {top_parent.fullname} does not appear to have a post by claimant {post.author}. Hrm...'
                )
                # noinspection PyUnresolvedReferences
                try:
                    post.reply(_(done_cannot_find_transcript))
                except praw.exceptions.ClientException as e:
                    # We've run into an issue where someone has commented and
                    # then deleted the comment between when the bot pulls mail
                    # and when it processes comments. This should catch that.
                    # Possibly should look into subclassing praw.Comment.reply
                    # to include some basic error handling of this so that
                    # we can fix it throughout the application.
                    logging.warning(e)
                return

            # Control flow:
            # If we have an override, we end up here to complete.
            # If there is no override, we go into the validation above.
            # If the validation fails, post the apology and return.
            # If the validation succeeds, come down here.

            if override:
                logging.info('Moderator override starting!')
            # noinspection PyUnresolvedReferences
            try:
                post.reply(_(done_completed_transcript))
                update_user_flair(post, config)
                logging.info(
                    f'Post {top_parent.fullname} completed by {post.author}!'
                )
            except praw.exceptions.ClientException:
                # If the butt deleted their comment and we're already this
                # far into validation, just mark it as done. Clearly they
                # already passed.
                logging.info(
                    f'Attempted to mark post {top_parent.fullname} as done... hit ClientException.'
                )
            flair_post(top_parent, flair.completed)

            config.redis.incr('total_completed', amount=1)

    except praw.exceptions.APIException as e:
        if e.error_type == 'DELETED_COMMENT':
            logging.info(
                f'Comment attempting to mark ID {top_parent.fullname} as done has been deleted'
            )
            return
        raise  # Re-raise exception if not


def process_thanks(post, config):
    try:
        post.reply(_(youre_welcome.format(random.choice(thumbs_up_gifs))))
    except praw.exceptions.APIException as e:
        if e.error_type == 'DELETED_COMMENT':
            logging.debug('Comment requiring thanks was deleted')
            return
        raise
