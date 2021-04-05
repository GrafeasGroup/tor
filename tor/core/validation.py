from praw.models import Comment, Submission  # type: ignore
from prawcore.exceptions import Forbidden  # type: ignore

from tor.core.config import Config
from tor.core.helpers import get_parent_post_id, send_to_modchat
from tor.strings import translation

i18n = translation()


def _author_check(original_post: Comment, claimant_post: Comment) -> bool:
    return original_post.author == claimant_post.author


def _footer_check(reply: Comment, cfg: Config) -> bool:
    """
    Is the footer in there?

    :param reply: Comment object; hopefully the one with the transcription in
        it.
    :param cfg: the global config object.
    :param tor_link: String; the magical url key.
    :return: True / None.
    """
    tor_link = i18n['urls']['ToR_link']

    if not cfg.perform_header_check:
        # If we don't want the check to take place, we'll just
        # return true to negate it.
        return True

    if tor_link not in reply.body:
        return False

    return "^(I'm a" in reply.body or '&#32;' in reply.body


def _thread_title_check(original_post: Comment, history_item: Comment) -> bool:
    """
    Verify that the link titles match. On the original post, it will be
    removed, but we should still be able to extract the title of the
    submission it's on. Then we check to see if the title for that submission
    is in the r/ToR post, mirroring the max line truncation that's in
    posts.py.

    :param original_post: Comment object; comment that says "done".
    :param history_item: Comment object; comment pulled from user's history.
    """
    max_title_length = 250
    return (
        history_item.link_title[:max_title_length - 4] in
        original_post.link_title
    )


def _thread_author_check(original_post: Comment, history_item: Comment, cfg: Config) -> bool:
    """
    This allows us to check whether the author of the thread that the
    transcription is posted in is the same as the author of the linked
    thread in the event of a removed comment where they cannot be directly
    linked.

    :param original_post: Comment object; comment that says "done".
    :param history_item: Comment object; comment pulled from user's history.
    :param cfg: the global config object.
    :return: True if the author of the original submission matches the author
        of the submission the transcription is on.
    """
    submission = cfg.r.submission(url=original_post.submission.url)
    return history_item.submission.author == submission.author


def _author_history_check(post: Comment, cfg: Config) -> bool:
    """
    Pull the ten latest comments from the user's history. Chances are that's
    enough to see if they've actually done the post or not without slowing
    everything down _too_ much. See if any of those ten items look right
    and complete the post if it's the transcript we're looking for.

    Warning: this is not very fast, but it does the job. Definitely something
    we're going to have to circle back to when we separate out the jobs.

    :param post: The Comment object that contains the string 'done'.
    :param cfg: the global config object.
    :return: True if the post is found in the history, False if not.
    """
    for history_post in post.author.comments.new(limit=10):
        if not history_post.is_root:
            continue
        if not _footer_check(history_post, cfg):
            continue
        if not _thread_title_check(post, history_post):
            continue
        if not _thread_author_check(post, history_post, cfg):
            continue

        return True

    return False


def verified_posted_transcript(post: Comment, cfg: Config) -> bool:
    """
    Because we're using basic gamification, we need to put in at least
    a few things to make it difficult to game the system. When a user
    says they've completed a post, we check the parent post for a top-level
    comment by the user who is attempting to complete the post and for the
    presence of the key. If it's all there, we update their flair and mark
    it complete. Otherwise, we ask them to please contact the mods.

    Process:
    Get source link, check all comments, look for a root level comment
    by the author of the post and verify that the key is in their post.
    Return True if found, False if not.

    :param post: The Comment object that contains the string 'done'.
    :param cfg: the global config object.
    :return: True if a post is found, False if not.
    """
    forbidden: bool = False
    top_parent: Submission = get_parent_post_id(post, cfg.r)
    linked_resource: Submission = cfg.r.submission(top_parent.id_from_url(top_parent.url))

    try:
    # get rid of the "See More Comments" crap
        linked_resource.comments.replace_more(limit=0)
        for top_level_comment in linked_resource.comments.list():
            if not _author_check(post, top_level_comment):
                continue
            if not _footer_check(top_level_comment, cfg):
                continue
            return True
    except Forbidden:
        # we've attempted to load a subreddit that we don't have access to. The
        # only way this can happen (reasonably) is when the sub goes private
        # after we've already pulled the submission from it. In this case, we
        # will default to the author history check.
        forbidden = True

    # Did their transcript get flagged by the spam filter? Check their history.
    if _author_history_check(post, cfg):
        # We only want to complain about it being removed if it was
        # actually removed.
        if not forbidden:
            send_to_modchat(
                f'Found removed post: <{post.submission.shortlink}>',
                cfg,
                channel='#removed_posts'
            )
        return True

    return False
