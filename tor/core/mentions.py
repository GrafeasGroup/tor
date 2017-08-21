import logging

# noinspection PyProtectedMember
from tor_core.helpers import _
from tor_core.helpers import clean_id
from tor_core.strings import reddit_url

from tor.helpers.flair import flair
from tor.helpers.flair import flair_post
from tor.helpers.reddit_ids import add_complete_post_id
from tor.helpers.reddit_ids import is_valid
from tor.strings.posts import rules_comment_unknown_format
from tor.strings.posts import summoned_by_comment
from tor.strings.posts import summoned_submit_title
from tor.strings.responses import something_went_wrong


def process_mention(mention, config):
    """
    Handles username mentions and handles the formatting and posting of
    those calls as workable jobs to ToR.

    :param mention: the Comment object containing the username mention.
    :param config: the global config dict
    :return: None.
    """

    # We have to do this entire parent / parent_permalink thing twice because
    # the method for calling a permalink changes for each object. Laaaame.
    if not mention.is_root:
        # this comment is in reply to something. Let's grab a comment object.
        parent = config.r.comment(id=clean_id(mention.parent_id))
        parent_permalink = parent.permalink()
        # a comment does not have a title attribute. Let's fake one by giving
        # it something to work with.
        parent.title = 'Unknown Content'
    else:
        # this is a post.
        parent = config.r.submission(id=clean_id(mention.link_id))
        parent_permalink = parent.permalink
        # format that sucker so it looks right in the template.
        parent.title = '"' + parent.title + '"'

        # Ignore requests made by the OP of content or the OP of the submission
        if mention.author == parent.author:
            logging.info(
                'Ignoring mention by OP u/{} on ID {}'.format(mention.author,
                                                              mention.parent_id)
            )
            return

    logging.info(
        'Posting call for transcription on ID {}'.format(mention.parent_id)
    )

    if is_valid(parent.fullname, config):
        # we're only doing this if we haven't seen this one before.

        # noinspection PyBroadException
        try:
            result = config.tor.submit(
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
                        config.r.comment(
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
            add_complete_post_id(parent.fullname, config)

            # I need to figure out what errors can happen here
        except Exception as e:
            logging.error(
                '{} - Posting failure message in response to caller, '
                'u/{}'.format(e, mention.author)
            )
            mention.reply(_(something_went_wrong))
