# Reddit Fetcher

一个使用 PRAW 库从 Reddit 获取帖子和评论的 Python 脚本。

## 功能

*   使用环境变量中的凭据初始化 PRAW。
*   从指定的 subreddit 获取帖子（按热门、最新、评分最高等排序）。
*   根据关键词搜索帖子。
*   获取指定 subreddit 的随机帖子。
*   获取帖子的评论，可指定深度。
*   提供格式化帖子和评论数据的辅助函数。
*   包含基本用法示例。

## 要求

*   Python 3.x
*   PRAW 库 (`pip install praw`)
*   Reddit API 凭据

## 设置

在运行脚本之前，你需要设置以下环境变量：

*   `REDDIT_CLIENT_ID`: 你的 Reddit 应用 Client ID。
*   `REDDIT_CLIENT_SECRET`: 你的 Reddit 应用 Client Secret。
*   `REDDIT_USER_AGENT`: 一个描述性的 User Agent 字符串 (例如 `'MyRedditBot/1.0 by u/YourUsername'`)。

你可以通过在终端中导出它们来设置这些变量：

```bash
export REDDIT_CLIENT_ID='你的客户端ID'
export REDDIT_CLIENT_SECRET='你的客户端密钥'
export REDDIT_USER_AGENT='你的用户代理'
```

或者将它们添加到你的 `.env` 文件中，并使用像 `python-dotenv` 这样的库来加载它们。

## 用法

你可以将 [`reddit_fetcher.py`](reddit_fetcher.py) 中的函数导入到你自己的 Python 脚本中。

```python
import reddit_fetcher
import os

# 确保环境变量已设置
# 例如：
# os.environ['REDDIT_CLIENT_ID'] = 'YOUR_ID'
# os.environ['REDDIT_CLIENT_SECRET'] = 'YOUR_SECRET'
# os.environ['REDDIT_USER_AGENT'] = 'YOUR_AGENT'

# 初始化 Reddit 实例
reddit = reddit_fetcher.initialize_reddit()

if reddit:
    # 获取 'learnpython' subreddit 的最新 5 个帖子
    posts = reddit_fetcher.get_subreddit_posts(reddit, 'learnpython', sort='new', limit=5)
    for post in posts:
        post_data = reddit_fetcher.format_post_data(post)
        print(f"- {post_data['title']}")

    # 搜索包含 'api' 的帖子
    search_results = reddit_fetcher.search_posts(reddit, query='api', limit=3)
    for post in search_results:
        print(f"Search Result: {post.title}")

    # 获取第一个搜索结果的评论
    if search_results:
        comments = reddit_fetcher.get_post_comments(search_results[0], limit=5, depth=1)
        for comment in comments:
             if isinstance(comment, praw.models.Comment): # 确保是评论对象
                comment_data = reddit_fetcher.format_comment_data(comment)
                print(f"  - Comment by {comment_data['author']}: {comment_data['body'][:50]}...")

```

## 运行示例

脚本包含一个 `if __name__ == "__main__":` 块，其中包含一些使用示例。你可以直接运行脚本来查看这些示例的输出：

```bash
python reddit_fetcher.py
```

## 主要函数

*   [`initialize_reddit()`](reddit_fetcher.py): 初始化并返回 PRAW Reddit 实例。
*   [`get_subreddit_posts()`](reddit_fetcher.py): 从 subreddit 获取帖子。
*   [`search_posts()`](reddit_fetcher.py): 搜索帖子。
*   [`get_random_post()`](reddit_fetcher.py): 获取随机帖子。
*   [`get_post_comments()`](reddit_fetcher.py): 获取帖子的评论。
*   [`format_post_data()`](reddit_fetcher.py): 将帖子对象格式化为字典。
*   [`format_comment_data()`](reddit_fetcher.py): 将评论对象格式化为字典。