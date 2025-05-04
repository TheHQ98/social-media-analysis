import unittest
import copy
import random
from mastodon import Mastodon
from mastodonApi import fetch_post_data
import os
import json

def config(k: str) -> str:
    with open(f"./configs/default/masto-config/{k}", "r") as f:
        return f.read().strip()

def get_live_post():
    mastodon = Mastodon(
        access_token=config("ACCESS_TOKEN"),
        api_base_url=config("API_BASE_URL")
    )
    post = mastodon.timeline_public(limit=1)[0]
    return {
        "id": post.id,
        "created_at": post.created_at,
        "content": post.content,
        "sensitive": post.sensitive,
        "spoiler_text": post.spoiler_text,
        "language": post.language,
        "visibility": post.visibility,
        "favourites_count": post.favourites_count,
        "reblogs_count": post.reblogs_count,
        "replies_count": post.replies_count,
        "tags": [{"name": tag.name} for tag in getattr(post, "tags", [])],
        "url": post.url,
        "account": {
            "id": post.account.id,
            "username": post.account.username,
            "acct": post.account.acct,
            "display_name": post.account.display_name,
            "created_at": post.account.created_at,
            "followers_count": post.account.followers_count,
            "following_count": post.account.following_count,
            "statuses_count": post.account.statuses_count,
            "bot": post.account.bot,
            "note": post.account.note
        }
    }

def mutate_remove_field(post, path):
    post = copy.deepcopy(post)
    obj = post
    for key in path[:-1]:
        obj = obj.get(key, {})
    obj.pop(path[-1], None)
    return post

def mutate_set_field(post, path, value):
    post = copy.deepcopy(post)
    obj = post
    for key in path[:-1]:
        obj = obj.get(key, {})
    obj[path[-1]] = value
    return post

def get_all_paths(d, prefix=None):
    if prefix is None:
        prefix = []
    paths = []
    if isinstance(d, dict):
        for k, v in d.items():
            new_prefix = prefix + [k]
            paths.append(new_prefix)
            paths.extend(get_all_paths(v, new_prefix))
    return paths

def random_mutate(post, num_mutations=3, protected_keys=None):
    post = copy.deepcopy(post)
    protected_keys = protected_keys or {"id", "created_at"}

    all_paths = [p for p in get_all_paths(post) if not any(k in protected_keys for k in p)]
    if not all_paths:
        return post

    for _ in range(num_mutations):
        path = random.choice(all_paths)
        op = random.choice(["remove", "set"])
        obj = post
        for key in path[:-1]:
            obj = obj.get(key, {})

        try:
            if op == "remove":
                obj.pop(path[-1], None)
            else:
                value = random.choice(["oops", 123, None, [], {}, True])
                obj[path[-1]] = value
        except Exception as e:
            print(f"❌ Mutation failed on {'.'.join(path)}: {e}")
    return post

class LiveMutationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("Fetching live post from Mastodon...")
        cls.base_post = get_live_post()
        with open("base_post.json", "w", encoding="utf-8") as f:
            json.dump(cls.base_post, f, indent=2, default=str)

    def try_mutation(self, mutated, description):
        with self.subTest(desc=description):
            try:
                result = fetch_post_data(mutated)
                self.assertIn("data", result)
                print(f"✅ {description} passed")
            except Exception as e:
                print(f"❌ {description} raised exception: {e}")
                self.fail(f"{description} failed")

    def test_fixed_mutations(self):
        base = self.base_post
        cases = [
            ("remove account", mutate_remove_field(base, ["account"])),#delete account
            ("remove account.username", mutate_remove_field(base, ["account", "username"])),#delete username
            ("set created_at to None", mutate_set_field(base, ["created_at"], None)),#set the created_at = None
            ("set account.followers_count to string", mutate_set_field(base, ["account", "followers_count"], "many")),#followers_count = many
            ("set tags to string", mutate_set_field(base, ["tags"], "bad")),#tags = "bad"
            ("set account.created_at to 'not-a-date'", mutate_set_field(base, ["account", "created_at"], "not-a-date")),#created_at = ntoa-a-date
        ]
        for desc, mutation in cases:
            self.try_mutation(mutation, desc)

    def test_random_mutation(self):
        for i in range(3):
            mutated = random_mutate(self.base_post, num_mutations=3)
            self.try_mutation(mutated, f"random mutation #{i+1}")

if __name__ == "__main__":
    unittest.main()
