import logging
import random

import praw
from praw.models import Message as RedditMessage
from tor import __BOT_NAMES__
from tor.core.helpers import (_, clean_id, get_parent_post_id, get_wiki_page,
                              reports, send_to_modchat)
from tor.core.strings import reddit_url
from tor.core.users import User
from tor.core.validation import verified_posted_transcript
from tor.core.validation import _footer_check
from tor.helpers.flair import flair, flair_post, update_user_flair
from tor.helpers.reddit_ids import is_removed
from tor.strings import translation

i18n = translation()


def coc_accepted(post, cfg):
    """
    Verifies that the user is has accepted the Code of Conduct as listed
    at https://www.reddit.com/r/transcribersofreddit/wiki/codeofconduct

    :param post: the Comment object containing the claim.
    :param cfg: the global config dict.
    :return: True if the user has accepted the Code of Conduct, False if they
        haven't.
    """
    result = cfg.blossom.get(
        '/volunteer/', params={'username', post.author.name}
    ).json()
    if not result.get('results'):
        # We have a new volunteer. They definitely haven't accepted the CoC.
        return False
    else:
        return result['results'][0]['accepted_coc']


def process_coc(post, cfg):
    """
    Creates a user on Blossom and sets the code of conduct flag to True.
    Because this function is called anytime a user uses the phrase
    "I accept", we include an escape hatch if they've already accepted
    the code of conduct (we just assume that they wanted to claim instead
    and process appropriately).

    :param post: The Comment object containing the claim.
    :param cfg: the global config dict.
    :return: None.
    """
    modchat_emote = random.choice([
        ':tada:',
        ':confetti_ball:',
        ':party-lexi:',
        ':party-parrot:',
        ':+1:',
        ':trophy:',
        ':heartpulse:',
        ':beers:',
        ':gold:',
        ':upvote:',
        ':coolio:',
        ':derp:',
        ':lenny1::lenny2:',
        ':panic:',
        ':fidget-spinner:',
        ':fb-like:'
    ])

    result = cfg.blossom.get(
        '/volunteer/', params={'username', post.author.name}
    ).json()
    if not result.get('results'):
        usercreate = cfg.blossom.post('/volunteer/', data={"username"})
        if usercreate.status_code != 200:
            raise Exception(
                f'Something went wrong with user creation: {usercreate.json()}'
            )
        # f strings don't like dictionary lookups for some reason
        user_id = usercreate.json()['data']['id']
        resp = cfg.blossom.patch(f'/volunteer/{user_id}', data={'accepted_coc': True})
        if resp.status_code != 200:
            raise Exception(
                f"Something went wrong while marking volunteer with 'accepted_coc':"
                f" {resp.json()}"
            )
        send_to_modchat(
            f'<{reddit_url.format("/user/" + post.author.name)}|u/{post.author.name}>'
            f' has just'
            f' <{reddit_url.format(post.context)}|accepted the CoC!>'
            f' {modchat_emote}',
            cfg,
            channel='new_volunteers'
        )
        process_claim(post, cfg, first_time=True)
    else:
        # We've seen them before. No need to give them the welcome experience.
        if result['results'][0].get('accepted_coc') is False:
            # So... we got a user in the response but they don't have
            # `accepted_coc` set. We should never hit this state; basically
            # the only way to do so is if the patch call above errors out.
            # Unlikely, but worth planning for. Just mark them again and move on.
            user_id = result['results'][0]['id']
            cfg.blossom.patch(f'/volunteer/{user_id}', data={'accepted_coc': True})

        process_claim(post, cfg)


