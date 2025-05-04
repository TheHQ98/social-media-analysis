from mastodon import Mastodon
import json

def config(k: str) -> str:
    with open(f"/configs/default/masto-config/{k}", "r") as f:
        return f.read().strip()

access_token = config("ACCESS_TOKEN")
api_base_url = config("API_BASE_URL")

mastodon = Mastodon(
    access_token=access_token,
    api_base_url=api_base_url
)

posts = mastodon.timeline_public(limit=1)

print(posts) 
