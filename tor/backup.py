import os
import logging

from tor.core.users import User
from tor.helpers.flair import _parse_existing_flair
from tor.core.config import config  # type: ignore
from tor.core.initialize import build_bot  # type: ignore

from tor import __version__


def run(cfg):
    for flair_obj in config.tor.flair(limit=None):
        username = str(flair_obj['user'])
        logging.info(f'Backing up transcription count for {username}')
        u = User(username, redis_conn=config.redis)
        count, flair_css = _parse_existing_flair(flair_obj['flair_text'])
        u.update('transcriptions', count)
        u.save()


def main():
    config.debug_mode = bool(os.environ.get('DEBUG_MODE', False))

    if config.debug_mode:
        bot_name = 'debug'
    else:
        bot_name = os.environ.get('BOT_NAME', 'bot')

    build_bot(bot_name, __version__, full_name='u/ToR')
    config.perform_header_check = True
    run(config)


if __name__ == '__main__':
    main()
