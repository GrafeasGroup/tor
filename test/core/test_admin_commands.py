from unittest.mock import MagicMock, patch

import pytest

from tor.core.admin_commands import from_moderator, process_override

tor = MagicMock()


class Object(object):
    pass


class message(object):
    reply = MagicMock()
    body = MagicMock()
    author = MagicMock()
    parent_id = MagicMock()


class reddit(MagicMock):
    comment = MagicMock()


def test_from_moderator_true():
    # enable dot notation to match what it's looking for
    config = Object()
    config.tor_mods = ['asdf', 'qwer']
    reply = Object()
    reply.author = 'qwer'

    assert from_moderator(reply, config) is True


def test_from_moderator_false():
    config = Object()
    config.tor_mods = ['asdf', 'qwer']
    reply = Object()
    reply.author = 'poiu'

    assert from_moderator(reply, config) is False


@pytest.mark.xfail(reason='Unmaintained test')
@patch('tor.core.user_interaction.process_done')
@patch('tor.core.helpers.clean_id', return_value='1234')
def test_process_override_not_moderator(mock_clean_id, mock_process_done):
    # for use with anything that requires a reply object

    config = Object()
    config.no_gifs = ['asdf', 'qwer']
    config.tor_mods = ['asdf']
    config.r = reddit
    config.tor = tor

    with patch('tor.core.helpers.clean_id'):
        process_override(message(), config)

    message.reply.assert_called_once()
    assert mock_process_done.call_count == 0


@pytest.mark.skip(reason='Unfinished test implementation')
@patch('tor.core.admin_commands.from_moderator', return_value=True)
@patch('tor.core.user_interaction.process_done')
def test_process_override_not_moderator2(mock_process_done, asd):
    # for use with anything that requires a reply object

    config = Object()
    config.no_gifs = ['asdf', 'qwer']
    config.tor_mods = ['asdf']
    config.r = reddit
    config.tor = tor
    with patch('tor.core.helpers.clean_id'):
        # pytest.set_trace()
        process_override(message(), config)

    message.reply.assert_called_once()
    mock_process_done.assert_called_once()
