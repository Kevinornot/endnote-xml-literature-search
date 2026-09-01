---
name: endnote-xml-literature-search
description: Use when answering research questions from a local EndNote XML export and its associated .Data/PDF library, especially when candidate retrieval, conservative PDF matching, targeted full-text reading, or evidence-location reporting is required.
---

# EndNote XML Literature Search

Use a strict sequence: understand the question, search XML metadata, rank candidates, match only candidate PDFs, read only relevant full text, and answer from located evidence. Never begin by reading every PDF.

## Workflow

1. Expand the question into its core topic, synonyms, abbreviations, English technical terms, study objects, and method terms. Preserve separate concept groups when a paper should cover several ideas at once.
2. Locate the EndNote export and matching `.Data/PDF` tree without opening PDF bytes:
   `python scripts/endnote_search.py discover --root <library-root>`
3. Build a lightweight index from the selected XML:
   `python scripts/endnote_search.py index --xml <library.xml> --out <temporary-index.json>`
   The initial retrieval corpus is strictly **Title + Abstract + Keywords**. Do not score authors, journal, DOI, URLs, attachment names, or PDF text at this stage.
4. Search with semantic expansions and concept alternatives:
   `python scripts/endnote_search.py search --index <temporary-index.json> --query <question> --term <term> --concept-group <alternative1|alternative2> --limit 20`
   Inspect match explanations and classify candidates as **Highly relevant**, Relevant, Possibly relevant, or Not relevant. Prefer the first two groups. If many remain, initially select only the top 10–20.
5. Only for selected candidates, resolve every explicit XML attachment:
   `python scripts/endnote_search.py resolve --root <library-root> --attachment <internal-pdf-url>`
   Treat `matched` as a candidate path, then verify paper identity. Treat `ambiguous` as **PDF not reliably matched**. Never confirm identity from a filename alone.
6. After candidates exist, read [PDF matching and targeted-reading guidance](references/pdf-matching-and-reading.md). Read the sections, figures, tables, or supplements needed to answer the question; do not make an aimless full-paper summary.
7. Before composing the answer or a comparison table, read [evidence and output guidance](references/evidence-and-output.md). Separate direct reports, multi-paper synthesis, and inference. If a detail is absent, write **Not reported** or `未在当前全文中找到`.

## Retrieval Boundaries

- Prefer XML File Attachments, then Record Number, DOI, complete title, author + year, and finally PDF metadata or first-page evidence.
- If the local XML has too little direct evidence, state `当前 EndNote Library 中未检索到足够直接相关的文献。` Put weak leads under `Potentially relevant references`; do not force them into the answer.
- Keep temporary indexes outside the installed skill and never package the user's XML, `.Data` directory, PDFs, caches, or extracted paper text.
- End every substantive answer with **References used from local EndNote Library** and list only papers actually inspected or used.

## Output Order

Lead with the conclusion, then supporting papers, key evidence locations, and only the methods/results details required by the question. Include Author, Year, Title, DOI, PDF page, Section, Figure/Table, and a short supporting-text locator whenever available.
