[![Stories in Ready](https://badge.waffle.io/itsthejoker/TranscribersOfReddit.png?label=ready&title=Ready)](http://waffle.io/itsthejoker/TranscribersOfReddit)

# Transcribers Of Reddit

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

## Moderator Bot (`/u/transcribersofreddit`)

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

### Running Moderator Bot

```
$ tor-moderator
# => [daemon mode + logging]
```

## Apprentice Bot (`/u/transcribot`)

Monitoring daemon (via Redis queue):

- Pull job (by post id) off of queue:
  - Download image
  - OCR the image
  - If OCR successful:
    - Post OCR-ed content to post on /r/TranscribersOfReddit in 9000 character chunks
  - Delete local copy of image

### Running Apprentice Bot

```
$ tor-apprentice
# => [daemon mode + logging]
```

## Archiver Bot (`/u/ToR_archivist`)

Monitoring daemon (via subreddit's /new feed):

- For each completed or unclaimed post:
   - Retrieve in which subreddit the original post was made
   - If the post is older than the configured amount of time for this subreddit:
     - Remove the post
     - If it was completed, make the same post in the archive subreddit

### Running Archiver Bot

```
$ tor-archivist
# => [daemon mode + logging]
```

# Contributing

See [`CONTRIBUTING.md`](/CONTRIBUTING.md) for more.
