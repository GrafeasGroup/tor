# Load configuration regardless of if bugsnag is setup correctly
try:
    import bugsnag
except ImportError:
    # If loading from setup.py or bugsnag isn't installed, we
    # don't want to bomb out completely
    bugsnag = None

from tor import __version__


class BaseConfig:
    """
    A base class used for all media-specific settings, e.g.,
    video, audio, image. This is intended to provide a unified
    interface, regardless of the actual media, to ask questions of
    the configuration:

        - What is the formatting string for this media?
        - What domains are whitelisted for this media?

    The inheritance model here is for easy type-checking from tests,
    allowing for validation of an expected interface in a quicker
    manner.

    Specify overridden values on object instantiation for purposes
    of testing and by pulling from remote source (e.g., Reddit Wiki)
    """

    # Whitelisted domains
    domains = []

    formatting = ''


class VideoConfig(BaseConfig):
    """
    Media-specific configuration class for video content

    Initialization should pull from the appropriate Reddit Wiki
    page and fill in the proper values.

    Include any video-specific configuration rules here
    """


class AudioConfig(BaseConfig):
    """
    Media-specific configuration class for audio content

    Initialization should pull from the appropriate Reddit Wiki
    page and fill in the proper values.
    """


class ImageConfig(BaseConfig):
    """
    Media-specific configuration class for image content

    Initialization should pull from the appropriate Reddit Wiki
    page and fill in the proper values.
    """


class Subreddit:
    """
    Subreddit-specific configurations

    Intended for asking questions of specific subreddits

    NOTE: WIP - Do not use in its current form
    """

    def __init__(self):
        """
        WIP - Do not use in production code yet
        """
        # TODO: set if upvote filter is needed per-subreddit

    def needs_upvote_filter(self):
        """
        TODO: fill in method based on subreddit rules
        """


class DefaultSubreddit(Subreddit):
    """
    A default configuration for subreddits that don't require
    special rules
    """


class Config:
    """
    A singleton object for checking global configuration from
    anywhere in the application
    """

    # Media-specific rules, which are fetchable by a dict key. These
    # are intended to be programmatically accessible based on a
    # parameter given instead of hardcoding the media type in a
    # switch-case style of control structure
    media = {
        'audio': AudioConfig(),
        'video': VideoConfig(),
        'image': ImageConfig(),
    }

    # List of mods of ToR, fetched later using PRAW
    mods = []

    # A collection of Subreddit objects, injected later based on
    # subreddit-specific rules
    subreddits = []
    subreddits_to_check = []

    # API keys for later overwriting based on contents of filesystem
    bugsnag_api_key = None
    slack_api_url = None

    # Templating string for the header of the bot post
    header = ''

    no_gifs = []

    perform_header_check = True
    debug_mode = False

    # delay times for removing posts; these are used by u/ToR_archivist
    archive_time_default = None
    archive_time_subreddits = {}

    # Global flag to enable/disable placing the triggers
    # for the OCR bot
    OCR = True


try:
    Config.bugsnag_api_key = open('bugsnag.key').readline().strip()
except OSError:
    Config.bugsnag_api_key = None

if bugsnag and Config.bugsnag_api_key:
    bugsnag.configure(
        api_key=Config.bugsnag_api_key,
        app_version=__version__
    )

try:
    Config.slack_api_url = open('slack.key').readline().strip()
except OSError:
    Config.slack_api_url = None


# ----- Compatibility -----
config = Config
config.video_domains = []
config.audio_domains = []
config.image_domains = []

config.video_formatting = ''
config.audio_formatting = ''
config.image_formatting = ''

config.subreddits_to_check = []
config.upvote_filter_subs = {}
config.no_link_header_subs = []

config.archive_time_default = 0
config.archive_time_subreddits = {}

config.tor_mods = []

# section for gifs
config.no_gifs = []
