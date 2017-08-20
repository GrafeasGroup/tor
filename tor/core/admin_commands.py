import logging

import sh

import random
import os
import sys
from tor.helpers.reddit_ids import clean_id
from tor.helpers.misc import _
from tor.core.user_interaction import process_done
from tor.core.initialize import initialize


def from_moderator(reply, config):
    return reply.author in config.tor_mods


def process_override(reply, config):
    """
    This process is for moderators of ToR to force u/transcribersofreddit
    to mark a post as complete and award flair when the bot refutes a
    `done` claim. The comment containing "!override" must be in response to
    the bot's comment saying that it cannot find the transcript.

    :param reply: the comment reply object from the moderator.
    :param config: the global config object.
    :return: None.
    """
    # first we verify that this comment comes from a moderator and that
    # we can work on it.
    if not from_moderator(reply, config):
        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            '{} just tried to override. Lolno.'.format(reply.author.name)
        )
        return
    # okay, so the parent of the reply should be the bot's comment
    # saying it can't find it. In that case, we need the parent's
    # parent. That should be the comment with the `done` call in it.
    reply_parent = config.r.comment(id=clean_id(reply.parent_id))
    parents_parent = config.r.comment(id=clean_id(reply_parent.parent_id))
    if 'done' in parents_parent.body.lower():
        logging.info(
            'Starting validation override for post {}'
            ', approved by {}'.format(parents_parent.fullname, reply.author.name)
        )
        process_done(
            parents_parent, config, override=True
        )


def reload_config(reply, config):
    if not from_moderator(reply, config):
        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            '{} just issued a reload command. No.'.format(reply.author.name)
        )
    else:
        logging.info(
            'Reloading configs at the request of {}'.format(reply.author.name)
        )
        initialize(config.tor, config)
        logging.info('Reload complete.')


def update_and_restart(reply, config):
    if not from_moderator(reply, config):

        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            '{} just issued update. No.'.format(reply.author.name)
        )
    else:
        # update from repo
        sh.git.pull("origin", "master")
        # restart own process
        os.execl(sys.executable, sys.executable, *sys.argv)
