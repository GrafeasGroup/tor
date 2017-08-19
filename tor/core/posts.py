import logging

from tor.helpers.flair import flair
from tor.helpers.flair import flair_post
from tor.helpers.misc import _
from tor.helpers.reddit_ids import add_complete_post_id
from tor.helpers.reddit_ids import is_valid
from tor.helpers.youtube import get_yt_transcript
from tor.helpers.youtube import get_yt_video_id
from tor.helpers.youtube import valid_youtube_video
from tor.strings.debug import id_already_handled_in_db
from tor.strings.posts import discovered_submit_title
from tor.strings.posts import rules_comment
from tor.strings.posts import yt_already_has_transcripts
from tor.strings.urls import reddit_url


def check_submissions(subreddit, r, tor, config):
    """
    Loops through all of the subreddits that have opted in and pulls
    the 10 newest submissions. It checks the domain of the submission
    against the domain lists and hands off the post to process_post()
    for formatting and posting on ToR.

    :param subreddit: String. A valid subreddit name.
    :param r: the Reddit object.
    :param tor: the ToR Subreddit object.
    :param config: the config object.
    :return: None.
    """

    sr = r.subreddit(subreddit).new(limit=10)

    for post in sr:
        if (
            post.domain in config.image_domains or
            post.domain in config.audio_domains or
            post.domain in config.video_domains
        ):
            process_post(post, tor, config)


def process_post(new_post, tor, config):
    """
    After a valid post has been discovered, this handles the formatting
    and posting of those calls as workable jobs to ToR.

    :param new_post: Submission object that needs to be posted.
    :param tor: TranscribersOfReddit subreddit instance.
    :param config: the config object.
    :return: None.
    """

    subreddit = new_post.subreddit

    if subreddit.display_name in config.upvote_filter_subs:
        # ignore posts if they don't meet the threshold for karma and the sub
        # is in our list of upvoted filtered ones
        if new_post.ups < config.upvote_filter_subs[subreddit.display_name]:
            return

    if not is_valid(new_post.fullname, config):
        logging.debug(id_already_handled_in_db.format(new_post.fullname))
        return

    if new_post.archived:
        return

    if new_post.author is None:
        # we don't want to handle deleted posts, that's just silly
        return

    logging.info(
        'Posting call for transcription on ID {} posted by {}'.format(
            new_post.fullname, new_post.author.name
        )
    )

    if new_post.domain in config.image_domains:
        content_type = 'image'
        content_format = config.image_formatting

    elif new_post.domain in config.audio_domains:
        content_type = 'audio'
        content_format = config.audio_formatting

    elif new_post.domain in config.video_domains:
        if 'youtu' in new_post.domain:
            if not valid_youtube_video(new_post.url):
                add_complete_post_id(new_post.fullname, config)
                return
            if get_yt_transcript(new_post.url):
                new_post.reply(_(
                    yt_already_has_transcripts
                ))
                add_complete_post_id(new_post.fullname, config)
                logging.info(
                    'Found YouTube video, {}, with good transcripts.'
                    ''.format(
                        get_yt_video_id(new_post.url)
                    )
                )
                return
        content_type = 'video'
        content_format = config.video_formatting
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
                    header=config.header
                )
            )
        )
        flair_post(result, flair.unclaimed)

        add_complete_post_id(new_post.fullname, config)
        config.redis.incr('total_posted', amount=1)

        if config.OCR and content_type == 'image':
            # hook for OCR bot; in order to avoid race conditions, we add the
            # key / value pair that the bot isn't looking for before adding
            # to the set that it's monitoring.
            config.redis.set(new_post.fullname, result.fullname)
            config.redis.rpush('ocr_ids', new_post.fullname)

        config.redis.incr('total_new', amount=1)

    # I need to figure out what errors can happen here
    except Exception as e:
        logging.error(
            '{} - unable to post content.\n'
            'ID: {id}\n'
            'Title: {title}\n'
            'Subreddit: {sub}'.format(
                e,
                id=new_post.fullname,
                title=new_post.title,
                sub=new_post.subreddit.display_name
            )
        )
