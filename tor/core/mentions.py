import logging

from praw.exceptions import ClientException as RedditClientException

from tor.core.helpers import _
from tor.strings import translation


def process_mention(mention):
    """
    Handles username mentions and handles the formatting and posting of
    those calls as workable jobs to ToR.

    :param mention: the Comment object containing the username mention.
    :return: None.
    """
    try:
        i18n = translation()
        pm_subject = i18n['responses']['direct_message']['subject']
        pm_body = i18n['responses']['direct_message']['body']

        # message format is subject, then body
        mention.author.message(pm_subject, _(pm_body))
        logging.info(f'Message sent to {mention.author.name}!')
    except (RedditClientException, AttributeError):
        # apparently this crashes with an AttributeError if someone
        # calls the bot and immediately deletes their comment. This
        # should fix that.
        pass
