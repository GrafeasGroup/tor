import logging

import tor.strings
from tor.core.helpers import _

text = tor.strings.translation(lang='en_US')
pm_body = text['responses']['direct_message']['body'].strip()
pm_subject = text['responses']['direct_message']['subject'].strip()


def process_mention(mention):
    """
    Handles username mentions and handles the formatting and posting of
    those calls as workable jobs to ToR.

    :param mention: the Comment object containing the username mention.
    :return: None.
    """

    # message format is subject, then body
    mention.author.message(pm_subject, _(pm_body))
    logging.info(f"Message sent to {mention.author.name}!")
