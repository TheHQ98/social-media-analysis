"""
Collect data from mastodon.au
Using timeline_public, which means get the latest mastodon posts
Finally, send the data to the enqueue/mastodon in redis
"""

from datetime import datetime
from mastodon import Mastodon
import requests
from flask import current_app

LIMIT = 40
CONFIG_MAP = "masto-config"
QUEUE_ENDPOINT = "http://router.fission.svc.cluster.local/enqueue/mastodon"


def config(k: str) -> str:
    """
    Reads configuration from config map file
    """
    with open(f'/configs/default/{CONFIG_MAP}/{k}', 'r') as f:
        return f.read()


def fetch_post_data(post):
    """
    Process the raw data, only keep uniformly customised data structures
    :param post: original post data
    :return: processed post data struct
    """
    data = {
        "id": post.get("id"),
        "createdAt": post.get("created_at").isoformat() + "Z" if post.get("created_at") else None,
        "content": post.get("content"),
        "sensitive": post.get("sensitive", False),
        "favouritesCount": post.get("favourites_count", 0),
        "repliesCount": post.get("replies_count", 0),
        "tags": [t["name"] for t in post.get("tags", [])],
        "url": post.get("url"),

        "account": {
            "id": post["account"].get("id"),
            "username": post["account"].get("username"),
            "createdAt": post["account"]["created_at"].isoformat() + "Z"
            if post["account"].get("created_at") else None,
            "followersCount/linkKarma": post["account"].get("followers_count", 0),
            "followingCount/commentKarma": post["account"].get("following_count", 0)
        }
    }

    return {
        "platform": "Mastodon",
        "version": 1.1,
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "sentiment": None,
        "sentimentLabel": None,
        "keywords": [],
        "data": data
    }


def fetch_posts(limit):
    """
    Get data from mastodon posts, and return processed data
    :param limit: int, maximum number of posts to fetch that mastodon allowed at once
    :return: list of mastodon posts
    """

    # get token and url from CONFIG_MAP
    access_token = config('ACCESS_TOKEN')
    api_base = config('API_BASE_URL')

    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=api_base
    )

    posts = mastodon.timeline_public(limit=limit)
    results = []

    for post in posts:
        results.append(fetch_post_data(post))

    return results


def main():
    # fetch number of limit post
    posts = fetch_posts(limit=LIMIT)

    # send to enqueue/mastodon one by one
    for post in posts:
        try:
            requests.post(
                url=QUEUE_ENDPOINT,
                json=post,
                timeout=5
            )
        except Exception as e:
            current_app.logger.error(f"Error pushing to queue: {e}")

    return "OK: fetched mastodon posts"


if __name__ == "__main__":
    main()
