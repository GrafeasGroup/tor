import logging

import praw
from tor_core.helpers import send_to_slack

from tor.core.admin_commands import process_override
from tor.core.admin_commands import reload_config
from tor.core.admin_commands import update_and_restart
from tor.core.mentions import process_mention
from tor.core.user_interaction import process_claim
from tor.core.user_interaction import process_coc
from tor.core.user_interaction import process_done
from tor.core.user_interaction import process_thanks


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
    mentions = []
    replies = []
    # Grab all of our messages and filter.
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
            continue

        if item.author.name == 'transcribot':
            item.mark_read()
            continue
        if item.subject == 'username mention':
            mentions.append(item)
            item.mark_read()
        if item.subject in ('comment reply', 'post reply'):
            replies.append(item)
            # we don't mark as read here so that any comments that are not
            # ones we're looking for will eventually get emailed to me as
            # things I need to look at
        if 'reload' in item.subject.lower():
            item.mark_read()
            reload_config(item, config)

            continue
        if 'update' in item.subject.lower():
            item.mark_read()
            update_and_restart(item, config)
            # there's no reason to do anything else here because the process
            # will terminate and respawn

        # ARE YOU ALIVE?!
        if item.subject.lower() == 'ping':
            item.mark_read()
            logging.info('Received ping from {}. Pong!'.format(item.author.name))
            item.reply('Pong!')

    # sort them and create posts where necessary
    for mention in mentions:
        logging.info('Received mention! ID {}'.format(mention))

        # noinspection PyUnresolvedReferences
        try:
            process_mention(mention)
        except (AttributeError, praw.exceptions.ClientException):
            # apparently this crashes with an AttributeError if someone calls
            # the bot and immediately deletes their comment. This should fix
            # that.
            continue

    # comment replies
    for reply in replies:
        # noinspection PyUnresolvedReferences
        try:
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
                return
            if 'good bot' in reply.body.lower() or 'bad bot' in reply.body.lower():
                # please stop emailing me, I just don't care
                reply.mark_read()

        except (AttributeError, praw.exceptions.ClientException):
            # the only way we should hit this is if somebody comments and then
            # deletes their comment before the bot finished processing. It's
            # uncommon, but common enough that this is necessary.
            continue
