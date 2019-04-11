import tor.strings.translation

db = tor.strings.translation(lang='en_US')


bot_footer = db['responses']['bot_footer'].strip()
reddit_url = db['urls']['reddit_url'].strip()
