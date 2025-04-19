import json
from datetime import datetime
from mastodon import Mastodon
from dotenv import load_dotenv
import os


def fetch_posts(limit=5):
    load_dotenv()
    access_token = os.getenv("ACCESS_TOKEN")
    api_base = os.getenv("API_BASE_URL", "https://mastodon.social")

    masto = Mastodon(
        access_token=access_token,
        api_base_url=api_base
    )

    posts = masto.timeline_public(limit=limit)
    results = []

    for post in posts:
        doc = {
            "sensitive": post.get("sensitive"),
            "createdAt": post.get("created_at").isoformat(),
            "content": post.get("content"),
            "sentiment": post.get("sentiment"),
            "filtered": post.get("filtered"),
            "favouritesCount": post.get("favouritesCount"),
            "url": post.get("url"),
            "mentions": [m["acct"] for m in post.get("mentions", [])],
            "inReplyTold": post.get("inReplyTold"),
            "tags": [t["name"] for t in post.get("tags", [])],
            "visibility": post.get("visibility"),
            "inReplyToAccountId": post.get("inReplyToAccountId"),
            "repliesCount": post.get("repliesCount"),
            "editedAt": post.get("edited_at").isoformat() if post.get("edited_at") else None,
            "reblog": post.get("reblog"),
            "spoilerText": post.get("spoiler_text"),
            "reblogsCount": post.get("reblogs_count"),
            "language": post.get("language"),
            "inReplyToId": post.get("in_reply_to_id"),
            "emojis": post.get("emojis", []),
            "card": post.get("card"),
            "uri": post.get("uri"),
            "poll": post.get("poll"),
            "mediaAttachments": [
                {
                    "url": media.get("url"),
                    "previewUrl": media.get("preview_url"),
                    "type": media.get("type"),
                    "meta": media.get("meta")
                }
                for media in post.get("media_attachments", [])
            ],
            "account": {
                "username": post["account"]["username"],
                "createdAt": post["account"].get("created_at").isoformat() if post["account"].get(
                    "created_at") else None,
                "indexable": post["account"].get("indexable"),
                "id": post["account"].get("id"),
                "acct": post["account"]["acct"],
                "displayName": post["account"]["display_name"],
                "url": post["account"]["url"],
                "avatar": post["account"]["avatar"],
                "header": post["account"]["header"],
                "note": post["account"]["note"],
                "followersCount": post["account"]["followers_count"],
                "followingCount": post["account"]["following_count"],
                "statusesCount": post["account"]["statuses_count"],
                "avatarStatic": post["account"].get("avatar_static"),
                "lastStatusAt": post["account"].get("last_status_at"),
                "locked": post["account"].get("locked"),
                "fields": post["account"].get("fields", []),
                "headerStatic": post["account"].get("header_static"),
                "bot": post["account"].get("bot"),
                "hideCollections": post["account"].get("hide_collections"),
                "group": post["account"].get("group"),
                "emojis": post["account"].get("emojis", []),
                "uri": post["account"].get("uri"),
                "discoverable": post["account"].get("discoverable"),
            }
        }

        api_meta = {
            "version": "1.0",
            "type": "Mastodon",
            "fetchedAt": datetime.utcnow().isoformat() + "Z"
        }

        results.append({
            "doc": doc,
            "api": api_meta
        })

    return results


def main():
    posts = fetch_posts(limit=100)  

    output_file = "mastodon_output.ndjson"

    with open(output_file, "w", encoding="utf-8") as f:
        for item in posts:
            f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")

    print(f"saved {len(posts)} posts to {output_file}")


if __name__ == "__main__":
    main()
