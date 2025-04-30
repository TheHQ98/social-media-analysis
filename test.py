#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta
import os, time
from dotenv import load_dotenv
from dateutil.parser import isoparse
from tqdm import tqdm
import praw

# ---------- .env ----------
load_dotenv()
CID = os.getenv("REDDIT_CLIENT_ID")
CSEC = os.getenv("REDDIT_CLIENT_SECRET")
UA = os.getenv("REDDIT_USER_AGENT")
assert all([CID, CSEC, UA]), "❌ 缺 Reddit 凭据，请检查 .env"

# ---------- 参数 ----------
SUBREDDIT = "AskAnAustralian"  # 换成你要统计的版块
END_DATE = "2023-01-01T00:00:00Z"  # 截止时间
END_TS = int(isoparse(END_DATE).timestamp())
BATCH_SEC = 30 * 24 * 3600  # 每次取 30 天
INFO_CHUNK = 100  # reddit.info 单批上限
# ---------------------------------

reddit = praw.Reddit(
    client_id=CID,
    client_secret=CSEC,
    user_agent=UA,
    username=os.getenv("REDDIT_USERNAME"),   # 需要 .env 再加两行
    password=os.getenv("REDDIT_PASSWORD"),
)


def daterange_chunks(end_ts):
    """生成 (start_ts, end_ts) 月度区间，从当前月向后回溯"""
    end_dt = datetime.now(timezone.utc).replace(hour=0, minute=0,
                                                second=0, microsecond=0)
    while end_dt.timestamp() > end_ts:
        start_dt = (end_dt - timedelta(seconds=BATCH_SEC))
        yield int(start_dt.timestamp()), int(end_dt.timestamp())
        end_dt = start_dt


def fetch_ids(subreddit, until_ts):
    ids = []
    bar = tqdm(desc="Fetch ID chunks", unit="chunk")
    for start_ts, end_ts in daterange_chunks(until_ts):
        query = f"timestamp:{start_ts}..{end_ts}"
        for p in reddit.subreddit(subreddit).search(
                query, syntax="cloudsearch", sort="new", limit=None):
            ids.append(p.id)
        bar.update(1)
        time.sleep(1)  # 避免速限
    bar.close()
    return ids


def count_with_info(ids):
    """用 reddit.info 验证（或拿详情），返回有效帖子数量"""
    count = 0
    for i in range(0, len(ids), INFO_CHUNK):
        chunk = ids[i:i + INFO_CHUNK]
        full = [f"t3_{_id}" for _id in chunk]
        try:
            submissions = list(reddit.info(fullnames=full))
            count += len(submissions)
        except Exception as e:
            print("reddit.info error:", e)
        time.sleep(2)
    return count


if __name__ == "__main__":
    print(f"▶️  统计 r/{SUBREDDIT} 从现在回溯到 {END_DATE} 的帖子数 …")
    id_list = fetch_ids(SUBREDDIT, END_TS)
    print(f"ID 抓取完毕，共 {len(id_list):,} 条，开始 reddit.info 校验…")
    total = count_with_info(id_list)
    print(f"\n✅  r/{SUBREDDIT} 2025-04-29 → 2023-01-01 共有 {total:,} 条帖子")
