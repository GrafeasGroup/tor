import os

import bugsnag
from addict import Dict

__version__ = '2.5.2'

config = Dict()

config.video_domains = []
config.audio_domains = []
config.image_domains = []

config.video_formatting = ''
config.audio_formatting = ''
config.image_formatting = ''
config.header = ''

config.subreddits_to_check = []

config.tor_mods = []

config.perform_header_check = True
config.debug_mode = False

# section for gifs
config.no_gifs = []

# global flag to enable / disable placing the triggers
# for the OCR bot
config.OCR = True

# configure bugsnag logging
bs_api_key = os.environ.get('BUGSNAG_API_KEY')

if bs_api_key:
    bugsnag.configure(
        api_key=bs_api_key,
        project_root=os.getcwd(),
    )
