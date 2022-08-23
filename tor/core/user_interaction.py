import logging
import random
import time
from typing import Tuple

from tor.core.config import (
    SLACK_COC_ACCEPTED_CHANNEL_ID,
    SLACK_FORMATTING_ISSUE_CHANNEL_ID,
)
from tor.helpers.flair import check_promotion, generate_promotion_message

import beeline
from blossom_wrapper import BlossomStatus
from praw.models import Comment, Message, Redditor, Submission

from tor.validation.formatting_validation import (
    check_for_formatting_issues,
    get_formatting_issue_message,
)
from tor.core.config import Config
from tor.core.helpers import get_wiki_page, remove_if_required, send_to_modchat
from tor.validation.transcription_validation import get_transcription
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


def modchat_blocked_user_ping(username: str, blossom_submission: dict, cfg: Config) -> None:
    user_url = i18n["urls"]["reddit_url"].format(f"/u/{username}")
    send_to_modchat(
        f":no_entry_sign: Blocked user <{user_url}|u/{username}> is trying to transcribe."
        f" <{blossom_submission['tor_url']}|Thread link>",
        cfg,
    )


@beeline.traced(name="process_coc")
def process_coc(
    username: str, context: str, blossom_submission: dict, cfg: Config
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
        new_acceptance = response.status == BlossomStatus.ok
        if new_acceptance:
            emote = random.choice(MODCHAT_EMOTES)
            user_url = i18n["urls"]["reddit_url"].format(f"/u/{username}")
            post_url = i18n["urls"]["reddit_url"].format(context)
            send_to_modchat(
                f"<{user_url}|u/{username}> has just "
                f"<{post_url}|accepted the CoC!> {emote}",
                cfg,
                channel=SLACK_COC_ACCEPTED_CHANNEL_ID,
            )
        return process_claim(
            username, blossom_submission, cfg, first_time=new_acceptance
        )
    elif user_response.status == BlossomStatus.not_found:
        cfg.blossom.create_user(username=username)
        return (
            i18n["responses"]["general"]["coc_not_accepted"].format(
                get_wiki_page("codeofconduct", cfg)
            ),
            None,
        )
    else:
        return process_claim(username, blossom_submission, cfg)


@beeline.traced(name="process_claim")
def process_claim(
    username: str, blossom_submission: dict, cfg: Config, first_time=False
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
        # A random tip to append to the response
        random_tip = i18n["tips"]["message"].format(
            tip_message=random.choice(i18n["tips"]["collection"])
        )

        message = (
            i18n["responses"]["claim"][
                "first_claim_success" if first_time else "success"
            ]
            + "\n\n"
            + random_tip
        )

        return_flair = flair.in_progress
        log.info(
            f'Claim on Submission {blossom_submission["tor_url"]} by {username} successful.'
        )

    elif response.status == BlossomStatus.coc_not_accepted:
        message = coc_not_accepted.format(get_wiki_page("codeofconduct", cfg))

    elif response.status == BlossomStatus.not_found:
        message = coc_not_accepted.format(get_wiki_page("codeofconduct", cfg))
        cfg.blossom.create_user(username=username)

    elif response.status == BlossomStatus.blocked:
        message = i18n["responses"]["general"]["blocked"]
        modchat_blocked_user_ping(username, blossom_submission, cfg)

    elif response.status == BlossomStatus.already_claimed:
        claimed_by = response.data["username"]
        if claimed_by == username:
            # This user already got the submission
            message = i18n["responses"]["claim"]["already_claimed_by_self"]
        else:
            # The submission was claimed by someone else
            message = i18n["responses"]["claim"]["already_claimed_by_someone"].format(
                claimed_by=claimed_by
            )

    elif response.status == BlossomStatus.too_many_claims:
        claimed_links = [submission["tor_url"] for submission in response.data]
        message = i18n["responses"]["claim"]["too_many_claims"].format(
            links="\n".join(f"- {link}" for link in claimed_links),
        )

    else:
        message = i18n["responses"]["general"]["oops"]

    return message, return_flair


@beeline.traced(name="process_done")
def process_done(
    user: Redditor,
    blossom_submission: dict,
    comment: Comment,
    cfg: Config,
    override=False,
    alt_text_trigger=False,
) -> Tuple:
    """
    Handles comments where the user claims to have completed a post.

    This function sends a reply to the user depending on the responses received
    from Blossom.

    :param user: The user claiming his transcription is done
    :param blossom_submission: The relevant submission in Blossom
    :param comment: The comment of the user, used to retrieve the user's flair
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
        return (
            coc_not_accepted.format(get_wiki_page("codeofconduct", cfg)),
            return_flair,
        )

    if not blossom_user.data["accepted_coc"]:
        # If the volunteer in question hasn't accepted the code of conduct,
        # eject early and return. Although the `create_transcription` endpoint
        # returns a code of conduct check, we only hit it when we create a
        # transcription, which requires that they wrote something. If a volunteer
        # just writes `done` without putting a transcription down, it will hit
        # this edge case.
        return (
            coc_not_accepted.format(get_wiki_page("codeofconduct", cfg)),
            return_flair,
        )

    transcription, is_visible = get_transcription(blossom_submission["url"], user, cfg)

    message = done_messages["cannot_find_transcript"]  # default message

    if not transcription:
        # When the user replies `done` quickly after posting the transcription,
        # it might not be available on Reddit yet. Wait a bit and try again.
        time.sleep(1)
        transcription, is_visible = get_transcription(
            blossom_submission["url"], user, cfg
        )

    if transcription and not override:
        # Try to detect common formatting errors
        formatting_errors = check_for_formatting_issues(transcription.body)
        if len(formatting_errors) > 0:
            # Formatting issues found.  Reject the `done` and ask the
            # volunteer to fix them.
            issues = ", ".join([error.value for error in formatting_errors])
            # TODO: Re-evaluate if this is necessary
            # This is more of a temporary thing to see how the
            # volunteers react to the bot.
            send_to_modchat(
                i18n["mod"]["formatting_issues"].format(
                    author=user.name,
                    issues=issues,
                    link=f"https://reddit.com{comment.context}",
                ),
                cfg,
                SLACK_FORMATTING_ISSUE_CHANNEL_ID,
            )
            message = get_formatting_issue_message(formatting_errors)
            return message, return_flair

    if transcription:
        cfg.blossom.create_transcription(
            transcription.id,
            transcription.body,
            i18n["urls"]["reddit_url"].format(str(transcription.permalink)),
            transcription.author.name,
            blossom_submission["id"],
            not is_visible,
        )

    if transcription or override:
        # because we can enter this state with or without a transcription, it
        # makes sense to have this as a separate block.
        done_response = cfg.blossom.done(blossom_submission["id"], user.name, override)
        # Note that both the not_found and coc_not_accepted status are already
        # caught in the previous lines of code, hence these are not checked again.
        if done_response.status == BlossomStatus.ok:
            return_flair = flair.completed
            set_user_flair(user, comment, cfg)
            log.info(
                f'Done on Submission {blossom_submission["tor_url"]} by {user.name}'
                f" successful."
            )
            message = done_messages["completed_transcript"]
            transcription_count = blossom_user.data["gamma"] + 1

            if check_promotion(transcription_count):
                additional_message = generate_promotion_message(transcription_count)
                message = f"{message}\n\n{additional_message}"

            if alt_text_trigger:
                message = f"I think you meant `done`, so here we go!\n\n{message}"

        elif done_response.status == BlossomStatus.already_completed:
            message = done_messages["already_completed"]

        elif done_response.status == BlossomStatus.missing_prerequisite:
            message = done_messages["not_claimed_by_user"]

        elif done_response.status == BlossomStatus.blocked:
            message = i18n["responses"]["general"]["blocked"]
            modchat_blocked_user_ping(user.name, blossom_submission, cfg)

    return message, return_flair


@beeline.traced(name="process_unclaim")
def process_unclaim(
    username: str, blossom_submission: dict, submission: Submission, cfg: Config
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
        removed = remove_if_required(cfg, submission, blossom_submission)
        if removed:
            # Let the user know that we removed the post
            message = unclaim_messages["success_removed"]
    elif response.status == BlossomStatus.not_found:
        message = i18n["responses"]["general"]["coc_not_accepted"].format(
            get_wiki_page("codeofconduct", cfg)
        )
        cfg.blossom.create_user(username)
    elif response.status == BlossomStatus.other_user:
        message = unclaim_messages["claimed_other_user"]
    elif response.status == BlossomStatus.already_completed:
        message = unclaim_messages["post_already_completed"]
    elif response.status == BlossomStatus.blocked:
        message = i18n["responses"]["general"]["blocked"]
        modchat_blocked_user_ping(username, blossom_submission, cfg)
    else:
        message = unclaim_messages["still_unclaimed"]
    return message, return_flair


@beeline.traced(name="process_message")
def process_message(message: Message, cfg: Config) -> None:
    dm_subject = i18n["responses"]["direct_message"]["dm_subject"]
    dm_body = i18n["responses"]["direct_message"]["dm_body"]

    author = message.author
    username = author.name if author else None

    if username:
        author.message(dm_subject, dm_body)
        send_to_modchat(
            f'DM from <{i18n["urls"]["reddit_url"].format("/u/" + username)}|u/{username}> -- '
            f"*{message.subject}*:\n{message.body}",
            cfg,
        )
        log.info(
            f"Received DM from {username}. \n Subject: {message.subject}\n\nBody: {message.body}"
        )
    else:
        send_to_modchat(
            f"DM with no author -- " f"*{message.subject}*:\n{message.body}", cfg
        )
        log.info(
            f"Received DM with no author. \n Subject: {message.subject}\n\nBody: {message.body}"
        )
