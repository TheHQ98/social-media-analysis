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
        "Australia rental market""Adelaide City",
        "Adelaide Hills",
        "Albany",
        "Albury",
        "Alice Springs",
        "Armadale",
        "Armidale",
        "Auburn",
        "Augusta - Margaret River - Busselton",
        "Bald Hills - Everton Park",
        "Ballarat",
        "Bankstown",
        "Banyule",
        "Barkly",
        "Barossa",
        "Barwon - West",
        "Bathurst",
        "Baulkham Hills",
        "Baw Baw",
        "Bayside",
        "Bayswater - Bassendean",
        "Beaudesert",
        "Beenleigh",
        "Belconnen",
        "Belmont - Victoria Park",
        "Bendigo",
        "Biloela",
        "Blacktown",
        "Blacktown - North",
        "Blue Mountains",
        "Blue Mountains - South",
        "Boroondara",
        "Botany",
        "Bourke - Cobar - Coonamble",
        "Bowen Basin - North",
        "Bribie - Beachmere",
        "Brighton",
        "Brimbank",
        "Bringelly - Green Valley",
        "Brisbane Inner",
        "Brisbane Inner - East",
        "Brisbane Inner - North",
        "Brisbane Inner - West",
        "Broadbeach - Burleigh",
        "Broken Hill and Far West",
        "Browns Plains",
        "Brunswick - Coburg",
        "Buderim",
        "Bunbury",
        "Bundaberg",
        "Burnett",
        "Burnie - Ulverstone",
        "Burnside",
        "Caboolture",
        "Caboolture Hinterland",
        "Cairns - North",
        "Cairns - South",
        "Caloundra",
        "Camden",
        "Campaspe",
        "Campbelltown (NSW)",
        "Campbelltown (SA)",
        "Canada Bay",
        "Canberra East",
        "Canning",
        "Canterbury",
        "Capalaba",
        "Cardinia",
        "Carindale",
        "Carlingford",
        "Casey - North",
        "Casey - South",
        "Centenary",
        "Central Highlands (Qld)",
        "Central Highlands (Tas.)",
        "Charles Sturt",
        "Charters Towers - Ayr - Ingham",
        "Chatswood - Lane Cove",
        "Chermside",
        "Christmas Island",
        "Clarence Valley",
        "Cleveland - Stradbroke",
        "Cockburn",
        "Cocos (Keeling) Islands",
        "Coffs Harbour",
        "Colac - Corangamite",
        "Coolangatta",
        "Cottesloe - Claremont",
        "Creswick - Daylesford - Ballan",
        "Cronulla - Miranda - Caringbah",
        "Daly - Tiwi - West Arnhem",
        "Dandenong",
        "Dapto - Port Kembla",
        "Darebin - North",
        "Darebin - South",
        "Darling Downs (West) - Maranoa",
        "Darling Downs - East",
        "Darwin City",
        "Darwin Suburbs",
        "Devonport",
        "Dubbo",
        "Dural - Wisemans Ferry",
        "East Arnhem",
        "East Pilbara",
        "Eastern Suburbs - North",
        "Eastern Suburbs - South",
        "Esperance",
        "Essendon",
        "Eyre Peninsula and South West",
        "Fairfield",
        "Far North",
        "Fleurieu - Kangaroo Island",
        "Forest Lake - Oxley",
        "Frankston",
        "Fremantle",
        "Gascoyne",
        "Gawler - Two Wells",
        "Geelong",
        "Gippsland - East",
        "Gippsland - South West",
        "Gladstone",
        "Glen Eira",
        "Glenelg - Southern Grampians",
        "Gold Coast - North",
        "Gold Coast Hinterland",
        "Goldfields",
        "Gosford",
        "Gosnells",
        "Goulburn - Mulwaree",
        "Grampians",
        "Granite Belt",
        "Great Lakes",
        "Griffith - Murrumbidgee (West)",
        "Gungahlin",
        "Gympie - Cooloola",
        "Hawkesbury",
        "Heathcote - Castlemaine - Kyneton",
        "Hervey Bay",
        "Hobart - North East",
        "Hobart - North West",
        "Hobart - South and West",
        "Hobart Inner",
        "Hobsons Bay",
        "Holdfast Bay",
        "Holland Park - Yeronga",
        "Hornsby",
        "Huon - Bruny Island",
        "Hurstville",
        "Illawarra Catchment Reserve",
        "Innisfail - Cassowary Coast",
        "Inverell - Tenterfield",
        "Ipswich Hinterland",
        "Ipswich Inner",
        "Jervis Bay",
        "Jimboomba",
        "Joondalup",
        "Kalamunda",
        "Katherine",
        "Keilor",
        "Kempsey - Nambucca",
        "Kenmore - Brookfield - Moggill",
        "Kiama - Shellharbour",
        "Kimberley",
        "Kingston",
        "Knox",
        "Kogarah - Rockdale",
        "Ku-ring-gai",
        "Kwinana",
        "Lachlan Valley",
        "Lake Macquarie - East",
        "Lake Macquarie - West",
        "Latrobe Valley",
        "Launceston",
        "Leichhardt",
        "Limestone Coast",
        "Litchfield",
        "Lithgow - Mudgee",
        "Liverpool",
        "Loddon - Elmore",
        "Loganlea - Carbrook",
        "Lord Howe Island",
        "Lower Hunter",
        "Lower Murray",
        "Lower North",
        "Macedon Ranges",
        "Mackay",
        "Maitland",
        "Mandurah",
        "Manjimup",
        "Manly",
        "Manningham - East",
        "Manningham - West",
        "Maribyrnong",
        "Marion",
        "Maroochy",
        "Maroondah",
        "Marrickville - Sydenham - Petersham",
        "Maryborough",
        "Maryborough - Pyrenees",
        "Meander Valley - West Tamar",
        "Melbourne City",
        "Melton - Bacchus Marsh",
        "Melville",
        "Merrylands - Guildford",
        "Mid North",
        "Mid West",
        "Migratory - Offshore - Shipping (ACT)",
        "Migratory - Offshore - Shipping (NSW)",
        "Migratory - Offshore - Shipping (NT)",
        "Migratory - Offshore - Shipping (OT)",
        "Migratory - Offshore - Shipping (Qld)",
        "Migratory - Offshore - Shipping (SA)",
        "Migratory - Offshore - Shipping (Tas.)",
        "Migratory - Offshore - Shipping (Vic.)",
        "Migratory - Offshore - Shipping (WA)",
        "Mildura",
        "Mitcham",
        "Moira",
        "Molonglo",
        "Monash",
        "Moree - Narrabri",
        "Moreland - North",
        "Mornington Peninsula",
        "Mount Druitt",
        "Mt Gravatt",
        "Mudgeeraba - Tallebudgera",
        "Mundaring",
        "Murray River - Swan Hill",
        "Murray and Mallee",
        "Nambour",
        "Narangba - Burpengary",
        "Nathan",
        "Nerang",
        "Newcastle",
        "Nillumbik - Kinglake",
        "No usual address (ACT)",
        "No usual address (NSW)",
        "No usual address (NT)",
        "No usual address (OT)",
        "No usual address (Qld)",
        "No usual address (SA)",
        "No usual address (Tas.)",
        "No usual address (Vic.)",
        "No usual address (WA)",
        "Noosa",
        "Noosa Hinterland",
        "Norfolk Island",
        "North Canberra",
        "North East",
        "North Lakes",
        "North Sydney - Mosman",
        "Norwood - Payneham - St Peters",
        "Nundah",
        "Onkaparinga",
        "Orange",
        "Ormeau - Oxenford",
        "Outback - North",
        "Outback - North and East",
        "Outback - South",
        "Outside Australia",
        "Palmerston",
        "Parramatta",
        "Pennant Hills - Epping",
        "Penrith",
        "Perth City",
        "Pittwater",
        "Playford",
        "Port Adelaide - East",
        "Port Adelaide - West",
        "Port Douglas - Daintree",
        "Port Macquarie",
        "Port Phillip",
        "Port Stephens",
        "Prospect - Walkerville",
        "Queanbeyan",
        "Redcliffe",
        "Richmond - Windsor",
        "Richmond Valley - Coastal",
        "Richmond Valley - Hinterland",
        "Robina",
        "Rockhampton",
        "Rockingham",
        "Rocklea - Acacia Ridge",
        "Rouse Hill - McGraths Hill",
        "Ryde - Hunters Hill",
        "Salisbury",
        "Sandgate",
        "Serpentine - Jarrahdale",
        "Shepparton",
        "Sherwood - Indooroopilly",
        "Shoalhaven",
        "Snowy Mountains",
        "Sorell - Dodges Ferry",
        "South Canberra",
        "South Coast",
        "South East Coast",
        "South Perth",
        "Southern Highlands",
        "Southport",
        "Springfield - Redbank",
        "Springwood - Kingston",
        "St Marys",
        "Stirling",
        "Stonnington - East",
        "Stonnington - West",
        "Strathfield - Burwood - Ashfield",
        "Strathpine",
        "Sunbury",
        "Sunnybank",
        "Sunshine Coast Hinterland",
        "Surf Coast - Bellarine Peninsula",
        "Surfers Paradise",
        "Sutherland - Menai - Heathcote",
        "Swan",
        "Sydney Inner City",
        "Tablelands (East) - Kuranda",
        "Tamworth - Gunnedah",
        "Taree - Gloucester",
        "Tea Tree Gully",
        "The Gap - Enoggera",
        "The Hills District",
        "Toowoomba",
        "Townsville",
        "Tuggeranong",
        "Tullamarine - Broadmeadows",
        "Tumut - Tumbarumba",
        "Tweed Valley",
        "Unley",
        "Upper Goulburn Valley",
        "Upper Hunter",
        "Upper Murray exc. Albury",
        "Uriarra - Namadgi",
        "Wagga Wagga",
        "Wangaratta - Benalla",
        "Wanneroo",
        "Warringah",
        "Warrnambool",
        "Wellington",
        "West Coast",
        "West Pilbara",
        "West Torrens",
        "Weston Creek",
        "Wheat Belt - North",
        "Wheat Belt - South",
        "Whitehorse - East",
        "Whitehorse - West",
        "Whitsunday",
        "Whittlesea - Wallan",
        "Woden Valley",
        "Wodonga - Alpine",
        "Wollondilly",
        "Wollongong",
        "Wyndham",
        "Wynnum - Manly",
        "Wyong",
        "Yarra",
        "Yarra Ranges",
        "Yorke Peninsula",
        "Young - Yass"
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
                            "sensitive": None,  # not provided, using null
                            "favouritesCount": post.get("likeCount", 0),
                            "repliesCount": post.get("replyCount", 0),
                            "tags": [term],  # Add the current search term as a tag
                            "url": f"https://bsky.app/profile/{post.get('author', {}).get('handle', '')}/post/{uri.split('/')[-1]}",
                            "account": {
                                "id": post.get("author", {}).get("did", ""),
                                "username": post.get("author", {}).get("handle", ""),
                                "createdAt": None,  # not provided, using null
                                "followersCount": None,  # not provided, using null
                                "followingCount": None  # not provided, using null
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
    three_years_ago = datetime.now(timezone.utc) - timedelta(days=3 * 365)

    token = load_session()

    search_australia_cost_of_living(token, start_date=three_years_ago)


if __name__ == "__main__":
    main()
