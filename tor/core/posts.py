import logging

from tor.core.helpers import _
from tor.core.strings import reddit_url
from tor.helpers.flair import flair, flair_post
from tor.helpers.reddit_ids import add_complete_post_id, is_valid
from tor.helpers.youtube import (get_yt_transcript, get_yt_video_id,
                                 valid_youtube_video)
from tor.strings.debug import id_already_handled_in_db
from tor.strings.posts import (discovered_submit_title, rules_comment,
                               yt_already_has_transcripts)


def process_post(new_post, cfg):
    """
    After a valid post has been discovered, this handles the formatting
    and posting of those calls as workable jobs to ToR.

    :param new_post: Submission object that needs to be posted.
    :param cfg: the config object.
    :return: None.
    """

    if new_post['subreddit'] in cfg.upvote_filter_subs:
        # ignore posts if they don't meet the threshold for karma and the sub
        # is in our list of upvoted filtered ones
        if new_post['ups'] < cfg.upvote_filter_subs[new_post['subreddit']]:
            return

    if not is_valid(new_post['name'], cfg):
        logging.debug(id_already_handled_in_db.format(new_post['name']))
        return

    if new_post['archived']:
        return

    if new_post['author'] is None:
        # we don't want to handle deleted posts, that's just silly
        return

    logging.info(
        f'Posting call for transcription on ID {new_post["name"]} posted by '
        f'{new_post["author"]}'
    )

    if new_post['domain'] in cfg.image_domains:
        content_type = 'image'
        content_format = cfg.image_formatting

    elif new_post['domain'] in cfg.audio_domains:
        content_type = 'audio'
        content_format = cfg.audio_formatting

    elif new_post['domain'] in cfg.video_domains:
        if 'youtu' in new_post['domain']:
            if not valid_youtube_video(new_post['url']):
                add_complete_post_id(new_post['name'], cfg)
                return
            if get_yt_transcript(new_post['url']):
                np = cfg.r.submission(id=new_post['name'])
                np.reply(_(
                    yt_already_has_transcripts
                ))
                add_complete_post_id(new_post['name'], cfg)
                logging.info(
                    f'Found YouTube video, {get_yt_video_id(new_post["url"])},'
                    f' with good transcripts.'
                )
                return
        content_type = 'video'
        content_format = cfg.video_formatting
    else:
        # This means we pulled from a subreddit bypassing the filters.
        content_type = 'Other'
        content_format = cfg.other_formatting

    # Truncate a post title if it exceeds 250 characters, so the added
    # formatting still fits in Reddit's 300 char limit for post titles
    post_title = new_post['title']
    max_title_length = 250
    if len(post_title) > max_title_length:
        post_title = post_title[:max_title_length - 3] + '...'

    # noinspection PyBroadException
    try:
        result = cfg.tor.submit(
            title=discovered_submit_title.format(
                sub=new_post['subreddit'],
                type=content_type.title(),
                title=post_title
            ),
            url=reddit_url.format(new_post['permalink'])
        )
        result.reply(
            _(
                rules_comment.format(
                    post_type=content_type,
                    formatting=content_format,
                    header=cfg.header
                )
            )
        )
        flair_post(result, flair.unclaimed)

        add_complete_post_id(new_post['name'], cfg)
        cfg.redis.incr('total_posted', amount=1)

        if cfg.OCR and content_type == 'image':
            # hook for OCR bot; in order to avoid race conditions, we add the
            # key / value pair that the bot isn't looking for before adding
            # to the set that it's monitoring.
            cfg.redis.set(new_post['name'], result.fullname)
            cfg.redis.rpush('ocr_ids', new_post['name'])

        cfg.redis.incr('total_new', amount=1)

    # The only errors that happen here are on Reddit's side -- pretty much
    # exclusively 503s and 403s that arbitrarily resolve themselves. A missed
    # post or two is not the end of the world.
    except Exception as e:
        logging.error(
            f'{e} - unable to post content.\nID: {new_post["name"]}\n '
            f'Title: {new_post["title"]}\n Subreddit: '
            f'{new_post["subreddit"]}'
        )
