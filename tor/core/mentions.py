import logging

from tor.helpers.flair import flair
from tor.helpers.flair import flair_post
from tor.helpers.misc import _
from tor.helpers.reddit_ids import add_complete_post_id
from tor.helpers.reddit_ids import clean_id
from tor.helpers.reddit_ids import is_valid
from tor.strings.posts import rules_comment_unknown_format
from tor.strings.posts import summoned_by_comment
from tor.strings.posts import summoned_submit_title
from tor.strings.responses import something_went_wrong
from tor.strings.urls import reddit_url


def process_mention(mention, r, tor, redis_server, config):
    """
    Handles username mentions and handles the formatting and posting of
    those calls as workable jobs to ToR.

    :param mention: the Comment object containing the username mention.
    :param r: Active Reddit instance.
    :param tor: A shortcut; the Subreddit instance for ToR.
    :param redis_server: Active redis instance.
    :return: None.
    """
    # We have to do this entire parent / parent_permalink thing twice because
    # the method for calling a permalink changes for each object. Laaaame.
    if not mention.is_root:
        # this comment is in reply to something. Let's grab a comment object.
        parent = r.comment(id=clean_id(mention.parent_id))
        parent_permalink = parent.permalink()
        # a comment does not have a title attribute. Let's fake one by giving
        # it something to work with.
        parent.title = 'Unknown Content'
    else:
        # this is a post.
        parent = r.submission(id=clean_id(mention.parent_id))
        parent_permalink = parent.permalink
        # format that sucker so it looks right in the template.
        parent.title = '"' + parent.title + '"'

    logging.info(
        'Posting call for transcription on ID {}'.format(mention.parent_id)
    )

    if is_valid(parent.fullname, redis_server):
        # we're only doing this if we haven't seen this one before.

        # noinspection PyBroadException
        try:
            result = tor.submit(
                title=summoned_submit_title.format(
                    sub=mention.subreddit.display_name,
                    commentorpost=parent.__class__.__name__.lower(),
                    title=parent.title
                ),
                url=reddit_url.format(parent_permalink)
            )
            result.reply(_(rules_comment_unknown_format.format(header=config.header)))
            result.reply(_(
                summoned_by_comment.format(
                    reddit_url.format(
                        r.comment(
                            clean_id(mention.fullname)
                        ).permalink()
                    )
                )
            ))
            flair_post(result, flair.summoned_unclaimed)
            logging.debug(
                'Posting success message in response to caller, u/{}'.format(mention.author)
            )
            mention.reply(_(
                'The transcribers have been summoned! Please be patient '
                'and we\'ll be along as quickly as we can.')
            )
            add_complete_post_id(parent.fullname, redis_server)

            # I need to figure out what errors can happen here
        except Exception as e:
            logging.error(e)
            logging.error(
                'Posting failure message in response to caller, u/{}'.format(
                    mention.author
                )
            )
            mention.reply(_(something_went_wrong))
