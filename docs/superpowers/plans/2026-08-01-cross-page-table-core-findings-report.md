# Cross-Page Table Core Findings Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce content-equivalent English and Simplified Chinese supervisor-facing reports that state the literature review's core conclusions and map every conclusion to verified references.

**Architecture:** Build the English report first from the reviewed structured evidence, using a fixed seven-finding argument and numbered citations. Translate it into formal academic Chinese without changing structure or evidence, then run pairwise checks over headings, tables, citation numbers, reference entries, URLs, identifiers, and numeric literals.

**Tech Stack:** Markdown, PowerShell, Python 3.12, Git

## Global Constraints

- Create `docs/reports/2026-08-02-cross-page-table-core-findings.en.md` and `docs/reports/2026-08-02-cross-page-table-core-findings.zh-CN.md` together.
- Use only facts recorded in `papers.csv`, `search-log.csv`, the bilingual synthesis, novelty gate, and PubTables-v2 inventory.
- Do not infer author names, venue details, DOI values, metrics, code releases, or experimental outcomes from model memory.
- Preserve the `revise` decision and distinguish reviewed facts, synthesis, and pending validation.
- Use the same heading hierarchy, tables, citation numbers, reference count, URLs, identifiers, and numeric literals in both files.
- Use publication-ready English and formal academic Chinese rather than literal sentence-by-sentence translation.

---

### Task 1: Draft the English Evidence-to-Decision Report

**Files:**
- Create: `docs/reports/2026-08-02-cross-page-table-core-findings.en.md`
- Read: `docs/literature/papers.csv`
- Read: `docs/literature/search-log.csv`
- Read: `docs/literature/2026-08-02-literature-synthesis.en.md`
- Read: `docs/reports/2026-07-24-novelty-gate.en.md`
- Read: `docs/reports/2026-07-24-pubtables-v2-inventory.en.md`

**Interfaces:**
- Consumes: 48 screened records, 31 full-read records, 56 logged searches, reviewed claims, and pinned dataset evidence
- Produces: one self-contained English report with seven core findings and a numbered reference catalog

- [x] **Step 1: Create the report frame**

Use this exact second-level heading order:

```markdown
# Core Findings of the Cross-Page Table Literature Review

## Executive Summary
## Scope and Evidence Base
## Task Definition
## Core Findings
## Closest-Work Comparison
## Defensible Research Gap
## Recommended Research Direction
## Three-to-Six-Month Priorities and Kill Criteria
## Evidence Boundaries and Open Questions
## References
```

- [x] **Step 2: State the seven core findings**

Create seven third-level subsections under `Core Findings`, each containing `Conclusion`,
`Evidence`, `Key references`, and `Implication for this project` paragraphs:

1. Cross-page table recovery is a document-level reconstruction task, not continuation
   classification alone.
2. Continuation classification is near saturation on PubTables-v2 and cannot support the main
   novelty claim.
3. The unresolved technical problem is explicit structural alignment across page fragments.
4. Layout analysis and page-level TSR should share objects with the cross-page relation model, but
   replacing the page extractor is unnecessary for the first paper.
5. PubTables-v2 is the primary public benchmark, but it lacks direct fine-grained alignment labels.
6. Document-level reconstruction metrics and leakage-resistant splits are necessary for credible
   evaluation.
7. VLMs are important competitive baselines, but auditable spatial structure remains a defensible
   advantage of a typed relation approach.

- [x] **Step 3: Add the closest-work comparison**

Use one Markdown table with these rows and columns:

```markdown
| Work | Main capability | Reported evidence | Missing capability | Role in this project |
|---|---|---|---|---|
| Qin et al. (2024) | BERT semantic matching for financial-table continuation | Classification precision/recall/F1 | Layout hierarchy, explicit alignment, and document reconstruction | Semantic continuation baseline |
| PubTables-v2 (2025) | ViT-B/16 continuation plus vertical merging | Approximately `F1 = 0.991`; merging improves document GriTS | Explicit column, repeated-header, and split-row alignment | Primary dataset and official compatibility anchor |
| VCCT (2026) | Cross-page context with header/border cues in a domain OCR pipeline | Structural integrity rises from `77.2%` to `82.0%` | Public data/code and standard document-table evaluation | Domain-specific contextual comparator |
| POTATR (2026) | Lightweight page image-to-graph extraction plus external merging | Single Pages `GriTS_Con = 0.964`; Full Documents `0.671` to `0.827`; continuation recall `0.995` | Joint cross-page optimization and alignment-aware decoding | Strong fixed page-extractor baseline |
```

