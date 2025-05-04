import json
import time
from datetime import datetime, timedelta, timezone
from mastodon import Mastodon
import requests
import argparse

LIMIT = 40
YEARS = 3
TAG = "trump"


def config(k: str) -> str:
    """Reads configuration from file."""
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
            limit=10,
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
                print(f"Sent post ID {doc['data']['id']}: {res.status_code}")
                sent += 1

            except Exception as e:
                print(f"Error pushing to queue: {e}")

        max_id = int(posts[-1]["id"]) - 1
        time.sleep(0.5)

def run_test_mode(testfile=None):
    if testfile:
        print(f"Loading test cases from file: {testfile}")
        with open(testfile, "r", encoding="utf-8") as f:
            test_cases = json.load(f)
    else:
        print("Entering manual test mode. Paste JSON input (empty line to finish):")
        lines = []
        while True:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        try:
            test_cases = [json.loads("\n".join(lines))]
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return

    for idx, test_post in enumerate(test_cases):
        try:
            print(f"\n--- Test Case {idx + 1} ---")
            processed = fetch_post_data(test_post)
            print(json.dumps(processed, indent=2))
        except Exception as e:
            print(f"Error in processing: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Enable test mode with manual input')
    parser.add_argument('--testfile', type=str, help='Provide JSON file for test input')
    args = parser.parse_args()

    if args.test:
        run_test_mode(args.testfile)
    else:
        posts = fetch_posts(limit=LIMIT)
        for post in posts:
            print(post)
            try:
                res = requests.post(
                    url="http://router.fission.svc.cluster.local/enqueue/mastodon",
                    json=post,
                    timeout=5
                )
            except Exception as e:
                print(f"Error pushing to queue: {e}")
        return "OK: fetched mastodon posts"


if __name__ == "__main__":
    main()
