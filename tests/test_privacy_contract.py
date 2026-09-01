import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".xml"}


def source_texts():
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.casefold() in TEXT_SUFFIXES:
            yield path, path.read_text(encoding="utf-8")


class PrivacyContractTests(unittest.TestCase):
    def test_uses_generic_skill_identity(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: endnote-xml-literature-search\n"))
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$endnote-xml-literature-search", metadata)

    def test_contains_no_private_or_original_fixture_values(self):
        forbidden_literals = [
            "Kev" + "in",
            "文献" + "精读",
            "My EndNote " + "Library Copy",
            "endnote-" + "local-literature-search",
            "Wang, " + "Xiaoming",
            "Müller, " + "Anna",
            "Li, " + "Wei",
            "10.1000/" + "example",
            "12345" + "67890",
        ]
        failures = []
        for path, text in source_texts():
            for value in forbidden_literals:
                if value.casefold() in text.casefold():
                    failures.append(f"{path.relative_to(ROOT)} contains {value!r}")
        self.assertEqual(failures, [])

    def test_contains_no_absolute_user_paths(self):
        windows_drive = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/]")
        user_home = re.compile(r"(?i)(?:[\\/]Users[\\/]|[\\/]home[\\/])[^\\/\s]+")
        failures = []
        for path, text in source_texts():
            if windows_drive.search(text) or user_home.search(text):
                failures.append(str(path.relative_to(ROOT)))
        self.assertEqual(failures, [])

    def test_excludes_session_notes(self):
        names = {path.name for path in ROOT.rglob("*")}
        self.assertNotIn("TEST-NOTES.md", names)


if __name__ == "__main__":
    unittest.main()
