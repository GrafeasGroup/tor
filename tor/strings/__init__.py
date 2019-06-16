import os

import yaml


def translation(lang='en_US'):
    with open(os.path.join(os.path.dirname(__file__), f'{lang}.yml'), 'r') as f:
        return yaml.safe_load(f)
