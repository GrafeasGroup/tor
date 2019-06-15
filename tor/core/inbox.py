import logging
import re

from praw.exceptions import ClientException as RedditClientException
from praw.models import Comment as RedditComment

from tor.core import validation
from tor.core.admin_commands import process_command, process_override
from tor.core.helpers import send_to_modchat
from tor.core.mentions import process_mention
from tor.core.strings import reddit_url
from tor.core.user_interaction import (process_claim, process_coc,
                                       process_done, process_thanks,
                                       process_unclaim,
                                       process_wrong_post_location)

MOD_SUPPORT_PHRASES = [
    re.compile('fuck', re.IGNORECASE),
    # re.compile('unclaim', re.IGNORECASE),
    re.compile('undo', re.IGNORECASE),
    # re.compile('(?:good|bad) bot', re.IGNORECASE),
]


def forward_to_slack(item, config):
    username = item.author.name

    send_to_modchat(
        f'<{reddit_url.format(item.context)}|Unhandled message>'
        f' by'
        f' <{reddit_url.format("/u/" + username)}|u/{username}> -- '
        f'*{item.subject}*:\n{item.body}', config
    )
    logging.info(
        f'Received unhandled inbox message from {username}. \n Subject: '
        f'{item.subject}\n\nBody: {item.body} '
    )


def process_mod_intervention(post, config):
    """
    Triggers an alert in slack with a link to the comment if there is something
    offensive or in need of moderator intervention
    """
    if not isinstance(post, RedditComment):
        # Why are we here if it's not a comment?
        return

    # Collect all offenses (noted by the above regular expressions) from the
    # original
    phrases = []
    for regex in MOD_SUPPORT_PHRASES:
        matches = regex.search(post.body)
        if not matches:
            continue

        phrases.append(matches.group())

    if len(phrases) == 0:
        # Nothing offensive here, why did this function get triggered?
        return

    # Wrap each phrase in double-quotes (") and commas in between
    phrases = '"' + '", "'.join(phrases) + '"'

    send_to_modchat(
        f':rotating_light::rotating_light: Mod Intervention Needed '
        f':rotating_light::rotating_light: '
        f'\n\nDetected use of {phrases} {post.submission.shortlink}',
        config
    )


def process_reply(reply, config):
    # noinspection PyUnresolvedReferences
    try:
        if any([regex.search(reply.body) for regex in MOD_SUPPORT_PHRASES]):
            process_mod_intervention(reply, config)
            reply.mark_read()
            return

        r_body = reply.body.lower()  # cache that thing

        if (
            'image transcription' in r_body or
            validation._footer_check(reply, config)
        ):
            process_wrong_post_location(reply)
            reply.mark_read()
            return

        if 'i accept' in r_body:
            process_coc(reply, config)
            reply.mark_read()
            return

        if 'unclaim' in r_body:
            process_unclaim(reply, config)
            reply.mark_read()
            return

        if (
            'claim' in r_body or
            'dibs' in r_body
        ):
            process_claim(reply, config)
            reply.mark_read()
            return

        if (
            'done' in r_body or
            'deno' in r_body  # we <3 u/Lornescri
        ):
            alt_text = True if 'done' not in r_body else False
            process_done(reply, config, alt_text_trigger=alt_text)
            reply.mark_read()
            return

        if 'thank' in r_body:  # trigger on "thanks" and "thank you"
            process_thanks(reply, config)
            reply.mark_read()
            return

        if '!override' in r_body:
            process_override(reply, config)
            reply.mark_read()
            return

        # If we made it this far, it's something we can't process automatically
        forward_to_slack(reply, config)
        reply.mark_read()  # no spamming the slack channel :)

    except (RedditClientException, AttributeError) as e:
        logging.warning(e)
        logging.warning(
            f"Unable to process comment {reply.submission.shortlink} "
            f"by {reply.author}"
        )
        # the only way we should hit this is if somebody comments and then
        # deletes their comment before the bot finished processing. It's
        # uncommon, but common enough that this is necessary.
        pass


def check_inbox(config):
    """
    Goes through all the unread messages in the inbox. It deliberately
    leaves mail which does not fit into either category so that it can
    be read manually at a later point.

    :return: None.
    """
    # Sort inbox, then act on it
    # Invert the inbox so we're processing oldest first!
    for item in reversed(list(config.r.inbox.unread(limit=None))):
        # Very rarely we may actually get a message from Reddit itself.
        # In this case, there will be no author attribute.
        if item.author is None:
            send_to_modchat(
                f'We received a message without an author -- '
                f'*{item.subject}*:\n{item.body}', config
            )
            item.mark_read()

        elif item.author.name == 'transcribot':
            item.mark_read()

        elif item.author.name in config.redis.smembers('blacklist'):
            logging.info(
                f'Skipping inbox item from {item.author.name} who is on the '
                f'blacklist '
            )
            item.mark_read()
            continue

        elif item.subject == 'username mention':
            logging.info(f'Received mention! ID {item}')

            # noinspection PyUnresolvedReferences
            try:
                process_mention(item)
            except (AttributeError, RedditClientException):
                # apparently this crashes with an AttributeError if someone
                # calls the bot and immediately deletes their comment. This
                # should fix that.
                continue
            item.mark_read()

        elif item.subject in ('comment reply', 'post reply'):
            process_reply(item, config)

        elif item.subject[0] == '!':
            # Handle our special commands
            process_command(item, config)
            item.mark_read()
            continue

        else:
            item.mark_read()
            forward_to_slack(item, config)
