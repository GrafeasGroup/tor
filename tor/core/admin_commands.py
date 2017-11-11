import csv
import logging
import random

from praw.exceptions import ClientException as RedditClientException
# noinspection PyProtectedMember
from tor_core.helpers import _
from tor_core.helpers import clean_id
from tor_core.initialize import initialize

from tor.core.user_interaction import process_done

no_mod_replies = ['ha nope \n\n{}', 'l0l no \n\n{}', '{}', 'nada \n\n{}']


def process_command(reply, config):
    """
    This function processes any commands send to the bot via PM with a subject
    that stars with a !. The basic flow is read CSV file, look for row with same
    subject, check if it needs mod, and check for mod, and then reply to the
    PM with the results of the function listed in the CSV file.

    To add a new command: add an entry to commands.csv, (look at the top line
    for row names) add your function to command_funcs, and add your function.
    :param reply:
    :param config:
    :return:
    """
    with open('commands.csv', newline='') as commands_file:
        command_reader = csv.reader(commands_file)
        for row in command_reader:
            # this code also iterates over the headers, but it doesn't really
            # matter

            logging.info(
                f'Searching for command {reply.subject[1:]}, '
                f'from {reply.author}.'
            )

            # command name, needs mod, function name
            if reply.subject[1:] == row[0]:
                # command found
                logging.info(
                    f'{reply.author} is attempting to run {reply.subject[1:]}'
                )
                # does it need mod privileges?
                if row[1] == 'true':
                    if not from_moderator(reply, config):
                        logging.info(
                            f"{reply.author} failed to run {reply.subject[1:]},"
                            f" because they aren't a mod"
                        )
                        reply.reply(
                            random.choice(no_mod_replies).format(
                                random.choice(config.no_gifs)
                            )
                        )

                        return

                logging.info(
                    f'Now executing command {reply.subject[1:]},'
                    f' by {reply.author}.'
                )

                try:
                    reply.reply(
                        command_funcs[row[2]](reply.body, config)
                    )
                except KeyError:
                    reply.reply(
                        "Command function not found, please message a developer"
                    )

                    logging.error(
                        "Did someone forget to add a function to command_funcs?"
                    )

                    return

            else:
                reply.reply(
                    "That command hasn't been implemented yet ):"
                    "\n\nMessage a dev to make your dream come true."
                )


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
                parents_parent.fullname,
                reply.author.name
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

    usernames = reply.body.splitlines()
    results = ""
    failed = []
    successes = []
    already_added = []

    for username in usernames:
        if username in config.tor_mods:
            results += f"{username} is a mod! Don't blacklist mods!\n"
            failed.append(username)
            continue

        try:
            config.r.redditor(username)
        except RedditClientException:
            results += f"{username} isn't a valid user\n"
            failed.append(username)
            continue

        already_added = config.redis.sadd('blacklist', username)
        if already_added == 0:
            results += f"{username} is already blacklisted, ya fool!\n"
            already_added.append(username)
            continue

        results += f"{username} is now blacklisted\n"
        successes.append(username)

        reply.reply(results)

        logging.info(
            "Blacklist: {failed} failed, {success} succeeded, {ignored} were "
            "already blacklisted".format(
                failed=repr(failed),
                success=repr(successes),
                ignored=repr(already_added)
            )
        )


def reload_config(reply, config):
    logging.info(
        'Reloading configs at the request of {}'.format(reply.author.name)
    )
    initialize(config)
    logging.info('Reload complete.')

    return 'Config reloaded!'


def update_and_restart(reply, config):
    return "This doesn't work quite yet"
    # TODO: This does not currently function on our primary box.
    # # update from repo
    # sh.git.pull("origin", "master")
    # # restart own process
    # os.execl(sys.executable, sys.executable, *sys.argv)


def ping(reply, config):
    return "Pongity ping pong pong!"


# Don't forget to add to this!
command_funcs = {
    'process_override': process_override,
    'reload_config': reload_config,
    'update_and_restart': update_and_restart,
    'ping': ping,
    'blacklist': "Not implemented yet"
}
