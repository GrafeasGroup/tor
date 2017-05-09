# TranscribersOfReddit

This is the source code for the set of bots that run under the usernames listed below. Together, they all assist in the running or r/TranscribersOfReddit, which is privileged to have the incredibly important job of organizing crowd-sourced transcriptions of images, video, and audio. 

* u/transcribersofreddit: the automated owner and warden of r/TranscribersOfReddit.
* u/transcribot: a companion bot that monitors a Redis queue, downloads, and attempts to OCR images to assist the human transcribers.

The ToR bots are designed to be as light on local resources as they can possibly be, though there are some external requirements.

* Redis (tracking completed posts and queue system)
* Tesseract (OCR solution used by u/transcribot)

### Note:
This code is not complete. The praw.ini file is required to run the bots and contains such information as the useragents and various secrets. It is built for Python 3.6.

# Process
Current functionality overview:

u/transcribersofreddit:

* check the inbox
  * if there's a username mention, grab the ID of the post above the one that called us and make a new post on ToR for it
  * if there's a process call, like `claim` or `done`, then apply that to the post that it's on if it's applicable
* for each subreddit that has opted in, loop through their /new feed for things that match our domain filters for audio, video, and images
  * if something is found, grab the url and post it back to ToR
* repeat

Run with `python -m tor.main`.

u/transcribot:

* monitor a Redis queue for new posts to work on
  * if one is found, download the image
  * otherwise, sleep
* attempt to OCR the image provided by u/transcribersofreddit
  * if there is no result, delete the image and sleep
* delete the image, then load the post by u/ToR
* break the transcription into 9000 character chunks and make replies on u/ToR's post so the volunteers can access them
* repeat

Run with `python -m tor.ocr`.


This package is in rapid development while bugs are being ironed out.
