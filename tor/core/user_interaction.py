import logging
import random

from praw.exceptions import APIException  # type: ignore
from praw.models import Comment, Message  # type: ignore

from tor import __BOT_NAMES__
from tor.core.blossom_wrapper import BlossomStatus
from tor.core.config import Config
from tor.core.helpers import (_, get_wiki_page,
                              remove_if_required, send_reddit_reply, send_to_modchat)
from tor.core.validation import get_transcription
from tor.helpers.flair import flair, flair_post, set_user_flair
from tor.strings import translation

i18n = translation()
log = logging.getLogger(__name__)

MODCHAT_EMOTES = [
    ":badger:",
    ":beers:",
    ":catta-tappa:",
    ":confetti_ball:",
    ":coolio:",
    ":derp:",
    ":fb-like:",
    ":fidget-spinner:",
    ":gold:",
    ":heartpulse:",
    ":lenny1::lenny2:",
    ":tada:",
    ":partyblob:",
    ":partylexi:",
    ":party_parrot:",
    ":trophy:",
    ":upvote:",
    ":+1:",
]


def process_coc(post: Comment, cfg: Config) -> None:
    """Process the acceptation of the CoC by the specified user."""
    username = post.author.name
    user_response = cfg.blossom.get_user(username=username)
    if user_response.status == BlossomStatus.ok:
        # The status codes are not checked because they are already caught by
        # getting the user.
        response = cfg.blossom.accept_coc(username=username)
        new_acceptance = response.status == BlossomStatus.ok
        if new_acceptance:
            emote = random.choice(MODCHAT_EMOTES)
            user_url = i18n['urls']['reddit_url'].format(f'/u/{username}')
            post_url = i18n['urls']['reddit_url'].format(post.context)
            send_to_modchat(
                f'<{user_url}|u/{post.author.name}> has just'
                f' <{post_url}|accepted the CoC!> {emote}',
                cfg,
                channel='new_volunteers'
            )
        process_claim(post, cfg, first_time=new_acceptance)
    elif user_response.status == BlossomStatus.not_found:
        cfg.blossom.create_user(username=post.author.name)
        send_reddit_reply(
            post,
            i18n["responses"]["general"]["coc_not_accepted"].format(get_wiki_page("codeofconduct", cfg))
        )
    else:
        process_claim(post, cfg)


def process_claim(post: Comment, cfg: Config, first_time=False) -> None:
    """
    Process a claim request.

    This function sends a reply depending on the response from Blossom and
    creates an user when this is the first time a user uses the bot.
    """
    submission = post.submission
    if submission.author.name not in __BOT_NAMES__:
        log.debug("Received 'claim' on post we do not own. Ignoring.")
        return

    response = cfg.blossom.get_submission(reddit_id=submission.fullname)
    if response.status != BlossomStatus.ok:
        # If we are here, this means that the current submission is not yet in Blossom.
        # TODO: Create the Submission in Blossom and try this method again.
        raise Exception("The post is not present in Blossom.")

    response = cfg.blossom.claim_submission(
        submission_id=response.data["id"], username=post.author.name
    )
    if response.status == BlossomStatus.ok:
        message = i18n["responses"]["claim"]["first_claim_success" if first_time else "success"]
        flair_post(submission, flair.in_progress)
        log.info(f'Claim on Submission {submission.fullname} by {post.author} successful.')
    elif response.status == BlossomStatus.coc_not_accepted:
        message = i18n["responses"]["general"]["coc_not_accepted"].format(get_wiki_page("codeofconduct", cfg))
    elif response.status == BlossomStatus.not_found:
        message = i18n["responses"]["general"]["coc_not_accepted"].format(get_wiki_page("codeofconduct", cfg))
        cfg.blossom.create_user(username=post.author.name)
    elif response.status == BlossomStatus.blacklisted:
        message = i18n["responses"]["general"]["blacklisted"]
    else:
        message = i18n["responses"]["claim"]["already_claimed"]
    send_reddit_reply(post, _(message))


