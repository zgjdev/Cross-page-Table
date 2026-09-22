# Novelty Gate: Cross-Page Table Recovery

**Review date:** 2026-07-24  
**Scope:** English born-digital academic PDFs; PubTables-v2 as the primary benchmark  
**Evidence:** 48 screened records, 31 full-read records, 56 logged searches, and two
backward/forward citation-snowball rounds

## Gate Summary

The broad direction remains researchable, but the original framing must be narrowed. Continuation
classification is effectively saturated on PubTables-v2, and POTATR now provides a much stronger
page-level image-to-graph component plus a `POTATR + continuation + vertical merge` document
baseline. A paper is defensible only if it targets typed structural alignment and final
document-level recovery under the same page-extraction input.

## 1. Joint Prediction Coverage

**Question:** Does prior work jointly predict layout relations, cross-page table membership, and
column/row correspondence?

**Finding:** No reviewed public work demonstrates all three together.

- POTATR jointly predicts page-level tables, rows, columns, cells, captions, footers, and
  hierarchical relations, but its cross-page step is an external ViT continuation classifier plus
  vertical concatenation.
- PubTables-v2 supervises cross-page table identity and evaluates reconstructed document tables,
  but its baseline does not predict column correspondence, repeated-header identity, or split-row
  relations.
- Qin et al. predict semantic continuation after table segmentation but do not integrate layout
  hierarchy or output a reconstructed structure.
- VCCT integrates cross-page context and header/border cues in a private power-grid OCR pipeline,
  but does not expose a public typed relation graph or standard document-table evaluation.
- HRDoc/DocHieNet/DocParser model document hierarchy, while GraphTSR/TGRNet model table-cell
  relations, but neither family joins those relation spaces across page boundaries.

The viable novelty is therefore a typed document table graph with explicit column, repeated-header,
and split-row edges, not the generic use of a graph network.

## 2. Direct Work After PubTables-v2

**Question:** Have new direct competitors or code appeared after PubTables-v2?

**Finding:** Yes, two 2026 papers materially update the landscape.

1. **POTATR, arXiv:2606.09788 (2026-06-08).** The 29M image-to-graph model reports Single Pages
   `GriTS_Con = 0.964`. On Full Documents it improves from 0.671 to 0.827 when composed with the
   PubTables-v2 ViT continuation classifier and vertical merging. The paper says code and models
   will be released; no released artifact was verified as of the review date.
2. **VCCT, DOI 10.2139/ssrn.6811737 (2026).** This domain-specific preprint uses cross-page context,
   header detection, and border analysis and reports table structural integrity improving from
   77.2% to 82.0%. No public data/code or standard academic-document evaluation was found.

OpenAlex reported zero indexed forward citations for PubTables-v2 and POTATR on the review date, so
the absence of further competitors is weak negative evidence rather than proof of novelty. The two
snowball rounds added newer hierarchy, long-table, and zero-shot table papers but no new
cross-page-alignment dataset or method category.

## 3. Continuation Saturation and Residual Errors

**Question:** Is continuation classification saturated, and where do the remaining errors arise?

**Finding:** It is too saturated to support the primary claim.

- PubTables-v2 reports ViT-B/16 continuation `F1` around 0.991.
- POTATR reports continuation recall of 0.995 in its full-document composition experiment.
- POTATR explicitly attributes the remaining document gap to page-level extraction on
  out-of-distribution multi-page table content and within-page table-part merging.
- The published merge is simple vertical concatenation. It does not separately score column drift,
  repeated headers, split logical rows/cells, or wrong correspondence between multiple table
  fragments.
- Page-parser false positives/negatives, structure errors near page boundaries, and text assignment
  errors propagate into final GriTS/TEDS even when continuation is correct.

The research must measure and improve structural alignment and final recovery. Continuation F1
remains a diagnostic only.

## 4. Template-Disjoint Evaluation

**Question:** Is there an existing public template-disjoint protocol for this task?

**Finding:** No public template-disjoint split for PubTables-v2 was found.

DocILE provides a useful precedent by reporting seen, few-shot, and zero-shot layouts. DocLayNet,
Document Domain Randomization, Aligning Benchmark Datasets, Shortcut Learning, and Data Leakage in
Visual Datasets establish the need for domain/template controls, but none defines a compatible
PubTables-v2 protocol.

A new protocol is potentially contributory if it is deterministic and auditable. It should group
whole documents by journal/ISSN where available, otherwise by a frozen template clustering process
using page size, column layout, fonts, and stable header/footer features. Similarity thresholds and
clusters must be established without inspecting test outcomes. The official split remains mandatory
for comparability.

## 5. Verifiable Increment Beyond Closest Work

**Question:** What new capability is added rather than merely changing the model?

The revised project must demonstrate all of the following:

1. A versioned alignment-label protocol or audited subset for column correspondence, repeated
   headers, and split rows derived from PubTables-v2, including confidence and human agreement.
2. A typed document graph that consumes the same page objects as the strongest reproducible
   vertical-merge baseline and predicts those relations jointly.
3. A constrained decoder that returns one logical table with page/cell provenance and reports
   invalid-graph or unresolved-alignment cases.
4. Gains in document `GriTS_Con`, `GriTS_Top`, and TEDS, plus relation-specific and exact-chain
   diagnostics, rather than continuation accuracy alone.
5. Official-split and template-disjoint results with modality/cue ablations and confidence
   intervals.

The decisive experiment holds the page parser fixed and compares vertical concatenation with
alignment-aware decoding. This isolates the proposed capability from page-extractor improvements.

## 6. Three-to-Six-Month Scope

### Minimum Viable Contributions

- Audit PubTables-v2 and reproduce the official/closest vertical-merging baseline using a fixed
  TATR/POTATR-style page parser.
- Derive high-confidence alignment labels and manually audit 200-300 diverse multi-page tables.
- Release the label schema, derivation code, confidence rules, and document/template-disjoint
  manifests when licensing permits.
- Train a relation model for continuation, monotonic column matching, repeated headers, and split
  rows over frozen page objects.
- Implement constrained reconstruction and document-level evaluation with an error taxonomy.
- Report oracle-versus-predicted page objects and official-versus-template-disjoint results.

### Enhancement Contributions

- Jointly fine-tune selected page-encoder layers with cross-page losses.
- Use 3-4 page message passing for longer chains.
- Add a locally deployable multi-page VLM or commercial MLLM evaluation.
- Extend to another document domain, scanned inputs, or multilingual data.
- Distill relation/context signals into a smaller production model.

The MVP is ambitious but credible in 3-6 months with H100 access because it reuses a page parser and
concentrates training on relation/alignment heads. Label derivation and baseline reproducibility are
the first kill points; model work should not proceed at scale until both pass.

## Required Revision to the Research Claim

Replace a broad claim of "joint layout analysis and cross-page table recognition" with:

> Alignment-aware document table recovery from born-digital academic PDFs, using a typed relation
> graph over spatially grounded layout/table objects to predict logical-table membership, column
> correspondence, repeated headers, and split rows, evaluated on final reconstructed structures
> under official and template-disjoint protocols.

This claim is falsifiable, differs from the closest public vertical-merge baseline, and makes the
layout integration concrete through shared objects and typed relations.

## Decision

`revise`
