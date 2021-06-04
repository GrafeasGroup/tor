import logging
import random
from typing import Dict, Tuple

from blossom_wrapper import BlossomStatus
from praw.models import Comment, Message, Redditor, Submission  # type: ignore

from tor.core.config import Config
from tor.core.helpers import (_, get_wiki_page,
                              remove_if_required, send_to_modchat)
from tor.core.validation import get_transcription
from tor.helpers.flair import flair, set_user_flair
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


def process_coc(
        username: str, context: str, blossom_submission: Dict, cfg: Config
) -> Tuple:
    """
    Process the acceptation of the CoC by the specified user.

    :param username: The name of the user accepting the CoC
    :param context: The context of the reply, to use as a link
    :param blossom_submission: The corresponding Submission in Blossom
    :param cfg: Config of tor
    """
    user_response = cfg.blossom.get_user(username=username)
    if user_response.status == BlossomStatus.ok:
        # The status codes of accepting the CoC are not checked because they are already
        # caught by getting the user.
        response = cfg.blossom.accept_coc(username=username)
        new_acceptance = (response.status == BlossomStatus.ok)
        if new_acceptance:
            emote = random.choice(MODCHAT_EMOTES)
            user_url = i18n["urls"]["reddit_url"].format(f"/u/{username}")
            post_url = i18n["urls"]["reddit_url"].format(context)
            send_to_modchat(
                f"<{user_url}|u/{username}> has just "
                f"<{post_url}|accepted the CoC!> {emote}",
                cfg,
                channel="new_volunteers"
            )
        return process_claim(username, blossom_submission, cfg, first_time=new_acceptance)
    elif user_response.status == BlossomStatus.not_found:
        cfg.blossom.create_user(username=username)
        return i18n["responses"]["general"]["coc_not_accepted"].format(
            get_wiki_page("codeofconduct", cfg)
        ), None
    else:
        return process_claim(username, blossom_submission, cfg)


def process_claim(
        username: str, blossom_submission: Dict, cfg: Config, first_time=False
) -> Tuple:
    """
    Process a claim request.

    This function sends a reply depending on the response from Blossom and
    creates an user when this is the first time a user uses the bot.

    :param username: Name of the user claiming the submission
    :param blossom_submission: The relevant submission in Blossom
    :param cfg: Config of tor
    :param first_time: Whether this is the first time a user claims something
    """
    coc_not_accepted = i18n["responses"]["general"]["coc_not_accepted"]

    response = cfg.blossom.claim(
        submission_id=blossom_submission["id"], username=username
    )
    return_flair = None
    if response.status == BlossomStatus.ok:
        message = i18n["responses"]["claim"]["first_claim_success" if first_time else "success"]
        return_flair = flair.in_progress
        log.info(f'Claim on Submission {blossom_submission["tor_url"]} by {username} successful.')

    elif response.status == BlossomStatus.coc_not_accepted:
        message = coc_not_accepted.format(get_wiki_page("codeofconduct", cfg))

    elif response.status == BlossomStatus.not_found:
        message = coc_not_accepted.format(get_wiki_page("codeofconduct", cfg))
        cfg.blossom.create_user(username=username)

    elif response.status == BlossomStatus.blacklisted:
        message = i18n["responses"]["general"]["blacklisted"]

    else:
        message = i18n["responses"]["claim"]["already_claimed"]

    return message, return_flair


