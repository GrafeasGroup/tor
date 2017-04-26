import logging
import re
import random

from helpers import _
from helpers import add_complete_post_id
from helpers import clean_id
from helpers import flair
from helpers import flair_post
from helpers import get_parent_post_id
from helpers import get_yt_transcript
from helpers import is_valid
from helpers import update_user_flair
from helpers import valid_youtube_video
from strings import ToR_link
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
from strings import yt_already_has_transcripts


def process_post(new_post, tor, redis_server, Context):
    """
    After a valid post has been discovered, this handles the formatting
    and posting of those calls as workable jobs to ToR.

    :param new_post: Submission object that needs to be posted.
    :param tor: TranscribersOfReddit subreddit instance.
    :param redis_server: Active Redis instance.
    :param Context: the Context object.
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

    if new_post.domain in Context.image_domains:
        content_type = 'image'
        content_format = Context.image_formatting
    elif new_post.domain in Context.audio_domains:
        content_type = 'audio'
        content_format = Context.audio_formatting
    elif new_post.domain in Context.video_domains:
        if 'youtu' in new_post.domain:
            if not valid_youtube_video(new_post.domain):
                return
            if get_yt_transcript(new_post.domain) != '':
                new_post.reply(_(
                    yt_already_has_transcripts
                ))
                add_complete_post_id(new_post.fullname, redis_server)
                return
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
                    post_type=content_type,
                    formatting=content_format,
                    header=Context.header
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


def process_mention(mention, r, tor, redis_server, Context):
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
            result.reply(_(rules_comment_unknown_format.format(header=Context.header)))
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
                'Posting failure message in response to caller, u/{}'.format(mention.author)
            )
            mention.reply(_(something_went_wrong))


def process_override(reply, r, tor, Context):
    """
    This process is for moderators of ToR to force u/transcribersofreddit
    to mark a post as complete and award flair when the bot refutes a
    `done` claim. The comment containing "!override" must be in response to
    the bot's comment saying that it cannot find the transcript.
    
    :param reply: the comment reply object from the moderator
    :param r: the active Reddit instance
    :param Context: the global Context object
    :return: None
    """
    # first we verify that this comment comes from a moderator and that
    # we can work on it.
    if reply.author not in Context.tor_mods:
        reply.reply(_(random.choice(Context.no_gifs)))
        logging.info(
            '{} just tried to override. Lolno.'.format(reply.author.name)
        )
        return
    # okay, so the parent of the reply should be the bot's comment saying
    # it can't find it. In that case, we need the parent's parent. That should
    # be the comment with the `done` call in it.
    reply_parent = r.comment(id=clean_id(reply.parent_id))s
    parents_parent = r.comment(id=clean_id(reply_parent.parent_id))
    if 'done' in parents_parent.body.lower():
        logging.info(
            'Starting validation override for post {}, approved by'
            '{}'.format(parents_parent.fullname, reply.author.name)
        )
        process_done(parents_parent, r, tor, Context, override=True)


def process_claim(post, r):
    """
    Handles comment replies containing the word 'claim' and routes
    based on a basic decision tree.
    
    :param post: The Comment object containing the claim.
    :param r: Active Reddit object.
    :return: None.
    """
    top_parent = get_parent_post_id(post, r)

    # WAIT! Do we actually own this post?
    if top_parent.author.name != 'transcribersofreddit':
        logging.debug('Received `claim` on post we do not own. Ignoring.')
        return

    # TODO: can we change this out for flair.unclaimed?
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


def _author_check(original_post, claimant_post):
    return original_post.author == claimant_post.author


def _header_check(reply, Context, tor_link=ToR_link):
    if Context.perform_header_check:
        return tor_link in reply.body
    else:
        # If we don't want the check to take place, we'll just return
        # true to negate it.
        return True


def verified_posted_transcript(post, r, Context):
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
                    if _author_check(reply, post) and _header_check(reply, Context):
                        return True
            except Exception as e:
                logging.error(e)
                # I don't care what the exception is, just don't break.
                return False

    # get source link, check all comments, look for root level comment
    # by the author of the post. Return True if found, False if not.
    linked_resource = r.submission(top_parent.id_from_url(top_parent.url))
    for top_level_comment in linked_resource.comments:
        if post.author == top_level_comment.author:
            return True
    return False


def process_done(post, r, tor, Context, override=False):
    """
    Handles comments where the user says they've completed a post.
    Also includes a basic decision tree to enable verification of
    the posts to try and make sure they actually posted a
    transcription.
    
    :param post: the Comment object which contains the string 'done'.
    :param r: Active Reddit object.
    :param tor: Shortcut; a Subreddit object for ToR.
    :param override: A parameter that can only come from process_override()
        and skips the validation check.
    :return: None.
    """

    top_parent = get_parent_post_id(post, r)

    # WAIT! Do we actually own this post?
    if top_parent.author.name != 'transcribersofreddit':
        logging.debug('Received `done` on post we do not own. Ignoring.')
        return

    if flair.unclaimed in top_parent.link_flair_text:
        post.reply(_(done_still_unclaimed))
    elif top_parent.link_flair_text == flair.in_progress:
        if not override:
            if not verified_posted_transcript(post, r, Context):
                # we need to double-check these things to keep people
                # from gaming the system
                logging.info(
                    'Post {} does not appear to have a post by claimant {}. '
                    'Hrm...'.format(
                        top_parent.fullname, post.author
                    )
                )
                post.reply(_(done_cannot_find_transcript))
                return
        # Control flow:
        # If we have an override, we end up here to complete.
        # If there is no override, we go into the validation.
        # If the validation fails, post the apology and return.
        # If the validation succeeds, come down here.
        post.reply(_(done_completed_transcript))
        flair_post(top_parent, flair.completed)
        update_user_flair(post, tor, r)
        if override:
            logging.info('Moderator override triggered!')
        logging.info(
            'Post {} completed by {}!'.format(
                top_parent.fullname, post.author
            )
        )

