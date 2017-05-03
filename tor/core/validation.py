import logging
import re

from tor.helpers.reddit_ids import get_parent_post_id
from tor.strings.posts import summoned_by_comment
from tor.strings.urls import ToR_link


def _author_check(original_post, claimant_post):
    return original_post.author == claimant_post.author


def _header_check(reply, Context, tor_link=ToR_link):
    if Context.perform_header_check:
        return tor_link in reply.body
    else:
        # If we don't want the check to take place, we'll just return
        # true to negate it.
        return True


def verified_posted_transcript(post, r, Context):
    """
    Because we're using basic gamification, we need to put in at least
    a few things to make it difficult to game the system. When a user
    says they've completed a post, we check the parent post for a top-level
    comment by the user who is attempting to complete the post. If it's
    there, we update their flair and mark it complete. Otherwise, we
    ask them to please contact the mods.

    :param post: The Comment object that contains the string 'done'.
    :param r: Active Reddit object.
    :param Context: the global context object.
    :return: True if a post is found, False if not.
    """
    top_parent = get_parent_post_id(post, r)

    # First we need to check to see if this is something we were
    # summoned for or not.
    for comment in top_parent.comments:
        if summoned_by_comment[:40] in comment.body and \
                        comment.author.name == 'transcribersofreddit':

            url_regex = re.compile(
                'their comment can be found here\.\]\((?P<url>.*)\)'
            )
            comment_url = re.search(url_regex, comment.body).group('url')

            # I don't like this because it's a costly operation on top
            # of all the other costly operations we need to make, but
            # if you just ask for the comment itself Reddit doesn't send
            # you the replies. That means you have to ask for the entire
            # thing (but really just the comment you want) and *then*
            # Reddit will send the replies. *headdesk*

            original_comment = ''  # stop pycharm from yelling at me

            # get all the comments (replies included) in a handy list
            original_comments = r.submission(url=comment_url).comments.list()
            for thingy in original_comments:
                if thingy.id in comment_url:
                    # thingy is the comment object we want! That's our parent!
                    original_comment = thingy
                    break
            # noinspection PyBroadException
            try:
                for reply in original_comment.replies:
                    if _author_check(reply, post) and _header_check(reply, Context):
                        return True
            except Exception as e:
                logging.error(e)
                # I don't care what the exception is, just don't break.
                return False

    # get source link, check all comments, look for root level comment
    # by the author of the post. Return True if found, False if not.
    linked_resource = r.submission(top_parent.id_from_url(top_parent.url))
    # get rid of the "See More Comments" crap
    linked_resource.comments.replace_more(limit=0)
    for top_level_comment in linked_resource.comments.list():
        if post.author == top_level_comment.author:
            return True
    return False