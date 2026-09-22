# Bilingual Literature and Reports Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert every current Markdown document under `docs/literature/` and `docs/reports/` into separate, content-equivalent English and Simplified Chinese documents.

**Architecture:** Existing English documents are renamed with `.en.md`; Chinese counterparts use `.zh-CN.md`. Structured CSV evidence remains single-source, while repository references and the bilingual policy are updated atomically. Parity is verified through heading, table, URL, identifier, numeric-literal, and decision checks.

**Tech Stack:** Markdown, PowerShell, Python 3.12, Git

## Global Constraints

- Use symmetric `{basename}.en.md` and `{basename}.zh-CN.md` filenames.
- Preserve claims, citations, URLs, identifiers, numbers, qualifications, and decisions in both languages.
- Write publication-ready English and formal academic Chinese; do not use literal machine-style translation.
- Keep `papers.csv`, `search-log.csv`, configs, manifests, code, and raw results language-neutral and single-copy.
- Remove old unsuffixed narrative files; do not leave compatibility stubs.
- Update both language files in the same commit whenever facts change.

---

### Task 1: Migrate Literature Documents

**Files:**
- Rename: `docs/literature/search-protocol.md` to `docs/literature/2026-07-24-search-protocol.en.md`
- Create: `docs/literature/2026-07-24-search-protocol.zh-CN.md`
- Rename: `docs/literature/synthesis.md` to `docs/literature/2026-08-02-literature-synthesis.en.md`
- Create: `docs/literature/2026-08-02-literature-synthesis.zh-CN.md`

**Interfaces:**
- Consumes: existing English literature prose and shared `papers.csv`/`search-log.csv` evidence
- Produces: two English/Chinese literature pairs with equivalent structure and evidence

- [x] **Step 1:** Rename the two existing English files with `.en.md` suffixes.
- [x] **Step 2:** Translate the search protocol into formal Chinese with identical sections and criteria.
- [x] **Step 3:** Translate the synthesis into formal Chinese, preserving all tables, metrics, citations, limitations, and the revised research claim.
- [x] **Step 4:** Compare heading levels, Markdown table rows, URLs, arXiv/DOI identifiers, and numeric literals across each pair.

### Task 2: Migrate Report Documents

**Files:**
- Rename: `docs/reports/novelty-gate.md` to `docs/reports/2026-07-24-novelty-gate.en.md`
- Create: `docs/reports/2026-07-24-novelty-gate.zh-CN.md`
- Rename: `docs/reports/pubtables-v2-inventory.md` to `docs/reports/2026-07-24-pubtables-v2-inventory.en.md`
- Create: `docs/reports/2026-07-24-pubtables-v2-inventory.zh-CN.md`

**Interfaces:**
- Consumes: existing reviewed report prose and pinned repository evidence
- Produces: two English/Chinese report pairs with unchanged `revise` decision and inventory facts

- [x] **Step 1:** Rename the two existing English files with `.en.md` suffixes.
- [x] **Step 2:** Translate the novelty gate, preserving all six questions, evidence qualifiers, scope boundary, and final `revise` token.
- [x] **Step 3:** Translate the inventory report, preserving the resolved SHA, archive paths, field names, byte counts, license distinction, and audit conclusions.
- [x] **Step 4:** Compare heading levels, table rows, URLs, identifiers, numeric literals, SHA, and decision token across each pair.

### Task 3: Update Policy and Repository References

**Files:**
- Modify: `docs/superpowers/specs/2026-07-26-bilingual-research-documents-design.md`
- Modify: `docs/superpowers/plans/2026-07-24-cross-page-table-phase-1.md`

**Interfaces:**
- Consumes: the four migrated language pairs
- Produces: future tasks and documentation references that always name both language outputs

- [x] **Step 1:** Expand the policy's initial migration table and boundary to include `pubtables-v2-inventory` and all future Markdown under the two target directories.
- [x] **Step 2:** Replace old literature/report filenames in the phase plan with paired `.en.md` and `.zh-CN.md` paths.
- [x] **Step 3:** State that future generated English reports must be followed by a reviewed Chinese counterpart before task completion.

### Task 4: Verify and Commit the Migration

**Files:**
- Verify: all Markdown files under `docs/literature/` and `docs/reports/`

**Interfaces:**
- Consumes: four bilingual pairs and updated references
- Produces: a clean, committed bilingual documentation state

- [x] **Step 1:** Confirm exactly eight Markdown files exist under the two directories and no unsuffixed narrative Markdown remains.
- [x] **Step 2:** Run pairwise parity checks for heading levels, Markdown table row counts, URLs, identifiers, numeric literals, SHA, and `revise` decision.
- [x] **Step 3:** Run `.venv\Scripts\python -m pytest -q`, `.venv\Scripts\python -m ruff check src tests scripts`, and `git diff --check`.
- [x] **Step 4:** Review `git diff --stat` and all repository references to old filenames.
- [x] **Step 5:** Commit with `git commit -m "docs: add bilingual literature and report documents"`.
