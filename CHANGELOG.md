# Changelog

We follow [Semantic Versioning](http://semver.org/) as a way of measuring stability of an update. This
means we will never make a backwards-incompatible change within a major version of the project.

## Unreleased

- Fix mod interventions to not prevent normal user commands from being executed (by @arfie)
- Change the user commands structure (by @arfie)

## v3.4.0 (2017-12-11)

- Send inbox messages to Slack if they don't match any of the commands (by @arfie)
- Send message to Slack on phrases that may need mod intervention (by @thelonelyghost)
- Allow blacklisting of people (by @perryprog)
- Add new command system (by @perryprog)
- Use the same colors for subreddit flairs as on Discord, depending on number of completed transcriptions (by @itsthejoker)
- Send message to Slack when flairing a post as Meta (by @arfie)
- Handles common typo `deno` as `done` (by @itsthejoker)

## v3.3.0 (2017-11-22)

- Enable alternate validation method to get around spam filter nuking posts (by @itsthejoker)

## v3.2.0 (2017-11-7)

- Update inbox handler to increase handling speed
- Update inbox handler to increase legibility and modularity
- Guard every comment reply in case it gets deleted
- Prunes unneeded dependencies from before tor_core extraction
- Defers bot reference in `praw.ini` and whether in debug mode from environment variables (by @thelonelyghost)

## v3.1.1 (2017-10-25)
- Minor bug fix, the bot would reply that the config was reloaded when it really wasn't.

## v3.1.0 (2017-10-14)
- Now processing inbox messages in the correct order
- Adds support for pulling all submissions from specific subreddits

## v3.0.4 (2017-10-12)

- Handle top-level post replies the same as comment replies

## v3.0.3 (2017-10-01)

- Removes ability to summon across Reddit
- Adds ability to PM users with stock message
- Updates Slack notification messages

## v3.0.2 (2017-09-20)

- Fixes bug with parsing messages from Reddit itself

## v3.0.1 (2017-09-05)

- Adds Travis CI support, enforcing support for python 3.6
- Updates docs for `pip install` using a git url
- Adds CLI tool `tor-moderator` to PATH (instead of `python tor/main.py`)
- Splits to multiple requirements.txt files, depending on usage
- `python setup.py test` defers to PyTest as the framework
- Initial attempts at automated test support
- Moves parts of `tor.strings` into `tor_core`
- Moves flair flair helpers into `tor_core`
- Post title is truncated if longer than 250 characters
- Better method dependency tracking (e.g., passing `config.r` instead of whole `config`)

## v3.0.0 (2017-08-20)

- Updates PRAW (Reddit API) library: v4.4.0 -> v5.0.1
- Extracts major parts of `tor.core` into [`tor_core`](https://github.com/GrafeasGroup/tor_core)
- Moves `tor-archivist` bot to [`ToR_Archivist`](https://github.com/GrafeasGroup/tor_archivist)
- Moves `tor-apprentice` bot to [`ToR_OCR`](https://github.com/GrafeasGroup/tor_ocr)
- Reverts dependency management change (pass entire `config` object again)
- Disable self-update directive to bot (does not yet work)
- Adds directive 'ping' to check if bot is alive
- Adds 'Meta' flair for posts by author who isn't a mod or known bot
- Rewrite `tor-moderator` to use bot framework in `tor_core`
- Rule change to have user transcript require footer instead of header

## v2.7.1 (2017-07-01)

- Modify date logic and fix config loading for archivist bot
- adds css_flair dict for easier interaction with css (by @itsthejoker)

## v2.7.0 (2017-07-01)

- Adds `setup.py` for pip packaging
- Fixes linting errors
- Removes imports and non-essential, mutating functions from `tor/__init__.py`
- Adds automated testing, starting with configuration object
- Significant rewording of `README.md` for clarity
- Add `bin/run` as user-friendly editing for task runner (see [`.git/safe/../../bin` PATH protocol](https://twitter.com/tpope/status/165631968996900865))
- Basics for a bot automatically removing and archiving old posts (by @arfie)
- Updated `README.md` with information on u/ToR_archivist (by @arfie)

## v2.6.14 (2017-06-07)

- Started logging changes into CHANGELOG.md
- [Some changes before this point may not be included]
