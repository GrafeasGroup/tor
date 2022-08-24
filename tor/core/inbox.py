import logging
import random
from typing import Optional

import beeline
from praw.exceptions import ClientException
from praw.models import Comment, Message
from praw.models.reddit.mixins import InboxableMixin

from tor import __BOT_NAMES__
from tor.core import (
    CLAIM_PHRASES,
    DONE_PHRASES,
    MOD_SUPPORT_PHRASES,
    UNCLAIM_PHRASES,
)
from tor.core.admin_commands import process_command, process_override, process_debug
from tor.core.config import Config
from tor.core.helpers import (
    _,
    is_our_subreddit,
    send_reddit_reply,
    send_to_modchat,
    check_for_phrase,
)
from tor.core.posts import get_blossom_submission
from tor.core.user_interaction import (
    process_claim,
    process_coc,
    process_done,
    process_message,
    process_unclaim,
)
from tor.helpers.flair import flair_post
from tor.strings import translation
from tor.validation.transcription_validation import is_comment_transcription

i18n = translation()

log = logging.getLogger(__name__)


def extract_sub_from_url(url: str) -> str:
    """returns the sub name from the given url without "r/" at the start."""
    return url.split("/")[4]


@beeline.traced(name="forward_to_slack")
def forward_to_slack(item: InboxableMixin, cfg: Config) -> None:
    username = str(item.author.name)

    send_to_modchat(
        f'<{i18n["urls"]["reddit_url"].format(item.context)}|Unhandled message>'
        f" by"
        f' <{i18n["urls"]["reddit_url"].format("/u/" + username)}|u/{username}> -- '
        f"*{item.subject}*:\n{item.body}",
        cfg,
    )
    log.info(
        f"Received unhandled inbox message from {username}. \n Subject: "
        f"{item.subject}\n\nBody: {item.body} "
    )


@beeline.traced(name="process_reply")
def process_reply(reply: Comment, cfg: Config) -> None:
    try:
        log.debug(f"Received reply from {reply.author.name}: {reply.body}")
        message: Optional[str] = ""
        flair: Optional[str] = None
        r_body = reply.body.lower()  # cache that thing

        if "image transcription" in r_body or is_comment_transcription(reply, cfg):
            post_link = reply.submission.url
            sub_name = extract_sub_from_url(post_link)
            message = i18n["responses"]["general"]["transcript_on_tor_post"].format(
                sub_name=sub_name,
                post_link=post_link,
            )
        elif matches := [
            match.group()
            for match in [regex.search(reply.body) for regex in MOD_SUPPORT_PHRASES]
            if match
        ]:
            phrases = '"' + '", "'.join(matches) + '"'
            send_to_modchat(
                i18n["mod"]["intervention_needed"].format(
                    phrases=phrases,
                    link=reply.submission.shortlink,
                    author=reply.author.name,
                    text=reply.body,
                ),
                cfg,
            )
            message = i18n["responses"]["general"]["getting_help"]
        elif "thank" in r_body:  # trigger on "thanks" and "thank you"
            thumbs_up_gifs = i18n["urls"]["thumbs_up_gifs"]
            youre_welcome = i18n["responses"]["general"]["youre_welcome"]
            message = youre_welcome.format(random.choice(thumbs_up_gifs))
        else:
            submission = reply.submission
            username = reply.author.name
            if submission.author.name not in __BOT_NAMES__:
                log.debug("Received 'command' on post we do not own. Ignoring.")
                return

            blossom_submission = get_blossom_submission(submission, cfg)
            if "i accept" in r_body:
                message, flair = process_coc(
                    username, reply.context, blossom_submission, cfg
                )
            elif check_for_phrase(r_body, UNCLAIM_PHRASES):
                message, flair = process_unclaim(
                    username, blossom_submission, submission, cfg
                )
            elif check_for_phrase(r_body, CLAIM_PHRASES):
                message, flair = process_claim(username, blossom_submission, cfg)
            elif check_for_phrase(r_body, DONE_PHRASES):
                alt_text = "done" not in r_body
                message, flair = process_done(
                    reply.author,
                    blossom_submission,
                    reply,
                    cfg,
                    alt_text_trigger=alt_text,
                )
            elif "!override" in r_body:
                message, flair = process_override(
                    reply.author, blossom_submission, reply.parent_id, cfg
                )
            elif "!debug" in r_body:
                message, flair = process_debug(reply.author, blossom_submission, cfg)
            elif "!comment" in r_body:
                message, flair = None, None
            else:
                # If we made it this far, it's something we can't process automatically
                forward_to_slack(reply, cfg)
        if message:
            send_reddit_reply(reply, message)
        if flair:
            flair_post(reply.submission, flair)

    except (ClientException, AttributeError) as e:
        # the only way we should hit this is if somebody comments and then
        # deletes their comment before the bot finished processing. It's
        # uncommon, but common enough that this is necessary.
        log.warning(e)
        log.warning(
            f"Unable to process comment {reply.submission.shortlink} "
            f"by {reply.author}"
        )


@beeline.traced(name="process_mention")
def process_mention(mention: Comment) -> None:
    """
    Handles username mentions and handles the formatting and posting of
    those calls as workable jobs to ToR.

    :param mention: the Comment object containing the username mention.
    :return: None.
    """
    try:
        pm_subject = i18n["responses"]["direct_message"]["subject"]
        pm_body = i18n["responses"]["direct_message"]["body"]

        # message format is subject, then body
        mention.author.message(pm_subject, _(pm_body))
        log.info(f"Message sent to {mention.author.name}!")
    except (ClientException, AttributeError):
        # apparently this crashes with an AttributeError if someone
        # calls the bot and immediately deletes their comment. This
        # should fix that.
        pass


@beeline.traced(name="check_inbox")
def check_inbox(cfg: Config) -> None:
    """
    Goes through all the unread messages in the inbox. It deliberately
    leaves mail which does not fit into either category so that it can
    be read manually at a later point.

    :return: None.
    """
    # Sort inbox, then act on it
    # Invert the inbox so we're processing oldest first!
    for item in reversed(list(cfg.r.inbox.unread(limit=None))):
        # Very rarely we may actually get a message from Reddit itself.
        # In this case, there will be no author attribute.
        author_name = item.author.name if item.author else None

        if author_name is None:
            send_to_modchat(
                f"We received a message without an author -- "
                f"*{item.subject}*:\n{item.body}",
                cfg,
            )
        elif author_name == "transcribot":
            # bot responses shouldn't trigger workflows in other bots
            log.info("Skipping response from our OCR bot")
        elif author_name == "blossom-app":
            log.info("Skipping response from Blossom")
        else:
            if isinstance(item, Comment):
                if is_our_subreddit(item.subreddit.name, cfg):
                    process_reply(item, cfg)
                else:
                    log.info(f"Received username mention! ID {item}")
                    process_mention(item)
            elif isinstance(item, Message):
                if item.subject[0] == "!":
                    process_command(item, cfg)
                else:
                    process_message(item, cfg)
            else:
                # We don't know what the heck this is, so just send it onto
                # slack for manual triage.
                forward_to_slack(item, cfg)
        # No matter what, we want to mark this as read so we don't re-process it.
        item.mark_read()
