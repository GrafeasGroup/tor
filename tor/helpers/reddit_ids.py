import logging

def clean_id(post_id):
    """
    Fixes the Reddit ID so that it can be used to get a new object.

    By default, the Reddit ID is prefixed with something like `t1_` or
    `t3_`, but this doesn't always work for getting a new object. This
    method removes those prefixes and returns the rest.

    :param post_id: String. Post fullname (ID)
    :return: String. Post fullname minus the first three characters.
    """
    return post_id[post_id.index('_') + 1:]


def get_parent_post_id(post, r):
    """
    Takes any given comment object and returns the object of the
    original post, no matter how far up the chain it is. This is
    a very time-intensive function because of how Reddit handles
    rate limiting and the fact that you can't just request the
    top parent -- you have to just loop your way to the top.

    :param post: comment object
    :param r: the instantiated reddit object
    :return: submission object of the top post.
    """
    while True:
        if not post.is_root:
            post = r.comment(id=clean_id(post.parent_id))
        else:
            return r.submission(id=clean_id(post.parent_id))


def add_complete_post_id(post_id, redis_server):
    """
    Adds the post id to the complete_post_ids set in Redis. This is used
    to make sure that we didn't break halfway through working on this post.

    NOTE: This does not keep track of *transcribed* posts. This is only
    used to track the actual posting process, from grabbing new posts
    to actually creating the post with the "Unclaimed" tag.

    :param post_id: string. The comment / post ID.
    :param redis_server: The active Redis instance.
    :return: None.
    """
    redis_server.sadd('complete_post_ids', post_id)


def is_valid(post_id, redis_server):
    """
    Returns true or false based on whether the parent id is in a set of IDs.
    It determines this by attempting to insert the value into the DB and
    returning the result. If the result is already in the set, we check the
    completed id set as well to make sure that it's actually been done. If
    it's in the post_ids set and *not* the complete_post_ids set, we assume
    something went horribly wrong and we try again.

    :param post_id: string. The comment / post ID.
    :param redis_server: The active Redis instance.
    :return: True if the ID is successfully inserted into the set; False if
        it's already there.
    """
    result = redis_server.sadd('post_ids', post_id)

    if result == 1:
        # the post id was submitted successfully and it's good to work on.
        return True

    else:
        # The post is already in post_ids, which is triggered when we start
        # the process. Let's see if we ever completed it.
        member = redis_server.sismember('complete_post_ids', post_id)
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