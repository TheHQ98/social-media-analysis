import matplotlib.pyplot as plt
from elasticsearch import Elasticsearch
from collections import defaultdict
from datetime import datetime

afl_teams = [
    "Adelaide", "Brisbane", "Carlton", "Collingwood", "Essendon", 
    "Fremantle", "Geelong", "Gold Coast", "GWS Giants", 
    "Hawthorn", "Melbourne", "North Melbourne", "Port Adelaide", 
    "Richmond", "St Kilda", "Sydney", "West Coast", "Western Bulldogs"
]

es = Elasticsearch(
    "https://elastic:elastic@127.0.0.1:9200",
    verify_certs=False, 
    ssl_show_warn=False,
    basic_auth=("elastic", "elastic"),
    timeout=60,             
    max_retries=5,          
    retry_on_timeout=True    
)

afl_team_filters = [{"match_phrase": {"data.content": team}} for team in afl_teams]

scroll_size = 10000  # 10000 every time
scroll_timeout = "2m" 

scroll_resp = es.search(
    index="socialplatform",
    query={
        "bool": {
            "must": [ 
                {
                    "range": {
                        "data.createdAt": {
                            "gte": "2023-01-01",
                            "lt": "2026-01-01"
                        }
                    }
                }
            ],
            "should": afl_team_filters,  
            "minimum_should_match": 1
        }
    },
    size=scroll_size,
    scroll=scroll_timeout
)


scroll_id = scroll_resp["_scroll_id"]
total_hits = scroll_resp["hits"]["total"]["value"]
print(f"Total Posts: {total_hits}")

monthly_team_sentiment = defaultdict(lambda: defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0}))

while True:
    for data in scroll_resp["hits"]["hits"]:
        post = data.get("_source", {})
        data_section = post.get('data', {})
        created_at = data_section.get('createdAt', '')
        keywords = post.get('keywords', [])
        sentiment = post.get("sentimentLabel", "neutral").lower()
        content = data_section.get('content', '')
        
        if not created_at:
            continue

        try:
            date_obj = datetime.fromisoformat(created_at[:-1])
            month_key = date_obj.strftime("%Y-%m")
        except ValueError:
            continue

        for team in afl_teams:
            if any(team.lower() in kw.lower() for kw in content):
                if sentiment in ["positive", "neutral", "negative"]:
                    monthly_team_sentiment[month_key][team][sentiment] += 1
                else:
                    monthly_team_sentiment[month_key][team]["neutral"] += 1

    scroll_resp = es.scroll(scroll_id=scroll_id, scroll=scroll_timeout)
    if not scroll_resp["hits"]["hits"]:
        break  

print("\n=== Monthly AFL Team Sentiment ===")
for month, teams in sorted(monthly_team_sentiment.items()):
    print(f"\n{month}:")
    for team, sentiments in teams.items():
        print(f"{team} - Positive: {sentiments['positive']} | Neutral: {sentiments['neutral']} | Negative: {sentiments['negative']}")

for month, teams in sorted(monthly_team_sentiment.items()):
    plt.figure(figsize=(12, 8))
    team_names = list(teams.keys())
    positives = [teams[team]['positive'] for team in team_names]
    neutrals = [teams[team]['neutral'] for team in team_names]
    negatives = [teams[team]['negative'] for team in team_names]

    bar_width = 0.25
    bar1 = range(len(team_names))
    bar2 = [i + bar_width for i in bar1]
    bar3 = [i + bar_width * 2 for i in bar1]

    plt.bar(bar1, positives, width=bar_width, label='Positive', color='green')
    plt.bar(bar2, neutrals, width=bar_width, label='Neutral', color='gray')
    plt.bar(bar3, negatives, width=bar_width, label='Negative', color='red')

    plt.xlabel("AFL Teams")
    plt.ylabel("Mentions")
    plt.title(f"AFL Team Sentiment in {month}")
    plt.xticks([r + bar_width for r in range(len(team_names))], team_names, rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()
