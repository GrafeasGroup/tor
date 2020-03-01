import logging
import re

from praw.exceptions import ClientException  # type: ignore
from praw.models import Comment, Message  # type: ignore
from praw.models.reddit.mixins import InboxableMixin  # type: ignore

from tor.core import validation
from tor.core.admin_commands import process_command, process_override
from tor.core.config import Config
from tor.core.helpers import send_to_modchat, is_our_subreddit, _
from tor.core.user_interaction import (process_claim, process_coc,
                                       process_done, process_message,
                                       process_thanks, process_unclaim,
                                       process_wrong_post_location)
from tor.strings import translation

MOD_SUPPORT_PHRASES = [
    re.compile('fuck', re.IGNORECASE),
    re.compile('undo', re.IGNORECASE),
    # re.compile('(?:good|bad) bot', re.IGNORECASE),
]

log = logging.getLogger(__name__)


def forward_to_slack(item: InboxableMixin, cfg: Config) -> None:
    username = str(item.author.name)
    i18n = translation()

    send_to_modchat(
        f'<{i18n["urls"]["reddit_url"].format(item.context)}|Unhandled message>'
        f' by'
        f' <{i18n["urls"]["reddit_url"].format("/u/" + username)}|u/{username}> -- '
        f'*{item.subject}*:\n{item.body}', cfg
    )
    log.info(
        f'Received unhandled inbox message from {username}. \n Subject: '
        f'{item.subject}\n\nBody: {item.body} '
    )


def process_mod_intervention(post: Comment, cfg: Config) -> None:
    """
    Triggers an alert in slack with a link to the comment if there is something
    offensive or in need of moderator intervention
    """
    # Collect all offenses (noted by the above regular expressions) from the
    # original
    phrase_list = []
    for regex in MOD_SUPPORT_PHRASES:
        matches = regex.search(post.body)
        if not matches:
            continue

        phrase_list.append(matches.group())

    if len(phrase_list) == 0:
        # Nothing offensive here, why did this function get triggered?
        return

    # Wrap each phrase in double-quotes (") and commas in between
    phrases = '"' + '", "'.join(phrase_list) + '"'

    send_to_modchat(
        f':rotating_light::rotating_light: Mod Intervention Needed '
        f':rotating_light::rotating_light: '
        f'\n\nDetected use of {phrases} {post.submission.shortlink}',
        cfg
    )


def process_reply(reply: Comment, cfg: Config) -> None:
    try:
        r_body = reply.body.lower()  # cache that thing

        if any([regex.search(reply.body) for regex in MOD_SUPPORT_PHRASES]):
            process_mod_intervention(reply, cfg)

        elif 'image transcription' in r_body or validation._footer_check(reply, cfg):
            process_wrong_post_location(reply, cfg)

        elif 'i accept' in r_body:
            process_coc(reply, cfg)

        elif 'unclaim' in r_body or 'cancel' in r_body:
            process_unclaim(reply, cfg)

        elif 'claim' in r_body or 'dibs' in r_body:
            process_claim(reply, cfg)

        elif 'done' in r_body or 'deno' in r_body or 'doen' in r_body:
            alt_text = True if 'done' not in r_body else False
            process_done(reply, cfg, alt_text_trigger=alt_text)

        elif 'thank' in r_body:  # trigger on "thanks" and "thank you"
            process_thanks(reply, cfg)

        elif '!override' in r_body:
            process_override(reply, cfg)

        else:
            # If we made it this far, it's something we can't process automatically
            forward_to_slack(reply, cfg)

    except (ClientException, AttributeError) as e:
        log.warning(e)
        log.warning(
            f"Unable to process comment {reply.submission.shortlink} "
            f"by {reply.author}"
        )
        # the only way we should hit this is if somebody comments and then
        # deletes their comment before the bot finished processing. It's
        # uncommon, but common enough that this is necessary.


def process_mention(mention: Comment) -> None:
    """
    Handles username mentions and handles the formatting and posting of
    those calls as workable jobs to ToR.

    :param mention: the Comment object containing the username mention.
    :return: None.
    """
    try:
        i18n = translation()
        pm_subject = i18n['responses']['direct_message']['subject']
        pm_body = i18n['responses']['direct_message']['body']

        # message format is subject, then body
        mention.author.message(pm_subject, _(pm_body))
        log.info(f'Message sent to {mention.author.name}!')
    except (ClientException, AttributeError):
        # apparently this crashes with an AttributeError if someone
        # calls the bot and immediately deletes their comment. This
        # should fix that.
        pass


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
                f'We received a message without an author -- '
                f'*{item.subject}*:\n{item.body}', cfg
            )

        elif author_name == 'transcribot':
            # bot responses shouldn't trigger workflows in other bots
            log.info('Skipping response from our OCR bot')

        elif cfg.redis.sismember('blacklist', author_name):
            log.info(f'Skipping inbox item from {author_name!r} who is on the blacklist')

        elif isinstance(item, Comment) and is_our_subreddit(item.subreddit.name, cfg):
            process_reply(item, cfg)
        elif isinstance(item, Comment):
            log.info(f'Received username mention! ID {item}')
            process_mention(item)

        elif isinstance(item, Message):
            if item.subject[0] == '!':
                process_command(item, cfg)
            else:
                process_message(item, cfg)

        else:
            # We don't know what the heck this is, so just send it onto
            # slack for manual triage.
            forward_to_slack(item, cfg)

        # No matter what, we want to mark this as read so we don't re-process it.
        item.mark_read()
