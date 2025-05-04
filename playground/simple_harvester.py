import praw
from dotenv import load_dotenv
import os
from datetime import datetime
import json

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)


def fetch_post_data(item):
    author = item.author

    post_data = {
        "id": item.id,
        "createdAt": datetime.utcfromtimestamp(item.created_utc).isoformat() + "Z",
        "content": item.selftext or item.title,
        "sensitive": item.over_18,
        "spoilerText": getattr(item, "spoiler_text", "") or "",
        "language": None,
        "visibility": "public",
        "favouritesCount": item.score,
        "reblogsCount": None,
        "repliesCount": item.num_comments,
        "tags": [item.link_flair_text] if item.link_flair_text else [],
        "url": item.url,
        "account": {
            "id": author.id if author else None,
            "username": author.name if author else None,
            "acct": None,
            "displayName": author.name if author else None,
            "createdAt": (
                    datetime.utcfromtimestamp(author.created_utc).isoformat() + "Z"
            ) if author and hasattr(author, "created_utc") else None,
            "followersCount/linkKarma": getattr(author, "link_karma", None),
            "followingCount/commentKarma": getattr(author, "comment_karma", None),
            "statusesCount": None,
            "bot": False,
            "note": None
        }
    }

    return post_data


for post in reddit.subreddit("afl").hot(limit=5):
    data = fetch_post_data(post)

    envelope = {
        "platform": "Reddit",
        "version": 1.0,
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "sentiment": None,
        "data": data
    }

    print(json.dumps(envelope))
