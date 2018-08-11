def add_complete_post_id(
    post_id: int, config, return_result: bool = False
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


def is_valid(post_id, config):
    """
    Returns true or false based on whether the parent id is in a set of IDs.
    It determines this by attempting to insert the value into the DB and
    returning the result. If the result is already in the set, return False,
    since we know we've already worked on that post. If we successfully inserted
    it, then return True so we can process it.

    :param post_id: string. The comment / post ID.
    :param config: the global config object.
    :return: True if the ID is successfully inserted into the set; False if
        it's already there.
    """

    # if we get back a True, then we return True because the post was submitted
    # successfully and it's good to work on. If the insert fails, then we
    # want to return a False because we cannot work on that post again.
    return add_complete_post_id(post_id, config, return_result=True)
