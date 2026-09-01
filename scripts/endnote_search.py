#!/usr/bin/env python3
"""Deterministic EndNote XML indexing and local attachment utilities."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import unquote


FIELD_WEIGHTS = {"title": 6.0, "keywords": 5.0, "abstract": 2.0}
EXACT_PHRASE_BONUS = 8.0
CONCEPT_GROUP_BONUS = 4.0


def element_text(element: ET.Element | None) -> str:
    """Return normalized text from an EndNote element, including nested styles."""
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def normalize_doi(value: str) -> str:
    """Normalize common DOI labels and resolver URLs."""
    normalized = value.strip().casefold()
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi\s*:\s*", "", normalized)
    return normalized.strip().rstrip(".,;)")


def normalize_title(value: str) -> str:
    """Create a Unicode-safe comparison key for a title."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def _first_text(record: ET.Element, paths: list[str]) -> str:
    for path in paths:
        value = element_text(record.find(path))
        if value:
            return value
    return ""


def _all_text(record: ET.Element, path: str) -> list[str]:
    return [value for node in record.findall(path) if (value := element_text(node))]


def parse_endnote_xml(path: Path) -> list[dict[str, Any]]:
    """Parse the lightweight metadata fields needed for local retrieval."""
    source = Path(path).resolve()
    root = ET.parse(source).getroot()
    records: list[dict[str, Any]] = []
    for node in root.findall(".//record"):
        records.append(
            {
                "record_number": _first_text(node, ["./rec-number"]),
                "title": _first_text(node, ["./titles/title"]),
                "authors": _all_text(node, "./contributors/authors/author"),
                "year": _first_text(node, ["./dates/year"]),
                "journal": _first_text(
                    node,
                    ["./secondary-title", "./periodical/full-title", "./periodical/abbr-1"],
                ),
                "abstract": _first_text(node, ["./abstract"]),
                "keywords": _all_text(node, "./keywords/keyword"),
                "doi": normalize_doi(_first_text(node, ["./electronic-resource-num"])),
                "urls": _all_text(node, "./urls/related-urls/url"),
                "attachments": _all_text(node, "./urls/pdf-urls/url"),
                "source_xml": str(source),
            }
        )
    return records


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by normalized DOI, then normalized title, retaining source IDs."""
    unique: list[dict[str, Any]] = []
    positions: dict[tuple[str, str], int] = {}
    for source_record in records:
        record = deepcopy(source_record)
        doi_key = normalize_doi(str(record.get("doi", "")))
        title_key = normalize_title(str(record.get("title", "")))
        key = ("doi", doi_key) if doi_key else ("title", title_key)
        if not key[1]:
            key = ("record", str(record.get("record_number", len(unique))))
        if key not in positions:
            record["duplicate_record_numbers"] = [str(record.get("record_number", ""))]
            positions[key] = len(unique)
            unique.append(record)
            continue
        existing = unique[positions[key]]
        record_number = str(record.get("record_number", ""))
        if record_number and record_number not in existing["duplicate_record_numbers"]:
            existing["duplicate_record_numbers"].append(record_number)
        for field in ("title", "year", "journal", "abstract", "doi"):
            if not existing.get(field) and record.get(field):
                existing[field] = record[field]
        for field in ("authors", "keywords", "urls", "attachments"):
            for value in record.get(field, []):
                if value not in existing[field]:
                    existing[field].append(value)
    return unique


def tokenize(value: str) -> list[str]:
    """Tokenize Latin and Unicode word-like terms for deterministic matching."""
    return [token.casefold() for token in re.findall(r"[\w]+(?:[-'][\w]+)*", value, re.UNICODE)]


def _searchable_text(record: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(record.get("title", "")).casefold(),
        "keywords": " ".join(str(value) for value in record.get("keywords", [])).casefold(),
        "abstract": str(record.get("abstract", "")).casefold(),
    }


def score_record(
    record: dict[str, Any],
    query: str,
    terms: list[str],
    concept_groups: list[list[str]],
) -> tuple[float, dict[str, Any]]:
    """Score only title, keywords, and abstract and return an audit trail."""
    fields = _searchable_text(record)
    query_phrase = " ".join(query.casefold().split())
    requested_terms = []
    for term in [*tokenize(query), *terms]:
        normalized = " ".join(str(term).casefold().split())
        if normalized and normalized not in requested_terms:
            requested_terms.append(normalized)

    score = 0.0
    matched_fields: set[str] = set()
    matched_terms: set[str] = set()
    matched_phrases: list[str] = []
    for field, text_value in fields.items():
        field_matches = [term for term in requested_terms if term in text_value]
        if field_matches:
            score += FIELD_WEIGHTS[field] * len(field_matches)
            matched_fields.add(field)
            matched_terms.update(field_matches)
        if query_phrase and query_phrase in text_value:
            score += EXACT_PHRASE_BONUS
            matched_fields.add(field)
            if query_phrase not in matched_phrases:
                matched_phrases.append(query_phrase)

    searchable_blob = "\n".join(fields.values())
    matched_concept_groups = 0
    matched_group_terms: list[str] = []
    for group in concept_groups:
        alternatives = [" ".join(str(value).casefold().split()) for value in group]
        matched = next((value for value in alternatives if value and value in searchable_blob), "")
        if matched:
            matched_concept_groups += 1
            matched_group_terms.append(matched)
            score += CONCEPT_GROUP_BONUS

    explanation = {
        "matched_fields": sorted(matched_fields),
        "matched_terms": sorted(matched_terms),
        "matched_phrases": matched_phrases,
        "matched_concept_groups": matched_concept_groups,
        "matched_group_terms": matched_group_terms,
    }
    return score, explanation


def search_records(
    records: list[dict[str, Any]],
    query: str,
    terms: list[str],
    concept_groups: list[list[str]],
    limit: int,
) -> list[dict[str, Any]]:
    """Return stable, explainable search results ordered by decreasing relevance."""
    results: list[dict[str, Any]] = []
    for record in records:
        score, explanation = score_record(record, query, terms, concept_groups)
        if score <= 0:
            continue
        result = deepcopy(record)
        result.update(explanation)
        result["score"] = score
        results.append(result)
    results.sort(
        key=lambda item: (
            -float(item["score"]),
            normalize_title(str(item.get("title", ""))),
            str(item.get("record_number", "")),
        )
    )
    return results[: max(0, limit)]


def is_within_root(root: Path, candidate: Path) -> bool:
    """Return true only when the fully resolved candidate stays inside root."""
    workspace = Path(root).resolve()
    try:
        Path(candidate).resolve().relative_to(workspace)
    except ValueError:
        return False
    return True


def _resolved_files(root: Path, pattern: str) -> list[Path]:
    workspace = Path(root).resolve()
    found: set[Path] = set()
    for path in workspace.rglob(pattern):
        resolved = path.resolve()
        if is_within_root(workspace, resolved) and resolved.is_file():
            found.add(resolved)
    return sorted(found)


def discover_library(root: Path) -> dict[str, Any]:
    """Discover EndNote XML/.Data pairs by paths only; never open PDF contents."""
    workspace = Path(root).resolve()
    xml_files = _resolved_files(workspace, "*.xml")
    all_pdfs = _resolved_files(workspace, "*.pdf")
    libraries: list[dict[str, Any]] = []
    for xml_path in xml_files:
        data_dir = xml_path.with_suffix(".Data")
        pdf_dir = data_dir / "PDF"
        valid_data_dir = data_dir.is_dir() and is_within_root(workspace, data_dir)
        valid_pdf_dir = valid_data_dir and pdf_dir.is_dir() and is_within_root(workspace, pdf_dir)
        library_pdfs = _resolved_files(pdf_dir, "*.pdf") if valid_pdf_dir else []
        libraries.append(
            {
                "xml": str(xml_path),
                "data_dir": str(data_dir.resolve()) if valid_data_dir else None,
                "pdf_dir": str(pdf_dir.resolve()) if valid_pdf_dir else None,
                "pdf_count": len(library_pdfs),
            }
        )
    return {
        "root": str(workspace),
        "xml_count": len(xml_files),
        "pdf_count": len(all_pdfs),
        "libraries": libraries,
    }


def parse_internal_attachment(value: str) -> tuple[str, str] | None:
    """Parse EndNote's internal-pdf storage-id and exact attached basename."""
    match = re.fullmatch(r"internal-pdf://([^/]+)/(.+)", value.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    storage_id = unquote(match.group(1)).strip()
    filename = unquote(match.group(2)).strip()
    if not storage_id or not filename or "/" in filename or "\\" in filename:
        return None
    return storage_id, filename


def resolve_attachment(root: Path, attachment: str) -> dict[str, Any]:
    """Resolve an explicit EndNote attachment without guessing from filename alone."""
    parsed = parse_internal_attachment(attachment)
    if parsed is None:
        return {
            "status": "invalid_attachment",
            "attachment": attachment,
            "message": "Expected internal-pdf://storage-id/filename.pdf",
        }
    storage_id, filename = parsed
    workspace = Path(root).resolve()
    candidates: list[Path] = []
    for path in workspace.rglob("*.pdf"):
        resolved = path.resolve()
        if not is_within_root(workspace, resolved) or not resolved.is_file():
            continue
        if resolved.name.casefold() != filename.casefold() or resolved.parent.name.casefold() != storage_id.casefold():
            continue
        if not any(parent.name.casefold() == "pdf" for parent in resolved.parents):
            continue
        candidates.append(resolved)
    candidates = sorted(set(candidates))
    if len(candidates) == 1:
        return {
            "status": "matched",
            "attachment": attachment,
            "path": str(candidates[0]),
            "matched_by": "storage_id_and_filename",
        }
    if not candidates:
        return {
            "status": "not_found",
            "attachment": attachment,
            "message": "No exact EndNote attachment path found",
        }
    return {
        "status": "ambiguous",
        "attachment": attachment,
        "message": "PDF not reliably matched",
        "candidates": [str(path) for path in candidates],
    }


def build_index(xml_path: Path) -> dict[str, Any]:
    source = Path(xml_path).resolve()
    records = deduplicate_records(parse_endnote_xml(source))
    return {
        "schema_version": 1,
        "source_xml": str(source),
        "record_count": len(records),
        "records": records,
    }


def _write_json(path: Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_concept_groups(values: list[str]) -> list[list[str]]:
    return [[part.strip() for part in value.split("|") if part.strip()] for value in values]


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Build a lightweight metadata index")
    index_parser.add_argument("--xml", type=Path, required=True)
    index_parser.add_argument("--out", type=Path, required=True)

    search_parser = subparsers.add_parser("search", help="Search title, abstract, and keywords")
    search_parser.add_argument("--index", type=Path, required=True)
    search_parser.add_argument("--query", default="")
    search_parser.add_argument("--term", action="append", default=[])
    search_parser.add_argument("--concept-group", action="append", default=[])
    search_parser.add_argument("--limit", type=int, default=20)

    discover_parser = subparsers.add_parser("discover", help="Find EndNote XML and paired PDF directories")
    discover_parser.add_argument("--root", type=Path, required=True)

    resolve_parser = subparsers.add_parser("resolve", help="Resolve an explicit internal-pdf attachment")
    resolve_parser.add_argument("--root", type=Path, required=True)
    resolve_parser.add_argument("--attachment", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    if args.command == "index":
        payload = build_index(args.xml)
        _write_json(args.out, payload)
        print(json.dumps({"record_count": payload["record_count"], "output": str(args.out.resolve())}, ensure_ascii=False))
        return 0
    if args.command == "search":
        index = json.loads(args.index.read_text(encoding="utf-8"))
        groups = _parse_concept_groups(args.concept_group)
        results = search_records(index.get("records", []), args.query, args.term, groups, args.limit)
        print(
            json.dumps(
                {
                    "query": args.query,
                    "terms": args.term,
                    "concept_groups": groups,
                    "result_count": len(results),
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "discover":
        print(json.dumps(discover_library(args.root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "resolve":
        result = resolve_attachment(args.root, args.attachment)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["status"] == "matched":
            return 0
        if result["status"] == "ambiguous":
            return 3
        return 2
    return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
