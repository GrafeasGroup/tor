import logging
import random

from praw.exceptions import ClientException as RedditClientException
# noinspection PyProtectedMember
from tor_core.helpers import _
from tor_core.helpers import clean_id
from tor_core.initialize import initialize

from tor.core.user_interaction import process_done


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
            ', approved by {}'.format(
                parents_parent.fullname, reply.author.name
            )
        )
        process_done(
            parents_parent, config, override=True
        )


def process_blacklist(reply, config):
    """
    This is used to basically "shadow-ban" people from the bot.
    Format is:
    Subject: !blacklist
    body: <username1>\n<username2>...
    :param reply: the comment reply object from the inbox
    :param config: the global config object
    :return: None
    """

    if not from_moderator(reply, config):
        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            '{} just tried to blacklist. Get your own bot!'
            ''.format(reply.author.name)
        )
        return

    usernames = reply.body.split('\n')
    results = ""
    results_for_log = {'failed': [], 'successes': []}

    for username in usernames:
        if username in config.tor_mods:
            results += f"{username} is a mod! Don't blacklist mods!\n"
            results_for_log['failed'].append(username)
            continue

        try:
            config.r.redditor(username)
        except RedditClientException:
            results += "{} isn't a valid user\n"
            results_for_log['failed'].append(username)
            continue

        config.redis.sadd('blacklist', username)
        results += "{} is now blacklisted (or already was :O)" \
            .format(username)
        results_for_log['successes'].append(username)

        reply.reply(results)

        logging.info(
            "{} failed to blacklist, {} were successfully blacklisted".format(
                ', '.join(results_for_log['failed']),
                ', '.join(results_for_log['successes'])
            )
        )


def reload_config(reply, config):
    if not from_moderator(reply, config):
        logging.info(
            '{} just issued a reload command. No.'.format(reply.author.name)
        )

        reply.reply(_(random.choice(config.no_gifs)))
    else:
        logging.info(
            'Reloading configs at the request of {}'.format(reply.author.name)
        )
        reply.reply(
            'Config reloaded!'
        )
        initialize(config)
        logging.info('Reload complete.')


def update_and_restart(reply, config):
    if not from_moderator(reply, config):

        reply.reply(_(random.choice(config.no_gifs)))
        logging.info(
            '{} just issued update. No.'.format(reply.author.name)
        )
    else:
        pass
        # TODO: This does not currently function on our primary box.
        # # update from repo
        # sh.git.pull("origin", "master")
        # # restart own process
        # os.execl(sys.executable, sys.executable, *sys.argv)
