import os

import yaml

with open(os.path.join(os.path.dirname(__file__), 'en_US.yml'), 'r') as f:
    id_already_handled_in_db = yaml.safe_load(f)['debug']['id_already_handled_in_db'].strip()
