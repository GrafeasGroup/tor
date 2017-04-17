import logging
import re

from helpers import _
from helpers import add_complete_post_id
from helpers import clean_id
from helpers import flair
from helpers import flair_post
from helpers import get_parent_post_id
from helpers import is_valid
from helpers import update_user_flair
from strings import already_claimed
from strings import claim_already_complete
from strings import claim_success
from strings import discovered_submit_title
from strings import done_cannot_find_transcript
from strings import done_completed_transcript
from strings import done_still_unclaimed
from strings import id_already_handled_in_db
from strings import reddit_url
from strings import rules_comment
from strings import rules_comment_unknown_format
from strings import something_went_wrong
from strings import summoned_by_comment
from strings import summoned_submit_title


def process_post(new_post, tor, redis_server, Context):
    """
    After a valid post has been discovered, this handles the formatting
    and posting of those calls as workable jobs to ToR.

    :param new_post: Submission object that needs to be posted.
    :return: None.
    """
    if not is_valid(new_post.fullname, redis_server):
        logging.info(id_already_handled_in_db.format(new_post.fullname))
        return

    logging.info(
        'Posting call for transcription on ID {} posted by {}'.format(
            new_post.fullname, new_post.author.name
        )
    )

    if new_post.domain in Context.image_domains:
        content_type = 'image'
        content_format = Context.image_formatting
    elif new_post.domain in Context.audio_domains:
        content_type = 'audio'
        content_format = Context.audio_formatting
    elif new_post.domain in Context.video_domains:
        content_type = 'video'
        content_format = Context.video_formatting
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
                    post_type=content_type, formatting=content_format
                )
            )
        )
        flair_post(result, flair.unclaimed)

        add_complete_post_id(new_post.fullname, redis_server)

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


def process_mention(mention, r, tor, redis_server):
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
            result.reply(_(rules_comment_unknown_format))
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
            logging.info(
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
                'Posting failure message in response to caller, u/{}'.format(mention.author)
            )
            mention.reply(_(something_went_wrong))


def process_claim(post, r):
    """
    Handles comment replies containing the word 'claim' and routes
    based on a basic decision tree.
    
    :param post: The Comment object containing the claim.
    :param r: Active Reddit object.
    :return: None.
    """
    top_parent = get_parent_post_id(post, r)

    if 'Unclaimed' in top_parent.link_flair_text:
        # need to get that "Summoned - Unclaimed" in there too
        post.reply(_(claim_success))
        flair_post(top_parent, flair.in_progress)
        logging.info(
            'Claim on ID {} by {} successful'.format(
                top_parent.fullname, post.author
            )
        )
    # can't claim something that's already claimed
    elif top_parent.link_flair_text == flair.in_progress:
        post.reply(_(already_claimed))
    elif top_parent.link_flair_text == flair.completed:
        post.reply(_(claim_already_complete))


def verified_posted_transcript(post, r):
    """
    Because we're using basic gamification, we need to put in at least
    a few things to make it difficult to game the system. When a user
    says they've completed a post, we check the parent post for a top-level
    comment by the user who is attempting to complete the post. If it's
    there, we update their flair and mark it complete. Otherwise, we
    ask them to please contact the mods.

    :param post: The Comment object that contains the string 'done'.
    :param r: Active Reddit object.
    :return: True if a post is found, False if not.
    """
    top_parent = get_parent_post_id(post, r)

    # First we need to check to see if this is something we were
    # summoned for or not.
    for comment in top_parent.comments:
        if summoned_by_comment[:40] in comment.body and \
                        comment.author.name == 'transcribersofreddit':

            url_regex = re.compile(
                'their comment can be found here\.\]\((?P<url>.*)\)'
            )
            comment_url = re.search(url_regex, comment.body).group('url')

            # I don't like this because it's a costly operation on top
            # of all the other costly operations we need to make, but
            # if you just ask for the comment itself Reddit doesn't send
            # you the replies. That means you have to ask for the entire
            # thing (but really just the comment you want) and *then*
            # Reddit will send the replies. *headdesk*

            original_comment = ''  # stop pycharm from yelling at me

            # get all the comments (replies included) in a handy list
            original_comments = r.submission(url=comment_url).comments.list()
            for thingy in original_comments:
                if thingy.id in comment_url:
                    # thingy is the comment object we want! That's our parent!
                    original_comment = thingy
                    break
            # noinspection PyBroadException
            try:
                for reply in original_comment.replies:
                    if reply.author == post.author:
                        return True
            except Exception:
                # I don't care what the exception is, just don't break.
                return False

    # get source link, check all comments, look for root level comment
    # by the author of the post. Return True if found, False if not.
    linked_resource = r.submission(top_parent.id_from_url(top_parent.url))
    for top_level_comment in linked_resource.comments:
        if post.author == top_level_comment.author:
            return True
    return False


def process_done(post, r, tor):
    """
    Handles comments where the user says they've completed a post.
    Also includes a basic decision tree to enable verification of
    the posts to try and make sure they actually posted a
    transcription.
    
    :param post: the Comment object which contains the string 'done'.
    :param r: Active Reddit object.
    :param tor: Shortcut; a Subreddit object for ToR.
    :return: None.
    """

    top_parent = get_parent_post_id(post, r)

    if flair.unclaimed in top_parent.link_flair_text:
        post.reply(_(done_still_unclaimed))
    elif top_parent.link_flair_text == flair.in_progress:
        if verified_posted_transcript(post, r):
            # we need to double-check these things to keep people
            # from gaming the system
            post.reply(_(done_completed_transcript))
            flair_post(top_parent, flair.completed)
            update_user_flair(post, tor, r)
            logging.info(
                'Post {} completed by {}!'.format(
                    top_parent.fullname, post.author
                )
            )
        else:
            logging.info(
                'Post {} does not appear to have a post by claimant {}. '
                'Hrm...'.format(
                    top_parent.fullname, post.author
                )
            )
            post.reply(_(done_cannot_find_transcript))
