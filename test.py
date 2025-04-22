import os
import time
from datetime import datetime, timezone

from mastodon import Mastodon, MastodonNetworkError

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
API_BASE_URL = "https://mastodon.au"
TAG = "AFL"
BATCH = 40
START_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)


def count_tag_posts():
    masto = Mastodon(
        access_token=ACCESS_TOKEN,
        api_base_url=API_BASE_URL,
        request_timeout=30
    )

    count = 0
    max_id = None
    retry = 0

    while True:
        try:
            posts = masto.timeline_hashtag(
                TAG,
                limit=BATCH,
                max_id=max_id
            )
            retry = 0
        except MastodonNetworkError:
            retry += 1
            if retry > 3:
                raise
            time.sleep(2 * retry)
            continue

        if not posts:
            break

        for post in posts:
            created = post["created_at"]
            if created < START_DATE:
                print(f"⏹️ stop at {created}")
                return count
            count += 1

        print(f"✅ Fetched {count} posts so far; oldest={posts[-1]['created_at']}")
        max_id = int(posts[-1]["id"]) - 1
        time.sleep(0.5)  # 速率控制


    return count


if __name__ == "__main__":
    total = count_tag_posts()
    print(f"\n🎯 Total #{TAG} local posts since 2022‑01‑01: {total}")
