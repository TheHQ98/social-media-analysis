import json
import time
from datetime import datetime, timedelta, timezone
from mastodon import Mastodon
import requests
from flask import current_app

LIMIT = 40
YEARS = 3
TAG = "trump"


def config(k: str) -> str:
    """
    Reads configuration from masto-config file
    """
    with open(f'/configs/default/masto-config/{k}', 'r') as f:
        return f.read()


def fetch_post_data(post):
    data = {
        "id": post.get("id"),
        "createdAt": post.get("created_at").isoformat() + "Z" if post.get("created_at") else None,
        "content": post.get("content"),
        "sensitive": post.get("sensitive", False),
        "spoilerText": post.get("spoiler_text", ""),
        "language": post.get("language"),
        "visibility": post.get("visibility", "public"),
        "favouritesCount": post.get("favourites_count", 0),
        "reblogsCount": post.get("reblogs_count", 0),
        "repliesCount": post.get("replies_count", 0),
        "tags": [t["name"] for t in post.get("tags", [])],
        "url": post.get("url"),

        "account": {
            "id": post["account"].get("id"),
            "username": post["account"].get("username"),
            "acct": post["account"].get("acct"),
            "displayName": post["account"].get("display_name"),
            "createdAt": post["account"]["created_at"].isoformat() + "Z"
            if post["account"].get("created_at") else None,
            "followersCount": post["account"].get("followers_count", 0),
            "followingCount": post["account"].get("following_count", 0),
            "statusesCount": post["account"].get("statuses_count", 0),
            "bot": post["account"].get("bot"),
            "note": post["account"].get("note", "")
        }
    }

    return {
        "platform": "Mastodon",
        "version": 1.0,
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "sentiment": None,
        "data": data
    }


def fetch_posts(limit):
    access_token = config('ACCESS_TOKEN')
    api_base = config('API_BASE_URL')

    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=api_base
    )

    posts = mastodon.timeline_public(limit=limit)
    # posts = mastodon.timeline_hashtag("AFL", limit=limit, local=True)
    results = []

    for post in posts:
        results.append(fetch_post_data(post))

    return results


def fetch_tags_and_send_posts():
    access_token = config('ACCESS_TOKEN')
    api_base = config('API_BASE_URL')

    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=api_base
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=YEARS * 365)
    max_id = None
    sent = 0

    while True:
        posts = mastodon.timeline_hashtag(
            TAG,
            limit=40,
            max_id=max_id
        )

        if not posts:
            break

        for post in posts:
            if post["created_at"] < cutoff:
                return

            doc = fetch_post_data(post)

            try:
                res = requests.post(
                    url="http://router.fission.svc.cluster.local/enqueue/mastodon",
                    json=doc,
                    timeout=5
                )
                sent += 1

            except Exception as e:
                current_app.logger.error(f"Error pushing to queue: {e}")

        max_id = int(posts[-1]["id"]) - 1
        time.sleep(0.5)


def main():
    # fetch number of limit post
    posts = fetch_posts(limit=LIMIT)
    # fetch_tags_and_send_posts()

    # send to enqueue/mastodon
    for post in posts:
        try:
            res = requests.post(
                url="http://router.fission.svc.cluster.local/enqueue/mastodon",
                json=post,
                timeout=5
            )
        except Exception as e:
            current_app.logger.error(f"Error pushing to queue: {e}")

    return "OK: fetched mastodon posts"


if __name__ == "__main__":
    main()
