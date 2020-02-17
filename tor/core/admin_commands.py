import json
import logging
import random

from praw.exceptions import ClientException as RedditClientException
from tor.core.helpers import _, clean_id, send_to_modchat
from tor.core.initialize import initialize
from tor.core.user_interaction import process_done


def process_command(reply, cfg):
    """
    This function processes any commands send to the bot via PM with a subject
    that stars with a !. The basic flow is read JSON file, look for key with
    same subject, check if the caller is mod, or is in the list of allowed
    people, then reply with the results of pythonFunction.

    To add a new command: add an entry to commands.json, (look at the other
    commands already listed), and add your function to admin_commands.py.

    :param reply: Object, the message object that contains the requested
        command
    :param cfg: the global config object
    :return: None
    """

    # Trim off the ! from the start of the string
    requested_command = reply.subject[1:]

    with open('commands.json', newline='') as commands_file:
        commands = json.load(commands_file)
        logging.debug(
            f'Searching for command {requested_command}, '
            f'from {reply.author.name}.'
        )

        try:
            command = commands['commands'][requested_command]

        except KeyError:
            if from_moderator(reply, cfg):
                reply.reply(
                    "That command hasn't been implemented yet ):"
                    "\n\nMessage a dev to make your dream come true."
                )

            logging.warning(
                f"Error, command: {requested_command} not found!"
                f" (from {reply.author.name})"
            )

            return

        # command found
        logging.info(
            f'{reply.author.name} is attempting to run {requested_command}'
        )

        # Mods are allowed to do any command, and some people are whitelisted
        # per command to be able to use them
        if (
            reply.author.name not in command['allowedNames'] and
            not from_moderator(reply, cfg)
        ):
            logging.info(
                f"{reply.author.name} failed to run {requested_command},"
                f"because they aren't a mod, or aren't whitelisted to use this"
                f" command"
            )
            username = reply.author.name
            send_to_modchat(
                f":banhammer: Someone did something bad! "
                f"<https://reddit.com/user/{username}|u/{username}> tried to "
                f"run {requested_command}!", cfg
            )

            reply.reply(
                random.choice(commands['notAuthorizedResponses']).format(
                    random.choice(cfg.no_gifs)
                )
            )

            return

        logging.debug(
            f'Now executing command {requested_command},'
            f' by {reply.author.name}.'
        )

        result = globals()[command['pythonFunction']](reply, cfg)

        if result is not None:
            reply.reply(result)


def from_moderator(reply, cfg):
    return reply.author in cfg.tor_mods


def process_override(reply, cfg):
    """
    This process is for moderators of ToR to force u/transcribersofreddit
    to mark a post as complete and award flair when the bot refutes a
    `done` claim. The comment containing "!override" must be in response to
    the bot's comment saying that it cannot find the transcript.

    :param reply: the comment reply object from the moderator.
    :param cfg: the global config object.
    :return: None.
    """

    # don't remove this check, it's not covered like other admin_commands
    # because it's used in reply to people, not as a PM
    if not from_moderator(reply, cfg):
        reply.reply(_(random.choice(cfg.no_gifs)))
        logging.info(
            f'{reply.author.name} just tried to override. Lolno.'
        )

        return

    # okay, so the parent of the reply should be the bot's comment
    # saying it can't find it. In that case, we need the parent's
    # parent. That should be the comment with the `done` call in it.
    reply_parent = cfg.r.comment(id=clean_id(reply.parent_id))
    parents_parent = cfg.r.comment(id=clean_id(reply_parent.parent_id))
    if 'done' in parents_parent.body.lower():
        logging.info(
            f'Starting validation override for post {parents_parent.fullname}, '
            f'approved by {reply.author.name}'
        )
        process_done(
            parents_parent, cfg, override=True
        )


def reload_config(reply, cfg):
    logging.info(
        f'Reloading configs at the request of {reply.author.name}'
    )
    initialize(cfg)
    logging.info('Reload complete.')

    return 'Config reloaded!'


def ping(reply, cfg):
    """
    Replies to the !ping command, and is used as a keep alive check
    :param reply: Not used, but it is here due to the way the function is called
    :param cfg: See reply param
    :return: The ping string, which in turn is given to Reddit's reply.reply()
    """
    logging.info(
        f'Received ping from {reply.author.name}. Pong!'
    )
    return "Pong!"
