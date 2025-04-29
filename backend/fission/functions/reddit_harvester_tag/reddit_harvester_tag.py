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
    # client_id = os.environ.get('REDDIT_CLIENT_ID')
    # client_secret = os.environ.get('REDDIT_CLIENT_SECRET')
    # user_agent = os.environ.get('REDDIT_USER_AGENT')

    client_id = config('REDDIT_CLIENT_ID')
    client_secret = config('REDDIT_CLIENT_SECRET')
    user_agent = config('REDDIT_USER_AGENT')

    if not all([client_id, client_secret, user_agent]):
        print("错误：请设置环境变量 REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, 和 REDDIT_USER_AGENT。", file=sys.stderr)
        sys.exit(1)  # 退出程序

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        # 验证凭据是否有效（尝试获取用户信息，只读模式下可能受限）
        # print(f"以用户 {reddit.user.me()} 的身份进行认证（只读模式）...") # 在只读模式下调用 reddit.user.me() 会失败
        print("尝试验证只读凭据...")
        reddit.subreddits.popular(limit=1)  # 尝试一个简单的只读 API 调用
        print("PRAW 初始化成功 (只读模式)。")
        return reddit
    except Exception as e:
        print(f"PRAW 初始化失败: {e}", file=sys.stderr)
        sys.exit(1)  # 退出程序


# --- 新增：转换为目标 JSON 结构的函数 ---
def convert_reddit_post_to_target_format(post: Submission) -> dict:
    """
    将 PRAW Submission 对象转换为指定的目标 JSON 结构。

    Args:
        post (praw.models.Submission): Reddit 帖子对象。

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
    print(f"上次的搜索id：r/{subreddit}, {last_fullname}")
    posts = list(sub.new(limit=LIMIT, params=params))

    if not posts:
        current_app.logger.warning(f"Didn't get any posts from r/{subreddit}")
        r.lpop(REDIS_TAGS_LIST)
        return

    for post in posts:
        data = convert_reddit_post_to_target_format(post)
        requests.post(QUEUE_ENDPOINT, json=data, timeout=5)

    oldest = min(posts, key=lambda p: p.created_utc)
    r.set(state_key, oldest.fullname)
    current_app.logger.info(f"更新id成功")

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

# def search_posts(reddit_instance, query, subreddit_name=None, sort='relevance', limit=25, time_filter='all',
#                  flair_text=None, start_time=None, end_time=None):
#     # 设想：加入create时间限制，需在2023/1/1之后创建的；加入subreddit限制，需在给定的subreddit列表范围内
#     """
#     在 Reddit 或指定 subreddit 中搜索包含关键词的帖子。
#
#     Args:
#         reddit_instance (praw.Reddit): 已初始化的 PRAW 实例。
#         query (str): 搜索的关键词。
#         subreddit_name (str, optional): 限制搜索范围的 subreddit 名称。默认为 None (搜索所有 Reddit)。
#         sort (str): 搜索结果排序方式 ('relevance', 'hot', 'top', 'new', 'comments')。默认为 'relevance'。
#         limit (int): 返回帖子的最大数量。默认为 25。
#         time_filter (str): 时间范围 ('all', 'day', 'hour', 'month', 'week', 'year')。默认为 'all'。
#         flair_text (str, optional): 仅返回具有此 Flair 文本的帖子。默认为 None (不筛选)。
#                                     注意：这是在获取后进行过滤。
#         start_time (float, optional): 帖子创建时间的 UTC 时间戳下限 (包含)。默认为 None。
#         end_time (float, optional): 帖子创建时间的 UTC 时间戳上限 (不包含)。默认为 None。
#
#     Returns:
#         list[praw.models.Submission]: 符合条件的 Reddit 帖子对象列表。
#     """
#     posts = []
#     try:
#         search_target = reddit_instance.subreddit(subreddit_name) if subreddit_name else reddit_instance.subreddit(
#             'all')
#         target_display = f"r/{subreddit_name}" if subreddit_name else "所有 Reddit"
#         print(f"\n正在在 {target_display} 中搜索关键词 '{query}' (排序: {sort}, 时间: {time_filter}, 限制: {limit})...")
#
#         search_iterator = search_target.search(query, sort=sort, time_filter=time_filter, limit=limit)
#
#         count = 0
#         fetched_count = 0
#         for post in search_iterator:
#             fetched_count += 1
#             # Flair 过滤
#             if flair_text and post.link_flair_text != flair_text:
#                 continue
#             # 时间范围过滤
#             if start_time and post.created_utc < start_time:
#                 continue
#             if end_time and post.created_utc >= end_time:
#                 continue
#             # subreddit过滤
#             if post.subreddit.display_name not in allowed_subreddits:
#                 # print(post.subreddit.display_name)
#                 continue
#
#             posts.append(post)
#             count += 1
#
#         print(f"从搜索到的 {fetched_count} 个帖子中，筛选出 {count} 个符合条件的帖子。")
#         return posts
#
#     except Exception as e:
#         print(f"搜索帖子时出错: {e}", file=sys.stderr)
#         return []