def process_done(
    post: Comment, cfg: Config, override=False, alt_text_trigger=False
) -> None:
    """
    Handles comments where the user claims to have completed a point.

    This function sends a reply to the user depending on the responses received
    from Blossom.

    :param post: the Comment object which contains the string 'done'.
    :param cfg: the global config object.
    :param override: whether the validation check should be skipped
    :param alt_text_trigger: whether there is an alternative to "done" that has
                             triggered this function.
    """
    submission = post.submission
    done_messages = i18n["responses"]["done"]
    coc_not_accepted = i18n["responses"]["general"]["coc_not_accepted"].format(
        get_wiki_page("codeofconduct", cfg)
    )

    if submission.author.name not in __BOT_NAMES__:
        log.debug("Received 'done' on post we do not own. Ignoring.")
        return

    response = cfg.blossom.get_submission(reddit_id=submission.fullname)
    if response.status != BlossomStatus.ok:
        # If we are here, this means that the current submission is not yet in Blossom.
        # TODO: Create the Submission in Blossom and try this method again.
        raise Exception(f"The Submission {submission.fullname} is not present in Blossom.")
    blossom_submission = response.data

    transcription, in_linked = get_transcription(submission, post.author, cfg)
    if transcription is None:
        message = done_messages["cannot_find_transcript"]
    else:
        create_response = cfg.blossom.create_transcription(
            transcription, blossom_submission["id"], not in_linked
        )
        if create_response.status in [
            BlossomStatus.not_found, BlossomStatus.coc_not_accepted
        ]:
            if create_response.status == BlossomStatus.not_found:
                # Since we know the Submission exists at this point, it should mean
                # in fact the user is not found within Blossom.
                cfg.blossom.create_user(username=post.author.name)
            message = coc_not_accepted
        else:
            done_response = cfg.blossom.done(
                blossom_submission["id"], post.author.name, override
            )
            # Note that both the not_found and coc_not_accepted status are already
            # caught in the previous lines of code, hence these are not checked again.
            if done_response.status == BlossomStatus.ok:
                flair_post(submission, flair.completed)
                set_user_flair(post.author, cfg)
                message = done_messages["completed_transcript"]
                if alt_text_trigger:
                    message = f"I think you meant `done`, so here we go!\n\n{message}"
            elif done_response.status == BlossomStatus.already_completed:
                message = done_messages["already_completed"]
            elif done_response.status == BlossomStatus.missing_prerequisite:
                message = done_messages["not_claimed_by_user"]
            elif response.status == BlossomStatus.blacklisted:
                message = i18n["responses"]["general"]["blacklisted"]
            else:
                message = done_messages["cannot_find_transcript"]
    send_reddit_reply(post, _(message))


def process_unclaim(post: Comment, cfg: Config) -> None:
    """
    Process an unclaim request.

    Note that this function also checks whether a post should be removed and
    does so when required.
    """
    submission = post.submission
    if submission.author.name not in __BOT_NAMES__:
        log.debug("Received 'unclaim' on post we do not own. Ignoring.")
        return

    response = cfg.blossom.get_submission(reddit_id=submission.fullname)
    if response.status != BlossomStatus.ok:
        # If we are here, this means that the current submission is not yet in Blossom.
        # TODO: Create the Submission in Blossom and try this method again.
        raise Exception(f"The Submission {submission.fullname} is not present in Blossom.")

    blossom_submission = response.data
    response = cfg.blossom.unclaim(
        submission_id=blossom_submission["id"], username=post.author.name
    )
    unclaim_messages = i18n["responses"]["unclaim"]
    if response.status == BlossomStatus.ok:
        message = unclaim_messages["success"]
        flair_post(submission, flair.unclaimed)
        removed, reported = remove_if_required(submission, blossom_submission["id"], cfg)
        if removed:
            # Select the message based on whether the post was reported or not.
            message = i18n[
                "success_with_report" if reported else "success_without_report"
            ]
    elif response.status == BlossomStatus.not_found:
        message = i18n["responses"]["general"]["coc_not_accepted"].format(
            get_wiki_page("codeofconduct", cfg)
        )
        cfg.blossom.create_user(post.author.name)
    elif response.status == BlossomStatus.other_user:
        message = unclaim_messages["claimed_other_user"]
    elif response.status == BlossomStatus.already_completed:
        message = unclaim_messages["post_already_completed"]
    elif response.status == BlossomStatus.blacklisted:
        message = i18n["responses"]["general"]["blacklisted"]
    else:
        message = unclaim_messages["still_unclaimed"]
    send_reddit_reply(post, _(message))


def process_thanks(post: Comment, cfg: Config) -> None:
    thumbs_up_gifs = i18n['urls']['thumbs_up_gifs']
    youre_welcome = i18n['responses']['general']['youre_welcome']
    try:
        post.reply(_(youre_welcome.format(random.choice(thumbs_up_gifs))))
    except APIException as e:
        if e.error_type == 'DELETED_COMMENT':
            log.debug('Comment requiring thanks was deleted')
            return
        raise


def process_wrong_post_location(post: Comment, cfg: Config) -> None:
    transcript_on_tor_post = i18n['responses']['general']['transcript_on_tor_post']
    try:
        post.reply(_(transcript_on_tor_post))
    except APIException:
        log.debug('Something went wrong with asking about a misplaced post; ignoring.')


def process_message(message: Message, cfg: Config) -> None:
    dm_subject = i18n['responses']['direct_message']['dm_subject']
    dm_body = i18n['responses']['direct_message']['dm_body']

    author = message.author
    username = author.name if author else None

    author.message(dm_subject, dm_body)

    if username:
        send_to_modchat(
            f'DM from <{i18n["urls"]["reddit_url"].format("/u/" + username)}|u/{username}> -- '
            f'*{message.subject}*:\n{message.body}', cfg
        )
        log.info(f'Received DM from {username}. \n Subject: {message.subject}\n\nBody: {message.body}')
    else:
        send_to_modchat(
            f'DM with no author -- '
            f'*{message.subject}*:\n{message.body}', cfg
        )
        log.info(f'Received DM with no author. \n Subject: {message.subject}\n\nBody: {message.body}')
