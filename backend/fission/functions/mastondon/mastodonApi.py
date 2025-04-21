import json
from datetime import datetime
from mastodon import Mastodon
from dotenv import load_dotenv
import os
import requests

LIMIT = 5


def config(k: str) -> str:
    """Reads configuration from file."""
    with open(f'/configs/default/masto-config/{k}', 'r') as f:
        return f.read()


def fetch_posts(limit):
    # load_dotenv()
    # access_token = os.getenv("ACCESS_TOKEN")
    # api_base = os.getenv("API_BASE_URL", "https://mastodon.social")
    access_token = config('ACCESS_TOKEN')
    api_base = config('API_BASE_URL')

    masto = Mastodon(
        access_token=access_token,
        api_base_url=api_base
    )

    posts = masto.timeline_public(limit=limit)
    results = []

    for post in posts:
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

        results.append({
            "platform": "Mastodon",
            "version": 1.0,
            "fetchedAt": datetime.utcnow().isoformat() + "Z",
            "sentiment": None,
            "data": data
        })

    return results


def main():
    # Fetch new posts
    posts = fetch_posts(limit=40)

    # Print out
    # for post in posts:
    #     print(
    #         json.dumps(
    #             post,
    #             ensure_ascii=False,
    #             default=str
    #         )
    #     )

    for post in posts:
        try:
            res = requests.post(
                url="http://router.fission.svc.cluster.local/enqueue/mastodon",
                json=post,
                timeout=5
            )
            print(res.status_code, res.text)
        except Exception as e:
            print(f"Error pushing to queue: {e}")

    return "OK"


if __name__ == "__main__":
    main()
