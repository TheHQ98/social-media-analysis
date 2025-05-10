import sys
from datetime import datetime, timezone
import redis
from flask import current_app
import requests
import praw
from praw.models import Submission
from prawcore.exceptions import PrawcoreException, NotFound

# Load a configuration value by key from the mounted config map directory
CONFIG_MAP = "reddit-config2"
REDIS_TAGS_LIST = "reddit:tags"
END_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
LIMIT = 8

# Connect to the server
REDIS_HOST = "redis-headless.redis.svc.cluster.local"
REDIS_PORT = 6379
QUEUE_ENDPOINT = "http://router.fission.svc.cluster.local/enqueue/reddit"

def config(k: str) -> str:
    """
    Reads configuration from config map file
    """
    with open(f'/configs/default/{CONFIG_MAP}/{k}', 'r') as f:
        return f.read()

def initialize_reddit():
    """
    Initializes and returns a PRAW Reddit instance using credentials from config files

    Required config keys:
    - REDDIT_CLIENT_ID: Reddit application Client ID
    - REDDIT_CLIENT_SECRET: Reddit application Client Secret
    - REDDIT_USER_AGENT: Descriptive user agent string (e.g., 'MyBot/1.0 by u/username')

    Returns:
        praw.Reddit: Configured Reddit client
    """
    # Local config keys
    client_id = config('REDDIT_CLIENT_ID')
    client_secret = config('REDDIT_CLIENT_SECRET')
    user_agent = config('REDDIT_USER_AGENT')

    if not all([client_id, client_secret, user_agent]):
        print("Error：Please set up REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT", file=sys.stderr)
        sys.exit(1)

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        reddit.subreddits.popular(limit=1)
        # Test if the credentials are valid by accessing a public endpoint
        print("PRAW initial success")
        return reddit
    except Exception as e:
        current_app.logger.warning(f"PRAW initial failed: {e}")
        sys.exit(1)

def convert_reddit_post_to_target_format(post: Submission, subreddit: str) -> dict:
    """
    Converts a PRAW Submission object into the target JSON structure

    Args:
        post (praw.models.Submission): Reddit post object
        subreddit (str): Name of the current subreddit

    Returns:
        dict: Formatted dictionary matching the target schema
    """
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"
    created_at = (
        datetime.fromtimestamp(post.created_utc, timezone.utc).isoformat(timespec="seconds") + "Z"
        if post.created_utc else None
    )

    author_obj = post.author
    if author_obj is None:
        account_data = {
            "id": None,
            "username": "[Deleted]",
            "createdAt": None,
            "followersCount/linkKarma": None,
            "followingCount/commentKarma": None,
        }
    else:
        try:
            author_username = author_obj.name or "[Unknown]"
            author_id = f"t2_{author_username}"
            author_created = datetime.fromtimestamp(
                author_obj.created_utc, timezone.utc
            ).isoformat(timespec="seconds") + "Z"
            link_karma = comment_karma = 0
        except Exception as e:
            current_app.logger.warning(
                f"[{post.id}] failed to fetch author info: {e}"
            )
            author_id = None
            author_username = "[Unavailable]"
            author_created = None
            link_karma = comment_karma = 0
        # Author's information
        account_data = {
            "id": author_id,
            "username": author_username,
            "createdAt": author_created,
            "followersCount/linkKarma": link_karma,
            "followingCount/commentKarma": comment_karma,
        }
    # Combine title and selftext if the post is a self-post
    content = post.title
    if post.is_self and post.selftext:
        content += f"\n\n{post.selftext}"

    tags = [post.link_flair_text] if post.link_flair_text else []
    if tags:
        tags.append(subreddit.lower())
    # Post's information
    data = {
        "id": post.id,
        "createdAt": created_at,
        "content": content,
        "sensitive": bool(post.over_18),
        "favouritesCount": post.score,
        "repliesCount": post.num_comments,
        "tags": tags,
        "url": f"https://www.reddit.com{post.permalink}",
        "account": account_data,
    }

    return {
        "platform": "Reddit",
        "version": 1.1,
        "fetchedAt": fetched_at,
        "sentiment": None,
        "sentimentLabel": None,
        "keywords": [],
        "data": data,
    }

