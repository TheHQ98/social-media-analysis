import praw
import os  # 建议使用环境变量存储敏感信息
import time
import requests
from datetime import datetime

# --- Reddit API 凭据 ---
client_id = os.environ.get('REDDIT_CLIENT_ID', 'YOUR_CLIENT_ID')
client_secret = os.environ.get('REDDIT_CLIENT_SECRET', 'YOUR_CLIENT_SECRET')
user_agent = os.environ.get('REDDIT_USER_AGENT', 'YOUR_USER_AGENT')

# 检查是否使用了默认占位符，如果是，则提示用户替换
if client_id == 'YOUR_CLIENT_ID' or client_secret == 'YOUR_CLIENT_SECRET' or user_agent == 'YOUR_USER_AGENT':
    print("请替换代码中的 'YOUR_CLIENT_ID', 'YOUR_CLIENT_SECRET' 和 'YOUR_USER_AGENT' 为你自己的信息。")
    print("或者设置环境变量 REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT。")
    exit()  # 退出程序，直到用户配置好凭据

print("client_id:", client_id)
print("client_secret:", client_secret)
print("user_agent:", user_agent)

# --- 初始化 PRAW ---
try:
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        check_for_async=False
    )
    print("✅ PRAW 初始化成功。")

    def unix_time(dt_str):
        return int(datetime.strptime(dt_str, "%Y-%m-%d").timestamp())

    start_time = unix_time("2023-01-01")
    end_time = unix_time("2025-01-01")
    after = start_time
    batch_size = 1000

    print("🚀 开始通过 Pushshift 抓取 2023/1/1 到 2025/1/1 Reddit 全站帖子...")

    count = 0
    while after < end_time:
        url = (
            f"https://api.pullpush.io/reddit/search/submission/"
            f"?after={after}&before={end_time}&size={batch_size}&sort=asc&sort_type=created_utc"
        )
        try:
            response = requests.get(url)
            data = response.json().get("data", [])

            if not data:
                print("✅ 抓取完成或无更多数据。")
                break

            for post in data:
                created_utc = post.get("created_utc")
                title = post.get("title", "[无标题]")
                post_time = datetime.utcfromtimestamp(created_utc).strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{post_time}] {title}")
                count += 1

            after = data[-1]["created_utc"]
            print(f"⏸️ 已抓取 {count} 条，休息 5 秒...")
            time.sleep(5)

        except KeyboardInterrupt:
            print("🛑 手动终止程序。"); break
        except Exception as e:
            print(f"⚠️ 错误: {e}，等待 10 秒重试...")
            time.sleep(10)

    print("✅ 抓取结束，总计帖子数：", count)

except Exception as e:
    print(f"发生错误: {e}")
