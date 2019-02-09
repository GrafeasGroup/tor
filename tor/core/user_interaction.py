import logging
import random

import praw

# noinspection PyProtectedMember
from tor.core.helpers import (
    _,
    clean_id,
    get_parent_post_id,
    get_wiki_page,
    reports,
    send_to_modchat,
)
from tor.core.strings import reddit_url
from tor.core.users import User
from tor.core.validation import verified_posted_transcript
from tor.helpers.flair import flair, flair_post, update_user_flair
from tor.helpers.reddit_ids import is_removed
from tor.strings.responses import (
    already_claimed,
    claim_already_complete,
    claim_success,
    done_cannot_find_transcript,
    done_completed_transcript,
    done_still_unclaimed,
    please_accept_coc,
    thumbs_up_gifs,
    transcript_on_tor_post,
    unclaim_failure_post_already_completed,
    unclaim_still_unclaimed,
    unclaim_success,
    unclaim_success_with_report,
    unclaim_success_without_report,
    youre_welcome,
)


def coc_accepted(post, config):
    """
    Verifies that the user is in the Redis set "accepted_CoC".

    :param post: the Comment object containing the claim.
    :param config: the global config dict.
    :return: True if the user has accepted the Code of Conduct, False if they
        haven't.
    """
    return config.redis.sismember("accepted_CoC", post.author.name) == 1


