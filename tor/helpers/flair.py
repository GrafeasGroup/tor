import logging

from addict import Dict

from tor.helpers.reddit_ids import clean_id

flair = Dict()
flair.unclaimed = 'Unclaimed'
flair.summoned_unclaimed = 'Summoned - Unclaimed'
flair.completed = 'Completed!'
flair.in_progress = 'In Progress'
flair.meta = 'Meta'
flair.disregard = 'Disregard'

css_flair = Dict()
css_flair.unclaimed = 'unclaimed'
css_flair.completed = 'transcriptioncomplete'
css_flair.in_progress = 'inprogress'
css_flair.meta = 'meta'
css_flair.disregard = 'disregard'


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
    :param tor: A shortcut for the Subreddit object for ToR.
    :param reddit: Active Reddit instance.
    :return: None.
    """
    flair_text = '0 Γ - Beta Tester'

    try:
        # The post object is technically an inbox mention, even though it's
        # a Comment object. In order to get the flair, we have to take the
        # ID of our post object and re-request it from Reddit in order to
        # get the *actual* object, even though they have the same ID. It's
        # weird.
        user_flair = config.r.comment(id=clean_id(post.fullname)).author_flair_text
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
