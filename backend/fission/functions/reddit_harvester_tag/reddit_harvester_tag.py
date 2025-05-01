import sys
from datetime import datetime, timezone
import redis
from flask import current_app
import requests

import praw
from praw.models import Submission
from prawcore.exceptions import PrawcoreException

CONFIG_MAP = "reddit-config2"
REDIS_TAGS_LIST = "reddit:tags"
END_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
LIMIT = 40

REDIS_HOST = "redis-headless.redis.svc.cluster.local"
REDIS_PORT = 6379
QUEUE_ENDPOINT = "http://router.fission.svc.cluster.local/enqueue/reddit"


def config(k: str) -> str:
    """
    Reads configuration from config map file
    """
    with open(f'/configs/default/{CONFIG_MAP}/{k}', 'r') as f:
        return f.read()


# --- Reddit 初始化 ---

def initialize_reddit():
    """
    使用环境变量中的凭据初始化并返回一个 PRAW Reddit 实例。

    环境变量需要设置:
    - REDDIT_CLIENT_ID: 你的 Reddit 应用 Client ID
    - REDDIT_CLIENT_SECRET: 你的 Reddit 应用 Client Secret
    - REDDIT_USER_AGENT: 一个描述性的 User Agent 字符串 (例如 'MyRedditBot/1.0 by u/YourUsername')

    如果凭据未设置或无效，将打印错误信息并退出程序。

    Returns:
        praw.Reddit: 配置好的 PRAW Reddit 实例。
    """

    client_id = config('REDDIT_CLIENT_ID')
    client_secret = config('REDDIT_CLIENT_SECRET')
    user_agent = config('REDDIT_USER_AGENT')

    if not all([client_id, client_secret, user_agent]):
        print("错误：请设置环境变量 REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, 和 REDDIT_USER_AGENT。", file=sys.stderr)
        sys.exit(1)

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        reddit.subreddits.popular(limit=1)
        print("PRAW initial success")
        return reddit
    except Exception as e:
        print(f"PRAW 初始化失败: {e}", file=sys.stderr)
        sys.exit(1)


# --- 新增：转换为目标 JSON 结构的函数 ---
def convert_reddit_post_to_target_format(post: Submission, subreddit: str) -> dict:
    """
    将 PRAW Submission 对象转换为指定的目标 JSON 结构。

    Args:
        post (praw.models.Submission): Reddit 帖子对象。
        subreddit: current subreddit topic
    Returns:
        dict: 符合目标结构的字典。
    """
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"
    created_at = datetime.fromtimestamp(post.created_utc, timezone.utc).isoformat(timespec="seconds") + "Z"

    if post.author:
        author_id = getattr(post.author, "id", None)
        author_username = getattr(post.author, "name", "[Unknown]")
        try:
            author_created = datetime.fromtimestamp(
                post.author.created_utc, timezone.utc
            ).isoformat(timespec="seconds") + "Z"
            link_karma = getattr(post.author, "link_karma", None)
            comment_karma = getattr(post.author, "comment_karma", None)
        except (AttributeError, PrawcoreException):
            current_app.logger.info(f"[{post.id}] author info unavailable")
            author_created = link_karma = comment_karma = None

        account_data = {
            "id": author_id,
            "username": author_username,
            "createdAt": author_created,
            "followersCount/linkKarma": link_karma,
            "followingCount/commentKarma": comment_karma,
        }
    else:  # Author deleted
        account_data = {
            "id": None,
            "username": "[Deleted]",
            "createdAt": None,
            "followersCount/linkKarma": None,
            "followingCount/commentKarma": None,
        }

    # 确定 content 字段内容
    content = post.title
    if post.is_self and post.selftext:
        content += f"\n\n{post.selftext}"

    # 处理 tags
    tags = [post.link_flair_text] if post.link_flair_text else []
    if tags:
        tags.append(subreddit.lower())

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


def fetch_reddit_posts(reddit):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # get the tag from redis list, if no more tag in list, then top
    subreddit = r.lindex(REDIS_TAGS_LIST, 0)
    if not subreddit:
        current_app.logger.warning("No more tags in Redis list.")
        return

    # get the last recorded max_id from redis list
    state_key = f"reddit:max_fullname:{subreddit}"
    last_fullname = r.get(state_key)

    sub = reddit.subreddit(subreddit)
    params = {"after": last_fullname} if last_fullname else None
    posts = list(sub.new(limit=LIMIT, params=params))

    if not posts:
        current_app.logger.warning(f"Didn't get any posts from r/{subreddit}")
        r.lpop(REDIS_TAGS_LIST)
        return

    for post in posts:
        data = convert_reddit_post_to_target_format(post, subreddit)
        requests.post(QUEUE_ENDPOINT, json=data, timeout=5)

    oldest = min(posts, key=lambda p: p.created_utc)
    r.set(state_key, oldest.fullname)
    current_app.logger.info(f"Update last_fullname")

    oldest_dt = datetime.fromtimestamp(oldest.created_utc, timezone.utc)
    if oldest_dt < END_DATE:
        r.lpop(REDIS_TAGS_LIST)
        current_app.logger.warning(f"Touched END_DATE, removed r/{subreddit}")


def main():
    reddit = initialize_reddit()

    fetch_reddit_posts(reddit)

    return "OK"


if __name__ == "__main__":
    main()