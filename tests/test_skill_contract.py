import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"

REQUIRED_SKILL_PHRASES = [
    "Title + Abstract + Keywords",
    "PDF not reliably matched",
    "Not reported",
    "Highly relevant",
    "References used from local EndNote Library",
]


class SkillContractTests(unittest.TestCase):
    def test_skill_contains_nonnegotiable_contract(self):
        text = SKILL.read_text(encoding="utf-8")
        for phrase in REQUIRED_SKILL_PHRASES:
            self.assertIn(phrase, text)

    def test_skill_links_conditional_references(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("references/pdf-matching-and-reading.md", text)
        self.assertIn("references/evidence-and-output.md", text)

    def test_skill_mentions_every_cli_command(self):
        text = SKILL.read_text(encoding="utf-8")
        for command in ("discover", "index", "search", "resolve"):
            self.assertIn(f"endnote_search.py {command}", text)

    def test_skill_has_expected_frontmatter(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: endnote-xml-literature-search\n"))
        self.assertIn("local EndNote XML export", text.split("---", 2)[1])


if __name__ == "__main__":
    unittest.main()
