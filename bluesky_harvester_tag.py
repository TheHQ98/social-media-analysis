import json
import requests
import time
from datetime import datetime, timezone, timedelta
import redis
from flask import current_app
import os
from dotenv import load_dotenv

# Configuration constants
CONFIG_MAP = "bluesky-config"
REDIS_TAGS_LIST = "bluesky:tags"
END_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
LIMIT = 8  # Number of posts to fetch per request

# Redis and Queue configuration
REDIS_HOST = "redis-headless.redis.svc.cluster.local"
REDIS_PORT = 6379
QUEUE_ENDPOINT = "http://router.fission.svc.cluster.local/enqueue/bluesky"

# Bluesky account credentials
BSKY_USERNAME = "upskysun.bsky.social"
BSKY_APP_PASSWORD = "wxlj-hvpk-z67p-3chj"

def load_session():
    """
    Initialize a Bluesky session by authenticating with the provided credentials.
    Returns the access JWT token if successful, None otherwise.
    """
    if not BSKY_USERNAME or not BSKY_APP_PASSWORD:
        current_app.logger.error("Error: Missing configuration BSKY_USERNAME or BSKY_APP_PASSWORD.")
        return None

    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": BSKY_USERNAME, "password": BSKY_APP_PASSWORD}

    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            current_app.logger.error(f"Error: HTTP status code {res.status_code}")
            current_app.logger.error(f"Response content: {res.text}")
            return None
        return res.json()["accessJwt"]
    except Exception as e:
        current_app.logger.error(f"Error during login: {e}")
        return None

def convert_bluesky_post_to_target_format(post, search_term: str) -> dict:
    """
    Convert a Bluesky post to the standardized target format.
    
    Args:
        post (dict): The original Bluesky post data
        search_term (str): The search term used to find this post
        
    Returns:
        dict: Post data in the standardized format
    """
    record = post.get("record", {})
    created_at = record.get("createdAt", "")
    content = record.get("text", "")
    uri = post.get("uri", "")

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"

    doc = {
        "platform": "Bluesky",
        "version": 1.1,
        "fetchedAt": fetched_at,
        "sentiment": None,
        "sentimentLabel": None,
        "keywords": [],
        "data": {
            "id": uri.split("/")[-1],
            "createdAt": created_at,
            "content": content,
            "sensitive": None,
            "favouritesCount": post.get("likeCount", 0),
            "repliesCount": post.get("replyCount", 0),
            "tags": [search_term],
            "url": f"https://bsky.app/profile/{post.get('author', {}).get('handle', '')}/post/{uri.split('/')[-1]}",
            "account": {
                "id": post.get("author", {}).get("did", ""),
                "username": post.get("author", {}).get("handle", ""),
                "createdAt": None,
                "followersCount": None,
                "followingCount": None
            }
        }
    }
    return doc

def fetch_bluesky_posts(token):
    """
    Fetch posts from Bluesky based on search terms stored in Redis.
    
    Args:
        token (str): The authentication token for Bluesky API
        
    The function:
    1. Gets the next search term from Redis
    2. Fetches posts matching the search term
    3. Converts posts to target format
    4. Sends posts to the queue endpoint
    5. Updates the cursor for pagination
    6. Removes search term if end date is reached
    """
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Get the current search term from Redis
    search_term = r.lindex(REDIS_TAGS_LIST, 0)
    if not search_term:
        current_app.logger.warning("No more search terms in Redis list.")
        return

    # Get the last cursor position for pagination
    state_key = f"bluesky:last_cursor:{search_term}"
    last_cursor = r.get(state_key)

    url = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept-Language": "en"
    }

    params = {
        "q": search_term,
        "limit": LIMIT
    }
    if last_cursor:
        params["cursor"] = last_cursor

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()

        posts = data.get("posts", [])
        if not posts:
            current_app.logger.warning(f"No posts found for term '{search_term}'")
            r.lpop(REDIS_TAGS_LIST)
            return

        # Process each post and send to queue
        for post in posts:
            post_data = convert_bluesky_post_to_target_format(post, search_term)
            requests.post(QUEUE_ENDPOINT, json=post_data, timeout=5)

        # Update cursor for pagination
        if data.get("cursor"):
            r.set(state_key, data["cursor"])
            current_app.logger.info(f"Updated {state_key} to {data['cursor']}")

        # Check if we've reached the end date
        if posts:
            oldest_post = min(posts, key=lambda p: p.get("record", {}).get("createdAt", ""))
            created_at = datetime.fromisoformat(oldest_post.get("record", {}).get("createdAt", "").replace("Z", "+00:00"))
            if created_at < END_DATE:
                r.lpop(REDIS_TAGS_LIST)
                current_app.logger.warning(f"Touched END_DATE, removed term '{search_term}'")

    except Exception as e:
        current_app.logger.error(f"Error during fetch: {e}")

def main():
    """
    Main entry point of the script.
    Initializes a Bluesky session and starts fetching posts.
    """
    token = load_session()
    if not token:
        return "Error: Failed to initialize Bluesky session"

    fetch_bluesky_posts(token)
    return "OK"

if __name__ == "__main__":
    main() 