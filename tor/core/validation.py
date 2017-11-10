from tor.strings.urls import ToR_link
from tor_core.helpers import get_parent_post_id


def _author_check(original_post, claimant_post):
    return original_post.author == claimant_post.author


def _header_check(reply, config, tor_link=ToR_link):
    if config.perform_header_check:
        return tor_link in reply.body
    else:
        # If we don't want the check to take place, we'll just return
        # true to negate it.
        return True


def _author_history_check(post, config):
    for doohickey in post.author.new(limit=3):
        if _header_check(doohickey, config):
            pass


def verified_posted_transcript(post, config):
    """
    Because we're using basic gamification, we need to put in at least
    a few things to make it difficult to game the system. When a user
    says they've completed a post, we check the parent post for a top-level
    comment by the user who is attempting to complete the post and for the
    presence of the key. If it's all there, we update their flair and mark
    it complete. Otherwise, we ask them to please contact the mods.

    :param post: The Comment object that contains the string 'done'.
    :param config: the global config object.
    :return: True if a post is found, False if not.
    """
    top_parent = get_parent_post_id(post, config.r)

    # get source link, check all comments, look for root level comment
    # by the author of the post and verify that the key is in their post.
    # Return True if found, False if not.
    linked_resource = config.r.submission(top_parent.id_from_url(top_parent.url))
    # get rid of the "See More Comments" crap
    linked_resource.comments.replace_more(limit=0)
    for top_level_comment in linked_resource.comments.list():
        if _author_check(post, top_level_comment) \
                and _header_check(top_level_comment, config):
            return True
    # Did it get removed? Check their history.
    # if _author_history_check:
    #     return True
    # return False
