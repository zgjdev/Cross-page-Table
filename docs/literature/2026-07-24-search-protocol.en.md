# Literature Search Protocol

## Scope

English-language research on table extraction, multi-page tables, hierarchical document
parsing, document graphs, structured table generation, and template/domain generalization.
The primary publication window is 2015-07-24 through 2026-07-24; earlier seminal work may
be included through backward citation search.

## Sources

Search arXiv, DBLP, Semantic Scholar, IEEE Xplore, ACM Digital Library, SpringerLink, and
CVF Open Access. Record the canonical paper URL and an official code/data URL when present.

## Queries

- "multi-page table" AND (recognition OR extraction OR detection)
- "cross-page table" AND (continuation OR merging OR structure)
- "table extraction" AND (full document OR page context)
- "hierarchical document parsing" AND (graph OR relation)
- "table structure recognition" AND (long table OR document)
- "document layout analysis" AND (relationship OR reading order)
- "template generalization" AND document AI

## Inclusion Criteria

- Defines a relevant task, dataset, model, metric, or evaluation protocol.
- Contains enough methodological detail to reproduce or compare the result.
- Uses document images, PDF text/layout, or both.

## Exclusion Criteria

- Web/relational tables without document layout.
- Spreadsheet-only processing.
- OCR-only papers without layout or table structure contribution.
- Non-research product pages without technical evidence.

## Screening

Deduplicate by DOI/arXiv ID, screen title and abstract, then read the full text for included
papers. For each included paper, record task, context level, modality, data, method, metrics,
code availability, strongest evidence, and a limitation relevant to this project.

## Stopping Rule

Stop the first pass after at least 40 screened papers, at least 25 fully read papers, and two
consecutive backward/forward citation rounds add no new method or dataset category.
