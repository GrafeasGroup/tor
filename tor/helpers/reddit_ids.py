from blossom_wrapper import BlossomStatus
from praw.models import Submission  # type: ignore

from tor.core.config import Config


def has_been_posted(post_url: str, cfg: Config) -> bool:
    return cfg.blossom.get_submission(post_url).status == BlossomStatus.ok


def is_removed(post: Submission) -> bool:
    """
    Reddit does not allow non-mods to tell whether or not a post has been
    removed, which understandably makes it a little difficult to figure out
    whether or not we should remove a post automatically. HOWEVER, as with
    pretty much everything else that Reddit does, they left enough detritus
    that we guess with a relatively high degree of accuracy.

    We can use a combination of checking to see if something is gildable or
    crosspostable (and its current content, if a selfpost) to identify its
    current state:

    flag                    can_gild    is_crosspostable    selftext
    removed                 Y           N                   ""
    dead user               N           Y                   ""
    removed + dead user     N           N                   ""
    deleted post            N           N                   [deleted]

    More information (and where this table is from): https://redd.it/7hfnew

    Because we don't necessarily need to remove a post in certain situations
    (e.g. the user account has been deleted), we can simplify the check. By
    setting `full_check`, we can return True for any issue.
    :param post: The post that we are attempting to investigate.
    :return: True is the post looks like it has been removed, False otherwise.
    """
    return not post.is_crosspostable
