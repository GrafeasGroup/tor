import os

import yaml

with open(os.path.join(os.path.dirname(__file__), 'en_US.yml'), 'r') as f:
    db = yaml.safe_load(f)

yt_transcript_url = db['urls']['yt_transcript_url'].strip()
ToR_link = db['urls']['ToR_link'].strip()
