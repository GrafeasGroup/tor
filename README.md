[![Stories in Ready](https://badge.waffle.io/TranscribersOfReddit/TranscribersOfReddit.png?label=ready&title=Ready)](http://waffle.io/TranscribersOfReddit/TranscribersOfReddit)
[![BugSnag](https://img.shields.io/badge/errors--hosted--by-Bugsnag-blue.svg)](https://www.bugsnag.com/open-source/)

# Transcribers of Reddit

This is the source code for the set of bots that run under the usernames listed
below. Together, they all assist in the running or /r/TranscribersOfReddit, which
is privileged to have the incredibly important job of organizing crowd-sourced
transcriptions of images, video, and audio.

- `/u/transcribersofreddit`: the automated owner and warden of /r/TranscribersOfReddit.
- `/u/transcribot`: a companion bot that monitors a Redis queue, downloads, and attempts to OCR images to assist the human transcribers.

The ToR bots are designed to be as light on local resources as they can possibly
be, though there are some external requirements.

- Redis (tracking completed posts and queue system)
- Tesseract (OCR solution used by u/transcribot)

> **NOTE:**
>
> This code is not complete. The praw.ini file is required to run the bots and
> contains such information as the useragents and various secrets. It is built
> for Python 3.6.

## Installation

Make sure you have an [up-to-date copy of pip installed](https://pip.pypa.io/en/stable/installing/) and Python 3.6.

Find the [latest release](https://github.com/TranscribersOfReddit/TranscribersOfReddit/releases/latest) and replace `v3.0.1` below with the more up-to-date version.

```
$ git clone https://github.com/TranscribersOfReddit/TranscribersOfReddit.git tor
$ cd tor/
$ git checkout v3.0.1
$ pip install --process-dependency-links .
```

OR

```
$ pip install --process-dependency-links 'git+https://github.com/TranscribersOfReddit/TranscribersOfReddit.git@master#egg=tor'
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

```
$ tor-moderator
# => [daemon mode + logging]
```

## Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.
