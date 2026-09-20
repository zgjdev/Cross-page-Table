# Bilingual Literature and Paper Document Design

**Date:** 2026-07-26  
**Languages:** English and Simplified Chinese  
**Scope:** Literature-research documents and paper manuscripts produced in this project

## 1. Objective

All literature-research deliverables and paper manuscripts must be maintained as two independent,
content-equivalent documents: one English version and one Simplified Chinese version. Neither
language is treated as an informal summary of the other. Both versions must be suitable for direct
review by a supervisor or collaborator.

## 2. File Naming

Use symmetric language suffixes:

- English: `{basename}.en.{extension}`
- Simplified Chinese: `{basename}.zh-CN.{extension}`

Current literature and report documents are migrated as follows:

| Current file | English file | Chinese file |
|---|---|---|
| `docs/literature/search-protocol.md` | `docs/literature/search-protocol.en.md` | `docs/literature/search-protocol.zh-CN.md` |
| `docs/literature/synthesis.md` | `docs/literature/synthesis.en.md` | `docs/literature/synthesis.zh-CN.md` |
| `docs/reports/novelty-gate.md` | `docs/reports/novelty-gate.en.md` | `docs/reports/novelty-gate.zh-CN.md` |
| `docs/reports/pubtables-v2-inventory.md` | `docs/reports/pubtables-v2-inventory.en.md` | `docs/reports/pubtables-v2-inventory.zh-CN.md` |

Future paper manuscripts use the same convention, for example:

- `paper.en.tex` and `paper.zh-CN.tex`; or
- `paper.en.md` and `paper.zh-CN.md`.

Language-neutral machine-readable files keep their current names.

## 3. Included and Excluded Artifacts

The bilingual requirement applies to:

- every narrative Markdown document under `docs/literature/` and `docs/reports/`;
- search protocols and narrative literature-review reports;
- literature syntheses, related-work analyses, and novelty reviews;
- dataset inventories, experiment reports, phase-gate reports, and other research reports;
- research-positioning documents intended to supply paper prose;
- abstracts, outlines, drafts, appendices, supplementary text, and final manuscripts.

The requirement does not duplicate:

- `papers.csv`, `search-log.csv`, BibTeX databases, or citation exports;
- YAML/JSON configuration and manifests;
- source code, tests, machine-generated metrics, or raw experimental results;
- implementation plans outside `docs/literature/` and `docs/reports/`.

Generated reports under `docs/reports/` are not exempt: a generator may produce the English file
first, but task completion requires a reviewed Chinese counterpart with equivalent facts.

## 4. Equivalence Requirements

Each language pair must preserve the same:

- section hierarchy and section order;
- tables, figures, captions, and numbered lists;
- citations, URLs, identifiers, and bibliography entries;
- dataset sizes, metric values, equations, thresholds, dates, and decisions;
- limitations, uncertainty statements, and evidence strength;
- final recommendation or novelty-gate outcome.

Translation may adjust sentence order and terminology for natural academic writing, but it must not
add, omit, soften, or strengthen a claim in only one language.

## 5. Terminology and Style

The English version uses publication-ready academic English. The Chinese version uses formal,
concise academic Chinese rather than literal word-for-word translation.

For the first occurrence of a specialized term in Chinese, use the established Chinese term with
the English term in parentheses when that helps disambiguation, for example `表格结构识别（table
structure recognition, TSR）`. Established model, dataset, metric, and venue names remain in their
official form.

Both versions must distinguish dataset licenses from paper licenses and must retain qualifiers such
as `reported`, `approximately`, `not publicly verified`, and `as of 2026-07-26`.

## 6. Synchronization Workflow

1. Create or modify both language files in the same task.
2. Update shared structured evidence first when facts change.
3. Apply the factual change to both narrative versions.
4. Compare headings, tables, citations, numeric literals, and decision keywords.
5. Commit both language files together.

A change that affects only one language version is incomplete unless it is strictly a grammar or
typography correction that does not change meaning.

## 7. Link and Reference Migration

References to a bilingual document must either:

- link to both language files with explicit `English` and `中文` labels; or
- link to the language appropriate for the surrounding document and provide the counterpart next
  to it.

The phase plan and research design must be updated so future tasks name both outputs. No compatibility
stub with the old unsuffixed filename will be retained, because that would create a third ambiguous
document and weaken the two-document rule.

## 8. Verification

The migration is accepted only when:

- all four existing literature/report documents have English and Chinese files;
- the old unsuffixed narrative files no longer exist;
- every pair has matching second-level heading counts and order;
- Markdown tables have matching row counts;
- DOI, arXiv ID, URL, numeric metric, and decision tokens are present in both versions;
- repository references point to suffixed filenames;
- the literature CSV validator, tests, Ruff, and `git diff --check` pass.

Future manuscript tasks must include the same parity checks in their completion criteria.

## 9. Initial Migration Boundary

The first implementation will migrate:

1. the literature search protocol;
2. the cross-page table literature synthesis;
3. the novelty-gate report;
4. the PubTables-v2 repository inventory;
5. references to those files in the phase plan and related research documents.

It will not translate implementation plans outside the target directories or source code. Every
future Markdown document created under `docs/literature/` or `docs/reports/`, including generated
dataset and experiment reports, must be delivered as an English/Chinese pair. Paper manuscript
pairs will be created when manuscript drafting begins.
