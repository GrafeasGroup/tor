import logging

import praw

from tor.core.admin_commands import process_override
from tor.core.admin_commands import reload_config
from tor.core.mentions import process_mention
from tor.core.user_interaction import process_claim
from tor.core.user_interaction import process_done
from tor.helpers.reddit_ids import is_valid
from tor.strings.debug import id_already_handled_in_db
from tor.core.user_interaction import process_coc
from tor.core.admin_commands import update_and_restart


def check_inbox(r, tor, config):
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
    # grab all of our messages and filter
    for item in r.inbox.unread(limit=None):
        if item.author.name == 'transcribot':
            item.mark_read()
            continue
        if item.subject == 'username mention':
            mentions.append(item)
            item.mark_read()
        if item.subject == 'comment reply':
            replies.append(item)
            # we don't mark as read here so that any comments that are not
            # ones we're looking for will eventually get emailed to me as
            # things I need to look at
        if 'reload' in item.subject.lower():
            item.mark_read()
            reload_config(item, tor, config)
            item.reply(
                'Config reloaded!'
            )
            continue
        if 'update' in item.subject.lower():
            item.mark_read()
            update_and_restart(item, config)
            # there's no reason to do anything else here because the process
            # will terminate and respawn

    # sort them and create posts where necessary
    for mention in mentions:
        logging.info('Received mention! ID {}'.format(mention))

        if not is_valid(mention.parent_id, config):
            # Do our check here to make sure we can actually work on this one and
            # that we haven't already posted about it. We use the full ID here
            # instead of the cleaned one, just in case.
            logging.info(id_already_handled_in_db.format(mention.parent_id))
            continue

        # noinspection PyUnresolvedReferences
        try:
            process_mention(mention, r, tor, config)
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
                process_coc(reply, r, tor, config)
                reply.mark_read()
                return

            if 'claim' in reply.body.lower():
                process_claim(reply, r, tor, config)
                reply.mark_read()
                return

            if 'done' in reply.body.lower():
                process_done(reply, r, tor, config)
                reply.mark_read()
                return

            if '!override' in reply.body.lower():
                process_override(reply, r, tor, config)
                reply.mark_read()
                return

        except (AttributeError, praw.exceptions.ClientException):
            # the only way we should hit this is if somebody comments and then
            # deletes their comment before the bot finished processing. It's
            # uncommon, but common enough that this is necessary.
            continue
