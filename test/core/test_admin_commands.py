import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from tor.core.admin_commands import process_override, is_moderator


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
    config = MagicMock()
    config.tor_mods = ["asdf", "qwer"]
    reply = MagicMock()
    reply.author = "qwer"

    assert is_moderator(reply.author, config) is True


def test_from_moderator_false():
    config = MagicMock()
    config.tor_mods = ["asdf", "qwer"]
    reply = MagicMock()
    reply.author = "poiu"

    assert is_moderator(reply, config) is False


@pytest.mark.xfail(reason="Unmaintained test")
@patch("tor.core.user_interaction.process_done")
@patch("tor_core.helpers.clean_id", return_value="1234")
def test_process_override_not_moderator(mock_clean_id, mock_process_done):
    # for use with anything that requires a reply object

    config = MagicMock()
    config.no_gifs = ["asdf", "qwer"]
    config.tor_mods = ["asdf"]
    config.r = reddit
    config.tor = tor

    with patch("tor_core.helpers.clean_id"):
        process_override(message(), config)

    message.reply.assert_called_once()
    assert mock_process_done.call_count == 0


@pytest.mark.skip(reason="Unfinished test implementation")
@patch("tor.core.admin_commands.is_moderator", return_value=True)
@patch("tor.core.user_interaction.process_done")
def test_process_override_not_moderator2(mock_process_done):
    # for use with anything that requires a reply object

    config = MagicMock()
    config.no_gifs = ["asdf", "qwer"]
    config.tor_mods = ["asdf"]
    config.r = reddit
    config.tor = tor
    with patch("tor_core.helpers.clean_id"):
        # pytest.set_trace()
        process_override(message(), config)

    message.reply.assert_called_once()
    mock_process_done.assert_called_once()
