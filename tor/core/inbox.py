import logging
import re

from praw.exceptions import ClientException as RedditClientException
from praw.models import Comment as RedditComment
from tor_core.helpers import send_to_slack

from tor.core.admin_commands import process_override
from tor.core.admin_commands import reload_config
from tor.core.admin_commands import update_and_restart
from tor.core.mentions import process_mention
from tor.core.user_interaction import process_claim
from tor.core.user_interaction import process_coc
from tor.core.user_interaction import process_done
from tor.core.user_interaction import process_thanks

MOD_SUPPORT_PHRASES = [
    re.compile('fuck', re.IGNORECASE),
    re.compile('unclaim', re.IGNORECASE),
    re.compile('undo', re.IGNORECASE),
    re.compile('(?:good|bad) bot', re.IGNORECASE),
]


def forward_to_slack(item, config):
    send_to_slack(
        'Unknown reply by **{author}**, {subject}: {body}'.format(
            author=item.author,
            body=item.body,
            subject=item.subject,
        ), config)

    logging.info(
        'Received unhandled inbox message from {}. \nSubject: {}\n\nBody: {}'
        ''.format(item.author, item.subject, item.body)
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

    send_to_slack(
        'Mod Intervention Needed: Detected use of {phrases} <{link}>'
        ''.format(link=post.submission.shortlink, phrases=phrases),
        config
    )


def process_reply(reply, config):
    # noinspection PyUnresolvedReferences
    try:
        if any([regex.search(reply.body) for regex in MOD_SUPPORT_PHRASES]):
            process_mod_intervention(reply, config)
            reply.mark_read()
            return

        if 'i accept' in reply.body.lower():
            process_coc(reply, config)
            reply.mark_read()
            return

        if 'claim' in reply.body.lower():
            process_claim(reply, config)
            reply.mark_read()
            return

        if 'done' in reply.body.lower():
            process_done(reply, config)
            reply.mark_read()
            return

        if 'thank' in reply.body.lower():  # trigger on "thanks" and "thank you"
            process_thanks(reply, config)
            reply.mark_read()
            return

        if '!override' in reply.body.lower():
            process_override(reply, config)
            reply.mark_read()
            return  # Because overrides should stop the world and start fresh

        forward_to_slack(reply, config)
        reply.mark_read()  # no spamming the slack channel :)

    except (AttributeError, RedditClientException):
        # the only way we should hit this is if somebody comments and then
        # deletes their comment before the bot finished processing. It's
        # uncommon, but common enough that this is necessary.
        pass


def check_inbox(config):
    """
    Goes through all the unread messages in the inbox. It has two
    loops within this section, each one dealing with a different type
    of mail. Also deliberately leaves mail which does not fit into
    either category so that it can be read manually at a later point.

    The first loop handles username mentions.
    The second loop sorts out and handles comments that include 'claim'
        and 'done'.
    :return: None.
    """
    # Sort inbox, then act on it
    # Invert the inbox so we're processing oldest first!
    for item in reversed(list(config.r.inbox.unread(limit=None))):
        # Very rarely we may actually get a message from Reddit itself.
        # In this case, there will be no author attribute.
        if item.author is None:
            send_to_slack(
                'We received a message without an author. Subject: {}'
                ''.format(item.subject), config
            )
            item.mark_read()

        elif item.author.name == 'transcribot':
            item.mark_read()

        elif item.subject == 'username mention':
            logging.info('Received mention! ID {}'.format(item))

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

        elif 'reload' in item.subject.lower():
            item.mark_read()
            reload_config(item, config)

        elif 'update' in item.subject.lower():
            item.mark_read()
            update_and_restart(item, config)
            # there's no reason to do anything else here because the process
            # will terminate and respawn

        # ARE YOU ALIVE?!
        elif item.subject.lower() == 'ping':
            item.mark_read()
            logging.info(
                'Received ping from {}. Pong!'.format(item.author.name)
            )
            item.reply('Pong!')

        else:
            item.mark_read()
            forward_to_slack(item, config)
