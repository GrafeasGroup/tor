import logging

from blossom_wrapper import BlossomStatus
from praw.models import Comment, Redditor, Submission  # type: ignore

from tor import __BOT_NAMES__
from tor.core.config import Config
from tor.core.helpers import clean_id, flair, send_to_modchat

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


def set_user_flair(user: Redditor, post: Comment, cfg: Config) -> None:
    """
    Set the flair from the comment's author according to their gamma and current flair

    This function uses Blossom to retrieve the up to date gamma. The current
    flair postfix is left intact in the process.
    """
    flair_postfix = ""
    gamma = 0
    user_response = cfg.blossom.get_user(username=user.name)
    if user_response.status == BlossomStatus.ok:
        gamma = user_response.data["gamma"]
        try:
            # Retrieve the possible custom postfix from the user's current flair.
            # Since there is no way to do this nicely, retrieve this flair from
            # the posted comment.
            current_flair = cfg.r.comment(id=clean_id(post.fullname)).author_flair_text
            if current_flair:
                flair_postfix = current_flair[current_flair.index("<CE><93>") + 1:]
        except (StopIteration, AttributeError, ValueError):
            # In this situation, either the user is not found or they do not have a flair.
            # This is not problematic and we will instead just use the standard flair.
            pass
    user_flair = f"{gamma} Γ{flair_postfix}"
    flair_css = _get_flair_css(gamma)
    cfg.tor.flair.set(user.name, text=user_flair, css_class=flair_css)


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
