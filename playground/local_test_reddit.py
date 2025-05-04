import praw
import os
import sys
import json
from datetime import datetime, timezone

# --- Reddit 初始化 ---
def initialize_reddit():
    client_id = os.environ.get('REDDIT_CLIENT_ID')
    client_secret = os.environ.get('REDDIT_CLIENT_SECRET')
    user_agent = os.environ.get('REDDIT_USER_AGENT')
    if not all([client_id, client_secret, user_agent]):
        print("错误：请设置环境变量 REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, 和 REDDIT_USER_AGENT。", file=sys.stderr)
        sys.exit(1)
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        print("尝试验证只读凭据...")
        reddit.subreddits.popular(limit=1)
        print("PRAW 初始化成功 (只读模式)。")
        return reddit
    except Exception as e:
        print(f"PRAW 初始化失败: {e}", file=sys.stderr)
        sys.exit(1)

# --- 帖子获取函数 ---
def get_subreddit_posts(reddit_instance, subreddit_name, sort='hot', limit=25, time_filter='all', flair_text=None, start_time=None, end_time=None):
    """
    从指定的 subreddit 获取帖子列表。

    Args:
        reddit_instance (praw.Reddit): 已初始化的 PRAW 实例。
        subreddit_name (str): 要获取帖子的 subreddit 名称。
        sort (str): 排序方式 ('hot', 'new', 'top', 'controversial', 'rising'). 默认为 'hot'。
        limit (int): 获取帖子的最大数量。默认为 25。
        time_filter (str): 时间范围，仅当 sort 为 'top' 或 'controversial' 时有效
                           ('all', 'day', 'hour', 'month', 'week', 'year')。默认为 'all'。
        flair_text (str, optional): 仅返回具有此 Flair 文本的帖子。默认为 None (不筛选)。
                                    注意：这是在获取后进行过滤，可能会减少返回的帖子数量。
        start_time (float, optional): 帖子创建时间的 UTC 时间戳下限 (包含)。默认为 None。
        end_time (float, optional): 帖子创建时间的 UTC 时间戳上限 (不包含)。默认为 None。

    Returns:
        list[praw.models.Submission]: 符合条件的 Reddit 帖子对象列表。
    """
    posts = []
    try:
        subreddit = reddit_instance.subreddit(subreddit_name)
        print(f"\n正在从 r/{subreddit_name} 获取最多 {limit} 个 '{sort}' 帖子 (时间范围: {time_filter})...")

        post_iterator = None
        if sort == 'hot':
            post_iterator = subreddit.hot(limit=limit)
        elif sort == 'new':
            post_iterator = subreddit.new(limit=limit)
        elif sort == 'top':
            post_iterator = subreddit.top(limit=limit, time_filter=time_filter)
        elif sort == 'controversial':
            post_iterator = subreddit.controversial(limit=limit, time_filter=time_filter)
        elif sort == 'rising':
             post_iterator = subreddit.rising(limit=limit)
        else:
            print(f"错误：不支持的排序方式 '{sort}'。", file=sys.stderr)
            return []

        count = 0
        fetched_count = 0
        for post in post_iterator:
            fetched_count += 1
            # Flair 过滤
            if flair_text and post.link_flair_text != flair_text:
                continue
            # 时间范围过滤
            if start_time and post.created_utc < start_time:
                continue
            if end_time and post.created_utc >= end_time:
                continue

            posts.append(post)
            count += 1
            # 注意：这里的 limit 是 PRAW 请求的 limit，最终返回的数量可能因过滤而减少
            # 如果需要精确数量，可能需要循环获取更多数据直到满足条件或无更多数据

        print(f"从获取到的 {fetched_count} 个帖子中，筛选出 {count} 个符合条件的帖子。")
        return posts

    except Exception as e:
        print(f"从 r/{subreddit_name} 获取帖子时出错: {e}", file=sys.stderr)
        return [] # 返回空列表表示失败

