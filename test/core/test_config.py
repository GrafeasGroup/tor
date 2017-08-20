import os

import pytest

from tor.core.config import config as SITE_CONFIG


@pytest.mark.skipif('secrets' in os.environ.get('TEST_SKIP', ''),
                    reason='Ignoring secrets check due to override')
def test_read_secrets_from_filesystem():
    '''Secret data has been read from the filesystem
    '''
    assert SITE_CONFIG.bugsnag_api_key is not None
    assert SITE_CONFIG.slack_api_url is not None


def test_config_structure():
    '''Config singleton is structured as expected
    '''
    assert type(SITE_CONFIG.video_domains) is list
    assert type(SITE_CONFIG.audio_domains) is list
    assert type(SITE_CONFIG.image_domains) is list

    assert type(SITE_CONFIG.video_formatting) is str
    assert type(SITE_CONFIG.audio_formatting) is str
    assert type(SITE_CONFIG.image_formatting) is str

    assert type(SITE_CONFIG.header) is str

    assert type(SITE_CONFIG.subreddits_to_check) is list
    assert type(SITE_CONFIG.upvote_filter_subs) is dict
    assert type(SITE_CONFIG.no_link_header_subs) is list

    assert type(SITE_CONFIG.tor_mods) is list

    assert type(SITE_CONFIG.perform_header_check) is bool
    assert type(SITE_CONFIG.debug_mode) is bool

    assert type(SITE_CONFIG.no_gifs) is list

    assert type(SITE_CONFIG.OCR) is bool

    assert type(SITE_CONFIG.bugsnag_api_key) is str or \
        SITE_CONFIG.bugsnag_api_key is None

    assert type(SITE_CONFIG.slack_api_url) is str or \
        SITE_CONFIG.slack_api_url is None