def process_coc(post, config):
    """
    Adds the username of the redditor to the db as accepting the code of
    conduct.

    :param post: The Comment object containing the claim.
    :param config: the global config dict.
    :return: None.
    """
    result = config.redis.sadd("accepted_CoC", post.author.name)

    modchat_emote = random.choice(
        [
            ":tada:",
            ":confetti_ball:",
            ":party-lexi:",
            ":party-parrot:",
            ":+1:",
            ":trophy:",
            ":heartpulse:",
            ":beers:",
            ":gold:",
            ":upvote:",
            ":coolio:",
            ":derp:",
            ":lenny1::lenny2:",
            ":panic:",
            ":fidget-spinner:",
            ":fb-like:",
        ]
    )

    # Have they already been added? If 0, then just act like they said `claim`
    # instead. If they're actually new, then send a message to slack.
    if result == 1:
        send_to_modchat(
            f'<{reddit_url.format("/user/" + post.author.name)}|u/{post.author.name}>'
            f" has just"
            f" <{reddit_url.format(post.context)}|accepted the CoC!>"
            f" {modchat_emote}",
            config,
            channel="new_volunteers",
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
    if top_parent.author.name != "transcribersofreddit":
        logging.debug("Received `claim` on post we do not own. Ignoring.")
        return

    try:
        if not coc_accepted(post, config):
            # do not cache this page. We want to get it every time.
            post.reply(
                _(please_accept_coc.format(get_wiki_page("codeofconduct", config)))
            )
            return

        # this can be either '' or None depending on how the API is feeling
        # today
        if top_parent.link_flair_text in ["", None]:
            # There exists the very small possibility that the post was
            # malformed and doesn't actually have flair on it. In that case,
            # let's set something so the next part doesn't crash.
            flair_post(top_parent, flair.unclaimed)

        if flair.unclaimed in top_parent.link_flair_text:
            # need to get that "Summoned - Unclaimed" in there too
            post.reply(_(claim_success))

            flair_post(top_parent, flair.in_progress)
            logging.info(
                f"Claim on ID {top_parent.fullname} by {post.author} successful"
            )

        # can't claim something that's already claimed
        elif top_parent.link_flair_text == flair.in_progress:
            post.reply(_(already_claimed))
        elif top_parent.link_flair_text == flair.completed:
            post.reply(_(claim_already_complete))

    except praw.exceptions.APIException as e:
        if e.error_type == "DELETED_COMMENT":
            logging.info(
                f"Comment attempting to claim ID {top_parent.fullname} has "
                f"been deleted. Back up for grabs! "
            )
            return
        raise  # Re-raise exception if not


def process_done(post, config, override=False, alt_text_trigger=False):
    """
    Handles comments where the user says they've completed a post.
    Also includes a basic decision tree to enable verification of
    the posts to try and make sure they actually posted a
    transcription.

    :param post: the Comment object which contains the string 'done'.
    :param config: the global config object.
    :param override: A parameter that can only come from process_override()
        and skips the validation check.
    :param alt_text_trigger: a trigger that adds an extra piece of text onto
        the response. Just something to help ease the number of
        false-positives.
    :return: None.
    """

    top_parent = get_parent_post_id(post, config.r)

    # WAIT! Do we actually own this post?
    if top_parent.author.name != "transcribersofreddit":
        logging.info("Received `done` on post we do not own. Ignoring.")
        return

    try:
        if flair.unclaimed in top_parent.link_flair_text:
            post.reply(_(done_still_unclaimed))
        elif top_parent.link_flair_text == flair.in_progress:
            if not override and not verified_posted_transcript(post, config):
                # we need to double-check these things to keep people
                # from gaming the system
                logging.info(
                    f"Post {top_parent.fullname} does not appear to have a "
                    f"post by claimant {post.author}. Hrm... "
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
                logging.info("Moderator override starting!")
            # noinspection PyUnresolvedReferences
            try:
                if alt_text_trigger:
                    post.reply(
                        _(
                            "I think you meant `done`, so here we go!\n\n"
                            + done_completed_transcript
                        )
                    )
                else:
                    post.reply(_(done_completed_transcript))
                update_user_flair(post, config)
                logging.info(f"Post {top_parent.fullname} completed by {post.author}!")
                # get that information saved for the user
                author = User(str(post.author), config.redis)
                author.list_update("posts_completed", clean_id(post.fullname))
                author.save()

            except praw.exceptions.ClientException:
                # If the butt deleted their comment and we're already this
                # far into validation, just mark it as done. Clearly they
                # already passed.
                logging.info(
                    f"Attempted to mark post {top_parent.fullname} "
                    f"as done... hit ClientException."
                )
            flair_post(top_parent, flair.completed)

            config.redis.incr("total_completed", amount=1)

    except praw.exceptions.APIException as e:
        if e.error_type == "DELETED_COMMENT":
            logging.info(
                f"Comment attempting to mark ID {top_parent.fullname} "
                f"as done has been deleted"
            )
            return
        raise  # Re-raise exception if not


def process_unclaim(post, config):
    # Sometimes people need to unclaim things. Usually this happens because of
    # an issue with the post itself, like it's been locked or deleted. Either
    # way, we should probably be able to handle it.

    # Process:
    # If the post has been reported, then remove it. No checks, just do it.
    # If the post has not been reported, attempt to load the linked post.
    #   If the linked post is still up, then reset the flair on ToR's side
    #    and reply to the user.
    #   If the linked post has been taken down or deleted, then remove the post
    #    on ToR's side and reply to the user.

    top_parent = post.submission
    # WAIT! Do we actually own this post?
    if top_parent.author.name != "transcribersofreddit":
        logging.info("Received `unclaim` on post we do not own. Ignoring.")
        return

    if flair.unclaimed in top_parent.link_flair_text:
        post.reply(_(unclaim_still_unclaimed))
        return

    for item in top_parent.user_reports:
        if (
            reports.original_post_deleted_or_locked in item[0]
            or reports.post_violates_rules in item[0]
        ):
            top_parent.mod.remove()
            send_to_modchat(
                "Removed the following reported post in response to an "
                "`unclaim`: {}".format(top_parent.shortlink),
                config,
                channel="removed_posts",
            )
            post.reply(_(unclaim_success_with_report))
            return

    # Okay, so they commented with unclaim, but they didn't report it.
    # Time to check to see if they should have.
    linked_resource = config.r.submission(top_parent.id_from_url(top_parent.url))
    if is_removed(linked_resource):
        top_parent.mod.remove()
        send_to_modchat(
            "Received `unclaim` on an unreported post, but it looks like it "
            "was removed on the parent sub. I removed ours here: {}"
            "".format(top_parent.shortlink),
            config,
            channel="removed_posts",
        )
        post.reply(_(unclaim_success_without_report))
        return

    # Finally, if none of the other options apply, we'll reset the flair and
    # continue on as normal.
    if top_parent.link_flair_text == flair.completed:
        post.reply(_(unclaim_failure_post_already_completed))
        return

    if top_parent.link_flair_text == flair.in_progress:
        flair_post(top_parent, flair.unclaimed)
        post.reply(_(unclaim_success))
        return


def process_thanks(post, config):
    try:
        post.reply(_(youre_welcome.format(random.choice(thumbs_up_gifs))))
    except praw.exceptions.APIException as e:
        if e.error_type == "DELETED_COMMENT":
            logging.debug("Comment requiring thanks was deleted")
            return
        raise


def process_wrong_post_location(post):
    try:
        post.reply(_(transcript_on_tor_post))
    except praw.exceptions.APIException:
        logging.debug(
            "Something went wrong with asking about a misplaced post; ignoring."
        )
