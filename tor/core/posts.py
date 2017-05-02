import logging

from tor.helpers.flair import flair
from tor.helpers.flair import flair_post
from tor.helpers.misc import _
from tor.helpers.reddit_ids import add_complete_post_id
from tor.helpers.reddit_ids import is_valid
from tor.helpers.wiki import update_wiki_page
from tor.helpers.youtube import get_yt_transcript
from tor.helpers.youtube import get_yt_video_id
from tor.helpers.youtube import valid_youtube_video
from tor.strings.debug import id_already_handled_in_db
from tor.strings.posts import discovered_submit_title
from tor.strings.posts import rules_comment
from tor.strings.posts import yt_already_has_transcripts
from tor.strings.urls import reddit_url


def check_submissions(subreddit, r, tor, redis_server, context):
    """
    Loops through all of the subreddits that have opted in and pulls
    the 100 newest submissions. It checks the domain of the submission
    against the domain lists and hands off the post to process_post()
    for formatting and posting on ToR.

    :param subreddit: String. A valid subreddit name.
    :param r: the Reddit object.
    :param tor: the ToR Subreddit object.
    :param redis_server: the active Redis server connection.
    :param Context: the context object.
    :return: None.
    """
    if subreddit in context.subreddit_members:
        sr = r.subreddit(subreddit).new(limit=10)
    else:
        sr = r.subreddit(subreddit).new(limit=50)
        context.subreddit_members.append(subreddit)
        update_wiki_page(
            'subreddits/members',
            '\r\n'.join(context.subreddit_members),
            tor
        )

    for post in sr:
        if (
            post.domain in context.image_domains or
            post.domain in context.audio_domains or
            post.domain in context.video_domains
        ):
            process_post(post, tor, redis_server, context)


def process_post(new_post, tor, redis_server, context):
    """
    After a valid post has been discovered, this handles the formatting
    and posting of those calls as workable jobs to ToR.

    :param new_post: Submission object that needs to be posted.
    :param tor: TranscribersOfReddit subreddit instance.
    :param redis_server: Active Redis instance.
    :param Context: the context object.
    :return: None.
    """
    if not is_valid(new_post.fullname, redis_server):
        logging.debug(id_already_handled_in_db.format(new_post.fullname))
        return

    if new_post.archived:
        return

    if new_post.author is None:
        logging.info(
            'Posting call for transcription on ID {} by deleted author'.format(
                new_post.fullname
            )
        )
    else:
        logging.info(
            'Posting call for transcription on ID {} posted by {}'.format(
                new_post.fullname, new_post.author.name
            )
        )

    if new_post.domain in context.image_domains:
        content_type = 'image'
        content_format = context.image_formatting
        # hook for ocr attempt
        redis_server.rpush('ocr_ids', new_post.fullname)

    elif new_post.domain in context.audio_domains:
        content_type = 'audio'
        content_format = context.audio_formatting

    elif new_post.domain in context.video_domains:
        if 'youtu' in new_post.domain:
            if not valid_youtube_video(new_post.url):
                return
            if get_yt_transcript(new_post.url):
                new_post.reply(_(
                    yt_already_has_transcripts
                ))
                add_complete_post_id(new_post.fullname, redis_server)
                logging.info(
                    'Found YouTube video, {}, with good transcripts.'
                    ''.format(
                        get_yt_video_id(new_post.url)
                    )
                )
                return
        content_type = 'video'
        content_format = context.video_formatting
    else:
        # how could we get here without fulfilling one of the above
        # criteria? Just remember: the users will find a way.
        content_type = 'Unknown'
        content_format = 'Formatting? I think something went wrong here...'

    # noinspection PyBroadException
    try:
        result = tor.submit(
            title=discovered_submit_title.format(
                sub=new_post.subreddit.display_name,
                type=content_type.title(),
                title=new_post.title
            ),
            url=reddit_url.format(new_post.permalink)
        )
        result.reply(
            _(
                rules_comment.format(
                    post_type=content_type,
                    formatting=content_format,
                    header=context.header
                )
            )
        )
        flair_post(result, flair.unclaimed)

        add_complete_post_id(new_post.fullname, redis_server)
        redis_server.incr('total_posted', amount=1)

    # I need to figure out what errors can happen here
    except Exception as e:
        logging.error(e)
        logging.error(
            'Something went wrong; unable to post content.\n'
            'ID: {id}\n'
            'Title: {title}\n'
            'Subreddit: {sub}'.format(
                id=new_post.fullname,
                title=new_post.title,
                sub=new_post.subreddit.display_name
            )
        )