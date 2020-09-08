import logging
from typing import Dict, Union

from blossom_wrapper import BlossomStatus
from praw.models import Submission  # type: ignore

from tor.core.config import Config
from tor.core.helpers import _
from tor.helpers.flair import flair, flair_post
from tor.helpers.reddit_ids import has_been_posted
from tor.helpers.youtube import (has_youtube_transcript, get_yt_video_id,
                                 is_transcribable_youtube_video, is_youtube_url)
from tor.strings import translation

i18n = translation()
log = logging.getLogger(__name__)

PostSummary = Dict[str, Union[str, int, bool, None]]


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

    log.info(f'Posting call for transcription on ID {new_post["name"]} posted by {new_post["author"]}')

    if new_post['domain'] in cfg.image_domains:
        content_type = 'image'
        content_format = cfg.image_formatting

    elif new_post['domain'] in cfg.audio_domains:
        content_type = 'audio'
        content_format = cfg.audio_formatting

    elif new_post['domain'] in cfg.video_domains:
        content_type = 'video'
        content_format = cfg.video_formatting
    else:
        # This means we pulled from a subreddit bypassing the filters.
        content_type = 'Other'
        content_format = cfg.other_formatting

    try:
        if not handle_youtube(new_post, cfg):
            request_transcription(new_post, content_type, content_format, cfg)
    # The only errors that happen here are on Reddit's side -- pretty much
    # exclusively 503s and 403s that arbitrarily resolve themselves. A missed
    # post or two is not the end of the world.
    except Exception as e:
        log.error(
            f'{e} - unable to post content.\n'
            f'ID: {new_post["name"]}\n'
            f'Title: {new_post["title"]}\n'
            f'Subreddit: {new_post["subreddit"]}'
        )
        return


def has_enough_upvotes(post: PostSummary, cfg: Config) -> bool:
    """
    Check if the post meets the minimum threshold for karma
    """
    subreddit = str(post['subreddit'])
    upvotes = int(str(post['ups']))

    # If the subreddit is not in the upvote filter, this would mean no threshold.
    return upvotes >= cfg.upvote_filter_subs.get(subreddit, float("-inf"))


def should_process_post(post: PostSummary, cfg: Config) -> bool:
    """
    Determine whether the provided post should be processed.
    """
    return all(
        [
            has_enough_upvotes(post, cfg),
            not has_been_posted(i18n["urls"]["reddit_url"].format(post["permalink"]), cfg),
            not post["archived"],
            post["author"]
        ]
    )


def handle_youtube(post: PostSummary, cfg: Config) -> bool:
    """
    Handle the provided post, checking whether it is from YouTube in the process.

    The returned boolean resembles whether the post is handled. If it is False,
    this means that further handling is required.

    A post gets handled when it is a YouTube post and it either has a
    transcription or it is not transcribable in the first place.
    """
    url = str(post["url"])
    if has_youtube_transcript(url):
        # Since there is already a transcript, let /u/transcribersofreddit
        # post to the original submission, stating it already has closed
        # captioning.
        video_id = get_yt_video_id(url)
        submission = cfg.r.submission(id=post["name"])
        submission.reply(_(i18n["posts"]["yt_already_has_transcripts"]))
        log.info(f"Found YouTube video, https://youtu.be/{video_id}, with good transcripts.")
    return is_youtube_url(url) and not is_transcribable_youtube_video(url)


def truncate_title(title: str) -> str:
    max_length = 250  # This is probably the longest we ever want it

    if len(title) <= max_length:
        return title

    return title[:(max_length - 3)] + '...'


def request_transcription(
        post: PostSummary, content_type: str, content_format: str, cfg: Config
) -> None:
    """Request a transcription by posting the provided post to our subreddit."""
    title = i18n['posts']['discovered_submit_title'].format(
        sub=str(post['subreddit']),
        type=content_type.title(),
        title=truncate_title(str(post['title'])),
    )
    permalink = i18n['urls']['reddit_url'].format(str(post['permalink']))
    submission = cfg.tor.submit(title=title, url=permalink)
    intro = i18n['posts']['rules_comment'].format(
        post_type=content_type, formatting=content_format, header=cfg.header,
    )
    submission.reply(_(intro))
    flair_post(submission, flair.unclaimed)
    create_blossom_submission(submission, cfg, post["url"])


def create_blossom_submission(
        submission: Submission, cfg: Config, content_url: str = None
) -> Dict:
    own_link = i18n["urls"]["reddit_url"].format(str(submission.permalink))
    content_url = content_url or cfg.r.submission(url=submission.url).url
    return cfg.blossom.create_submission(
        submission.fullname, own_link, submission.url, content_url
    )


def get_blossom_submission(submission: Submission, cfg: Config) -> Dict:
    response = cfg.blossom.get_submission(submission.url)
    if response.status == BlossomStatus.ok:
        return response.data
    else:
        # If we are here, this means that the current submission is not yet in Blossom.
        return create_blossom_submission(submission, cfg)
