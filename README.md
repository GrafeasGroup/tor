![GitHub Actions CI status](https://github.com/GrafeasGroup/tor/workflows/automated-tests/badge.svg)

# Transcribers of Reddit

This is the source code for the bot moderating and managing several parts of the subreddit
[/r/TranscribersOfReddit](https://reddit.com/r/TranscribersOfReddit) ("ToR"), a community dedicated to transcribing images, audio, and video. It acts under the username "[/u/TranscribersOfReddit](https://reddit.com/u/TranscribersOfReddit)".

Among other things, this bot handles:

- Posting transcription requests to /r/TranscribersOfReddit as relevant content shows up on partner subreddits
- Responding to transcribers claiming and marking requests as complete
- Augmenting the score of a transcriber upon successful completion of a transcription

## Requirements

- Redis (tracking completed posts and queue system)
- Reddit API keys

> **NOTE:**
>
> This code is not complete. The praw.ini file is required to run the bots and
> contains such information as the useragents and various secrets. It is built
> for Python 3.6.

## Installation

### From release

Given a release in <https://github.com/GrafeasGroup/tor/releases> (perhaps the [latest](https://github.com/GrafeasGroup/tor/releases/latest)), download the attached `.whl` file for your platform/architecture and `pip install` it directly like so:

```sh
$ pip install ./path/to/tor-3.6.1-py3-any-none.whl
```

### From source

Make sure you have an [up-to-date copy of pip installed](https://pip.pypa.io/en/stable/installing/), the latest version of [Poetry](https://www.python-poetry.org/), and Python 3.6.

```sh
$ git clone https://github.com/GrafeasGroup/tor.git tor
$ cd tor/
$ poetry install
```

## Big Picture

Triggered flow (via bot inbox):

- If username mention in a comment:
  - Grab id of mentioned post's parent
  - Make new post on ToR
- If reply to comment (e.g., `claim` or `done`):
  - `claim` - Assigns transcription ownership of the post to the user who first commented this way
  - `done` - Checks for transcription and adjusts flair according to reward system

Monitoring daemon (via subreddit's /new feed):

- For each subreddit that has opted in:
  - Search for audio, video, and image content:
    - Check against whitelist of domain filters
    - Post url to the content back to /r/TranscribersOfReddit

## Build

To build the package from source, start in the base of the repository and run:

```sh
$ poetry build
```

When building is complete, upload everything in the `dist/` directory that was just created as part of the GitHub release.

## Usage

```sh
$ tor-moderator
# => [daemon mode + logging]
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.

## Sponsors

<a href="https://bugsnag.com"><img src="https://raw.githubusercontent.com/GrafeasGroup/tor/master/images/bugsnag_logo_navy.png" alt="Bugsnag logo" width=130></a>
- For providing free error handling through [their open source program](https://www.bugsnag.com/open-source/)
