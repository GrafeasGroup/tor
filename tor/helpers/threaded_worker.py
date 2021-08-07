import logging
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List

import beeline
import requests

from tor.core.config import Config
from tor.core.posts import process_post, PostSummary
from tor.strings import translation

log = logging.getLogger()
i18n = translation()


def check_domain_filter(item: Dict, cfg: Config) -> bool:
    """
    Validate that a given post is actually one that we can (or should) work on
    by checking the domain of the post against our filters.

    :param item: a dict which has the post information in it.
    :param cfg: the config object.
    :return: True if we can work on it, False otherwise.
    """
    if item['domain'] in cfg.image_domains:
        return True
    if item['domain'] in cfg.audio_domains:
        return True
    if item['domain'] in cfg.video_domains:
        return True
    if item['subreddit'] in cfg.subreddits_domain_filter_bypass:
        return True

    return False


@beeline.traced_thread
def get_subreddit_posts(sub: str) -> List[PostSummary]:
    def generate_user_agent() -> str:
        """
        Reddit routinely blocks / throttles common user agents. The easiest way
        to deal with that is to (nicely) generate a partially unique user-agent
        in an easy-to-follow pattern in case they decide that they do want to
        block us for this.
        :return: A complete user agent string.
        """
        return (
            '0.1.0.ToR.Client.Thread.{}.ID.{} (contact u/itsthejoker)'.format(
                random.randrange(0, 30),
                ''.join(
                    [random.choice(string.ascii_lowercase) for _ in range(6)]
                ),
            )
        )

    def parse_json_posts(posts: Dict) -> List[PostSummary]:
        trimmed_links: List[PostSummary] = []
        for item in posts['data']['children'][:10]:  # last 10 posts
            # there are only two top level keys here; kind (comment / post) and
            # data. No reason to keep the kind because we're only pulling posts.
            item = item['data']
            if not item['is_self']:
                trimmed_links.append({
                    'subreddit': item['subreddit'],
                    'name': item['name'],  # remember, this is the ID: t3_8swl2n
                    'title': item['title'],
                    'permalink': item['permalink'],
                    'is_nsfw': item['over_18'],
                    'is_gallery': hasattr(item, 'is_gallery'),
                    'domain': item['domain'],
                    'ups': item['ups'],
                    'locked': item['locked'],
                    'archived': item['archived'],
                    'author': item.get('author', None),
                    'url': item['url']
                })
        return trimmed_links

    with beeline.tracer(name='get_subreddit_posts'):
        beeline.add_context({'subreddit': sub})

        headers = {
            'User-Agent': generate_user_agent()
        }
        url = f'https://www.reddit.com/r/{sub}/new/.json'
        result = requests.get(url, headers=headers).json()
        # we have two states here: one has the data we want and the other is an
        # error state. The error state looks like this:
        # {'message': 'Too Many Requests', 'error': 429}

        if result.get('error', None):
            log.warning('hit error state for {}'.format(sub))
            return []
        return parse_json_posts(result)


def is_time_to_scan(cfg: Config) -> bool:
    return datetime.now() > cfg.last_post_scan_time + timedelta(seconds=45)


@beeline.traced(name='threaded_check_submissions')
def threaded_check_submissions(cfg: Config) -> None:
    """
    Single threaded PRAW performance:
    finished in 56.75446701049805s

    Single threaded json performance:
    finished in 16.70485234260559s

    multi-threaded json performance:
    finished in 1.3632569313049316s
    """

    if not is_time_to_scan(cfg):
        # we're still within the defined time window from the last time we
        # looked for new posts. We'll try again later.
        return

    cfg.last_post_scan_time = datetime.now()

    subreddits = cfg.subreddits_to_check

    total_posts: List[PostSummary] = []
    # by not specifying a maximum number of threads, ThreadPoolExecutor will
    # grab the CPU count of the current machine and multiply it by 5, allowing
    # us to keep sane limits wherever we're running.

    with ThreadPoolExecutor() as executor:
        jobs = list()
        for sub in subreddits:
            jobs.append(executor.submit(get_subreddit_posts, sub))
        for f in as_completed(jobs):
            try:
                data: List[PostSummary] = f.result()
                total_posts += data
            except Exception as exc:
                log.warning('an exception was generated: {}'.format(exc))
    total_posts = [post for post in total_posts if check_domain_filter(post, cfg)]
    unseen_post_urls = cfg.blossom.post(
        "/submission/bulkcheck/",
        data={
            "urls": [
                i18n["urls"]["reddit_url"].format(post["permalink"])
                for post in total_posts
            ]
        }
    ).json()
    unseen_posts = [
        post for post in total_posts
        if i18n["urls"]["reddit_url"].format(post["permalink"]) in unseen_post_urls
    ]
    for item in unseen_posts:
        process_post(item, cfg)
