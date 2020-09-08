import datetime
import os
from typing import Dict, List, Union

from blossom_wrapper import BlossomAPI
from praw import Reddit  # type: ignore
from praw.models import Subreddit  # type: ignore
from praw.models.reddit.subreddit import ModeratorRelationship  # type: ignore
from slackclient import SlackClient  # type: ignore

from tor import __root__, __version__, __SELF_NAME__
from tor.core import cached_property

# Load configuration regardless of if bugsnag is setup correctly
try:
    import bugsnag  # type: ignore
except ImportError:
    # If loading from setup.py or bugsnag isn't installed, we
    # don't want to bomb out completely
    bugsnag = None


class Config(object):
    """
    A singleton object for checking global configuration from
    anywhere in the application
    """

    r: Reddit

    # List of mods of ToR, fetched later using PRAW
    tor_mods: Union[List[str], ModeratorRelationship] = []

    # A collection of Subreddit objects, injected later based on
    # subreddit-specific rules
    subreddits_to_check: List[str] = []
    subreddits_domain_filter_bypass: List[str] = []

    # API keys for later overwriting based on contents of filesystem
    bugsnag_api_key = ''

    # Templating string for the header of the bot post
    header = ''

    no_gifs: List[str] = []

    perform_header_check = True
    debug_mode = False

    # Name of the bot
    name = __SELF_NAME__
    bot_version = __version__

    last_post_scan_time = datetime.datetime(1970, 1, 1, 1, 1, 1)

    @cached_property
    def blossom(self):
        return BlossomAPI(
            email=os.getenv('BLOSSOM_EMAIL'),
            password=os.getenv('BLOSSOM_PASSWORD'),
            api_key=os.getenv('BLOSSOM_API_KEY'),
            api_base_url=os.getenv('BLOSSOM_API_URL'),
        )

    @cached_property
    def tor(self) -> Subreddit:
        if self.debug_mode:
            return self.r.subreddit('ModsOfTor')
        else:
            return self.r.subreddit('transcribersofreddit')

    @cached_property
    def modchat(self):
        return SlackClient(os.getenv('SLACK_API_KEY', None))
    # Compatibility
    core_version = __version__
    video_domains: List[str] = []
    audio_domains: List[str] = []
    image_domains: List[str] = []
    video_formatting = ''
    audio_formatting = ''
    image_formatting = ''
    other_formatting = ''
    upvote_filter_subs: Dict[str, int] = {}
    no_link_header_subs: List[str] = []


try:
    Config.bugsnag_api_key = open('bugsnag.key').readline().strip()
except OSError:
    Config.bugsnag_api_key = os.getenv('BUGSNAG_API_KEY', '')

if bugsnag and Config.bugsnag_api_key:
    bugsnag.configure(
        api_key=Config.bugsnag_api_key,
        app_version=__version__,
        project_root=__root__,
    )


# ----- Compatibility -----
config = Config()