# def get_random_post(reddit_instance, subreddit_name):
#     """
#     从指定的 subreddit 获取一个随机帖子。
#     如果 random() 方法失败，会退化为从热门帖子中随机选择一个。
#
#     Args:
#         reddit_instance (praw.Reddit): 已初始化的 PRAW 实例。
#         subreddit_name (str): 要获取帖子的 subreddit 名称。
#
#     Returns:
#         praw.models.Submission or None: 一个随机的 Reddit 帖子对象，如果出错则返回 None。
#     """
#     try:
#         subreddit = reddit_instance.subreddit(subreddit_name)
#         print(f"\n正在从 r/{subreddit_name} 获取一个随机帖子...")
#         try:
#             random_post = subreddit.random()
#             if random_post:
#                 print(f"成功获取随机帖子: {random_post.title}")
#                 return random_post
#         except Exception as e:
#             print(f"使用 random() 方法获取随机帖子失败(可能是subreddit禁用了此功能): {e}")
#             print("尝试替代方法：从热门帖子中随机选择...")
#
#         # 当random()方法失败时，从热门帖子列表中随机选择一个
#         hot_posts = list(subreddit.hot(limit=25))
#         if hot_posts:
#             random_post = random.choice(hot_posts)
#             print(f"成功从热门帖子中随机选择: {random_post.title}")
#             return random_post
#         else:
#             print(f"无法从 r/{subreddit_name} 获取任何帖子。")
#             return None
#
#     except Exception as e:
#         print(f"获取随机帖子时出错: {e}", file=sys.stderr)
#         return None


# --- 评论获取函数 ---

# def get_post_comments(post, limit=None, depth=1):
#     """
#     获取指定帖子的评论。
#
#     Args:
#         post (praw.models.Submission): 要获取评论的帖子对象。
#         limit (int, optional): 获取顶级评论的最大数量。默认为 None (获取所有顶级评论)。
#         depth (int, optional): 要获取的评论树深度。1 表示只获取顶级评论，
#                                2 表示获取顶级评论及其直接回复，依此类推。
#                                默认为 1。设置为 None 会尝试获取所有评论（可能非常耗时且数据量大）。
#
#     Returns:
#         list[praw.models.Comment or praw.models.MoreComments]: 评论对象列表。
#             可能包含 MoreComments 对象，表示可以在该位置加载更多评论。
#     """
#     comments = []
#     print(f"\n正在获取帖子 '{post.title}' (ID: {post.id}) 的评论 (限制: {limit}, 深度: {depth})...")
#     try:
#         # 设置评论排序方式（可选，例如 'new', 'top', 'controversial'）
#         # post.comment_sort = 'top'
#         post.comments.replace_more(limit=0)  # 初始时不展开 MoreComments
#
#         comment_queue = list(post.comments)
#         processed_comments = 0
#         current_depth = 1
#
#         # 使用广度优先或深度优先遍历评论树（这里用简单的层级处理）
#         # 注意：PRAW 的 comment_forest 直接迭代就是深度优先
#         # 为了按深度限制，我们需要手动控制或检查 comment.depth 属性
#
#         # 简单实现：只获取指定深度内的评论
#         q = [(c, 1) for c in post.comments[:limit]]  # (comment, level)
#         visited = set()  # 防止重复处理（虽然 PRAW 结构通常不会）
#
#         while q:
#             current_comment, level = q.pop(0)  # 广度优先
#
#             if current_comment.id in visited:
#                 continue
#             visited.add(current_comment.id)
#
#             # 检查是否是 Comment 类型，排除 MoreComments
#             if isinstance(current_comment, praw.models.Comment):
#                 comments.append(current_comment)
#                 processed_comments += 1
#
#                 # 如果当前层级小于目标深度，且有回复，则将回复加入队列
#                 if (depth is None or level < depth) and hasattr(current_comment, 'replies'):
#                     # 在处理回复前，可能需要 replace_more
#                     # current_comment.replies.replace_more(limit=0) # 谨慎使用，可能增加 API 调用
#                     for reply in current_comment.replies:
#                         if isinstance(reply, praw.models.Comment):  # 只添加实际评论
#                             q.append((reply, level + 1))
#                         # 可以选择是否将 MoreComments 对象也加入列表让调用者处理
#                         # elif isinstance(reply, praw.models.MoreComments):
#                         #    comments.append(reply)
#
#             # 如果是 MoreComments，可以选择性地加载或忽略
#             # elif isinstance(current_comment, praw.models.MoreComments):
#             #    comments.append(current_comment) # 将 MoreComments 对象返回给调用者
#
#             # 简单的数量限制（应用于返回的 Comment 对象总数）
#             # 注意：这与 PRAW 的 limit 不同，PRAW 的 limit 通常用于 replace_more
#             # if limit is not None and processed_comments >= limit:
#             #    break # 如果是限制返回的评论总数，可以在这里 break
#
#         print(f"成功获取 {len(comments)} 条评论 (达到深度 {depth})。")
#         return comments
#
#     except Exception as e:
#         print(f"获取评论时出错: {e}", file=sys.stderr)
#         return []

