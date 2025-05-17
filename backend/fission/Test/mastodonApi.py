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
    with open(f'./configs/default/masto-config/{k}', 'r') as f:
        return f.read().strip()


def fetch_post_data(post):
    def validate_type(name, value, expected_type):
        if not isinstance(value, expected_type):
            raise TypeError(f"Field '{name}' should be {expected_type}, got {type(value)}")

    def safe_int(value, name):
        if isinstance(value, (int, str)):
            try:
                return int(value)
            except:
                raise TypeError(f"Field '{name}' should be int-compatible, got {type(value)}")
        raise TypeError(f"Field '{name}' should be int or str, got {type(value)}")

    try:
        # Validate and convert top-level fields
        post_id = safe_int(post.get("id"), "id")
        created_at = post.get("created_at")
        if created_at is not None and not hasattr(created_at, "isoformat"):
            raise TypeError("Field 'created_at' must be datetime-like")

        tags = post.get("tags", [])
        if not isinstance(tags, list):
            raise TypeError("Field 'tags' should be a list")
        for tag in tags:
            if not isinstance(tag, dict) or "name" not in tag:
                raise TypeError("Each tag must be a dict with a 'name' field")

        account = post.get("account")
        if not isinstance(account, dict):
            raise TypeError("Field 'account' must be a dict")

        account_id = safe_int(account.get("id"), "account.id")
        account_created_at = account.get("created_at")
        if account_created_at is not None and not hasattr(account_created_at, "isoformat"):
            raise TypeError("Field 'account.created_at' must be datetime-like")

        # Build structured output
        data = {
            "id": post_id,
            "createdAt": created_at.isoformat() + "Z" if created_at else None,
            "content": post.get("content"),
            "sensitive": post.get("sensitive", False),
            "spoilerText": post.get("spoiler_text", ""),
            "language": post.get("language"),
            "visibility": post.get("visibility", "public"),
            "favouritesCount": post.get("favourites_count", 0),
            "reblogsCount": post.get("reblogs_count", 0),
            "repliesCount": post.get("replies_count", 0),
            "tags": [t["name"] for t in tags],
            "url": post.get("url"),

            "account": {
                "id": account_id,
                "username": account.get("username"),
                "acct": account.get("acct"),
                "displayName": account.get("display_name"),
                "createdAt": account_created_at.isoformat() + "Z" if account_created_at else None,
                "followersCount": account.get("followers_count", 0),
                "followingCount": account.get("following_count", 0),
                "statusesCount": account.get("statuses_count", 0),
                "bot": account.get("bot"),
                "note": account.get("note", "")
            }
        }

        return {
            "platform": "Mastodon",
            "version": 1.0,
            "fetchedAt": datetime.utcnow().isoformat() + "Z",
            "sentiment": None,
            "data": data
        }

    except Exception as e:
        print(f"Skipped malformed post: {e}")
        raise 

def fetch_posts(limit):
    access_token = config('ACCESS_TOKEN')
    api_base = config('API_BASE_URL')

    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=api_base
    )

    posts = mastodon.timeline_public(limit=limit)
    results = []

    for post in posts:
        raw = post._raw if hasattr(post, '_raw') else post
        processed = fetch_post_data(raw)
        if processed:
            results.append(processed)

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
        posts = mastodon.timeline_hashtag(TAG, limit=10, max_id=max_id)

        if not posts:
            break

        for post in posts:
            raw = post._raw if hasattr(post, '_raw') else post

            if raw["created_at"] < cutoff:
                return

            doc = fetch_post_data(raw)
            if not doc:
                continue

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

        max_id = int(raw["id"]) - 1
        time.sleep(0.5)


def run_test_mode(testfile=None):
    if testfile:
        print(f"📂 Loading test cases from file: {testfile}")
        with open(testfile, "r", encoding="utf-8") as f:
            test_cases = json.load(f)
    else:
        print("Manual test mode. Paste JSON input (empty line to finish):")
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
            if processed:
                print(json.dumps(processed, indent=2))
            else:
                print("Invalid format. Post skipped.")
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
