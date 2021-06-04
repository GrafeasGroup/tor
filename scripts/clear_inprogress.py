from datetime import datetime, timedelta

from praw import Reddit
from praw.exceptions import RedditAPIException

r = Reddit('bot2')

current_time = datetime.now()
for x in range(30):
    submissions = r.subreddit("transcribersofreddit").hot(limit=None)
    for item in submissions:
        if item.link_flair_text == 'Unclaimed':
            submission_time = datetime.fromtimestamp(item.created_utc)
            if submission_time < current_time - timedelta(days=1):
                print(f"Removing {item.name}, posted on {str(submission_time)}")
                item.mod.remove()
                # try:
                #     item.reply(
                #         "This submission has been open for at least three days and is listed as in progress"
                #         " -- it has been removed to make room for other submissions in the queue. Please contact"
                #         " itsthejoker if there is an issue."
                #     )
                # except RedditAPIException:
                #     pass
