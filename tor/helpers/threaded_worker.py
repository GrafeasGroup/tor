# After a lengthy discussion with @thelonelyghost, it became apparent that we're
# fully expecting to completely throw away this codebase when we finish the
# rewrite for celery. Therefore, ugly-ass hacks are allowed in the name of
# making the current bots faster if at all possible. Is it maintainable?
# Not really, but that's a conscious decision on our part. Feast your eyes
# upon the ugliness... and know that we are sorry.

import logging
import random
import string
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

import requests
from typing import Dict
from typing import List

from tor.core.posts import process_post


def check_domain_filter(item: Dict, config) -> bool:
    """
    Validate that a given post is actually one that we can (or should) work on
    by checking the domain of the post against our filters.

    :param item: a dict which has the post information in it.
    :param config: the config object.
    :return: True if we can work on it, False otherwise.
    """

    return True if (
        item['domain'] in config.image_domains or
        item['domain'] in config.audio_domains or
        item['domain'] in config.video_domains or
        item['subreddit'] in config.subreddits_domain_filter_bypass
    ) else False


def get_subreddit_posts(sub: str) -> [List, None]:

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

    def parse_json_posts(posts: Dict) -> List:
        trimmed_links = list()
        number_of_posts = 10
        posts_raw = posts['data']['children']
        posts_raw = posts_raw[:number_of_posts]  # cut the list from 25 to 10
        for item in posts_raw:
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
                    'domain': item['domain'],
                    'ups': item['ups'],
                    'locked': item['locked'],
                    'archived': item['archived'],
                    'author': item.get('author', None),
                    'url': item['url']
                })
        return trimmed_links

    headers = {
        'User-Agent': generate_user_agent()
    }
    url = 'https://www.reddit.com/r/{}/new/.json'.format(sub)
    result = requests.get(url, headers=headers).json()
    # we have two states here: one has the data we want and the other is an
    # error state. The error state looks like this:
    # {'message': 'Too Many Requests', 'error': 429}

    if result.get('error', None):
        logging.warning('hit error state for {}'.format(sub))
        return []
    return parse_json_posts(result)


def threaded_check_submissions(config):
    """
    Single threaded PRAW performance:
    finished in 56.75446701049805s

    Single threaded json performance:
    finished in 16.70485234260559s

    multi-threaded json performance:
    finished in 1.3632569313049316s
    """
    subreddits = config.subreddits_to_check

    total_posts = list()
    # by not specifying a maximum number of threads, ThreadPoolExecutor will
    # grab the CPU count of the current machine and multiply it by 5, allowing
    # us to keep sane limits wherever we're running.
    with ThreadPoolExecutor() as executor:
        jobs = list()
        for sub in subreddits:
            jobs.append(executor.submit(get_subreddit_posts, sub))
        for f in as_completed(jobs):
            try:
                data = f.result()
                total_posts += data
            except Exception as exc:
                logging.warning('an exception was generated: {}'.format(exc))

    for item in total_posts:
        if check_domain_filter(item, config):
            process_post(item, config)
