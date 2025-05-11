from elasticsearch import Elasticsearch
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime

es = Elasticsearch(
    "https://elastic:elastic@127.0.0.1:9200",
    verify_certs=False, 
    ssl_show_warn=False,
    basic_auth=("elastic", "elastic")
)

all_resp = es.search(
    index="socialplatform",
    query={ 
        "bool": {
            "must": [
                {"terms": {"data.tags":["melbourne", "sydney", "brisbane", "adelaide", "perth", "hobart", "darwin", "canberra"]}}
            ]
        }
    },
    track_total_hits=True, 
    size=10000  
)

print("match_all 总命中：", all_resp["hits"]["total"]["value"])

fields = [
    'id', 'createdAt', 'content', 'sensitive', 'favouritesCount', 'repliesCount', 'tags', 'url', 'username'
]

print("\n=== datas ===")
for data in all_resp["hits"]["hits"]:
    post = data.get("_source", {})
    data_section = post.get('data', {})
    account_section = data_section.get('account', {})

    row = {
        "id": data_section.get('id', ''),
        "createdAt": data_section.get('createdAt', ''),
        "content": data_section.get('content', ''),
        "sensitive": data_section.get('sensitive', ''),
        "favouritesCount": data_section.get('favouritesCount', ''),
        "repliesCount": data_section.get('repliesCount', ''),
        "tags": ','.join(data_section.get('tags', [])), 
        "url": data_section.get('url', ''),
        "username": account_section.get('username', '') 
    }

    #print(row) 

print("\n✅ end")
