from elasticsearch import Elasticsearch
from collections import defaultdict
from datetime import datetime

es = Elasticsearch(
    "https://elastic:elastic@127.0.0.1:9200",
    verify_certs=False, 
    ssl_show_warn=False,
    basic_auth=("elastic", "elastic"),
    timeout=60,             
    max_retries=5,          
    retry_on_timeout=True    
)

all_resp = es.search(
    index="socialplatform",
    query={
        "range": {
            "data.createdAt": {
                "gte": "2023-01-01",
                "lt": "2026-01-01"
            }
        }
    },
    track_total_hits=True, 
    size=10000
)

print("match_all ：", all_resp["hits"]["total"]["value"])

monthly_tags = defaultdict(lambda: defaultdict(int))

for data in all_resp["hits"]["hits"]:
    post = data.get("_source", {})
    data_section = post.get('data', {})
    #print(post.get('keywords',{}))
    #print(data_section['createdAt'])
    
    created_at = data_section['createdAt']
    keywords = post.get('keywords',{})
    
    if not created_at or not keywords:
        continue

    try:
        date_obj = datetime.fromisoformat(created_at[:-1])
        #print(date_obj)
        month_key = date_obj.strftime("%Y-%m")  # "2023-04"
    except ValueError:
        continue

    for keyword in keywords:
        monthly_tags[month_key][keyword] += 1

print("\n=== Top 5 in every month ===")
for month, tags in sorted(monthly_tags.items()):
    sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
    top_5_tags = sorted_tags[:5]
    
    print(f"\n{month} top 5 keywords：")
    for tag, count in top_5_tags:
        print(f"{tag}: {count} times")
