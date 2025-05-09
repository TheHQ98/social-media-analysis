import requests
from datetime import datetime, timezone
import redis
from flask import current_app

# Configuration constants
CONFIG_MAP = "bluesky-config"
REDIS_TAGS_LIST = "bluesky:tags"
LIMIT = 40  # Number of posts to fetch per request

# Redis and Queue configuration
REDIS_HOST = "redis-headless.redis.svc.cluster.local"
REDIS_PORT = 6379
QUEUE_ENDPOINT = "http://router.fission.svc.cluster.local/enqueue/bluesky"


def config(k: str) -> str:
    """
    Reads configuration from config map file
    """
    with open(f'/configs/default/{CONFIG_MAP}/{k}', 'r') as f:
        return f.read()


def load_session():
    """
    Initialize a Bluesky session by authenticating with the provided credentials.
    Returns the access JWT token if successful, None otherwise.
    """
    username = config('BSKY_USERNAME')
    password = config('BSKY_APP_PASSWORD')

    if not username or not password:
        current_app.logger.error("Error: Missing configuration BSKY_USERNAME or BSKY_APP_PASSWORD.")
        return None

    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": username, "password": password}

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
            "sensitive": False,
            "favouritesCount": post.get("likeCount", 0),
            "repliesCount": post.get("replyCount", 0),
            "tags": [search_term],
            "url": f"https://bsky.app/profile/{post.get('author', {}).get('handle', '')}/post/{uri.split('/')[-1]}",
            "account": {
                "id": post.get("author", {}).get("did", ""),
                "username": post.get("author", {}).get("handle", ""),
                "createdAt": "1970-01-01T00:00:00Z",
                "followersCount/linkKarma": 0,
                "followingCount/commentKarma": 0
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
    """
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Get the current search term from Redis
    search_term = r.lpop(REDIS_TAGS_LIST)
    if not search_term:
        current_app.logger.warning("No more search terms in Redis list.")
        return

    url = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept-Language": "en"
    }

    params = {
        "q": search_term,
        "sort": "latest",
        "limit": LIMIT
    }

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()

        posts = data.get("posts", [])
        if not posts:
            current_app.logger.warning(f"No posts found for term '{search_term}'")
            return

        # Process each post and send to queue
        for post in posts:
            post_data = convert_bluesky_post_to_target_format(post, search_term)
            requests.post(QUEUE_ENDPOINT, json=post_data, timeout=5)

    except Exception as e:
        current_app.logger.error(f"Error during fetch: {e}")

    finally:
        r.rpush(REDIS_TAGS_LIST, search_term)


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
