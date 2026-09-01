# Evidence classification and answer format

## Evidence classes

- **A. 文献明确报告 / Directly reported:** the full text directly supports the statement. Give the paper and exact evidence location.
- **B. 多篇文献综合得到 / Cross-paper synthesis:** the statement summarizes compatible findings from multiple papers. Name the contributing papers and disclose differences or exceptions.
- **C. 合理推断 / Reasoned inference:** the interpretation follows from reported results but the authors did not directly state it. Label it as inference and never present C as A.

When a requested detail is absent, use `Not reported` or `未在当前全文中找到`. Never invent experimental conditions, statistics, sample size, analytical methods, or mechanisms from conventional practice.

## Answer sequence

1. Conclusion calibrated to the strength and scope of the evidence.
2. Supporting papers grouped by relevance or claim.
3. Key evidence with location and evidence class.
4. Necessary methods, results, caveats, and disagreements.
5. `References used from local EndNote Library` containing only papers actually used.

For each reference, prefer: Author(s), Year; Title; Journal; DOI. For each important claim, prefer: PDF page; Section; Figure/Table; short supporting-text locator.

## Candidate and comparison reporting

Classify XML hits as `Highly relevant`, `Relevant`, `Possibly relevant`, or `Not relevant`. Explain why a synonym or related concept was included rather than requiring literal keyword identity.

When comparing papers, build a temporary evidence table whose columns follow the question. A useful starting pattern is:

| Reference | Research object | Method/condition | Main result | Key evidence location | Evidence class | Relevance |
|---|---|---|---|---|---|---|

Change the fields when the question concerns chemical shifts, pH ranges, material performance, mechanisms, or engineering applicability. Do not force every domain into one template.

## Insufficient evidence

If the metadata search finds too little direct literature, state exactly: `当前 EndNote Library 中未检索到足够直接相关的文献。` Weak leads may be listed separately under `Potentially relevant references` with a reason, but must not be used to manufacture a definitive answer.
