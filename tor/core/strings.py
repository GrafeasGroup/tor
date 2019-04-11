import os

import yaml

with open(os.path.join(os.path.dirname(__file__), '..', 'strings', 'en_US.yml'), 'r') as f:
    db = yaml.safe_load(f)


bot_footer = db['responses']['bot_footer'].strip()
reddit_url = db['urls']['reddit_url'].strip()
