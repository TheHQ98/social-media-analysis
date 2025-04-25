import json
import time
import os
import random
from datetime import datetime, timezone
from mastodon import Mastodon
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from keybert import KeyBERT

load_dotenv()
TAGS = ["melbourne", "sydney", "brisbane", "adelaide", "perth", "hobart", "darwin", "canberra"]
LIMIT = 40
MAX_TOTAL = 100
SAVE_FILE = "aus_cost_of_living_random_keywords.json"

kw_model = KeyBERT()

def config(k: str) -> str:
    value = os.getenv(k)
    if value is None:
        raise ValueError(f"Missing config: {k}")
    return value.strip()

def clean_text(text):
    return BeautifulSoup(text or "", "html.parser").get_text()

def extract_keywords(text, top_n=4):
    keyphrases = kw_model.extract_keywords(text, top_n=top_n, stop_words='english')
    return [kw[0] for kw in keyphrases]

def fetch_post_data(post, selected_tag):
    content = clean_text(post.get("content", ""))
    keywords = extract_keywords(content, top_n=4)
    return {
        "platform": "Mastodon",
        "version": 1.1,
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "sentiment": None,
        "sentimentLabel": None,
        "keywords": keywords,
        "data": {
            "id": post.get("id"),
            "createdAt": post.get("created_at").isoformat() + "Z" if post.get("created_at") else None,
            "content": post.get("content"),
            "sensitive": post.get("sensitive", False),
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
                "createdAt": post["account"]["created_at"].isoformat() + "Z" if post["account"].get("created_at") else None,
                "followersCount": post["account"].get("followers_count", 0),
                "followingCount": post["account"].get("following_count", 0),
                "statusesCount": post["account"].get("statuses_count", 0),
                "bot": post["account"].get("bot"),
                "note": post["account"].get("note", "")
            }
        }
    }

def append_posts_to_file(posts, file_path):
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    existing.extend(posts)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(posts)} posts to {file_path}")



def main():
    access_token = config('ACCESS_TOKEN')
    api_base = config('API_BASE_URL')

    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=api_base,
        request_timeout=10
    )

    total = 0
    collected = []
    seen_ids = set()

    while total < MAX_TOTAL:
        selected_tag = random.choice(TAGS)
        print(f"Fetching posts tagged #{selected_tag}...")

        try:
            posts = mastodon.timeline_hashtag(selected_tag, limit=LIMIT)
        except Exception as e:
            print(f"API failed for #{selected_tag}: {e}")
            time.sleep(3)
            continue

        if not posts:
            print(f"No posts found for #{selected_tag}")
            continue

        batch = []
        for post in posts:
            post_id = post["id"]
            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)
            batch.append(fetch_post_data(post, selected_tag))

        if batch:
            collected.extend(batch)
            total += len(batch)
            print(f"Collected {len(batch)} new posts (Total: {total})")

        time.sleep(1)

    append_posts_to_file(collected, SAVE_FILE)
    print(f"Finished! Total {total} unique posts saved to {SAVE_FILE}")

if __name__ == "__main__":
    main()
