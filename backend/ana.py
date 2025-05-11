import matplotlib.pyplot as plt
from elasticsearch import Elasticsearch
from collections import defaultdict
from datetime import datetime
import re

es = Elasticsearch(
    "https://elastic:elastic@127.0.0.1:9200",
    verify_certs=False, 
    ssl_show_warn=False,
    basic_auth=("elastic", "elastic"),
    timeout=60,             
    max_retries=5,          
    retry_on_timeout=True    
)

scroll_size = 10000  # 10000 every time
scroll_timeout = "2m" 
scroll_resp = es.search(
    index="socialplatform",
    query={
        "range": {
            "data.createdAt": {
                "gte": "2023-01-01",
                "lt": "2026-01-01"
            }
        }
    },
    size=scroll_size,
    scroll=scroll_timeout
)

scroll_id = scroll_resp["_scroll_id"]
total_hits = scroll_resp["hits"]["total"]["value"]
print(f"Total Posts: {total_hits}")

monthly_keywords = defaultdict(lambda: defaultdict(int))

while True:
    for data in scroll_resp["hits"]["hits"]:
        post = data.get("_source", {})
        data_section = post.get('data', {})

        created_at = data_section['createdAt']
        keywords = post.get('keywords', {})
        
        if not created_at or not keywords:
            continue

        try:
            date_obj = datetime.fromisoformat(created_at[:-1])
            month_key = date_obj.strftime("%Y-%m")
        except ValueError:
            continue

        for keyword in keywords:
            monthly_keywords[month_key][keyword] += 1

    scroll_resp = es.scroll(scroll_id=scroll_id, scroll=scroll_timeout)
    if not scroll_resp["hits"]["hits"]:
        break  


print("\n=== Top 5 keywords ===")
for month, keywords in sorted(monthly_keywords.items()):
    sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
    top_5_keywords = sorted_keywords[:5]
    
    print(f"\n{month} top 5")
    for keyword, count in top_5_keywords:
        print(f"{keyword}: {count} times")

    # Pie chart for each month
    labels = [kw for kw, _ in top_5_keywords]
    sizes = [count for _, count in top_5_keywords]
    other_count = sum(keywords.values()) - sum(sizes)
    labels.append('Other')
    sizes.append(other_count)

    plt.figure(figsize=(6,6))
    plt.pie(sizes, labels=labels, autopct="%.2f%%", startangle=90, counterclock=False)
    plt.title(f"Top 5 Keywords in {month}")
    plt.show()