def convert_comment_to_target_format(comment, subreddit: str) -> dict:
    """
    Converts a PRAW Comment object into the target JSON structure

    Args:
        comment (praw.models.Comment): Reddit comment object
        subreddit (str): Name of the subreddit where the comment was posted

    Returns:
        dict: Formatted dictionary representing the comment, including author and parent post metadata
    """
    fetched_at = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    created_at = datetime.fromtimestamp(comment.created_utc, timezone.utc).isoformat(timespec='seconds') + 'Z'
    post = comment.submission

    author_obj = comment.author
    if author_obj is None:
        account_data = {
            "id": None,
            "username": "[Deleted]",
            "createdAt": None,
            "followersCount/linkKarma": None,
            "followingCount/commentKarma": None,
        }
    else:
        try:
            author_username = author_obj.name or "[Unknown]"
            author_id = f"t2_{author_username}"
            author_created = datetime.fromtimestamp(author_obj.created_utc, timezone.utc).isoformat(
                timespec="seconds") + "Z"
            link_karma = comment_karma = 0
        except (NotFound, PrawcoreException):
            author_id = None
            author_username = "[Unavailable]"
            author_created = None
            link_karma = comment_karma = 0

        account_data = {
            "id": author_id,
            "username": author_username,
            "createdAt": author_created,
            "followersCount/linkKarma": link_karma,
            "followingCount/commentKarma": comment_karma,
        }
    # Add a "comment" tag to seperate from other posts, and also mark the id of its parent post
    tags = [f"comment: {post.id}", subreddit]
    if post.link_flair_text:
        tags.append(post.link_flair_text)

    data = {
        "id": f"comment_{comment.id}",
        "createdAt": created_at,
        "content": comment.body,
        "sensitive": post.over_18,
        "favouritesCount": comment.score,
        "repliesCount": len(comment.replies),
        "tags": tags,
        "url": f"https://www.reddit.com{post.permalink}",
        "account": account_data
    }

    return {
        "platform": "Reddit",
        "version": 1.1,
        "fetchedAt": fetched_at,
        "sentiment": None,
        "sentimentLabel": None,
        "keywords": [],
        "data": data
    }

def fetch_reddit_posts(reddit):
    """
    Fetches recent posts from the current subreddit tag in Redis, converts them to the target format,
    and uploads them to the queue endpoint

    Args:
        reddit (praw.Reddit): An initialized Reddit API client

    Returns:
        None
    """
    # Connect to Redis to retrieve the current subreddit and state tracking
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    subreddit = r.lindex(REDIS_TAGS_LIST, 0)
    if not subreddit:
        current_app.logger.warning("No more tags in Redis list.")
        return

    state_key = f"reddit:max_fullname:{subreddit}"
    last_fullname = r.get(state_key)

    sub = reddit.subreddit(subreddit)
    params = {"before": last_fullname} if last_fullname else None
    posts = list(sub.new(limit=LIMIT, params=params))

    if not posts:
        current_app.logger.warning(f"No posts found for r/{subreddit} before {last_fullname}")
        r.lpop(REDIS_TAGS_LIST)
        return

    for post in posts:
        # upload post information
        post_data = convert_reddit_post_to_target_format(post, subreddit)
        requests.post(QUEUE_ENDPOINT, json=post_data, timeout=5)

        # upload comment information (same format)
        try:
            post.comment_sort = 'best'
            post.comments.replace_more(limit=0)

            count = 0
            for comment in post.comments:
                if isinstance(comment, praw.models.Comment) and comment.depth == 0:
                    comment_data = convert_comment_to_target_format(comment, subreddit)
                    requests.post(QUEUE_ENDPOINT, json=comment_data, timeout=5)
                    count += 1
                    if count >= 5:
                        break
        except Exception as e:
            current_app.logger.warning(f"Process comment error: {e}")

    oldest = min(posts, key=lambda p: p.created_utc)
    r.set(state_key, oldest.fullname)
    current_app.logger.info(f"Updated {state_key} to {oldest.fullname}")

    latest_dt = datetime.fromtimestamp(oldest.created_utc, timezone.utc)
    if latest_dt < END_DATE:
        r.lpop(REDIS_TAGS_LIST)
        current_app.logger.warning(f"Touched END_DATE, removed r/{subreddit}")

def main():
    """
    Main entry point. Initializes Reddit client and starts post fetching process
    """
    # Initialize a Reddit API client
    reddit = initialize_reddit()
    fetch_reddit_posts(reddit)
    return "OK"

if __name__ == "__main__":
    main()
