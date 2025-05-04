import os
import json
import unittest
from mastodonApi import fetch_post_data

TEST_CASE_DIR = "test_cases"

class TestFetchPostData(unittest.TestCase):
    def run_test_file(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                test_cases = json.load(f)
            except json.JSONDecodeError as e:
                self.fail(f"Invalid JSON in {filepath}: {e}")

        for i, case in enumerate(test_cases):
            with self.subTest(file=filepath, case=i + 1):
                try:
                    result = fetch_post_data(case)
                    self.assertIn("platform", result)
                    self.assertEqual(result["platform"], "Mastodon")
                    self.assertIn("data", result)
                    self.assertIn("id", result["data"])
                except Exception as e:
                    self.fail(f"Exception in {filepath}, case {i + 1}: {e}")

    def test_all_cases(self):
        for filename in os.listdir(TEST_CASE_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(TEST_CASE_DIR, filename)
                self.run_test_file(filepath)

if __name__ == "__main__":
    unittest.main()