def process_claim(post, cfg, first_time=False):
    """
    Handles comment replies containing the word 'claim' and routes
    based on a basic decision tree.

    :param post: The Comment object containing the claim.
    :param cfg: the global config dict.
    :return: None.
    """
    top_parent = get_parent_post_id(post, cfg.r)

    already_claimed = i18n['responses']['claim']['already_claimed']
    claim_already_complete = i18n['responses']['claim']['already_complete']
    please_accept_coc = i18n['responses']['general']['coc_not_accepted']

    if first_time:
        claim_success = i18n['responses']['claim']['first_claim_success']
    else:
        claim_success = i18n['responses']['claim']['success']

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        logging.debug('Received `claim` on post we do not own. Ignoring.')
        return

    try:
        if not coc_accepted(post, cfg):
            # do not cache this page. We want to get it every time.
            post.reply(_(
                please_accept_coc.format(get_wiki_page('codeofconduct', cfg))
            ))
            return

        # this can be either '' or None depending on how the API is feeling
        # today
        if top_parent.link_flair_text in ['', None]:
            # There exists the very small possibility that the post was
            # malformed and doesn't actually have flair on it. In that case,
            # let's set something so the next part doesn't crash.
            flair_post(top_parent, flair.unclaimed)

        if flair.unclaimed in top_parent.link_flair_text:
            # need to get that "Summoned - Unclaimed" in there too
            post.reply(_(claim_success))

            flair_post(top_parent, flair.in_progress)
            logging.info(
                f'Claim on ID {top_parent.fullname} by {post.author} successful'
            )

        # can't claim something that's already claimed
        elif top_parent.link_flair_text == flair.in_progress:
            post.reply(_(already_claimed))
        elif top_parent.link_flair_text == flair.completed:
            post.reply(_(claim_already_complete))

    except praw.exceptions.APIException as e:
        if e.error_type == 'DELETED_COMMENT':
            logging.info(
                f'Comment attempting to claim ID {top_parent.fullname} has '
                f'been deleted. Back up for grabs! '
            )
            return
        raise  # Re-raise exception if not


def process_done(post, cfg, override=False, alt_text_trigger=False):
    """
    Handles comments where the user says they've completed a post.
    Also includes a basic decision tree to enable verification of
    the posts to try and make sure they actually posted a
    transcription.

    :param post: the Comment object which contains the string 'done'.
    :param cfg: the global config object.
    :param override: A parameter that can only come from process_override()
        and skips the validation check.
    :param alt_text_trigger: a trigger that adds an extra piece of text onto
        the response. Just something to help ease the number of
        false-positives.
    :return: None.
    """

    top_parent = get_parent_post_id(post, cfg.r)

    done_cannot_find_transcript = i18n['responses']['done']['cannot_find_transcript']
    done_completed_transcript = i18n['responses']['done']['completed_transcript']
    done_still_unclaimed = i18n['responses']['done']['still_unclaimed']

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        logging.info('Received `done` on post we do not own. Ignoring.')
        return

    try:
        if flair.unclaimed in top_parent.link_flair_text:
            post.reply(_(done_still_unclaimed))
        elif top_parent.link_flair_text == flair.in_progress:
            if not override and not verified_posted_transcript(post, cfg):
                # we need to double-check these things to keep people
                # from gaming the system
                logging.info(
                    f'Post {top_parent.fullname} does not appear to have a '
                    f'post by claimant {post.author}. Hrm... '
                )
                # noinspection PyUnresolvedReferences
                try:
                    post.reply(_(done_cannot_find_transcript))
                except praw.exceptions.ClientException as e:
                    # We've run into an issue where someone has commented and
                    # then deleted the comment between when the bot pulls mail
                    # and when it processes comments. This should catch that.
                    # Possibly should look into subclassing praw.Comment.reply
                    # to include some basic error handling of this so that
                    # we can fix it throughout the application.
                    logging.warning(e)
                return

            # Control flow:
            # If we have an override, we end up here to complete.
            # If there is no override, we go into the validation above.
            # If the validation fails, post the apology and return.
            # If the validation succeeds, come down here.

            if override:
                logging.info('Moderator override starting!')
            # noinspection PyUnresolvedReferences
            try:
                if alt_text_trigger:
                    post.reply(_(
                        'I think you meant `done`, so here we go!\n\n'
                        f'{done_completed_transcript}'
                    ))
                else:
                    post.reply(_(done_completed_transcript))
                update_user_flair(post, cfg)
                logging.info(
                    f'Post {top_parent.fullname} completed by {post.author}!'
                )
                # get that information saved for the user
                author = User(str(post.author), cfg.redis)
                author.list_update('posts_completed', clean_id(post.fullname))
                author.save()

            except praw.exceptions.ClientException:
                # If the butt deleted their comment and we're already this
                # far into validation, just mark it as done. Clearly they
                # already passed.
                logging.info(
                    f'Attempted to mark post {top_parent.fullname} '
                    f'as done... hit ClientException.'
                )
            flair_post(top_parent, flair.completed)

            cfg.redis.incr('total_completed', amount=1)

    except praw.exceptions.APIException as e:
        if e.error_type == 'DELETED_COMMENT':
            logging.info(
                f'Comment attempting to mark ID {top_parent.fullname} '
                f'as done has been deleted'
            )
            return
        raise  # Re-raise exception if not


