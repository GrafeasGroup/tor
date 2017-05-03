class context(object):
    """
    Support object for the bot -- holds data that doesn't have
    anywhere else to go.
    """
    video_domains = []
    audio_domains = []
    image_domains = []

    video_formatting = ''
    audio_formatting = ''
    image_formatting = ''
    header = ''

    subreddits_to_check = []
    # subreddits that we're only getting 100 posts at a time from
    # instead of jump-starting it with 500
    subreddit_members = []
    tor_mods = []

    perform_header_check = True
    debug_mode = False

    # section for gifs
    no_gifs = []

    # global flag to enable / disable placing the triggers
    # for the OCR bot
    OCR = True