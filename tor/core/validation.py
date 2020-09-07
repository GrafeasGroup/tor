from typing import Union, Tuple

from praw.models import Comment, Redditor, Submission  # type: ignore

from tor.core.config import Config
from tor.strings import translation

i18n = translation()


def get_transcription(
    submission_url: str, user: Redditor, cfg: Config
) -> Tuple[Union[Comment, None], bool]:
    """
    Get the transcription Comment of the Submission by the provided user.

    To obtain this Comment, first top level comments of the linked Submission
    are checked. If no valid transcription is found, the user's 10 most recent
    posts are checked. This can be the case when the transcription is
    automatically removed or hidden for another reason. If no transcription is
    found after this, None is returned.

    This function also returns whether the transcription was available in the
    linked submission or not.
    """
    linked_submission = cfg.r.submission(url=submission_url)
    linked_submission.comments.replace_more(limit=0)
    for top_level_comment in linked_submission.comments.list():
        if all([
            top_level_comment.author.name == user.name,
            contains_footer(top_level_comment, cfg)
        ]):
            return top_level_comment, True

    # In the case where the comment cannot be found within the top-level
    # comments, instead attempt to find it in the user's last 10 posts.
    for post in user.comments.new(limit=10):
        if all([
            post.submission.fullname == linked_submission.fullname,
            post.is_root,
            contains_footer(post, cfg)
        ]):
            return post, False
    return None, False


def contains_footer(comment: Comment, cfg: Config) -> bool:
    """
    Check whether the footer is within the provided comment.

    If the perform_header_check option is not set in the configuration, this
    function always returns True.
    """
    if not cfg.perform_header_check:
        return True
    if i18n['urls']['ToR_link'] not in comment.body:
        return False

    return "^(I'm a" in comment.body or "&#32;" in comment.body
