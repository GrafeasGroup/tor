[![Waffle.io - Ready](https://img.shields.io/waffle/label/GrafeasGroup/tor/ready.svg?colorB=yellow&label=Available%20Issues)](https://waffle.io/GrafeasGroup/tor)
[![Waffle.io - In Progress](https://img.shields.io/waffle/label/GrafeasGroup/tor/in%20progress.svg?colorB=green&label=Issues%20Being%20Worked%20On)](https://waffle.io/GrafeasGroup/tor)
[![Codacy quality](https://img.shields.io/codacy/grade/3b7f08973a9644cc98faea4cbcd71eb2.svg)](https://www.codacy.com/app/GrafeasGroup/tor)
[![Codacy coverage](https://img.shields.io/codacy/coverage/3b7f08973a9644cc98faea4cbcd71eb2.svg)](https://www.codacy.com/app/GrafeasGroup/tor)
[![Travis build status](https://img.shields.io/travis/GrafeasGroup/tor.svg)](https://travis-ci.org/GrafeasGroup/tor)
[![BugSnag](https://img.shields.io/badge/errors--hosted--by-Bugsnag-blue.svg)](https://www.bugsnag.com/open-source/)

# Transcribers of Reddit

This is the source code for the bot moderating and managing several parts of the subreddit
[/r/TranscribersOfReddit](https://reddit.com/r/TranscribersOfReddit) ("ToR"), a community dedicated to transcribing images, audio, and video.
It acts under the username "[/u/TranscribersOfReddit](https://reddit.com/u/TranscribersOfReddit)".

Among other things, this bot handles:

- Posting transcription requests to /r/TranscribersOfReddit as relevant content shows up on partner subreddits
- Responding to transcribers claiming and marking requests as complete
- Augmenting the score of a transcriber upon successful completion of a transcription

## Requirements

Redis (tracking completed posts and queue system)
Reddit API keys

> **NOTE:**
>
> This code is not complete. The praw.ini file is required to run the bots and
> contains such information as the useragents and various secrets. It is built
> for Python 3.6.

## Installation

Make sure you have an [up-to-date copy of pip installed](https://pip.pypa.io/en/stable/installing/) and Python 3.6.

```sh
$ git clone https://github.com/GrafeasGroup/tor.git tor
$ cd tor/
$ pip install --process-dependency-links .
```

OR

```sh
$ pip install --process-dependency-links 'git+https://github.com/GrafeasGroup/tor.git@master#egg=tor-0'
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

## Usage

```sh
$ tor-moderator
# => [daemon mode + logging]
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.
