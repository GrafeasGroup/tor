import os

import yaml

with open(os.path.join(os.path.dirname(__file__), 'en_US.yml'), 'r') as f:
    db = yaml.safe_load(f)

discovered_submit_title = db['posts']['discovered_submit_title'].strip()
rules_comment = db['posts']['rules_comment'].strip()
yt_already_has_transcripts = db['posts']['yt_already_has_transcripts'].strip()
