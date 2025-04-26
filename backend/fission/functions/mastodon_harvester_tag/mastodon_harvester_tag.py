from datetime import datetime, timezone
from mastodon import Mastodon, MastodonNetworkError
import requests
from flask import current_app
import redis

TAG = "sydney"

LIMIT = 40
END_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
CONFIG_MAP = "masto-config"
REDIS_HOST = "redis-headless.redis.svc.cluster.local"
REDIS_PORT = 6379
REDIS_KEY = f"mastodon:max_id:{TAG}"
QUEUE_ENDPOINT = "http://router.fission.svc.cluster.local/enqueue/mastodon"


def config(k: str) -> str:
    """
    Reads configuration from config map file
    """
    with open(f'/configs/default/{CONFIG_MAP}/{k}', 'r') as f:
        return f.read()


def fetch_post_data(post):
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


def fetch_tags_and_send_posts():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    max_id_str = r.get(REDIS_KEY)
    if max_id_str:
        max_id = int(max_id_str)
    else:
        max_id = None

    access_token = config('ACCESS_TOKEN')
    api_base = config('API_BASE_URL')

    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=api_base,
        request_timeout=30
    )

    try:
        posts = mastodon.timeline_hashtag(
            TAG,
            limit=LIMIT,
            max_id=max_id,
            remote=True,
        )
    except MastodonNetworkError as e:
        current_app.logger.error(f"Mastodon Network Error：{e}")
        return "NetworkError"

    if not posts:
        current_app.logger.warning("No more posts!")
        return "NoData"

    for record in posts:
        post = fetch_post_data(record)

        created_str = post["data"]["createdAt"]
        created_dt = datetime.fromisoformat(
            created_str.replace("Z", "")
        ).date() if created_str else None

        if created_dt and created_dt < END_DATE.date():
            current_app.logger.warning("touched END_DATE!")
            return "ReachedEndDate"

        try:
            requests.post(QUEUE_ENDPOINT, json=post, timeout=5)
        except Exception as e:
            current_app.logger.error(f"Error pushing to queue：{e}")

    new_max_id = int(posts[-1]["id"]) - 1
    r.set(REDIS_KEY, new_max_id)
    current_app.logger.info(f"Updated new max_id={new_max_id}")

    return


def main():
    fetch_tags_and_send_posts()

    return f"OK: fetched mastodon posts from {TAG}"


if __name__ == "__main__":
    main()
