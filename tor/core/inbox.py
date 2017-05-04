import logging

from tor.core.admin_commands import process_override
from tor.core.mentions import process_mention
from tor.core.user_interaction import process_claim
from tor.core.user_interaction import process_done
from tor.helpers.reddit_ids import is_valid
from tor.strings.debug import id_already_handled_in_db


def check_inbox(r, tor, redis_server, context):
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
    # first we do mentions, then comment replies
    mentions = []
    # grab all of our messages and filter
    for item in r.inbox.unread(limit=None):
        if item.subject == 'username mention':
            mentions.append(item)
            item.mark_read()

    # sort them and create posts where necessary
    for mention in mentions:
        logging.info('Received mention! ID {}'.format(mention))

        if not is_valid(mention.parent_id, redis_server):
            # Do our check here to make sure we can actually work on this one and
            # that we haven't already posted about it. We use the full ID here
            # instead of the cleaned one, just in case.
            logging.info(id_already_handled_in_db.format(mention.parent_id))
            continue

        process_mention(mention, r, tor, redis_server, context)

    # comment replies
    replies = []
    for item in r.inbox.unread(limit=None):
        if item.author.name == 'transcribot':
            item.mark_read()
            continue
        if item.subject == 'comment reply':
            replies.append(item)

    for reply in replies:
        # if 'thank' in reply.body.lower():
        #     respond_to_thanks(reply)
        #     reply.mark_read()
        #     continue
        if 'claim' in reply.body.lower():
            process_claim(reply, r)
            reply.mark_read()
        if 'done' in reply.body.lower():
            process_done(reply, r, tor, redis_server, context)
            reply.mark_read()
        if '!override' in reply.body.lower():
            process_override(reply, r, tor, redis_server, context)
            reply.mark_read()