def process_done(
        user: Redditor,
        blossom_submission: Dict,
        post: Comment,
        cfg: Config,
        override=False,
        alt_text_trigger=False
) -> Tuple:
    """
    Handles comments where the user claims to have completed a post.

    This function sends a reply to the user depending on the responses received
    from Blossom.

    :param user: The user claiming his transcription is done
    :param blossom_submission: The relevant submission in Blossom
    :param post: The post of the user, used to retrieve the user's flair
    :param cfg: the global config object.
    :param override: whether the validation check should be skipped
    :param alt_text_trigger: whether there is an alternative to "done" that has
                             triggered this function.
    """
    return_flair = None
    done_messages = i18n["responses"]["done"]
    # This is explicitly missing the format call that adds the code of
    # conduct text because if we populate it here, we will fetch the wiki
    # page on _every single `done`_ and that's just silly. Only populate
    # it if it's necessary.
    coc_not_accepted = i18n["responses"]["general"]["coc_not_accepted"]

    blossom_user = cfg.blossom.get_user(username=user.name)
    if blossom_user.status != BlossomStatus.ok:
        # If we don't know who the volunteer is, then we don't have a record of
        # them and they need to go through the code of conduct process.
        return coc_not_accepted.format(get_wiki_page("codeofconduct", cfg)), return_flair

    if not blossom_user.data['accepted_coc']:
        # If the volunteer in question hasn't accepted the code of conduct,
        # eject early and return. Although the `create_transcription` endpoint
        # returns a code of conduct check, we only hit it when we create a
        # transcription, which requires that they wrote something. If a volunteer
        # just writes `done` without putting a transcription down, it will hit
        # this edge case.
        return coc_not_accepted.format(get_wiki_page("codeofconduct", cfg)), return_flair

    transcription, is_visible = get_transcription(blossom_submission["url"], user, cfg)
    if transcription is None:
        message = done_messages["cannot_find_transcript"]
    else:
        cfg.blossom.create_transcription(
            transcription.id,
            transcription.body,
            transcription.permalink,
            transcription.author.name,
            blossom_submission["id"],
            not is_visible
        )

        done_response = cfg.blossom.done(
            blossom_submission["id"], user.name, override
        )
        # Note that both the not_found and coc_not_accepted status are already
        # caught in the previous lines of code, hence these are not checked again.
        if done_response.status == BlossomStatus.ok:
            return_flair = flair.completed
            set_user_flair(user, post, cfg)
            message = done_messages["completed_transcript"]
            if alt_text_trigger:
                message = f"I think you meant `done`, so here we go!\n\n{message}"

        elif done_response.status == BlossomStatus.already_completed:
            message = done_messages["already_completed"]

        elif done_response.status == BlossomStatus.missing_prerequisite:
            message = done_messages["not_claimed_by_user"]

        elif done_response.status == BlossomStatus.blacklisted:
            message = i18n["responses"]["general"]["blacklisted"]

        else:
            message = done_messages["cannot_find_transcript"]

    return message, return_flair


def process_unclaim(
        username: str, blossom_submission: Dict, submission: Submission, cfg: Config
) -> Tuple:
    """
    Process an unclaim request.

    Note that this function also checks whether a post should be removed and
    does so when required.

    :param username: The name of the user unclaiming the submission
    :param blossom_submission: The relevant Submission of Blossom
    :param submission: The relevant Submission in Reddit
    :param cfg: Config of tor
    """
    response = cfg.blossom.unclaim(
        submission_id=blossom_submission["id"], username=username
    )
    return_flair = None
    unclaim_messages = i18n["responses"]["unclaim"]
    if response.status == BlossomStatus.ok:
        message = unclaim_messages["success"]
        return_flair = flair.unclaimed
        removed, reported = remove_if_required(submission, blossom_submission["id"], cfg)
        if removed:
            # Select the message based on whether the post was reported or not.
            message = unclaim_messages[
                "success_with_report" if reported else "success_without_report"
            ]
    elif response.status == BlossomStatus.not_found:
        message = i18n["responses"]["general"]["coc_not_accepted"].format(
            get_wiki_page("codeofconduct", cfg)
        )
        cfg.blossom.create_user(username)
    elif response.status == BlossomStatus.other_user:
        message = unclaim_messages["claimed_other_user"]
    elif response.status == BlossomStatus.already_completed:
        message = unclaim_messages["post_already_completed"]
    elif response.status == BlossomStatus.blacklisted:
        message = i18n["responses"]["general"]["blacklisted"]
    else:
        message = unclaim_messages["still_unclaimed"]
    return message, return_flair


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
