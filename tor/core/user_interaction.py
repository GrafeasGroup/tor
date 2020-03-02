import logging
import random

import bugsnag  # type: ignore
from praw.models import Comment, Message  # type: ignore

from tor import __BOT_NAMES__
from tor.core.blossom import ClaimResponse, CocResponse, DoneResponse, UnclaimResponse
from tor.core.config import Config
from tor.core.helpers import (_, clean_id, get_parent_post_id, get_wiki_page,
                              reports, send_reddit_reply, send_to_modchat)
from tor.core.validation import verified_posted_transcript
from tor.helpers.flair import flair, flair_post, update_user_flair
from tor.helpers.reddit_ids import is_removed
from tor.strings import translation

i18n = translation()
log = logging.getLogger(__name__)


def coc_accepted(post: Comment, cfg: Config) -> bool:
    """
    Verifies that the user is in the Redis set "accepted_CoC".

    :param post: the Comment object containing the claim.
    :param cfg: the global config dict.
    :return: True if the user has accepted the Code of Conduct, False if they
        haven't.
    """
    volunteer = cfg.blossom.get_volunteer(post.author.name)

    return volunteer.get('accepted_coc', False)


def process_coc(post: Comment, cfg: Config) -> None:
    """
    Adds the username of the redditor to the db as accepting the code of
    conduct.

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

    response = cfg.blossom.accept_coc(post.author.name)
    if response == CocResponse.ok:
        send_to_modchat(
            f'<{i18n["urls"]["reddit_url"].format("/user/" + post.author.name)}|u/{post.author.name}>'
            f' has just'
            f' <{i18n["urls"]["reddit_url"].format(post.context)}|accepted the CoC!>'
            f' {modchat_emote}',
            cfg,
            channel='new_volunteers'
        )

    process_claim(post, cfg, first_time=True)


def process_claim(post: Comment, cfg: Config, first_time=False) -> None:
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
    url = i18n["urls"]["reddit_url"].format(top_parent.permalink)
    something_went_wrong = i18n['responses']['general']['oops']

    claim_success = i18n['responses']['claim']['first_claim_success' if first_time else 'success']

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        log.debug('Received `claim` on post we do not own. Ignoring.')
        return

    if not coc_accepted(post, cfg):
        # do not cache this page. We want to get it every time.
        send_reddit_reply(post, please_accept_coc.format(get_wiki_page('codeofconduct', cfg)))
        return

    # In order to claim this, Blossom will be the arbiter of whether it is up for grabs
    blossom_post = cfg.blossom.get_post(clean_id(top_parent.fullname))
    if blossom_post.get('id', None) is None:
        blossom_post = cfg.blossom.create_post(reddit_id=clean_id(top_parent.fullname),
                                               reddit_url=top_parent.url,
                                               tor_url=url)

    if blossom_post.get('claimed_by') is not None:
        send_reddit_reply(post, already_claimed)
        # TODO: Fix so people can't reset posts to in-progress again
        flair_post(top_parent, flair.in_progress)
        return

    if blossom_post.get('completed_by') is not None:
        send_reddit_reply(post, claim_already_complete)
        flair_post(top_parent, flair.completed)
        return

    volunteer = cfg.blossom.get_volunteer(str(post.author.name))
    claim = cfg.blossom.claim_post(blossom_post['id'], volunteer['id'])

    if claim == ClaimResponse.ok:
        send_reddit_reply(post, claim_success)
        flair_post(post, flair.in_progress)
        log.info(f'Claim on ID {top_parent.fullname} by {post.author} successful')
        return

    send_reddit_reply(post, something_went_wrong)
    bugsnag.notify(
        Exception('Failed to finish claim'),
        context='process_claim',
        meta_data={'blossom_post': blossom_post, 'volunteer': volunteer},
    )


def process_done(post: Comment, cfg: Config, override=False, alt_text_trigger=False) -> None:
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
    done_already_completed = i18n['responses']['done']['already_complete']
    done_not_claimed_by_you = i18n['responses']['done']['not_claimed_by_you']
    url = i18n["urls"]["reddit_url"].format(top_parent.permalink)
    something_went_wrong = i18n['responses']['general']['oops']

    if alt_text_trigger:
        done_completed_transcript = 'I think you meant `done`, so here we go!\n\n' + done_completed_transcript

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        log.info('Received `done` on post we do not own. Ignoring.')
        return

    blossom_post = cfg.blossom.get_post(clean_id(top_parent.fullname))
    if blossom_post.get('id', None) is None:
        blossom_post = cfg.blossom.create_post(reddit_id=clean_id(top_parent.fullname),
                                               reddit_url=top_parent.url,
                                               tor_url=url)

    if override:
        # We don't care about previous state. The mods have spoken!
        log.info('Moderator override starting')
        done = cfg.blossom.complete_post(blossom_post['id'], post.author.name, override=True)

    ##############################
    # Client-side error checking #
    # -------------------------- #
    elif blossom_post.get('claimed_by') is None:
        send_reddit_reply(post, done_still_unclaimed)
        flair_post(top_parent, flair.unclaimed)
        return
    elif blossom_post.get('claimed_by') != post.author.name:
        send_reddit_reply(post, done_not_claimed_by_you)
        return
    elif blossom_post.get('completed_by') is not None:
        send_reddit_reply(post, done_already_completed)
        flair_post(top_parent, flair.completed)
        return

    ##############################
    # Server-side error checking #
    # -------------------------- #
    elif verified_posted_transcript(post, cfg):
        done = cfg.blossom.complete_post(blossom_post['id'], post.author.name)
    else:
        # we need to double-check these things to keep people
        # from gaming the system
        log.info(f'Post {top_parent.fullname} does not appear to have a post by claimant {post.author}. Hrm... ')
        send_reddit_reply(post, done_cannot_find_transcript)
        return

    #############################
    # Blossom response handling #
    # ------------------------- #
    if done == DoneResponse.ok:
        send_reddit_reply(post, done_completed_transcript)
        update_user_flair(post, cfg)
        log.info(f'Post {top_parent.fullname} completed by {post.author}!')
        flair_post(post, flair.completed)
        return
    elif done == DoneResponse.unclaimed:
        send_reddit_reply(post, done_still_unclaimed)
        flair_post(top_parent, flair.unclaimed)
        return
    elif done == DoneResponse.claimed_by_another:
        send_reddit_reply(post, done_not_claimed_by_you)
        return
    elif done == DoneResponse.already_completed:
        send_reddit_reply(post, done_already_completed)
        flair_post(top_parent, flair.completed)
        return

    send_reddit_reply(post, something_went_wrong)
    bugsnag.notify(
        Exception('Failed to mark transcription as complete'),
        context='process_done',
        meta_data={'blossom_post': blossom_post, 'username': post.author.name, 'response': done},
    )


def process_unclaim(post: Comment, cfg: Config) -> None:
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
    unclaim_success_with_report = i18n['responses']['unclaim']['success_with_report']
    unclaim_success_without_report = i18n['responses']['unclaim']['success_without_report']
    unclaim_failure_post_you_didnt_claim = i18n['responses']['unclaim']['post_you_didnt_claim']
    url = i18n["urls"]["reddit_url"].format(top_parent.permalink)
    something_went_wrong = i18n['responses']['general']['oops']

    # WAIT! Do we actually own this post?
    if top_parent.author.name not in __BOT_NAMES__:
        log.info('Received `unclaim` on post we do not own. Ignoring.')
        return

    blossom_post = cfg.blossom.get_post(clean_id(top_parent.fullname))
    if blossom_post.get('id') is None:
        blossom_post = cfg.blossom.create_post(clean_id(top_parent.fullname), url, top_parent.url)

    unclaim = cfg.blossom.unclaim_post(str(blossom_post['id']), str(post.author.name))

    if unclaim == UnclaimResponse.not_claimed:
        send_reddit_reply(post, unclaim_still_unclaimed)
        flair_post(top_parent, flair.unclaimed)
        return
    elif unclaim == UnclaimResponse.claimed_by_another:
        send_reddit_reply(post, unclaim_failure_post_you_didnt_claim)
        flair_post(top_parent, flair.in_progress)
        return
    elif unclaim == UnclaimResponse.already_completed:
        send_reddit_reply(post, unclaim_failure_post_already_completed)
        return
    elif unclaim == UnclaimResponse.ok:
        fragments = [reports.original_post_deleted_or_locked, reports.post_violates_rules]
        if any(any(fragment in reason for fragment in fragments) for reason in top_parent.user_reports):
            # One of the report reasons on the /r/ToR post contained one of the
            # fragments listed above
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
        transcribable_post = cfg.r.submission(top_parent.id_from_url(top_parent.url))
        if is_removed(transcribable_post):
            top_parent.mod.remove()
            send_to_modchat(
                'Received `unclaim` on an unreported post, but it looks like it '
                'was removed on the parent sub. I removed ours here: {}'.format(
                    top_parent.shortlink),
                cfg,
                channel='removed_posts'
            )
            send_reddit_reply(post, unclaim_success_without_report)
            post.reply(_(unclaim_success_without_report))
            return

        flair_post(top_parent, flair.unclaimed)
        send_reddit_reply(post, unclaim_success_without_report)
        return

    send_reddit_reply(post, something_went_wrong)
    bugsnag.notify(
        Exception('Failed to unclaim transcription'),
        context='process_unclaim',
        meta_data={'blossom_post': blossom_post, 'username': post.author.name, 'response': unclaim},
    )


def process_thanks(post: Comment, cfg: Config) -> None:
    thumbs_up_gifs = i18n['urls']['thumbs_up_gifs']
    youre_welcome = i18n['responses']['general']['youre_welcome']
    send_reddit_reply(post, youre_welcome.format(random.choice(thumbs_up_gifs)))


def process_wrong_post_location(post: Comment, cfg: Config) -> None:
    transcript_on_tor_post = i18n['responses']['general']['transcript_on_tor_post']
    send_reddit_reply(post, transcript_on_tor_post)


def process_message(message: Message, cfg: Config) -> None:
    dm_subject = i18n['responses']['direct_message']['dm_subject']
    dm_body = i18n['responses']['direct_message']['dm_body']

    author = message.author
    username = author.name if author else None

    if author:
        author.message(dm_subject, dm_body)

    if username:
        send_to_modchat(
            f'DM from <{i18n["urls"]["reddit_url"].format("/u/" + username)}|u/{username}> -- '
            f'*{message.subject}*:\n{message.body}', cfg
        )
        log.info(f'Received DM from {username}. \n Subject: {message.subject}\n\nBody: {message.body}')
    else:
        send_to_modchat(
            f'DM with no author -- '
            f'*{message.subject}*:\n{message.body}', cfg
        )
        log.info(f'Received DM with no author. \n Subject: {message.subject}\n\nBody: {message.body}')
