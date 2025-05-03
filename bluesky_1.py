import json
import requests
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

def load_session():
    load_dotenv("bluesky.env")
    username = os.getenv("BSKY_USERNAME")
    password = os.getenv("BSKY_APP_PASSWORD")

    if not username or not password:
        print("Error: Missing environment variables BSKY_USERNAME or BSKY_APP_PASSWORD.")
        print("Please ensure the bluesky.env file exists and contains correct credentials.")
        exit(1)

    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": username, "password": password}

    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"Error: HTTP status code {res.status_code}")
            print(f"Response content: {res.text}")
            res.raise_for_status()
        return res.json()["accessJwt"]
    except Exception as e:
        print(f"Error during login: {e}")
        print("Please ensure you are using the correct username/email and app password.")
        exit(1)

def search_australia_cost_of_living(token, start_date=None, max_results=1000):
    url = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept-Language": "en"
    }

    search_terms = [
        "Australia cost of living",
        "Australian housing prices",
        "Sydney rent expensive",
        "Melbourne housing cost",
        "Australia inflation",
        "Australia living expenses",
        "Australia rent crisis",
        "Australia property market",
        "Australia grocery prices",
        "Australia utility bills",
        "Australia housing affordability",
        "Brisbane rent prices",
        "Perth cost of living",
        "Australia housing bubble",
        "Australia rental market"
    ]

    seen_uris = set()
    total_fetched_posts = 0  # Total number of fetched posts across all terms

    for term in search_terms:
        cursor = None
        found_for_term = 0
        page = 0

        while found_for_term < 100 and page < 10:
            params = {
                "q": term,
                "limit": 50
            }
            if cursor:
                params["cursor"] = cursor

            try:
                res = requests.get(url, headers=headers, params=params)
                res.raise_for_status()
                data = res.json()

                posts_in_page = 0

                for post in data.get("posts", []):
                    record = post.get("record", {})
                    created_at = record.get("createdAt", "")
                    content = record.get("text", "")
                    uri = post.get("uri", "")

                    if uri in seen_uris:
                        continue

                    if start_date and created_at:
                        try:
                            post_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            if post_date < start_date:
                                continue
                        except ValueError:
                            pass

                    seen_uris.add(uri)

                    doc = {
                        "platform": "Bluesky",
                        "version": 1.1,
                        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "sentiment": None,
                        "sentimentLabel": None,
                        "keywords": [],
                        "data": {
                            "id": uri.split("/")[-1],
                            "createdAt": created_at,
                            "content": content,
                            "sensitive": False,
                            "favouritesCount": post.get("likeCount", 0),
                            "repliesCount": post.get("replyCount", 0),
                            "tags": [],
                            "url": f"https://bsky.app/profile/{post.get('author', {}).get('handle', '')}/post/{uri.split('/')[-1]}",
                            "account": {
                                "id": post.get("author", {}).get("did", ""),
                                "username": post.get("author", {}).get("handle", ""),
                                "createdAt": "2022-10-30T00:00:00Z",
                                "followersCount": 0,
                                "followingCount": 0
                            }
                        }
                    }

                    print(json.dumps(doc))

                    found_for_term += 1
                    total_fetched_posts += 1
                    posts_in_page += 1

                if not data.get("cursor") or len(data.get("posts", [])) == 0:
                    break

                cursor = data.get("cursor")
                page += 1

                time.sleep(1)

            except Exception as e:
                print(f"Error during search: {e}")
                break

    print(f"\n Total posts fetched across all terms: {total_fetched_posts}")

def main():
    three_years_ago = datetime.now(timezone.utc) - timedelta(days=3*365)

    token = load_session()

    search_australia_cost_of_living(token, start_date=three_years_ago)

if __name__ == "__main__":
    main()