# --- 评论获取函数 ---
'''def get_post_comments(post, limit=None, depth=1):
    comments = []
    print(f"\n正在获取帖子 '{post.title}' (ID: {post.id}) 的评论 (限制: {limit}, 深度: {depth})...")
    try:
        # post.comment_sort = 'top'
        post.comments.replace_more(limit=0) # 初始时不展开 MoreComments

        comment_queue = list(post.comments)
        processed_comments = 0
        current_depth = 1

        # 使用广度优先或深度优先遍历评论树（这里用简单的层级处理）
        # 注意：PRAW 的 comment_forest 直接迭代就是深度优先
        # 为了按深度限制，我们需要手动控制或检查 comment.depth 属性

        # 简单实现：只获取指定深度内的评论
        q = [(c, 1) for c in post.comments[:limit]] # (comment, level)
        visited = set() # 防止重复处理（虽然 PRAW 结构通常不会）

        while q:
            current_comment, level = q.pop(0) # 广度优先

            if current_comment.id in visited:
                continue
            visited.add(current_comment.id)

            # 检查是否是 Comment 类型，排除 MoreComments
            if isinstance(current_comment, praw.models.Comment):
                comments.append(current_comment)
                processed_comments += 1

                # 如果当前层级小于目标深度，且有回复，则将回复加入队列
                if (depth is None or level < depth) and hasattr(current_comment, 'replies'):
                    # 在处理回复前，可能需要 replace_more
                    # current_comment.replies.replace_more(limit=0) # 谨慎使用，可能增加 API 调用
                    for reply in current_comment.replies:
                         if isinstance(reply, praw.models.Comment): # 只添加实际评论
                            q.append((reply, level + 1))
                         # 可以选择是否将 MoreComments 对象也加入列表让调用者处理
                         # elif isinstance(reply, praw.models.MoreComments):
                         #    comments.append(reply)

            # 如果是 MoreComments，可以选择性地加载或忽略
            # elif isinstance(current_comment, praw.models.MoreComments):
            #    comments.append(current_comment) # 将 MoreComments 对象返回给调用者

            # 简单的数量限制（应用于返回的 Comment 对象总数）
            # 注意：这与 PRAW 的 limit 不同，PRAW 的 limit 通常用于 replace_more
            # if limit is not None and processed_comments >= limit:
            #    break # 如果是限制返回的评论总数，可以在这里 break

        print(f"成功获取 {len(comments)} 条评论 (达到深度 {depth})。")
        return comments

    except Exception as e:
        print(f"获取评论时出错: {e}", file=sys.stderr)
        return []'''

def get_post_comments(post):
    """
    获取指定帖子的第一层评论，按 best 排序，返回所有可获取的顶级评论。
    """
    print(f"\n获取帖子 '{post.title}' (ID: {post.id}) 的第一层评论（排序：best）...")
    try:
        post.comment_sort = 'best'
        post.comments.replace_more(limit=0)  # 只抓顶层
        top_level_comments = []
        for comment in post.comments:
            if isinstance(comment, praw.models.Comment) and comment.depth == 0:
                top_level_comments.append(comment)

        print(f"获取到 {len(top_level_comments)} 条顶级评论。")
        return top_level_comments

    except Exception as e:
        print(f"获取评论出错: {e}", file=sys.stderr)
        return []



# --- 数据格式化 (示例，通常由调用者完成) ---
def format_post_data(post):
    """将 PRAW Submission 对象格式化为字典 (示例 - 这是转换前的“原始”结构之一)。"""
    author_name = f"u/{post.author.name}" if post.author else "[已删除]"
    return {
        "id": post.id,
        "title": post.title,
        "subreddit": post.subreddit.display_name,
        "author": author_name,
        "score": post.score,
        "num_comments": post.num_comments,
        "url": post.url, # 指向内容的 URL (可能是外部链接或帖子本身)
        "permalink": f"https://www.reddit.com{post.permalink}", # 指向 Reddit 帖子的永久链接
        "selftext": post.selftext if post.is_self else None,
        "created_utc": post.created_utc,
        "flair": post.link_flair_text,
        "is_self": post.is_self,
        "upvote_ratio": post.upvote_ratio,
        "over_18": post.over_18, # NSFW 标记
        "spoiler": post.spoiler, # 剧透标记
        # 可以添加更多字段
    }

