import logging
from typing import Tuple

from praw.models import Comment, Submission  # type: ignore

from tor import __BOT_NAMES__
from tor.core.config import Config
from tor.core.helpers import clean_id, flair, send_to_modchat
from tor.core.users import User

log = logging.getLogger(__name__)


def flair_post(post: Submission, text: str) -> None:
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
    log.error(f'Cannot find requested flair {text}. Not flairing.')


def _get_flair_css(transcription_count: int) -> str:
    if transcription_count >= 10000:
        return 'grafeas-jade'
    elif transcription_count >= 5000:
        return 'grafeas-topaz'
    elif transcription_count >= 2500:
        return 'grafeas-ruby'
    elif transcription_count >= 1000:
        return 'grafeas-diamond'
    elif transcription_count >= 500:
        return 'grafeas-golden'
    elif transcription_count >= 250:
        return 'grafeas-purple'
    elif transcription_count >= 100:
        return 'grafeas-teal'
    elif transcription_count >= 50:
        return 'grafeas-green'
    else:
        return 'grafeas'


def _parse_existing_flair(user_flair: str) -> Tuple[int, str]:
    """
    Take the flair string and identify the proper incremented score along with
    its matching CSS class.

    :param user_flair: String; the existing flair string for the user.
    :return:
    """

    # extract their current flair and add one to it
    new_flair_count = int(user_flair[:user_flair.index('Γ') - 1]) + 1

    css = _get_flair_css(new_flair_count)

    return new_flair_count, css


def update_user_flair(post: Comment, cfg: Config) -> None:
    """
    On a successful transcription, this takes the user's current flair,
    increments the counter by one, and stores it back to the subreddit.

    If the user is past 50 transcriptions, select the appropriate flair
    class and write that back too.

    :param post: The post which holds the author information.
    :param cfg: The global config instance.
    :return: None.
    """
    flair_text = '{} Γ - Beta Tester'

    post_author = User(str(post.author), redis_conn=cfg.redis)
    current_transcription_count = post_author.get('transcriptions', 0)

    try:
        # The post object is technically an inbox mention, even though it's
        # a Comment object. In order to get the flair, we have to take the
        # ID of our post object and re-request it from Reddit in order to
        # get the *actual* object, even though they have the same ID. It's
        # weird.
        user_flair = cfg.r.comment(id=clean_id(post.fullname)).author_flair_text
    except AttributeError:
        user_flair = flair_text.format('0')

    if not user_flair:
        # HOLD ON. Do we have one saved? Maybe Reddit's screwing up.
        if current_transcription_count != 0:
            # we have a user object for them and shouldn't have landed here.
            user_flair = flair_text.format(current_transcription_count)
        else:
            user_flair = flair_text.format('0')

    if 'Γ' in user_flair:
        new_count, flair_css = _parse_existing_flair(user_flair)

        # if there's anything special in their flair string, let's save it
        additional_flair_text = user_flair[user_flair.index('Γ') + 1:]
        user_flair = f'{new_count} Γ'
        # add in that special flair bit back in to keep their flair intact
        user_flair += additional_flair_text

        cfg.tor.flair.set(post.author, text=user_flair, css_class=flair_css)
        log.info(f'Setting flair for {post.author}')

        post_author.update('transcriptions', current_transcription_count + 1)
        post_author.save()


def set_meta_flair_on_other_posts(cfg: Config) -> None:
    """
    Loops through the 10 newest posts on ToR and sets the flair to
    'Meta' for any post that is not authored by the bot or any of
    the moderators.

    :param cfg: the active config object.
    :return: None.
    """
    for post in cfg.tor.new(limit=10):
        if str(post.author) in __BOT_NAMES__:
            continue
        if str(post.author) in cfg.tor_mods:
            continue
        if post.link_flair_text == flair.meta:
            continue

        log.info(f'Flairing post {post.fullname} by author {post.author} with Meta.')
        flair_post(post, flair.meta)
        send_to_modchat(
            f'New meta post: <{post.shortlink}|{post.title}>',
            cfg
        )
