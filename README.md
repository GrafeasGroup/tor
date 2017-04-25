#TranscribersOfReddit

This is the source code for the bot that runs under the username of u/transcribersofreddit. It is the automated owner and warden of r/TranscribersOfReddit, and is privileged to have the incredibly important job of organizing crowd-sourced transcripts of images, video, and audio.

###Note:
This code is not complete. The praw.ini file is required to run the bot and contains such information as the useragent and various secrets.

#Process
The ToR bot is designed to be as light on local resources as it can possibly be, only requiring Redis for the set() functionality and to track completed posts so they aren't started again. Current functionality overview:

* check the inbox
  * if there's a username mention, grab the ID of the post above the one that called us and make a new post on ToR for it
  * if there's a process call, like `claim` or `done`, then apply that to the post that it's on if it's applicable
* for each subreddit that has opted in, loop through their /new feed for things that match our domain filters for audio, video, and images
  * if something is found, grab the url and post it back to ToR
* repeat

This bot is in rapid development while bugs are being ironed out.

###Other
This code is, for right now, copyright Joe Kaufeld, all rights reserved.