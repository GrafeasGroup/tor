import logging
from typing import Dict, Union

import beeline
from blossom_wrapper import BlossomStatus
from praw.models import Submission

from tor.core.config import Config
from tor.core.helpers import _, cleanup_post_title
from tor.helpers.flair import flair
from tor.helpers.youtube import (
    is_transcribable_youtube_video,
    is_youtube_url,
)
from tor.strings import translation

i18n = translation()
log = logging.getLogger(__name__)

PostSummary = Dict[str, Union[str, int, bool, None]]


@beeline.traced(name="process_post")
def process_post(new_post: PostSummary, cfg: Config) -> None:
    """
    After a valid post has been discovered, this handles the formatting
    and posting of those calls as workable jobs to ToR.

    :param new_post: Submission object that needs to be posted.
    :param cfg: the config object.
    :return: None.
    """
    if not should_process_post(new_post, cfg):
        return

    log.info(
        f'Posting call for transcription on ID {new_post["name"]} posted by {new_post["author"]}'
    )

    if new_post["is_gallery"]:
        content_type = "gallery"
        content_format = cfg.image_formatting

    elif new_post["domain"] in cfg.image_domains:
        content_type = "image"
        content_format = cfg.image_formatting

    elif new_post["domain"] in cfg.audio_domains:
        content_type = "audio"
        content_format = cfg.audio_formatting

    elif new_post["domain"] in cfg.video_domains:
        content_type = "video"
        content_format = cfg.video_formatting

    else:
        # This means we pulled from a subreddit bypassing the filters.
        content_type = "Other"
        content_format = cfg.image_formatting

    try:
        request_transcription(new_post, content_type, content_format, cfg)
    # The only errors that happen here are on Reddit's side -- pretty much
    # exclusively 503s and 403s that arbitrarily resolve themselves. A missed
    # post or two is not the end of the world.
    except Exception as e:
        log.error(
            f"{e} - unable to post content.\n"
            f'ID: {new_post["name"]}\n'
            f'Title: {new_post["title"]}\n'
            f'Subreddit: {new_post["subreddit"]}'
        )
        return


def has_enough_upvotes(post: PostSummary, cfg: Config) -> bool:
    """
    Check if the post meets the minimum threshold for karma
    """
    subreddit = str(post["subreddit"])
    upvotes = int(str(post["ups"]))

    # If the subreddit is not in the upvote filter, this would mean no threshold.
    return upvotes >= cfg.upvote_filter_subs.get(subreddit, float("-inf"))


def should_process_post(post: PostSummary, cfg: Config) -> bool:
    """
    Determine whether the provided post should be processed.
    """
    url = str(post["url"])
    return all(
        [
            has_enough_upvotes(post, cfg),
            not post["archived"],
            post["author"],
            is_transcribable_youtube_video(url) if is_youtube_url(url) else True,
        ]
    )


def truncate_title(title: str) -> str:
    max_length = 250  # This is probably the longest we ever want it

    if len(title) <= max_length:
        return title

    return title[: (max_length - 3)] + "..."


@beeline.traced(name="request_transcription")
def request_transcription(
    post: PostSummary, content_type: str, content_format: str, cfg: Config
) -> None:
    """Request a transcription by posting the provided post to our subreddit."""
    title = i18n["posts"]["discovered_submit_title"].format(
        sub=str(post["subreddit"]),
        type=content_type.title(),
        title=truncate_title(cleanup_post_title(str(post["title"]))),
    )
    permalink = i18n["urls"]["reddit_url"].format(str(post["permalink"]))
    submission = cfg.tor.submit(title=title, url=permalink, flair_id=flair.unclaimed)
    intro = i18n["posts"]["rules_comment"].format(
        post_type=content_type,
        formatting=content_format,
        header=cfg.header,
    )
    submission.reply(_(intro))
    create_blossom_submission(post, submission, cfg)


def create_blossom_submission(
    original_post: PostSummary,  # original submission
    tor_post: Submission,  # tor submission
    cfg: Config,
) -> Dict:
    if (content_url := str(original_post["url"])) is None:
        content_url = cfg.r.submission(url=tor_post.url).url
    tor_url = i18n["urls"]["reddit_url"].format(str(tor_post.permalink))
    original_url = i18n["urls"]["reddit_url"].format(str(original_post["permalink"]))
    return cfg.blossom.create_submission(
        original_post["name"],
        tor_url,
        original_url,
        content_url,
        post_title=cleanup_post_title(str(original_post["title"])),
        nsfw=original_post["is_nsfw"],
    )


def get_blossom_submission(submission: Submission, cfg: Config) -> Dict:
    response = cfg.blossom.get_submission(url=submission.url)
    if response.status == BlossomStatus.ok:
        return response.data[0]
    else:
        # If we are here, this means that the current submission is not yet in Blossom.
        # Mock up a Blossom object, since this will only be used when Blossom doesn't
        # know about it
        post_summary = {}
        linked_post = cfg.r.submission(url=submission.url)
        post_summary["url"] = linked_post.url
        post_summary["permalink"] = linked_post.permalink
        post_summary["name"] = linked_post.fullname
        post_summary["title"] = linked_post.title
        post_summary["is_nsfw"] = linked_post.over_18

        new_submission = create_blossom_submission(post_summary, submission, cfg)
        # this submission will have the wrong post times because we didn't know about
        # it, so let's leave a marker that we can clean up later on Blossom's side.
        cfg.blossom.patch(
            f"submission/{new_submission['id']}/",
            data={"redis_id": "incomplete"},
        )
        return new_submission
