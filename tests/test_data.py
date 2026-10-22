import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/cases.json").read_text(encoding="utf-8"))["cases"]
HEROES = json.loads((ROOT / "data/heroes.json").read_text(encoding="utf-8"))
QUEUE = json.loads((ROOT / "data/research-queue.json").read_text(encoding="utf-8"))["items"]

class TestData(unittest.TestCase):
    def test_unique_ids(self):
        ids = [c["id"] for c in CASES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_valid_cases(self):
        heroes = set(HEROES["heroes"])
        for c in CASES:
            with self.subTest(case=c["id"]):
                self.assertEqual(len(c["def"]), 3)
                self.assertEqual(len(c["atk"]), 3)
                self.assertIn(c["review"], ("ready", "hold", "archive"))
                self.assertIn(c["grade"], ("primary", "repost"))
                self.assertIn(c["spanBasis"], ("mine", "enemy", "unspecified"))
                self.assertTrue(c["url"].startswith(("https://", "http://")))
                self.assertRegex(c["date"], r"^20\d\d-\d\d-\d\d$")
                for item in c["def"] + c["atk"]:
                    for hero in item if isinstance(item, list) else [item]:
                        if hero is not None:
                            self.assertIn(hero, heroes)

    def test_aliases(self):
        for key, value in HEROES["aliases"].items():
            self.assertIn(value, HEROES["heroes"], key)

    def test_research_links(self):
        for item in QUEUE:
            self.assertTrue(item["url"].startswith("https://"))

    def test_generated_html(self):
        html = (ROOT / "dist/index.html").read_text(encoding="utf-8")
        self.assertNotIn("__CASES_JSON__", html)
        self.assertIn("douyin-1", html)

if __name__ == "__main__":
    unittest.main()
