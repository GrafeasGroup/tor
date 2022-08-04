import logging
import random
from typing import Optional

from blossom_wrapper import BlossomStatus
from praw.models import Comment, Redditor, Submission

from tor import __BOT_NAMES__
from tor.core.config import Config
from tor.core.helpers import clean_id, flair, send_to_modchat
from tor.strings import translation

log = logging.getLogger(__name__)
i18n = translation()

FLAIR_DATA = {
    20000: {"class": "grafeas-sapphire", "name": "Sapphire"},
    10000: {"class": "grafeas-jade", "name": "Jade"},
    5000: {"class": "grafeas-topaz", "name": "Topaz"},
    2500: {"class": "grafeas-ruby", "name": "Ruby"},
    1000: {"class": "grafeas-diamond", "name": "Diamond"},
    500: {"class": "grafeas-golden", "name": "Golden"},
    250: {"class": "grafeas-purple", "name": "Purple"},
    100: {"class": "grafeas-teal", "name": "Teal"},
    50: {"class": "grafeas-green", "name": "Green"},
    25: {"class": "grafeas-pink", "name": "Pink"},
    1: {"class": "grafeas", "name": "Initiate"},
}


def flair_post(post: Submission, flair_id: Optional[str]) -> None:
    """
    Sets the requested flair on a given post.

    :param post: A Submission object on ToR.
    :param flair_id: String. The ID of the flair template to apply.
    You can use the flair class to select the flair ID.
    :return: None.
    """
    if not flair_id:
        log.error(
            "Trying to flair post without providing a flair ID. "
            "Did you set the .env variables?"
        )
        return

    post.flair.select(flair_template_id=flair_id)


def _get_flair_css(transcription_count: int) -> str:
    keys = list(FLAIR_DATA.keys())
    keys.sort()  # arrange from smallest to largest
    keys.reverse()  # rearrange from largest to smallest
    # The only time we interact with this function should be with a positive
    # value for the count, but a little extra validation never hurt.
    if transcription_count < 1:
        transcription_count = 1
    return [FLAIR_DATA[i]["class"] for i in keys if i <= transcription_count][0]


def check_promotion(count):
    return True if count in FLAIR_DATA.keys() else False


def generate_promotion_message(count: int) -> str:
    keys = list(FLAIR_DATA.keys())
    keys.sort()
    text = i18n["responses"]["done"]["promotion_text"]
    rank = [FLAIR_DATA[r].get("name") for r in keys if r == count][0]
    exclamation = random.choice(text["exclamations"])

    new_rank = (
        text["new_rank"].format(rank=rank)
        if rank and count != 1  # if the user is a newbie, show different message
        else text["first_rank"]
    )

    try:
        next_rank_obj = [FLAIR_DATA[r] for r in keys if r > count][0]
        next_rank = text["next_rank"].format(
            intro=random.choice(text["next_rank_intros"]),
            rank=next_rank_obj["name"],
            count=[k for k, v in FLAIR_DATA.items() if v == next_rank_obj][0],
        )
    except IndexError:
        next_rank = text["highest_rank"]

    return f"{exclamation} {new_rank} {next_rank}"


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
                flair_postfix = current_flair[current_flair.index("Γ") + 1 :]
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

    new_last_time = cfg.last_set_meta_flair_time
    for post in cfg.tor.new(limit=10):
        if str(post.author) in __BOT_NAMES__:
            continue
        if str(post.author) in cfg.tor_mods:
            continue
        if post.link_flair_template_id == flair.meta:
            continue

        # Skip this post if it older than the last post we processed
        if post.created_utc < cfg.last_set_meta_flair_time:
            continue

        new_last_time = max(new_last_time, post.created_utc)
        log.info(f"Flairing post {post.fullname} by author {post.author} with Meta.")
        flair_post(post, flair.meta)
        send_to_modchat(f"New meta post: <{post.shortlink}|{post.title}>", cfg)

    cfg.last_set_meta_flair_time = new_last_time