'''
def format_comment_data(comment):
    author_name = f"u/{comment.author.name}" if comment.author else "[已删除]"
    return {
        "id": comment.id,
        "post_id": comment.submission.id,
        "author": author_name,
        "body": comment.body,
        "score": comment.score,
        "created_utc": comment.created_utc,
        "depth": comment.depth,
        "parent_id": comment.parent_id, # e.g., "t1_xxxxx" or "t3_xxxxx"
    }
'''

def format_comment_data(comment):
    fetched_at = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    created_at = datetime.fromtimestamp(comment.created_utc, timezone.utc).isoformat(timespec='seconds') + 'Z'
    post = comment.submission

    # 获取作者信息
    if comment.author:
        try:
            author_created = datetime.fromtimestamp(comment.author.created_utc, timezone.utc).isoformat(timespec="seconds") + "Z"
            link_karma = comment.author.link_karma
            comment_karma = comment.author.comment_karma
        except Exception:
            author_created = link_karma = comment_karma = None
        account_data = {
            "id": comment.author.id,
            "username": comment.author.name,
            "createdAt": author_created,
            "followersCount/linkKarma": link_karma,
            "followingCount/commentKarma": comment_karma,
        }
    else:
        account_data = {
            "id": None,
            "username": "[Deleted]",
            "createdAt": None,
            "followersCount/linkKarma": None,
            "followingCount/commentKarma": None,
        }

    # 构建 tags 列表
    tags = ["comment", post.subreddit.display_name]
    if post.link_flair_text:
        tags.append(post.link_flair_text)

    # 构建评论 JSON 对象
    return {
        "platform": "Reddit",
        "version": 2.1,
        "fetchedAt": fetched_at,
        "sentiment": None,
        "sentimentLabel": None,
        "keywords": [],
        "data": {
            "id": comment.id,
            "post_id": post.id,
            "createdAt": created_at,
            "content": comment.body,
            "sensitive": post.over_18,
            "favouritesCount": comment.score,
            "repliesCount": len(comment.replies),
            "tags": tags,
            "url": f"https://www.reddit.com{post.permalink}",
            "account": account_data
        }
    }


# --- 新增：转换为目标 JSON 结构的函数 ---
def convert_reddit_post_to_target_format(post: praw.models.Submission):
    """
    将 PRAW Submission 对象转换为指定的目标 JSON 结构。

    Args:
        post (praw.models.Submission): Reddit 帖子对象。

    Returns:
        dict: 符合目标结构的字典。
    """
    fetched_at = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    created_at = datetime.fromtimestamp(post.created_utc, timezone.utc).isoformat(timespec='seconds') + 'Z'

    account_data = None
    if post.author:
        try:
            # 尝试获取作者创建时间，如果失败则设为 None
            author_created_at = datetime.fromtimestamp(post.author.created_utc, timezone.utc).isoformat(timespec='seconds') + 'Z'
            # 获取 karma 数据
            link_karma = post.author.link_karma
            comment_karma = post.author.comment_karma
        except Exception: # 可能因为作者信息不完整或 PRAW 限制
             author_created_at = None
             link_karma = None
             comment_karma = None

        account_data = {
            "id": post.author.id,
            "username": post.author.name,
            "createdAt": author_created_at,
            "followersCount/linkKarma": link_karma, # 使用 link_karma
            "followingCount/commentKarma": comment_karma, # 使用 comment_karma
        }
    else: # 处理已删除用户
         account_data = {
            "id": None,
            "username": "[Deleted]",
            # Reddit API 不提供已删除用户的创建时间
            "createdAt": None,
            "followersCount/linkKarma": None, # 已删除用户无 karma
            "followingCount/commentKarma": None, # 已删除用户无 karma
        }

    # 确定 content 字段内容
    content = post.title
    if post.is_self and post.selftext:
        content += f"\n\n{post.selftext}" # 如果是自包含帖子，将内容附加到标题后

    # 处理 tags
    tags = []
    if post.link_flair_text:
        tags.append(post.link_flair_text) # 使用 Flair 作为 Tag

    data = {
        "id": post.id,
        "createdAt": created_at,
        "content": content,
        "sensitive": post.over_18, # 将 NSFW 映射为 sensitive
        "favouritesCount": post.score, # 使用 score 作为点赞数的近似值
        "repliesCount": post.num_comments,
        "tags": tags,
        "url": f"https://www.reddit.com{post.permalink}", # 帖子的 Reddit 链接
        "account": account_data
    }

    return {
        "platform": "Reddit",   # 平台名称
        "version": 1.1,         # 版本号
        "fetchedAt": fetched_at,
        "sentiment": None,      # 初始为 null
        "sentimentLabel": None, # 新增字段，初始为 null
        "keywords": [],
        "data": data
    }

