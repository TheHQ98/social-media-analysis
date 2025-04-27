"""
This program used to fetch posts by tag from mastodon.au and send the data to redis
1. Through the timeline_hashtag continuously grab the latest posts up to specified END_DATA by
specified TAG and paging
2. Unify the formatting of each post to extract the key information
3. Use Redis to record the max_id of each tag to achieve breakpoints
4. When a tag backtracks to END_DATE, it automatically removed the current tag from the list,
and switched to the next tag
"""

from datetime import datetime, timezone
from mastodon import Mastodon, MastodonNetworkError
import requests
from flask import current_app
import redis

REDIS_TAGS_LIST = "mastodon:tags"

LIMIT = 40
END_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
CONFIG_MAP = "masto-config"
REDIS_HOST = "redis-headless.redis.svc.cluster.local"
REDIS_PORT = 6379
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


def fetch_tags_and_send_posts():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # get the tag from redis list, if no more tag in list, then top
    tag = r.lindex(REDIS_TAGS_LIST, 0)
    if not tag:
        current_app.logger.warning("No more tags in Redis list.")
        return

    # get the last recorded max_id from redis list
    redis_key = f"mastodon:max_id:{tag}"
    max_id_str = r.get(redis_key)
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

    # fetch data from mastodon.au
    try:
        posts = mastodon.timeline_hashtag(
            tag,
            limit=LIMIT,
            max_id=max_id,
            remote=True,
        )
    except MastodonNetworkError as e:
        current_app.logger.error(f"Mastodon Network Error：{e}")
        return

    if not posts:
        current_app.logger.warning("No more posts")
        return

    # process raw data, and send to redis used by enqueue
    for record in posts:
        post = fetch_post_data(record)

        created_str = post["data"]["createdAt"]
        created_dt = datetime.fromisoformat(
            created_str.replace("Z", "")
        ).date() if created_str else None

        # checking for exceeding the specified time
        if created_dt and created_dt < END_DATE.date():
            r.lpop(REDIS_TAGS_LIST)
            current_app.logger.warning(f"Touched END_DATE. Removed {tag} from Redis.")
            return

        try:
            requests.post(QUEUE_ENDPOINT, json=post, timeout=5)
        except Exception as e:
            current_app.logger.error(f"Error pushing to queue：{e}")

    # updated max_id and send to redis
    new_max_id = int(posts[-1]["id"]) - 1
    r.set(redis_key, new_max_id)
    current_app.logger.info(f"Updated new max_id={new_max_id}")

    return


def main():
    fetch_tags_and_send_posts()

    return "OK"


if __name__ == "__main__":
    main()
