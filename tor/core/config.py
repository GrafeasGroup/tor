import datetime
import logging
import os
import random

from tor import __root__, __version__
from tor.core import __HEARTBEAT_FILE__, cached_property

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

    # List of mods of ToR, fetched later using PRAW
    mods = []

    # A collection of Subreddit objects, injected later based on
    # subreddit-specific rules
    subreddits_to_check = []
    subreddits_domain_filter_bypass = []

    # API keys for later overwriting based on contents of filesystem
    bugsnag_api_key = ''

    # Templating string for the header of the bot post
    header = ''
    modchat = None  # the actual modchat instance

    no_gifs = []

    perform_header_check = True
    debug_mode = False

    # delay times for removing posts; these are used by u/ToR_archivist
    archive_time_default = None
    archive_time_subreddits = {}

    # Global flag to enable/disable placing the triggers
    # for the OCR bot
    OCR = True

    # Name of the bot
    name = None
    bot_version = '0.0.0'  # this should get overwritten by the bot process
    heartbeat_logging = False

    last_post_scan_time = datetime.datetime(1970, 1, 1, 1, 1, 1)

    @cached_property
    def redis(self):
        """
        Lazy-loaded redis connection
        """
        from redis import StrictRedis
        import redis.exceptions

        try:
            url = os.environ.get('REDIS_CONNECTION_URL',
                                 'redis://localhost:6379/0')
            conn = StrictRedis.from_url(url)
            conn.ping()
        except redis.exceptions.ConnectionError:
            logging.fatal("Redis server is not running")
            raise
        return conn

    @cached_property
    def tor(self):
        if self.debug_mode:
            return self.r.subreddit('ModsOfTor')
        else:
            return self.r.subreddit('transcribersofreddit')

    @cached_property
    def heartbeat_port(self):
        try:
            with open(__HEARTBEAT_FILE__, 'r') as port_file:
                port = int(port_file.readline().strip())
            logging.debug('Found existing port saved on disk')
            return port
        except OSError:
            pass

        while True:
            port = random.randrange(40000, 40200)  # is 200 ports too much?
            if self.redis.sismember('active_heartbeat_ports', port) == 0:
                self.redis.sadd('active_heartbeat_ports', port)

                with open(__HEARTBEAT_FILE__, 'w') as port_file:
                    port_file.write(str(port))
                logging.debug(f'generated port {port} and saved to disk')

                return port


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
config.core_version = __version__
config.video_domains = []
config.audio_domains = []
config.image_domains = []

config.video_formatting = ''
config.audio_formatting = ''
config.image_formatting = ''

config.upvote_filter_subs = {}
config.no_link_header_subs = []

config.archive_time_default = 0
config.archive_time_subreddits = {}

config.tor_mods = []

# section for gifs
config.no_gifs = []

# enables debug information for the cherrypy heartbeat server
config.heartbeat_logging = False

config.modchat = Config.modchat
