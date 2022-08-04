import datetime
import os

import bugsnag
from blossom_wrapper import BlossomAPI
from dotenv import load_dotenv
from praw import Reddit
from praw.models import Subreddit
from praw.models.reddit.subreddit import ModeratorRelationship
from slackclient import SlackClient
from typing import Dict, List, Union

from tor import __root__, __version__
from tor.core import cached_property


load_dotenv()

# Pull the IDs of the Slack channels
SLACK_DEFAULT_CHANNEL_ID = os.getenv("SLACK_DEFAULT_CHANNEL_ID", "")
SLACK_COC_ACCEPTED_CHANNEL_ID = os.getenv("SLACK_COC_ACCEPTED_CHANNEL_ID", "")
SLACK_REMOVED_POST_CHANNEL_ID = os.getenv("SLACK_REMOVED_POST_CHANNEL_ID", "")
SLACK_FORMATTING_ISSUE_CHANNEL_ID = os.getenv("SLACK_FORMATTING_ISSUE_CHANNEL_ID", "")


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
    bugsnag_api_key = ""

    # Templating string for the header of the bot post
    header = ""

    no_gifs: List[str] = []

    perform_header_check = True
    debug_mode = False

    last_post_scan_time = datetime.datetime(1970, 1, 1, 1, 1, 1)
    last_set_meta_flair_time = datetime.datetime(1970, 1, 1, 1, 1, 1)

    @cached_property
    def blossom(self):
        return BlossomAPI(
            email=os.environ["BLOSSOM_EMAIL"],
            password=os.environ["BLOSSOM_PASSWORD"],
            api_key=os.environ["BLOSSOM_API_KEY"],
            api_base_url=os.environ["BLOSSOM_API_URL"],
        )

    @cached_property
    def tor(self) -> Subreddit:
        if self.debug_mode:
            return self.r.subreddit("ModsOfTor")
        else:
            return self.r.subreddit("transcribersofreddit")

    @cached_property
    def modchat(self):
        return SlackClient(os.getenv("SLACK_API_KEY", None))

    # Compatibility
    core_version = __version__
    video_domains: List[str] = []
    audio_domains: List[str] = []
    image_domains: List[str] = []
    video_formatting = ""
    audio_formatting = ""
    image_formatting = ""
    upvote_filter_subs: Dict[str, float] = {}
    no_link_header_subs: List[str] = []


try:
    Config.bugsnag_api_key = open("bugsnag.key").readline().strip()
except OSError:
    Config.bugsnag_api_key = os.getenv("BUGSNAG_API_KEY", "")

if bugsnag and Config.bugsnag_api_key:
    bugsnag.configure(
        api_key=Config.bugsnag_api_key,
        app_version=__version__,
        project_root=__root__,
    )


# ----- Compatibility -----
config = Config()
