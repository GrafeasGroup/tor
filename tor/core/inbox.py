import logging

from tor.core.admin_commands import process_override
from tor.core.admin_commands import reload_config
from tor.core.mentions import process_mention
from tor.core.user_interaction import process_claim
from tor.core.user_interaction import process_done
from tor.helpers.reddit_ids import is_valid
from tor.strings.debug import id_already_handled_in_db
from tor.core.user_interaction import process_coc


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
            reload_config(item, tor, config)
            item.mark_read()
            item.reply(
                'Config reloaded!'
            )

    # sort them and create posts where necessary
    for mention in mentions:
        logging.info('Received mention! ID {}'.format(mention))

        if not is_valid(mention.parent_id, config):
            # Do our check here to make sure we can actually work on this one and
            # that we haven't already posted about it. We use the full ID here
            # instead of the cleaned one, just in case.
            logging.info(id_already_handled_in_db.format(mention.parent_id))
            continue

        process_mention(mention, r, tor, config)

    # comment replies
    for reply in replies:
        if 'i accept' in reply.body.lower():
            process_coc(reply, r, tor, config)
            reply.mark_read()
            return

        # The current implementation allows for a comment reading "claim done"
        # to process the entire thing in one go.
        # This is an abuse of the decision tree and something I didn't catch
        # until it was too late, but since it's useful in certain circumstances
        # we'll let it slide.
        if 'claim' in reply.body.lower():
            process_claim(reply, r, tor, config)
            reply.mark_read()
        if 'done' in reply.body.lower():
            process_done(reply, r, tor, config)
            reply.mark_read()

        if '!override' in reply.body.lower():
            process_override(reply, r, tor, config)
            reply.mark_read()
            return
