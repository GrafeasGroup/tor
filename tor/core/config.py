# Load configuration regardless of if bugsnag is setup correctly
try:
    import bugsnag
except ImportError:
    bugsnag = None

from tor import __version__


class BaseConfig:
    '''
    '''

    # Whitelisted domains
    domains = []

    formatting = ''


class VideoConfig(BaseConfig):
    '''
    '''


class AudioConfig(BaseConfig):
    '''
    '''


class ImageConfig(BaseConfig):
    '''
    '''


class Subreddit:
    '''
    '''

    def __init__(self):
        '''
        '''
        # TODO: set if upvote filter is needed per-subreddit

    def needs_upvote_filter(self):
        '''
        '''


class Config:
    '''
    '''
    media = {
        'audio': AudioConfig,
        'video': VideoConfig,
        'image': ImageConfig,
    }
    mods = []
    subreddits = []

    bugsnag_api_key = None
    slack_api_url = None
    header = ''

    no_gifs = []

    perform_header_check = True
    debug_mode = False

    # Global flag to enable/disable placing the triggers
    # for the OCR bot
    OCR = True


try:
    Config.bugsnag_api_key = open('bugsnag.key').readline().strip()
except FileNotFoundError:
    Config.bugsnag_api_key = None

try:
    Config.slack_api_url = open('slack.key').readline().strip()
except FileNotFoundError:
    Config.slack_api_url = None


# ----- Compatibility -----
config = Config
config.video_domains = []
config.audio_domains = []
config.image_domains = []

config.video_formatting = ''
config.audio_formatting = ''
config.image_formatting = ''
config.header = ''

config.subreddits_to_check = []
config.upvote_filter_subs = {}
config.no_link_header_subs = []

config.tor_mods = []

config.perform_header_check = True
config.debug_mode = False

# section for gifs
config.no_gifs = []

# global flag to enable / disable placing the triggers
# for the OCR bot
config.OCR = True

# configure bugsnag logging
try:
    config.bs_api_key = open('bugsnag.key').readline().strip()
except FileNotFoundError:
    config.bs_api_key = None

if bugsnag and config.bs_api_key:
    bugsnag.configure(
        api_key=config.bs_api_key,
        app_version=__version__
    )

# load slack API url
try:
    config.slack_api_url = open('slack.key').readline().strip()
except FileNotFoundError:
    config.slack_api_url = None
