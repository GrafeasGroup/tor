import pytest
import redis.exceptions

from tor.core.config import config as SITE_CONFIG


@pytest.mark.skip
def test_read_secrets_from_filesystem():
    """Secret data has been read from the filesystem
    """
    assert SITE_CONFIG.bugsnag_api_key is not None


def test_config_structure():
    """Config singleton is structured as expected
    """
    assert isinstance(SITE_CONFIG.video_domains, list)
    assert isinstance(SITE_CONFIG.audio_domains, list)
    assert isinstance(SITE_CONFIG.image_domains, list)

    assert isinstance(SITE_CONFIG.video_formatting, str)
    assert isinstance(SITE_CONFIG.audio_formatting, str)
    assert isinstance(SITE_CONFIG.image_formatting, str)

    assert isinstance(SITE_CONFIG.header, str)

    assert isinstance(SITE_CONFIG.subreddits_to_check, list)
    assert isinstance(SITE_CONFIG.upvote_filter_subs, dict)
    assert isinstance(SITE_CONFIG.no_link_header_subs, list)

    assert isinstance(SITE_CONFIG.tor_mods, list)

    assert isinstance(SITE_CONFIG.perform_header_check, bool)
    assert isinstance(SITE_CONFIG.debug_mode, bool)

    assert isinstance(SITE_CONFIG.no_gifs, list)

    assert isinstance(SITE_CONFIG.OCR, bool)

    assert isinstance(SITE_CONFIG.bugsnag_api_key, str) or \
        SITE_CONFIG.bugsnag_api_key is None


def test_redis_config_property():
    try:
        assert SITE_CONFIG.redis, 'Does not observe lazy loader'
    except redis.exceptions.ConnectionError:
        pass

    # Check stubbing with derivations of BaseException
    type(SITE_CONFIG).redis = property(lambda x: (_ for _ in ()).throw(
        NotImplementedError('Redis was disabled')))

    with pytest.raises(NotImplementedError):
        SITE_CONFIG.redis.ping()
