import os
import toml

try:
    with open(os.path.join(os.path.dirname(__file__), '..', 'pyproject.toml'), 'r') as f:
        __version__ = toml.load(f)['tool']['poetry']['version']
except OSError:
    __version__ = 'unknown'

__SELF_NAME__ = 'transcribersofreddit'
__BOT_NAMES__ = os.environ.get('BOT_NAMES', 'transcribersofreddit,tor_archivist,transcribot').split(',')
__root__ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
