import os

__version__ = "?????"

__SELF_NAME__ = "transcribersofreddit"
__BOT_NAMES__ = os.environ.get(
    "BOT_NAMES", "transcribersofreddit,tor_archivist,transcribot"
).split(",")
__root__ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
