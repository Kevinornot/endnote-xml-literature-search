import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample-endnote.xml"
SCRIPT = ROOT / "scripts" / "endnote_search.py"

spec = importlib.util.spec_from_file_location("endnote_search", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_record(title="", abstract="", keywords=None, record_number="1"):
    return {
        "record_number": record_number,
        "title": title,
        "authors": [],
        "year": "",
        "journal": "",
        "abstract": abstract,
        "keywords": keywords or [],
        "doi": "",
        "urls": [],
        "attachments": [],
        "source_xml": "fixture.xml",
        "duplicate_record_numbers": [record_number],
    }


class ParseTests(unittest.TestCase):
    def test_parses_nested_endnote_fields(self):
        records = module.parse_endnote_xml(FIXTURE)
        self.assertEqual(records[0]["record_number"], "10")
        self.assertEqual(records[0]["title"], "Redox control of phosphorus release")
        self.assertEqual(records[0]["authors"], ["Example, Author A", "Example, Author B"])
        self.assertEqual(records[0]["year"], "2021")
        self.assertEqual(records[0]["journal"], "Water Research")
        self.assertEqual(records[0]["keywords"], ["redox", "phosphorus"])
        self.assertEqual(
            records[0]["attachments"],
            ["internal-pdf://0000000000/example-paper.pdf"],
        )

    def test_normalizes_doi_and_title(self):
        self.assertEqual(module.normalize_doi("https://doi.org/10.0000/EXAMPLE-A"), "10.0000/example-a")
        self.assertEqual(module.normalize_doi("doi: 10.0000/example-a"), "10.0000/example-a")
        self.assertEqual(
            module.normalize_title("  Redox—control: of phosphorus release! "),
            "redox control of phosphorus release",
        )

    def test_deduplicates_doi_then_title(self):
        records = module.parse_endnote_xml(FIXTURE)
        unique = module.deduplicate_records(records)
        self.assertEqual(len(unique), 2)
        self.assertEqual(unique[0]["record_number"], "10")
        self.assertEqual(unique[0]["duplicate_record_numbers"], ["10", "11"])


class SearchTests(unittest.TestCase):
    def test_title_match_ranks_above_abstract_only_match(self):
        records = [
            make_record(title="Phosphate release under anoxia", record_number="1"),
            make_record(
                title="Unrelated title",
                abstract="Phosphate release under anoxia",
                record_number="2",
            ),
        ]
        results = module.search_records(records, "phosphate release anoxia", [], [], 10)
        self.assertEqual(results[0]["title"], "Phosphate release under anoxia")
        self.assertIn("title", results[0]["matched_fields"])

    def test_multiple_concept_groups_receive_bonus(self):
        records = [
            make_record(
                title="Sulfide controls lake denitrification",
                keywords=["nitrogen"],
                record_number="1",
            ),
            make_record(title="Sulfur transformations", record_number="2"),
        ]
        groups = [
            ["sulfur", "sulfide"],
            ["denitrification", "nitrogen"],
            ["lake", "reservoir"],
        ]
        results = module.search_records(records, "", [], groups, 10)
        self.assertGreater(
            results[0]["matched_concept_groups"],
            results[1]["matched_concept_groups"],
        )

    def test_non_searchable_metadata_does_not_score(self):
        record = make_record(title="Unrelated")
        record["authors"] = ["Phosphate, Alice"]
        record["journal"] = "Anoxia Reports"
        record["doi"] = "10.1/phosphorus"
        self.assertEqual(module.search_records([record], "phosphate anoxia", [], [], 10), [])


class CliTests(unittest.TestCase):
    def test_index_writes_versioned_utf8_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "index",
                    "--xml",
                    str(FIXTURE),
                    "--out",
                    str(output),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["record_count"], 2)
            self.assertEqual(Path(payload["source_xml"]), FIXTURE.resolve())

    def test_search_emits_limited_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.json"
            subprocess.run(
                [sys.executable, str(SCRIPT), "index", "--xml", str(FIXTURE), "--out", str(output)],
                check=True,
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "search",
                    "--index",
                    str(output),
                    "--query",
                    "phosphorus redox",
                    "--term",
                    "anoxia",
                    "--concept-group",
                    "redox|reduction",
                    "--limit",
                    "1",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["result_count"], 1)
            self.assertEqual(len(payload["results"]), 1)
            self.assertEqual(payload["results"][0]["record_number"], "10")

    def test_discover_and_resolve_commands_emit_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Library.xml").write_text("<xml><records /></xml>", encoding="utf-8")
            pdf = root / "Library.Data" / "PDF" / "0000000000" / "example-paper.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"not opened")
            discovered = subprocess.run(
                [sys.executable, str(SCRIPT), "discover", "--root", str(root)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(discovered.returncode, 0, discovered.stderr)
            self.assertEqual(json.loads(discovered.stdout)["pdf_count"], 1)
            resolved = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "resolve",
                    "--root",
                    str(root),
                    "--attachment",
                    "internal-pdf://0000000000/example-paper.pdf",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(resolved.returncode, 0, resolved.stderr)
            self.assertEqual(json.loads(resolved.stdout)["status"], "matched")


class DiscoveryAndResolutionTests(unittest.TestCase):
    def test_root_boundary_rejects_resolved_paths_outside_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            root.mkdir()
            inside = root / "inside.xml"
            outside = base / "outside.xml"
            inside.write_text("<xml />", encoding="utf-8")
            outside.write_text("<xml />", encoding="utf-8")
            self.assertTrue(module.is_within_root(root, inside))
            self.assertFalse(module.is_within_root(root, outside))

    def test_discovers_libraries_without_opening_pdf_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Library.xml").write_text("<xml><records /></xml>", encoding="utf-8")
            (root / "Other.xml").write_text("<xml><records /></xml>", encoding="utf-8")
            pdf_dir = root / "Library.Data" / "PDF" / "0000000000"
            pdf_dir.mkdir(parents=True)
            (pdf_dir / "example-paper.pdf").write_bytes(b"invalid pdf one")
            (pdf_dir / "second.pdf").write_bytes(b"invalid pdf two")
            with mock.patch("builtins.open", side_effect=AssertionError("PDF bytes were opened")):
                result = module.discover_library(root)
            self.assertEqual(result["xml_count"], 2)
            self.assertEqual(result["pdf_count"], 2)
            self.assertEqual(len(result["libraries"]), 2)
            matched = next(item for item in result["libraries"] if item["xml"].endswith("Library.xml"))
            self.assertEqual(matched["pdf_count"], 2)

    def test_resolves_internal_pdf_by_storage_id_and_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "Library.Data" / "PDF" / "0000000000" / "example-paper.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"")
            result = module.resolve_attachment(root, "internal-pdf://0000000000/example-paper.pdf")
            self.assertEqual(result["status"], "matched")
            self.assertTrue(Path(result["path"]).samefile(pdf))

    def test_returns_ambiguous_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("One.Data", "Two.Data"):
                pdf = root / name / "PDF" / "0000000000" / "example-paper.pdf"
                pdf.parent.mkdir(parents=True)
                pdf.write_bytes(b"")
            result = module.resolve_attachment(root, "internal-pdf://0000000000/example-paper.pdf")
            self.assertEqual(result["status"], "ambiguous")
            self.assertEqual(result["message"], "PDF not reliably matched")
            self.assertEqual(len(result["candidates"]), 2)

    def test_rejects_filename_only_attachment(self):
        with tempfile.TemporaryDirectory() as directory:
            result = module.resolve_attachment(Path(directory), "paper.pdf")
            self.assertEqual(result["status"], "invalid_attachment")


if __name__ == "__main__":
    unittest.main()