def process_unclaim(post, cfg):
    # Sometimes people need to unclaim things. Usually this happens because of
    # an issue with the post itself, like it's been locked or deleted. Either
    # way, we should probably be able to handle it.

    # Process:
    # If the post has been reported, then remove it. No checks, just do it.
    # If the post has not been reported, attempt to load the linked post.
    #   If the linked post is still up, then reset the flair on ToR's side
    #    and reply to the user.
    #   If the linked post has been taken down or deleted, then remove the post
    #    on ToR's side and reply to the user.

    top_parent = post.submission

    unclaim_failure_post_already_completed = i18n['responses']['unclaim']['post_already_completed']
    unclaim_still_unclaimed = i18n['responses']['unclaim']['still_unclaimed']
    unclaim_success = i18n['responses']['unclaim']['success']
    unclaim_success_with_report = i18n['responses']['unclaim']['success_with_report']
    unclaim_success_without_report = i18n['responses']['unclaim']['success_without_report']

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        logging.info('Received `unclaim` on post we do not own. Ignoring.')
        return

    if flair.unclaimed in top_parent.link_flair_text:
        post.reply(_(unclaim_still_unclaimed))
        return

    for item in top_parent.user_reports:
        if (
            reports.original_post_deleted_or_locked in item[0] or reports.post_violates_rules in item[0]
        ):
            top_parent.mod.remove()
            send_to_modchat(
                'Removed the following reported post in response to an '
                '`unclaim`: {}'.format(top_parent.shortlink),
                cfg,
                channel='removed_posts'
            )
            post.reply(_(unclaim_success_with_report))
            return

    # Okay, so they commented with unclaim, but they didn't report it.
    # Time to check to see if they should have.
    linked_resource = cfg.r.submission(
        top_parent.id_from_url(top_parent.url)
    )
    if is_removed(linked_resource):
        top_parent.mod.remove()
        send_to_modchat(
            'Received `unclaim` on an unreported post, but it looks like it '
            'was removed on the parent sub. I removed ours here: {}'
            ''.format(top_parent.shortlink),
            cfg,
            channel='removed_posts'
        )
        post.reply(_(unclaim_success_without_report))
        return

    # Finally, if none of the other options apply, we'll reset the flair and
    # continue on as normal.
    if top_parent.link_flair_text == flair.completed:
        post.reply(_(unclaim_failure_post_already_completed))
        return

    if top_parent.link_flair_text == flair.in_progress:
        flair_post(top_parent, flair.unclaimed)
        post.reply(_(unclaim_success))
        return


def process_thanks(post, cfg):
    thumbs_up_gifs = i18n['urls']['thumbs_up_gifs']
    youre_welcome = i18n['responses']['general']['youre_welcome']
    try:
        post.reply(_(youre_welcome.format(random.choice(thumbs_up_gifs))))
    except praw.exceptions.APIException as e:
        if e.error_type == 'DELETED_COMMENT':
            logging.debug('Comment requiring thanks was deleted')
            return
        raise


def process_wrong_post_location(post, cfg):
    transcript_on_tor_post = i18n['responses']['general']['transcript_on_tor_post']
    if _footer_check(post, cfg, new_reddit=True):
        transcript_on_tor_post += i18n['responses']['general']['new_reddit_transcript']
    try:
        post.reply(_(transcript_on_tor_post))
    except praw.exceptions.APIException:
        logging.debug(
            'Something went wrong with asking about a misplaced post; '
            'ignoring.'
        )


def process_message(message: RedditMessage, cfg):
    dm_subject = i18n['responses']['direct_message']['dm_subject']
    dm_body = i18n['responses']['direct_message']['dm_body']

    author = message.author
    username = author.name if author else None

    author.message(dm_subject, dm_body)

    if username:
        send_to_modchat(
            f'DM from <{reddit_url.format("/u/" + username)}|u/{username}> -- '
            f'*{message.subject}*:\n{message.body}', cfg
        )
        logging.info(
            f'Received DM from {username}. \n Subject: '
            f'{message.subject}\n\nBody: {message.body} '
        )
    else:
        send_to_modchat(
            f'DM with no author -- '
            f'*{message.subject}*:\n{message.body}', cfg
        )
        logging.info(
            f'Received DM with no author. \n Subject: '
            f'{message.subject}\n\nBody: {message.body} '
        )