# def format_post_data(post):
#     """将 PRAW Submission 对象格式化为字典 (示例 - 这是转换前的“原始”结构之一)。"""
#     author_name = f"u/{post.author.name}" if post.author else "user_deleted"
#     return {
#         "id": post.id,
#         "title": post.title,
#         "subreddit": post.subreddit.display_name,
#         "author": author_name,
#         "score": post.score,
#         "num_comments": post.num_comments,
#         "url": post.url,  # 指向内容的 URL (可能是外部链接或帖子本身)
#         "permalink": f"https://www.reddit.com{post.permalink}",  # 指向 Reddit 帖子的永久链接
#         "selftext": post.selftext if post.is_self else None,
#         "created_utc": post.created_utc,
#         "flair": post.link_flair_text,
#         "is_self": post.is_self,
#         "upvote_ratio": post.upvote_ratio,
#         "over_18": post.over_18,  # NSFW 标记
#         "spoiler": post.spoiler,  # 剧透标记
#         # 可以添加更多字段
#     }

# def format_comment_data(comment):
#     """将 PRAW Comment 对象格式化为字典 (示例)。"""
#     author_name = f"u/{comment.author.name}" if comment.author else "[已删除]"
#     return {
#         "id": comment.id,
#         "post_id": comment.submission.id,
#         "author": author_name,
#         "body": comment.body,
#         "score": comment.score,
#         "created_utc": comment.created_utc,
#         "depth": comment.depth,
#         "parent_id": comment.parent_id,  # e.g., "t1_xxxxx" or "t3_xxxxx"
#         # 可以添加更多字段
#     }

