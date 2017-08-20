from addict import Dict
import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from tor.core.admin_commands import from_moderator
from tor.core.admin_commands import process_override


tor = MagicMock()


class message(object):
    reply = MagicMock()
    body = MagicMock()
    author = MagicMock()
    parent_id = MagicMock()


class reddit(MagicMock):
    comment = MagicMock()


def test_from_moderator_true():
    # enable dot notation to match what it's looking for
    config = Dict({'tor_mods': ['asdf', 'qwer']})
    reply = Dict({'author': 'qwer'})

    assert from_moderator(reply, config) is True


def test_from_moderator_false():
    config = Dict({'tor_mods': ['asdf', 'qwer']})
    reply = Dict({'author': 'poiu'})

    assert from_moderator(reply, config) is False


@patch('tor.core.user_interaction.process_done')
@patch('tor.helpers.reddit_ids.clean_id', return_value='1234')
def test_process_override_not_moderator(mock_clean_id, mock_process_done):
    # for use with anything that requires a reply object

    config = Dict({'no_gifs': ['asdf', 'qwer'], 'tor_mods': ["asdf"]})
    with patch('tor.helpers.reddit_ids.clean_id') as qwerty:
        process_override(message(), reddit, tor, config)

    message.reply.assert_called_once()
    assert mock_process_done.call_count == 0


@patch('tor.core.admin_commands.from_moderator', return_value=True)
@patch('tor.core.user_interaction.process_done')
def test_process_override_not_moderator(mock_process_done, asd):
    # for use with anything that requires a reply object

    config = Dict({'no_gifs': ['asdf', 'qwer'], 'tor_mods': ["asdf"]})
    with patch('tor.helpers.reddit_ids.clean_id') as qwerty:
        # pytest.set_trace()
        process_override(message(), reddit, tor, config)

    message.reply.assert_called_once()
    mock_process_done.assert_called_once()
