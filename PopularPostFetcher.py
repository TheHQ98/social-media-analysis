import praw
import os # 建议使用环境变量存储敏感信息

# --- Reddit API 凭据 ---
# 建议将这些信息存储在环境变量中，而不是直接写在代码里
# 例如：
# export REDDIT_CLIENT_ID='YOUR_CLIENT_ID'
# export REDDIT_CLIENT_SECRET='YOUR_CLIENT_SECRET'
# export REDDIT_USER_AGENT='MyPopularPostFetcher/1.0 by YourRedditUsername'

# 从环境变量获取凭据，如果不存在则使用占位符
client_id = os.environ.get('REDDIT_CLIENT_ID', 'YOUR_CLIENT_ID')
client_secret = os.environ.get('REDDIT_CLIENT_SECRET', 'YOUR_CLIENT_SECRET')
# user_agent 应该包含你的应用名称、版本和你的 Reddit 用户名
user_agent = os.environ.get('REDDIT_USER_AGENT', 'YOUR_USER_AGENT')

# 检查是否使用了默认占位符，如果是，则提示用户替换
if client_id == 'YOUR_CLIENT_ID' or client_secret == 'YOUR_CLIENT_SECRET' or user_agent == 'YOUR_USER_AGENT':
    print("请替换代码中的 'YOUR_CLIENT_ID', 'YOUR_CLIENT_SECRET' 和 'YOUR_USER_AGENT' 为你自己的信息。")
    print("或者设置环境变量 REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT。")
    exit() # 退出程序，直到用户配置好凭据

# --- 初始化 PRAW ---
try:
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )
    print("PRAW 初始化成功。")

    # --- 访问 'popular' 板块 ---
    # 在 PRAW 中，可以通过 reddit.subreddit('popular') 来访问 popular feed
    # 然后使用 .hot() 方法获取热门帖子列表
    # limit=1 表示只获取第一个帖子
    print("正在获取 popular 板块的第一个帖子...")
    popular_posts_iterator = reddit.subreddit('popular').hot(limit=1)

    # 从迭代器中获取第一个帖子对象
    # next() 函数用于从迭代器中获取下一个元素
    # 如果迭代器为空，next() 会抛出 StopIteration 异常，使用 default=None 可以避免异常
    first_post = next(popular_posts_iterator, None)

    # --- 显示帖子信息 ---
    if first_post:
        print("\n--- 找到帖子 ---")
        print(f"标题: {first_post.title}")
        print(f"Subreddit: r/{first_post.subreddit.display_name}")
        print(f"作者: u/{first_post.author.name if first_post.author else '[已删除]'}")
        print(f"分数: {first_post.score}")
        print(f"评论数: {first_post.num_comments}")
        print(f"URL: {first_post.url}")
        print(f"帖子ID: {first_post.id}")
        # 如果是自发帖，可以显示内容
        if first_post.is_self:
             # 只显示部分自发帖内容，避免过长
             print(f"内容预览: {first_post.selftext[:200]}..." if len(first_post.selftext) > 200 else first_post.selftext)

    else:
        print("未能获取到 popular 板块的帖子。")

except Exception as e:
    print(f"发生错误: {e}")