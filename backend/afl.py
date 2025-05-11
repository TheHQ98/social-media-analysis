from elasticsearch import Elasticsearch
from collections import defaultdict

es = Elasticsearch(
    "https://elastic:elastic@127.0.0.1:9200",
    verify_certs=False, 
    ssl_show_warn=False,
    basic_auth=("elastic", "elastic"),
    timeout=60,             
    max_retries=5,          
    retry_on_timeout=True    
)

afl_teams_aliases = {
    "Adelaide Crows": ["Adelaide", "Crows", "The Crows", "Ades"],
    "Brisbane Lions": ["Brisbane", "Lions", "Brissie", "The Lions"],
    "Carlton": ["Carlton", "Blues", "The Blues"],
    "Collingwood Magpies": ["Collingwood", "Magpies", "Pies", "The Pies"],
    "Essendon Bombers": ["Essendon", "Bombers", "Dons", "The Bombers"],
    "Fremantle Dockers": ["Fremantle", "Dockers", "Freo", "The Dockers"],
    "Geelong Cats": ["Geelong", "Cats", "The Cats"],
    "Gold Coast Suns": ["Gold Coast", "Suns", "The Suns"],
    "GWS Giants": ["GWS", "Giants", "Greater Western Sydney", "The Giants"],
    "Hawthorn Hawks": ["Hawthorn", "Hawks", "The Hawks"],
    "Melbourne Demons": ["Melbourne", "Demons", "Dees", "The Demons"],
    "North Melbourne Kangaroos": ["North Melbourne", "Kangaroos", "Roos", "The Roos"],
    "Port Adelaide Power": ["Port Adelaide", "Power", "The Power", "Port"],
    "Richmond Tigers": ["Richmond", "Tigers", "The Tigers"],
    "St Kilda Saints": ["St Kilda", "Saints", "The Saints"],
    "Sydney Swans": ["Sydney", "Swans", "The Swans"],
    "West Coast Eagles": ["West Coast", "Eagles", "The Eagles"],
    "Western Bulldogs": ["Western Bulldogs", "Bulldogs", "Doggies", "The Bulldogs"]
}

afl_team_filters = []
for team, aliases in afl_teams_aliases.items():
    for alias in aliases:
        afl_team_filters.append({"match": {"data.content": alias}})
        afl_team_filters.append({"match_phrase": {"data.content": alias}})

scroll_size = 10000  
scroll_timeout = "2m" 
scroll_resp = es.search(
    index="socialplatform",
    query={
        "bool": {
            "must": [
                {"range": {"data.createdAt": {"gte": "2023-01-01", "lt": "2026-01-01"}}}
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

team_sentiment = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})

while True:
    for data in scroll_resp["hits"]["hits"]:
        post = data.get("_source", {})
        data_section = post.get('data', {})
        content = data_section.get('content', '').lower()
        sentiment = post.get("sentimentLabel", "neutral").lower()
        
        if not content:
            continue

        for team, aliases in afl_teams_aliases.items():
            if any(alias.lower() in content for alias in aliases):
                if sentiment in ["positive", "neutral", "negative"]:
                    team_sentiment[team][sentiment] += 1
                else:
                    team_sentiment[team]["neutral"] += 1

    scroll_resp = es.scroll(scroll_id=scroll_id, scroll=scroll_timeout)
    if not scroll_resp["hits"]["hits"]:
        break  

print("\n=== AFL Team Sentiment (Loose Filtering) ===")
for team, sentiments in sorted(team_sentiment.items()):
    print(f"{team} - Positive: {sentiments['positive']} | Neutral: {sentiments['neutral']} | Negative: {sentiments['negative']}")
