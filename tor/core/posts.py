import logging
from typing import Dict, Union

from praw.models import Submission  # type: ignore

from tor.core.config import Config
from tor.core.helpers import send_reddit_reply
from tor.helpers.flair import flair, flair_post
from tor.helpers.reddit_ids import add_complete_post_id, has_been_posted
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

    if is_youtube_url(str(new_post['url'])):
        if not is_transcribable_youtube_video(str(new_post['url'])):
            # Not transcribable, so let's add it to the completed posts and skip over it forever
            add_complete_post_id(str(new_post['url']), cfg)
            return

    request_transcription(new_post, content_type, content_format, cfg)


def has_enough_upvotes(post: PostSummary, cfg: Config) -> bool:
    """
    Check if the post meets the minimum threshold for karma
    """
    subreddit = str(post['subreddit'])
    upvotes = int(str(post['ups']))

    if subreddit not in cfg.upvote_filter_subs:
        # Must not be a sub which has a minimum threshold
        return True

    if upvotes >= cfg.upvote_filter_subs[subreddit]:
        return True

    return False


def should_process_post(post: PostSummary, cfg: Config) -> bool:
    if not has_enough_upvotes(post, cfg):
        return False
    if has_been_posted(str(post['name']), cfg):
        return False
    if post['archived']:
        return False
    if not post['author']:
        return False

    return True


def truncate_title(title: str) -> str:
    max_length = 250  # This is probably the longest we ever want it

    if len(title) <= max_length:
        return title

    return title[:(max_length - 3)] + '...'


def request_transcription(post: PostSummary, content_type: str, content_format: str, cfg: Config):
    # Truncate a post title if it exceeds 250 characters, so the added
    # formatting still fits in Reddit's 300 char limit for post titles
    title = i18n['posts']['discovered_submit_title'].format(
        sub=str(post['subreddit']),
        type=content_type.title(),
        title=truncate_title(str(post['title'])),
    )
    url = i18n['urls']['reddit_url'].format(str(post['permalink']))
    intro = i18n['posts']['rules_comment'].format(
        post_type=content_type,
        formatting=content_format,
        header=cfg.header,
    )

    submission: Submission

    if is_youtube_url(str(post['url'])) and has_youtube_transcript(str(post['url'])):
        try:
            # NOTE: This has /u/transcribersofreddit post to the original
            # subreddit where the video was posted saying it already has
            # closed captioning
            video_id = get_yt_video_id(str(post['url']))
            submission = cfg.r.submission(id=post['name'])
            send_reddit_reply(submission, i18n['posts']['yt_already_has_transcripts'])
            add_complete_post_id(str(post['name']), cfg)
            log.info(f'Found YouTube video, https://youtu.be/{video_id}, with good transcripts.')
        # The only errors that happen here are on Reddit's side -- pretty much
        # exclusively 503s and 403s that arbitrarily resolve themselves. A missed
        # post or two is not the end of the world.
        except Exception as e:
            log.error(
                f'{e} - unable to post content.\n'
                f'ID: {post["name"]}\n'
                f'Title: {post["title"]}\n'
                f'Subreddit: {post["subreddit"]}'
            )
        return

    try:
        submission = cfg.tor.submit(title=title, url=url)
        send_reddit_reply(submission, intro)
        flair_post(submission, flair.unclaimed)
        add_complete_post_id(str(post['name']), cfg)

        cfg.redis.incr('total_posted', amount=1)
        cfg.blossom.create_post(submission.fullname, str(post['url']), url)
        queue_ocr_bot(post, submission, cfg)
        cfg.redis.incr('total_new', amount=1)
    # The only errors that happen here are on Reddit's side -- pretty much
    # exclusively 503s and 403s that arbitrarily resolve themselves. A missed
    # post or two is not the end of the world.
    except Exception as e:
        log.error(
            f'{e} - unable to post content.\n'
            f'ID: {post["name"]}\n'
            f'Title: {post["title"]}\n'
            f'Subreddit: {post["subreddit"]}'
        )


def queue_ocr_bot(post: PostSummary, submission: Submission, cfg: Config) -> None:
    if post['domain'] not in cfg.image_domains:
        # We only OCR images at this time
        return

    # Set the payload for the job
    cfg.redis.set(str(post['name']), submission.fullname)

    # Queue up the job reference
    cfg.redis.rpush('ocr_ids', str(post['name']))
