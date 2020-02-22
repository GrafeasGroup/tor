import random

import bugsnag
import logging
import praw
from praw.models import Comment as RedditComment, Message as RedditMessage

from tor import __BOT_NAMES__
from tor.core.blossom import get_blossom_volunteer_from_post
from tor.core.config import Config
from tor.core.helpers import (_, clean_id, get_parent_post_id, get_wiki_page,
                              reports, send_to_modchat, send_reddit_reply,
                              get_or_create_blossom_post_from_response)
from tor.core.strings import reddit_url
from tor.core.users import User
from tor.core.validation import _footer_check
from tor.core.validation import verified_posted_transcript
from tor.helpers.flair import flair, flair_post, update_user_flair
from tor.helpers.reddit_ids import is_removed
from tor.strings import translation

i18n = translation()


def coc_accepted(post: RedditComment, cfg: Config) -> bool:
    """
    Verifies that the user is has accepted the Code of Conduct as listed
    at https://www.reddit.com/r/transcribersofreddit/wiki/codeofconduct

    :param post: the Comment object containing the claim.
    :param cfg: the global config dict.
    :return: True if the user has accepted the Code of Conduct, False if they
        haven't.
    """
    volunteer = get_blossom_volunteer_from_post(post, cfg)
    if not volunteer:
        return False
    else:
        return volunteer['accepted_coc']


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

    volunteer = get_blossom_volunteer_from_post(post, cfg)
    if not volunteer:
        usercreate = cfg.blossom.post(
            '/volunteer/', data={"username": post.author.name}
        )
        if usercreate.status_code != 200:
            raise Exception(
                f'Something went wrong with user creation: {usercreate.json()}'
            )
        # f strings don't like dictionary lookups for some reason
        user_id = usercreate.json()['data']['id']
        resp = cfg.blossom.patch(f'/volunteer/{user_id}/', data={'accepted_coc': True})
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
        if volunteer.get('accepted_coc') is False:
            # So... we got a user in the response but they don't have
            # `accepted_coc` set. We should never hit this state because
            # we only create the user when they accept the code of conduct.
            # Basically the only way to hit this case is if the patch call
            # above errors out. Unlikely, but worth planning for. Just mark
            # them again and move on.
            user_id = volunteer['id']
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
    something_went_wrong = i18n['responses']['general']['oops']

    if first_time:
        claim_success = i18n['responses']['claim']['first_claim_success']
    else:
        claim_success = i18n['responses']['claim']['success']

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        logging.debug('Received `claim` on post we do not own. Ignoring.')
        return

    if not coc_accepted(post, cfg):
        # do not cache this page. We want to get it every time.
        send_reddit_reply(
            post, please_accept_coc.format(get_wiki_page('codeofconduct', cfg))
        )
        return

    blossom_post = cfg.blossom.get("/submission/", params={
        "submission_id": clean_id(top_parent.fullname)
    })

    blossom_post = get_or_create_blossom_post_from_response(
        blossom_post, top_parent, cfg
    )

    # both of these fields need to be empty before we can process.
    if blossom_post.get('claimed_by') is not None:
        send_reddit_reply(post, already_claimed)
        # ignore whatever flair is on Reddit -- override it with what it
        # should be
        flair_post(top_parent, flair.in_progress)
        return

    if blossom_post.get('completed_by') is not None:
        send_reddit_reply(post, claim_already_complete)
        flair_post(top_parent, flair.completed)
        return

    # we made it past the code of conduct check, so we know that they're
    # registered and good to go.
    volunteer = get_blossom_volunteer_from_post(post, cfg)

    resp = cfg.blossom.post(
        f"/submission/{blossom_post['id']}/claim/", data={"v_id": volunteer["id"]}
    )
    if resp.get('result') == "success":
        send_reddit_reply(post, claim_success)
        flair_post(top_parent, flair.in_progress)
        logging.info(
            f'Claim on ID {top_parent.fullname} by {post.author} successful'
        )
    else:
        send_reddit_reply(post, something_went_wrong)
        bugsnag.notify(
            Exception("Failed to finish claim!"),
            context="process_claim",
            meta_data={"blossom_response": resp}
        )


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
    done_already_completed = i18n['responses']['done']['already_completed']
    done_not_claimed_by_you = i18n['responses']['done']['not_claimed_by_you']

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        logging.info('Received `done` on post we do not own. Ignoring.')
        return

    blossom_post = cfg.blossom.get("/submission/", params={
        "submission_id": clean_id(top_parent.fullname)
    })

    blossom_post = get_or_create_blossom_post_from_response(
        blossom_post, top_parent, cfg
    )

    if not override and not verified_posted_transcript(post, cfg):
        # we need to double-check these things to keep people
        # from gaming the system
        logging.info(
            f'Post {top_parent.fullname} does not appear to have a '
            f'post by claimant {post.author}. Hrm... '
        )
        send_reddit_reply(post, done_cannot_find_transcript)
        return

    # Control flow:
    # If we have an override, we end up here to complete.
    # If there is no override, we go into the validation above.
    # If the validation fails, post the apology and return.
    # If the validation succeeds, come down here.

    resp = cfg.blossom.post(f"/submission/{blossom_post['id']}/done/", data={
        "username": post.author.name,
        "mod_override": override
    })
    if resp.status_code == 200:
        if override:
            logging.info('Moderator override starting!')
        # noinspection PyUnresolvedReferences
        if alt_text_trigger:
            send_reddit_reply(
                post,
                'I think you meant `done`, so here we go!\n\n'
                f'{done_completed_transcript}'
            )
        else:
            send_reddit_reply(post, done_completed_transcript)
        update_user_flair(post, cfg)
        logging.info(
            f'Post {top_parent.fullname} completed by {post.author}!'
        )

        flair_post(top_parent, flair.completed)
    elif resp.status_code == 409:
        send_reddit_reply(post, done_already_completed)
        flair_post(top_parent, flair.completed)
    elif resp.status_code == 412:
        if "not yet been claimed" in resp.get('message'):
            send_reddit_reply(post, done_still_unclaimed)
            flair_post(top_parent, flair.unclaimed)
        else:
            send_reddit_reply(post, done_not_claimed_by_you)
            flair_post(top_parent, flair.in_progress)


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
    unclaim_failure_post_you_didnt_claim = i18n['responses']['unclaim']['post_you_didnt_claim']
    something_went_wrong = i18n['responses']['general']['oops']

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        logging.info('Received `unclaim` on post we do not own. Ignoring.')
        return

    blossom_response = cfg.blossom.get("/submission/", params={
        "submission_id": clean_id(top_parent.fullname)
    })

    blossom_post = get_or_create_blossom_post_from_response(blossom_response, top_parent, cfg)

    unclaim_response = cfg.blossom.post(
        f"/submission/{blossom_post['id']}/unclaim/",
        data={"username": post.author.name}
    )

    if unclaim_response.status_code == 412:
        post.reply(_(unclaim_still_unclaimed))
        flair_post(top_parent, flair.unclaimed)
    elif unclaim_response.status_code == 406:
        send_reddit_reply(post, unclaim_failure_post_you_didnt_claim)
        flair_post(top_parent, flair.in_progress)
    elif unclaim_response.status_code == 409:
        send_reddit_reply(post, unclaim_failure_post_already_completed)
    elif unclaim_response.status_code == 200:
        # the unclaim was successful, we just need to figure out what message
        # to respond with
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
                send_reddit_reply(post, unclaim_success_with_report)
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
            send_reddit_reply(post, unclaim_success_without_report)
            return

        # guess there's nothing special, just give them the regular line
        flair_post(top_parent, flair.unclaimed)
        send_reddit_reply(post, unclaim_success)
        return

    # if we hit this, we fell through the other options and something went wrong.
    send_reddit_reply(post, something_went_wrong)
    bugsnag.notify(
        Exception("Failed to finish unclaim!"),
        context="process_unclaim",
        meta_data={"blossom_response": blossom_response}
    )


def process_thanks(post, cfg):
    thumbs_up_gifs = i18n['urls']['thumbs_up_gifs']
    youre_welcome = i18n['responses']['general']['youre_welcome']
    send_reddit_reply(post, youre_welcome.format(random.choice(thumbs_up_gifs)))


def process_wrong_post_location(post, cfg):
    transcript_on_tor_post = i18n['responses']['general']['transcript_on_tor_post']
    if _footer_check(post, cfg, new_reddit=True):
        transcript_on_tor_post += i18n['responses']['general']['new_reddit_transcript']

    send_reddit_reply(post, transcript_on_tor_post)


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
