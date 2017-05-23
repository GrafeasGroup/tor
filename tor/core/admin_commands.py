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


def process_override(reply, r, tor, config):
    """
    This process is for moderators of ToR to force u/transcribersofreddit
    to mark a post as complete and award flair when the bot refutes a
    `done` claim. The comment containing "!override" must be in response to
    the bot's comment saying that it cannot find the transcript.

    :param reply: the comment reply object from the moderator.
    :param r: the active Reddit instance.
    :param tor: the TranscribersOfReddit subreddit object.
    :param config: the global config object.
    :return: None.
    """
    # first we verify that this comment comes from a moderator and that
    # we can work on it.
    if not from_moderator(reply, config):
        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            f'{reply.author.name} just tried to override. Lolno.'
        )
        return
    # okay, so the parent of the reply should be the bot's comment
    # saying it can't find it. In that case, we need the parent's
    # parent. That should be the comment with the `done` call in it.
    reply_parent = r.comment(id=clean_id(reply.parent_id))
    parents_parent = r.comment(id=clean_id(reply_parent.parent_id))
    if 'done' in parents_parent.body.lower():
        logging.info(
            f'Starting validation override for post {parents_parent.fullname}'
            f', approved by {reply.author.name}'
        )
        process_done(
            parents_parent, r, tor, config, override=True
        )


def reload_config(reply, tor, config):
    if not from_moderator(reply, config):
        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            f'{reply.author.name} just issued a reload command. No.'
        )
    else:
        logging.info(
            f'Reloading configs at the request of {reply.author.name}'
        )
        initialize(tor, config)
        logging.info('Reload complete.')


def update_and_restart(reply, config):
    if not from_moderator(reply, config):
        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            f'{reply.author.name} just issued update. No.'
        )
    else:
        # update from repo
        sh.git.pull("origin", "master")
        # restart own process
        os.execl(sys.executable, sys.executable, *sys.argv)
