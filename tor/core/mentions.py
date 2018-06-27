import logging

from tor.strings.responses import pm_body
from tor.strings.responses import pm_subject

# noinspection PyProtectedMember
from tor_core.helpers import _


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
