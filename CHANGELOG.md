# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

- Track timestamp of last reddit post processed before sending to mod chat (credit: @crhopkins)
- Add missing backslash in unescaped heading string (credit: @MurdoMaclachlan)

## [4.2.4] - 2021-04-05

- Odd error with PRAW necessitates a core library upgrade

## [4.2.3] - 2021-03-24

- Hotfix for private subreddits

## [4.2.2] - 2021-01-17

- Fixes bug introduced by Reddit where bot cannot post on other subs, thus cross-posting capability was removed

## [4.2.1] - 2021-01-06

- Fixes args used in CLI invocation, making testing if it is installed correctly work more smoothly

## [4.2.0] - 2020-12-26

- Includes flair for "topaz" and "jade" levels

## [4.1.0] - 2020-03-03

- Update logging to note the current transcription number and minor testing config changes

## [4.0.0] - 2020-02-29

- Minor typos in bot messages
- Removes heartbeat server
- Adds type annotations to method signatures
- Removes a metric crap-ton of dead code
- Clarifies the logic of what the bot is doing and why, using more semantic names of methods
- Tightens some overly broad interfaces (Only default value of a keyword arg is used? Buh-bye keyword arg, you're now permanently set that way!)
- Uses flake8, mypy, and pytest as part of CI execution
- Replaces Travis CI with GitHub Actions

## [3.12.2] - 2020-02-29

- Fixes bug in build system (Poetry) where command is not generated

## [3.12.1] - 2020-02-29

- Skip mod flags that (somehow) come back as `null`, because obviously human intervention is needed (credit @thelonelyghost)
- Add link to tutorial for first transcriptions (credit @Pf441)
- Mentions donation option in (successful) response to `done` (credit @thelonelyghost)

## [3.12.0] - 2019-12-12

- Replaces `setup.py` with Poetry tooling for development and packaging ease
- Fixes no-author condition if the mods message the bot
- Adds `cancel` as an alias for `unclaim` for user directives to the bot
- Makes inbox triage less English-language dependent
- Offloads more work to Redis instead of Python

## [3.11.2] - 2019-09-14

- Adds missing `package_data` manifest to `setup.py` so it will actually be included when packaging the module (credit @thelonelyghost)

## [3.11.1] - 2019-09-14

- Fixes typo in capitalization of one of the user-facing messages
- Fixes flair colors to level up at (e.g.) 50, not 51 (#96)
- Extend check for transcription in the right place to handle New Reddit editor (credit @itsthejoker)
- Fixes packaging of python module to include data files and up-to-date methods (credit @thelonelyghost)

## [3.11.0] - 2019-06-17

- Add replies to DMs (credit: @davidarchibald)

## [3.10.1] - 2019-06-17

- Fixes history check on users who have submissions stickied to their profile (credit @arfie)
- Fixes youtube auto-transcription attempts erroring out when unable to detect the video id (credit @thelonelyghost)
- Adds clearer indicator for post type to rules comment (credit @itsthejoker)

## [3.10.0] - 2019-06-16

- Fixes [#102](https://github.com/GrafeasGroup/tor/issues/102), adding better guidance for first-time transcribers
- Allows CLI flags like `--help`, `--version`, `--debug`, and `--noop` on `tor-moderator`

## [3.9.0] - 2019-06-16

- Removes remaining references to RocketChat
- Fixes typo in YAML dict name
- Adds more context to Bugsnag events
- Corrects version reported to Bugsnag to be `tor`'s, not `tor.core`'s

## [3.8.0] - 2019-06-16

- Removes Sentry client and dependency
- Replaces strings.py references with YAML

## [3.7.0] - 2019-06-16

- Adds No Operation (NOOP) mode
- Merges in `tor_core` as `tor.core` (Fixes [#150](https://github.com/GrafeasGroup/tor/issues/150))
- Uses `tox` as the default testing mechanism (easier CI and enforces virtualenv sandbox testing)

## [3.6.2] - 2019-06-15

- FIX: `Reddit.user.me` is a method not a property, resulting in stack traces on every attempt to run the bot

## [3.6.1] - 2019-06-07

- HOTFIX release:
  - Makes the (protected) bot names an environment variable we can override in case usernames need to suddenly change
  - Add reference to the currently running bot's username, as determined by Reddit's API

## [3.6.0] - 2018-12-02

- Add handling for `unclaim` comments (credit: @itsthejoker)

## [3.5.0] - 2018-08-19

- Add check to verify the transcription goes to the right place (credit: @itsthejoker)
- Allow dibs to claim a post (credit: @davidarchibald)
- Update Slack messages to include direct links (credit: @pejmanpoh)
- Remove check for incomplete posts (credit: @itsthejoker)
- Add threaded model to update the process of checking for new content (credit: @itsthejoker)
- Move volunteer notifications to their own channel (credit: @itsthejoker)
- Update detection of flair (credit: @itsthejoker)
- Add system to use history of volunteer to validate posts if comment is autoremoved (credit: @itsthejoker)

## [3.4.0] - 2017-12-11

- Send inbox messages to Slack if they don't match any of the commands (credit: @arfie)
- Send message to Slack on phrases that may need mod intervention (credit: @thelonelyghost)
- Allow blacklisting of people (credit: @perryprog)
- Add new command system (credit: @perryprog)
- Use the same colors for subreddit flairs as on Discord, depending on number of completed transcriptions (credit: @itsthejoker)
- Send message to Slack when flairing a post as Meta (credit: @arfie)
- Handles common typo `deno` as `done` (credit: @itsthejoker)

## [3.3.0] - 2017-11-22

- Enable alternate validation method to get around spam filter nuking posts (credit: @itsthejoker)

## [3.2.0] - 2017-11-07

- Update inbox handler to increase handling speed
- Update inbox handler to increase legibility and modularity
- Guard every comment reply in case it gets deleted
- Prunes unneeded dependencies from before tor_core extraction
- Defers bot reference in `praw.ini` and whether in debug mode from environment variables (credit: @thelonelyghost)

## [3.1.1] - 2017-10-25

- Minor bug fix, the bot would reply that the config was reloaded when it really wasn't

## [3.1.0] - 2017-10-14

- Now processing inbox messages in the correct order
- Adds support for pulling all submissions from specific subreddits

## [3.0.4] - 2017-10-12

- Handle top-level post replies the same as comment replies

## [3.0.3] - 2017-10-01

- Removes ability to summon across Reddit
- Adds ability to PM users with stock message
- Updates Slack notification messages

## [3.0.2] - 2017-09-20

- Fixes bug with parsing messages from Reddit itself

## [3.0.1] - 2017-09-05

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

## [3.0.0] - 2017-08-20

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

## [2.7.1] - 2017-07-01

- Modify date logic and fix config loading for archivist bot
- adds css_flair dict for easier interaction with css (credit: @itsthejoker)

## [2.7.0] - 2017-07-01

- Adds `setup.py` for pip packaging
- Fixes linting errors
- Removes imports and non-essential, mutating functions from `tor/__init__.py`
- Adds automated testing, starting with configuration object
- Significant rewording of `README.md` for clarity
- Add `bin/run` as user-friendly editing for task runner (see [`.git/safe/../../bin` PATH protocol](https://twitter.com/tpope/status/165631968996900865))
- Basics for a bot automatically removing and archiving old posts (credit: @arfie)
- Updated `README.md` with information on u/ToR_archivist (credit: @arfie)

## [2.6.14] - 2017-06-07

- Started logging changes into CHANGELOG.md
- [Some changes before this point may not be included]
