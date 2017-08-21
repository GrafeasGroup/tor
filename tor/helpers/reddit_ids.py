import logging


def add_complete_post_id(post_id, config):
    """
    Adds the post id to the complete_post_ids set in Redis. This is used
    to make sure that we didn't break halfway through working on this post.

    NOTE: This does not keep track of *transcribed* posts. This is only
    used to track the actual posting process, from grabbing new posts
    to actually creating the post with the "Unclaimed" tag.

    :param post_id: string. The comment / post ID.
    :param config: the global config dict.
    :return: None.
    """
    config.redis.sadd('complete_post_ids', post_id)


def is_valid(post_id, config):
    """
    Returns true or false based on whether the parent id is in a set of IDs.
    It determines this by attempting to insert the value into the DB and
    returning the result. If the result is already in the set, we check the
    completed id set as well to make sure that it's actually been done. If
    it's in the post_ids set and *not* the complete_post_ids set, we assume
    something went horribly wrong and we try again.

    :param post_id: string. The comment / post ID.
    :param config: the global config object.
    :return: True if the ID is successfully inserted into the set; False if
        it's already there.
    """
    result = config.redis.sadd('post_ids', post_id)

    if result == 1:
        # the post id was submitted successfully and it's good to work on.
        return True

    else:
        # The post is already in post_ids, which is triggered when we start
        # the process. Let's see if we ever completed it.
        member = config.redis.sismember('complete_post_ids', post_id)
        if member != 1:
            # It's in post_ids, which means we started it, but it's not
            # in complete_post_ids, which means we never finished it for
            # some reason. Let's try it again.
            logging.warning('Incomplete post found! ID: {}'.format(post_id))
            return True

        else:
            # it *is* in complete_post_ids, which means we've already
            # worked on it. Therefore, the post generally is not valid
            # to work on because it's already been successfully completed.
            return False
