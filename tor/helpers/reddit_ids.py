from praw.models import Submission

from tor.core.config import Config


def add_complete_post_id(
    post_id: str, config: Config, return_result: bool = False
) -> [None, bool]:
    """
    Adds the post id to the complete_post_ids set in Redis. This is used to keep
    track of which posts we've worked on and which ones we haven't.

    NOTE: This does not keep track of *transcribed* posts. This is only
    used to track the actual posting process, from grabbing new posts
    to actually creating the post with the "Unclaimed" tag.

    :param post_id: string. The comment / post ID.
    :param config: the global config dict.
    :param return_result: Do we want to get the result back? Most of the time
        we don't care.
    """
    result = config.redis.sadd("complete_post_ids", post_id)
    if return_result:
        return True if result == 1 else False


def is_valid(post_id: str, config: Config) -> bool:
    """
    Returns true or false based on whether the parent id is in a set of IDs.
    It determines this by attempting to insert the value into the DB and
    returning the result. If the result is already in the set, return False,
    since we know we've already worked on that post. If we successfully
    inserted it, then return True so we can process it.

    :param post_id: string. The comment / post ID.
    :param config: the global config object.
    :return: True if the ID is successfully inserted into the set; False if
        it's already there.
    """

    # if we get back a True, then we return True because the post was submitted
    # successfully and it's good to work on. If the insert fails, then we
    # want to return a False because we cannot work on that post again.
    return add_complete_post_id(post_id, config, return_result=True)


def is_removed(post: Submission, full_check: bool = False) -> bool:
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

    if full_check:
        return False if post.is_crosspostable and post.can_gild else True
    else:
        return not post.is_crosspostable
