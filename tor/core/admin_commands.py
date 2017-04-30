import logging

import random
from tor.helpers.reddit_ids import clean_id
from tor.helpers.misc import _


def process_override(reply, r, tor, redis_server, Context):
    """
    This process is for moderators of ToR to force u/transcribersofreddit
    to mark a post as complete and award flair when the bot refutes a
    `done` claim. The comment containing "!override" must be in response to
    the bot's comment saying that it cannot find the transcript.

    :param reply: the comment reply object from the moderator.
    :param r: the active Reddit instance.
    :param tor: the TranscribersOfReddit subreddit object.
    :param redis_server: Active Redis object.
    :param Context: the global context object.
    :return: None.
    """
    # first we verify that this comment comes from a moderator and that
    # we can work on it.
    if reply.author not in Context.tor_mods:
        reply.reply(_(random.choice(Context.no_gifs)))
        logging.info(
            '{} just tried to override. Lolno.'.format(reply.author.name)
        )
        return
    # okay, so the parent of the reply should be the bot's comment
    # saying it can't find it. In that case, we need the parent's
    # parent. That should be the comment with the `done` call in it.
    reply_parent = r.comment(id=clean_id(reply.parent_id))
    parents_parent = r.comment(id=clean_id(reply_parent.parent_id))
    if 'done' in parents_parent.body.lower():
        logging.info(
            'Starting validation override for post {}, approved by'
            '{}'.format(parents_parent.fullname, reply.author.name)
        )
        process_done(
            parents_parent, r, tor, redis_server, Context, override=True
        )