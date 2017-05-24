from addict import Dict

__version__ = '2.6.1'

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