def get_convert_reddit_comments(post):
    """
    获取指定帖子的顶层评论（按 best 排序），并返回符合目标结构的 JSON 列表。
    Args:
        post (praw.models.Submission): Reddit 帖子对象
    Returns:
        list[dict]: 格式化后的评论 JSON 对象列表
    """
    ### print(f"\n获取帖子 '{post.title}' (ID: {post.id}) 的第一层评论（排序：best）...")
    try:
        post.comment_sort = 'best'
        post.comments.replace_more(limit=0)
        results = []

        for comment in post.comments:
            if not isinstance(comment, praw.models.Comment) or comment.depth != 0:
                continue

            fetched_at = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
            created_at = datetime.fromtimestamp(comment.created_utc, timezone.utc).isoformat(timespec='seconds') + 'Z'

            # 获取作者信息
            if comment.author:
                try:
                    author_created = datetime.fromtimestamp(comment.author.created_utc, timezone.utc).isoformat(timespec="seconds") + "Z"
                    link_karma = comment.author.link_karma
                    comment_karma = comment.author.comment_karma
                except Exception:
                    author_created = link_karma = comment_karma = None
                account_data = {
                    "id": comment.author.id,
                    "username": comment.author.name,
                    "createdAt": author_created,
                    "followersCount/linkKarma": link_karma,
                    "followingCount/commentKarma": comment_karma,
                }
            else:
                account_data = {
                    "id": None,
                    "username": "[Deleted]",
                    "createdAt": None,
                    "followersCount/linkKarma": None,
                    "followingCount/commentKarma": None,
                }

            # 构建 tags
            tags = ["comment", post.subreddit.display_name]
            if post.link_flair_text:
                tags.append(post.link_flair_text)

            # 构建 JSON
            comment_json = {
                "platform": "Reddit",
                "version": 2.1,
                "fetchedAt": fetched_at,
                "sentiment": None,
                "sentimentLabel": None,
                "keywords": [],
                "data": {
                    "id": comment.id,
                    "post_id": post.id,
                    "createdAt": created_at,
                    "content": comment.body,
                    "sensitive": post.over_18,
                    "favouritesCount": comment.score,
                    "repliesCount": len(comment.replies),
                    "tags": tags,
                    "url": f"https://www.reddit.com{post.permalink}",
                    "account": account_data
                }
            }

            results.append(comment_json)

        ### print(f"获取到 {len(results)} 条顶级评论。")
        return results

    except Exception as e:
        print(f"获取评论失败: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    # 1. 初始化 Reddit 连接
    reddit = initialize_reddit()
    if reddit:
        # --- 示例 1: 获取指定Subreddit的最新帖子 ---
        print("\n--- 示例 1: 获取指定Subreddit的最新帖子 ---")
        latest_python_posts = get_subreddit_posts(reddit, 'australia', sort='hot', limit=100)
        if (latest_python_posts):
            post = latest_python_posts[0]
            print("\n原始结构 (来自 format_post_data):")
            original_data = format_post_data(post)
            print(json.dumps(original_data, indent=2, ensure_ascii=False))

            print("\n转换后的目标结构:")
            converted_data = convert_reddit_post_to_target_format(post)
            print(json.dumps(converted_data, indent=2, ensure_ascii=False))
        else:
            print("未能获取到帖子。")

        # --- 示例 2: 获取帖子的评论 ---
        if latest_python_posts:
            target_post = latest_python_posts[0]
            print(f"\n--- 获取帖子 '{target_post.title}' 的顶级评论 ---")
            comments = get_post_comments(target_post)
            print(f"帖子总评论数: {target_post.num_comments}") # 显示帖子实际评论数
            for comment in comments:
                 if isinstance(comment, praw.models.Comment): # 确保是评论对象
                    comment_data = format_comment_data(comment)
                    print(comment_data)
        else:
            print("\n--- 示例 2: 跳过，因为没有获取到帖子 ---")