# def get_subreddit_posts(reddit_instance, subreddit_name, sort='hot', limit=25, time_filter='all', flair_text=None,
#                         start_time=None, end_time=None, after=None):
#     """
#     从指定的 subreddit 获取帖子列表。
#
#     Args:
#         reddit_instance (praw.Reddit): 已初始化的 PRAW 实例。
#         subreddit_name (str): 要获取帖子的 subreddit 名称。
#         sort (str): 排序方式 ('hot', 'new', 'top', 'controversial', 'rising'). 默认为 'hot'。
#         limit (int): 获取帖子的最大数量。默认为 25。
#         time_filter (str): 时间范围，仅当 sort 为 'top' 或 'controversial' 时有效
#                            ('all', 'day', 'hour', 'month', 'week', 'year')。默认为 'all'。
#         flair_text (str, optional): 仅返回具有此 Flair 文本的帖子。默认为 None (不筛选)。
#                                     注意：这是在获取后进行过滤，可能会减少返回的帖子数量。
#         start_time (float, optional): 帖子创建时间的 UTC 时间戳下限 (包含)。默认为 None。
#         end_time (float, optional): 帖子创建时间的 UTC 时间戳上限 (不包含)。默认为 None。
#         after : last id search
#     Returns:
#         list[praw.models.Submission]: 符合条件的 Reddit 帖子对象列表。
#     """
#     posts = []
#     try:
#         subreddit = reddit_instance.subreddit(subreddit_name)
#         print(f"\n正在从 r/{subreddit_name} 获取最多 {limit} 个 '{sort}' 帖子 (时间范围: {time_filter})...")
#
#         post_iterator = None
#         if sort == 'hot':
#             post_iterator = subreddit.hot(limit=limit)
#         elif sort == 'new':
#             if after:
#                 post_iterator = subreddit.new(limit=limit, params={"after": after})
#             else:
#                 post_iterator = subreddit.new(limit=limit)
#         elif sort == 'top':
#             post_iterator = subreddit.top(limit=limit, time_filter=time_filter)
#         elif sort == 'controversial':
#             post_iterator = subreddit.controversial(limit=limit, time_filter=time_filter)
#         elif sort == 'rising':
#             post_iterator = subreddit.rising(limit=limit)
#         else:
#             print(f"错误：不支持的排序方式 '{sort}'。", file=sys.stderr)
#             return []
#
#         count = 0
#         fetched_count = 0
#         for post in post_iterator:
#             fetched_count += 1
#             # Flair 过滤
#             if flair_text and post.link_flair_text != flair_text:
#                 continue
#             # 时间范围过滤
#             if start_time and post.created_utc < start_time:
#                 continue
#             if end_time and post.created_utc >= end_time:
#                 continue
#
#             posts.append(post)
#             count += 1
#             # 注意：这里的 limit 是 PRAW 请求的 limit，最终返回的数量可能因过滤而减少
#             # 如果需要精确数量，可能需要循环获取更多数据直到满足条件或无更多数据
#
#         print(f"从获取到的 {fetched_count} 个帖子中，筛选出 {count} 个符合条件的帖子。")
#         return posts
#
#     except Exception as e:
#         print(f"从 r/{subreddit_name} 获取帖子时出错: {e}", file=sys.stderr)
#         return []  # 返回空列表表示失败

