# Cross-Page Table Core Findings Report Design

**Date:** 2026-08-01  
**Primary audience:** Research supervisor  
**Languages:** English and Simplified Chinese

## 1. Objective

Produce a self-contained research-decision report that answers two questions: what the literature
review has established about cross-page table recovery, and which publications support each
conclusion. The report must help a supervisor judge whether the topic remains publishable and what
the next research step should be.

## 2. Outputs

- `docs/reports/2026-08-02-cross-page-table-core-findings.en.md`
- `docs/reports/2026-08-02-cross-page-table-core-findings.zh-CN.md`

The two documents are independent, content-equivalent reports. The English version uses academic
English; the Chinese version uses formal academic Chinese suitable for a supervisor briefing.

## 3. Evidence Sources

The report may use only evidence already recorded in:

- `docs/literature/papers.csv`;
- `docs/literature/search-log.csv`;
- the bilingual literature synthesis;
- the bilingual novelty-gate report;
- the bilingual PubTables-v2 repository inventory.

Bibliographic details, identifiers, URLs, dataset statistics, and reported metrics must be copied
from these reviewed sources. No author name, venue, DOI, metric, or release claim may be inferred
from model memory.

## 4. Report Structure

1. Executive summary and recommendation.
2. Scope, evidence base, and review boundary.
3. Task definition separating continuation detection, structural alignment, and document-level
   recovery.
4. Seven core findings. Each finding contains the claim, supporting evidence, key references, and
   implication for this project.
5. Comparison of the closest work: Qin et al., PubTables-v2, VCCT, and POTATR.
6. Defensible research gap and revised research question.
7. Recommended technical route and minimum publishable contribution.
8. Three-to-six-month execution priorities and kill criteria.
9. Evidence boundaries and unresolved questions.
10. Complete references with title, year, venue, stable URL or DOI, and code/data URL where
    relevant and available.

## 5. Core Argument

The report will defend a narrow conclusion: continuation classification alone is not a viable main
contribution because the strongest public results are near saturation. The remaining defensible
gap is alignment-aware document table recovery over shared layout/table objects, with explicit
column correspondence, repeated-header, split-row, and table-membership relations. The final
evaluation must measure reconstructed document tables and include leakage-resistant document- and
template-disjoint protocols.

This is a literature-supported research direction, not an experimental result. The report must not
claim that the proposed model improves any metric before experiments are run.

## 6. Citation Strategy

Use numbered Markdown citations such as `[1]` and a complete numbered reference list. Every core
finding must cite its primary supporting work in the same subsection. Dataset and baseline claims
should prefer their primary papers; generalization and leakage claims should cite the relevant
benchmark or methodological paper.

The main narrative should prioritize the references needed to support the decision, while the
reference list should include all works explicitly discussed. It need not reproduce all 31 full-read
records when they do not materially support a stated conclusion.

## 7. Evidence Labels

The report distinguishes:

- **Established by reviewed literature:** directly reported task definitions, datasets, methods,
  metrics, and limitations.
- **Synthesis:** conclusions obtained by comparing multiple reviewed sources.
- **Pending validation:** proposed labels, model design, split construction, reproducibility, and
  expected gains that still require data or experiments.

Qualifiers such as `reported`, `approximately`, `not publicly verified`, and the review date must
be preserved.

## 8. Acceptance Criteria

- Both language files have identical heading hierarchy, table row counts, citation numbers,
  reference count, URLs, identifiers, and numeric literals.
- Every core finding maps to at least one primary reference and a concrete project implication.
- The decision is consistent with the existing novelty gate: `revise`, not unconditional
  `proceed`.
- The report clearly separates literature findings from planned experiments.
- No placeholder, uncited key metric, fabricated bibliography field, or unsupported novelty claim
  remains.
- Repository tests, Ruff, and `git diff --check` pass.