Preserve these reviewed values where relevant: `F1 = 0.991`, continuation recall `0.995`,
`GriTS_Con = 0.964`, Full Documents `0.671` to `0.827`, and structural integrity `77.2%` to
`82.0%`.

- [x] **Step 4: State the revised research decision**

The report must retain the decision token `revise` and define the target as alignment-aware
document table recovery over spatially grounded layout/table objects, predicting logical-table
membership, column correspondence, repeated headers, and split rows. It must state that metric
improvements remain pending experimental validation.

- [x] **Step 5: Add the numbered reference catalog**

Use these 24 reviewed records in this fixed order, with title, year, venue, paper URL or DOI, and
code/data URL when recorded as available:

```text
1  smock2025pubtablesv2
2  smock2026potatr
3  qin2024bertcrosspage
4  han2026vcct
5  smock2022pubtables1m
6  zhong2020pubtabnet
7  nassar2022tableformer
8  smock2023grits
9  zheng2021gte
10 rausch2021docparser
11 ma2023hrdoc
12 ma2024detectorderconstruct
13 wang2024dochienet
14 chi2019graphtsr
15 xue2021tgrnet
16 shit2022relationformer
17 luo2024docgraphlm
18 ma2024mmlongbenchdoc
19 hu2025mplugdocowl2
20 li2025dotsocr
21 pfitzmann2022doclaynet
22 smock2023aligning
23 geirhos2020shortcut
24 bontempi2025dataleakage
```

Do not add authors because `papers.csv` does not contain an author field. State this bibliographic
boundary once before the list.

- [x] **Step 6: Check English evidence coverage**

Run a PowerShell check that confirms seven `### Finding` headings, references `[1]` through `[24]`,
the `revise` token, and the five required metric expressions. Expected: no missing item and exit 0.

---

### Task 2: Produce the Chinese Counterpart

**Files:**
- Read: `docs/reports/2026-08-02-cross-page-table-core-findings.en.md`
- Create: `docs/reports/2026-08-02-cross-page-table-core-findings.zh-CN.md`

**Interfaces:**
- Consumes: the reviewed English report from Task 1
- Produces: a structurally and factually equivalent Chinese supervisor report

- [x] **Step 1: Translate the complete report**

Use formal Chinese terms consistently: `续接检测`, `结构对齐`, `文档级表格恢复`, `类型化关系图`,
`重复表头`, `拆分行`, `文档不相交`, and `模板不相交`. Preserve official model, dataset, metric,
and venue names.

- [x] **Step 2: Preserve the evidence labels**

Translate the three labels as `文献已证实`, `综合判断`, and `待实验验证`. Do not turn a synthesis
or proposal into an established fact.

- [x] **Step 3: Preserve the citation map**

Each English citation marker `[n]` must occur in the equivalent Chinese section. Keep the same 24
reference entries in the same order with identical titles, venues, URLs, DOI strings, and code/data
links.

- [x] **Step 4: Review academic readability**

Check that the executive summary can be read independently by a supervisor, each finding directly
answers why the topic should or should not continue, and Chinese sentences do not follow English
syntax mechanically.

---

### Task 3: Verify and Commit the Bilingual Report

**Files:**
- Verify: `docs/reports/2026-08-02-cross-page-table-core-findings.en.md`
- Verify: `docs/reports/2026-08-02-cross-page-table-core-findings.zh-CN.md`

**Interfaces:**
- Consumes: the two complete reports
- Produces: a verified bilingual report pair committed on the current research branch

- [x] **Step 1: Run pairwise parity checks**

Compare heading levels, Markdown table row counts, citation-number multisets, reference count,
Markdown link targets, DOI/arXiv identifiers, and numeric-literal multisets. Expected: all checks
report equality and both files contain exactly 24 references.

- [x] **Step 2: Run content gates**

Confirm both files contain the `revise` decision, all seven findings, all four closest-work data
rows, and explicit statements that novelty and metric gains remain unverified.

- [x] **Step 3: Run repository quality gates**

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check src tests scripts
git diff --check
```

Expected: all tests pass, Ruff exits 0, and `git diff --check` reports no errors.

- [x] **Step 4: Review the staged diff**

Run `git diff --stat`, inspect both complete reports, and verify that no unrelated file changed.

- [x] **Step 5: Commit**

```powershell
git add docs/reports/2026-08-02-cross-page-table-core-findings.en.md docs/reports/2026-08-02-cross-page-table-core-findings.zh-CN.md docs/superpowers/plans/2026-08-01-cross-page-table-core-findings-report.md
git commit -m "docs: summarize cross-page table research findings"
```