# def original_main():
#     # 设置subreddit范围
#     allowed_subreddits = [
#         "AskAnAustralian", "australia", "MovingToBrisbane", "australian", "AustraliaTravel", "AusFinance",
#         "CarsAustralia",
#         "AusEcon", "AustralianPolitics", "AusProperty", "AusPropertyChat", "howislivingthere", "tasmania", "perth",
#         "adelaide", "brisbane", "melbourne", "sydney", "canberra", "darwin", "WesternAustralia", "AussieMaps",
#         "southaustralia",
#         "woolworths"
#     ]
#
#     # 1. 初始化 Reddit 连接
#     reddit = initialize_reddit()
#
#     if reddit:
#         # --- 示例 1: 获取指定 Subreddit 的最新帖子 ---
#         print("\n--- 示例 1: 获取 r/melbourne 的最新帖子 ---")
#         # 设定停止的最早时间点
#         stop_timestamp = datetime.strptime("2023-01-01", "%Y-%m-%d").timestamp()
#
#         for subreddit in allowed_subreddits:
#             print(f"\n开始抓取 r/{subreddit}...")
#             finished = False
#             total_posts = 0
#             while not finished:
#                 latest_python_posts = get_subreddit_posts(reddit, subreddit, sort='new', limit=500)
#                 if latest_python_posts:
#                     for post in latest_python_posts:
#                         original_data = format_post_data(post)
#                         print("\n转换后的目标结构:")
#                         converted_data = convert_reddit_post_to_target_format(post)
#                         print(json.dumps(converted_data, indent=2, ensure_ascii=False))
#                     total_posts += len(latest_python_posts)
#
#                     # 检查发布时间
#                     earliest_post = min(latest_python_posts, key=lambda x: x.created_utc)
#
#                     if len(latest_python_posts) < 500:
#                         print(f"r/{subreddit} 本轮未满500，实际抓到 {len(latest_python_posts)} 条，停止抓取。")
#                         finished = True
#                     elif earliest_post.created_utc < stop_timestamp:
#                         print(f"r/{subreddit} 抓取到 2023/1/1 之前的帖子，停止抓取。")
#                         finished = True
#                     else:
#                         print(f"r/{subreddit} 本轮抓满500条，继续下一轮抓取...")
#                 else:
#                     print(f"r/{subreddit} 未能抓到帖子，提前停止。")
#                     finished = True
#
#             print(f"完成 r/{subreddit} 的抓取，总共抓取了 {total_posts} 条帖子。")
#             time.sleep(2)  # 防止频率过高
#
#         '''
#         # --- 示例 2: 搜索包含特定关键词的帖子 ---
#         print("\n--- 示例 2: 搜索包含 'kmart' 的帖子 ---")
#         search_results = search_posts(reddit, query='kmart', sort='new', time_filter='all', limit=2000, start_time = int(datetime.strptime("2023-01-01", "%Y-%m-%d").timestamp()))
#         for post in search_results:
#             post_data = format_post_data(post)
#             print(f"  - [{post_data['subreddit']}] {post_data['title']} (Score: {post_data['score']})")
#
#         # --- 示例 3: 获取帖子的评论 ---
#         if search_results:
#             target_post = search_results[0] # 获取第一篇帖子的评论
#             print(f"\n--- 示例 3: 获取帖子 '{target_post.title}' 的顶级评论 ---")
#             comments = get_post_comments(target_post, limit=5, depth=1) # 获取最多5条顶级评论
#             print(f"帖子总评论数: {target_post.num_comments}") # 显示帖子实际评论数
#             for comment in comments:
#                  if isinstance(comment, praw.models.Comment): # 确保是评论对象
#                     comment_data = format_comment_data(comment)
#                     print(f"    - {comment_data['author']}: {comment_data['body'][:80]}... (Score: {comment_data['score']})")
#         else:
#             print("\n--- 示例 3: 跳过，因为没有获取到帖子 ---")
#
#         # --- 示例 4: 获取随机帖子 ---
#         print("\n--- 示例 4: 获取 r/melbourne 的随机帖子 ---")
#         random_post = get_random_post(reddit, 'melbourne')
#         if random_post:
#             post_data = format_post_data(random_post)
#             print(f"  - 随机帖子: [{post_data['subreddit']}] {post_data['title']}")
#
#         # --- 示例 5: 按 Flair 和时间范围过滤 ---
#         print("\n--- 示例 5: 获取 r/melbourne 过去一天内的热门帖子并检查各种Flair/Tag ---")
#         now_utc = time.time()
#         one_day_ago_utc = now_utc - (24 * 60 * 60)
#         hot_posts = get_subreddit_posts(
#             reddit, 'melbourne', sort='hot', limit=20,
#             start_time=one_day_ago_utc, end_time=now_utc
#         )
#         flairs = {}
#         for post in hot_posts:
#             flair = post.link_flair_text
#             if flair: flairs[flair] = flairs.get(flair, 0) + 1
#         print(f"过去一天内发现的Flair/Tag类型: {flairs if flairs else '无'}")
#         if flairs:
#             most_common_flair = max(flairs.items(), key=lambda x: x[1])[0]
#             print(f"\n使用最常见的Flair/Tag '{most_common_flair}' 进行过滤:")
#             filtered_posts = [p for p in hot_posts if p.link_flair_text == most_common_flair]
#             for post in filtered_posts:
#                 post_data = format_post_data(post)
#                 print(f"  - [{post_data['subreddit']}] {post_data['title']} (Flair/Tag: {post_data['flair']}, Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(post_data['created_utc']))} UTC)")
#         '''
#
#         # --- 关于定时抓取 ---
#         # 本库提供按需抓取的函数。定时抓取应由外部脚本或工具实现。
#         # 例如，使用 time.sleep() 进行简单循环 (不推荐用于生产环境):
#         # interval_seconds = 3600 # 每小时抓取一次
#         # while True:
#         #     print(f"\n--- 定时抓取 ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
#         #     new_posts = get_subreddit_posts(reddit, 'popular', sort='new', limit=10)
#         #     # 在这里处理 new_posts, 例如存入数据库
#         #     print(f"获取了 {len(new_posts)} 条新帖子。")
#         #     print(f"等待 {interval_seconds} 秒...")
#         #     time.sleep(interval_seconds)
#         #
#         # 更健壮的方法是使用操作系统的 cron (Linux/macOS), Task Scheduler (Windows),
#         # 或者 Python 库如 APScheduler 或 Celery。
