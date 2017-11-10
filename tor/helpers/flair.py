import logging

from tor_core.helpers import clean_id
from tor_core.helpers import flair


def flair_post(post, text):
    """
    Sets the requested flair on a given post. Must provide a string
    which matches an already-available flair template.

    :param post: A Submission object on ToR.
    :param text: String. The name of the flair template to apply.
    :return: None.
    """
    # Flair looks like this:
    # {
    #   'flair_css_class': 'unclaimed-flair',
    #   'flair_template_id': 'fe9d6950-142a-11e7-901e-0ecc947f9ff4',
    #   'flair_text_editable': False,
    #   'flair_position': 'left',
    #   'flair_text': 'Unclaimed'
    # }
    for choice in post.flair.choices():
        if choice['flair_text'] == text:
            post.flair.select(
                flair_template_id=choice['flair_template_id']
            )
            return

    # if the flairing is successful, we won't hit this line.
    logging.error(
        'Cannot find requested flair {}. Not flairing.'.format(text)
    )


def update_user_flair(post, config):
    """
    On a successful transcription, this takes the user's current flair,
    increments the counter by one, and stores it back to the subreddit.

    :param post: The post which holds the author information.
    :param config: The global config instance.
    :return: None.
    """
    flair_text = '0 Γ - Beta Tester'

    try:
        # The post object is technically an inbox mention, even though it's
        # a Comment object. In order to get the flair, we have to take the
        # ID of our post object and re-request it from Reddit in order to
        # get the *actual* object, even though they have the same ID. It's
        # weird.
        user_flair = config.r.comment(
            id=clean_id(post.fullname)
        ).author_flair_text
    except AttributeError:
        user_flair = flair_text

    if user_flair is None:
        user_flair = flair_text

    if 'Γ' in user_flair:
        # take their current flair and add one to it
        new_flair_count = int(user_flair[:user_flair.index('Γ') - 1])
        # if there's anything special in their flair string, let's save it
        additional_flair_text = user_flair[user_flair.index('Γ') + 1:]
        user_flair = '{} Γ'.format(new_flair_count + 1)
        # add in that special flair bit back in to keep their flair intact
        user_flair += additional_flair_text
        config.tor.flair.set(post.author, text=user_flair, css_class='grafeas')
        logging.info('Setting flair for {}'.format(post.author))
    else:
        # they're bot or a mod and have custom flair. Leave it alone.
        return


def set_meta_flair_on_other_posts(config):
    """
    Loops through the 10 newest posts on ToR and sets the flair to
    'Meta' for any post that is not authored by the bot or any of
    the moderators.

    :param config: the active config object.
    :return: None.
    """
    for post in config.tor.new(limit=10):

        if (
            post.author != config.r.redditor('transcribersofreddit') and
            post.author not in config.tor_mods and
            post.link_flair_text != flair.meta
        ):
            logging.info(
                'Flairing post {} by author {} with Meta.'.format(
                    post.fullname, post.author
                )
            )
            flair_post(post, flair.meta)
