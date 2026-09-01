# PDF matching and targeted reading

Apply this guidance only after XML metadata retrieval has produced candidates.

## Reliable identity matching

Use the following order and retain the evidence used for the match:

1. Resolve the exact XML File Attachment (`internal-pdf://storage-id/filename`) with the bundled script.
2. Check EndNote Record Number when it appears in a known export/storage relationship.
3. Compare DOI in XML with DOI in PDF metadata or the article itself.
4. Compare the complete title after normalizing punctuation and spacing.
5. Compare first author or author set plus publication year.
6. Inspect PDF metadata and the first page for journal, volume, pages, or article number.

An exact attachment path is strong location evidence but still verify the document identity before quoting it. A filename alone is never sufficient. If evidence conflicts, the attachment is absent, or multiple paths remain plausible, report `PDF not reliably matched` and do not treat the PDF as the paper.

## Question-directed reading

Choose sections according to the requested claim:

| Question type | Read first | Common supporting locations |
|---|---|---|
| Experimental method or parameter | Materials and Methods | Supplementary methods, protocol tables |
| Measured result or effect size | Results | Figures, tables, captions, supplementary results |
| Mechanism | Results + Discussion | Mechanism figures, correlations, pathway analyses |
| Authors' interpretation or limitations | Discussion + Conclusion | Limitations paragraph, outlook |
| General topic or scope | Abstract + Introduction | Study aims and site description |

Read adjacent context before extracting a sentence. Check axis units, legends, footnotes, statistical annotations, and whether a result belongs to the main article or supplementary information. For a precise experimental condition, require an explicit Methods or Supplementary-information statement; do not substitute a conventional value.

Record PDF page, printed page if different, section heading, figure/table identifier, and a short locating phrase. Keep verbatim excerpts short and only as needed for verification.
