import logging

from tor.core.helpers import _
from tor.strings import translation


def process_mention(mention):
    """
    Handles username mentions and handles the formatting and posting of
    those calls as workable jobs to ToR.

    :param mention: the Comment object containing the username mention.
    :return: None.
    """
    i18n = translation()
    pm_subject = i18n['responses']['direct_message']['subject']
    pm_body = i18n['responses']['direct_message']['body']

    # message format is subject, then body
    mention.author.message(pm_subject, _(pm_body))
    logging.info(f'Message sent to {mention.author.name}!')
