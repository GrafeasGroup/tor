import logging

import prawcore


def get_wiki_page(pagename, tor, return_on_fail=None):
    """
    Return the contents of a given wiki page.

    :param pagename: String. The name of the page to be requested.
    :param tor: Active ToR instance.
    :param return_on_fail: Any value to return when nothing is found
        at the requested page. This allows us to specify returns for
        easier work in debug mode.
    :return: String or None. The content of the requested page if
        present else None.
    """
    logging.debug(f'Retrieving wiki page {pagename}')
    try:
        result = tor.wiki[pagename].content_md
        return result if result != '' else return_on_fail
    except prawcore.exceptions.NotFound:
        return return_on_fail


def update_wiki_page(pagename, content, tor):
    """
    Sends new content to the requested wiki page.

    :param pagename: String. The name of the page to be edited.
    :param content: String. New content for the wiki page.
    :param tor: Active ToR instance.
    :return: None.
    """
    logging.debug(f'Updating wiki page {pagename}')
    try:
        return tor.wiki[pagename].edit(content)
    except prawcore.exceptions.NotFound as e:
        logging.error(
            f'{e} - Requested wiki page {pagename} not found. '
            f'Cannot update.', exc_info=1
        )
