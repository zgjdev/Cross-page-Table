# Core Findings of the Cross-Page Table Literature Review

## Executive Summary

The literature supports a `revise` decision, not a claim that continuation classification alone is
novel. Continuation classification is near saturation on the reported PubTables-v2 official setup,
but this review does not establish saturation under future template-disjoint evaluation. The
defensible target is **alignment-aware document table recovery** for born-digital
academic PDFs: a typed relation model over spatially grounded layout and table objects that
predicts logical-table membership, column correspondence, repeated headers, and split rows.
Reported metric improvements for this target remain pending experimental validation. The closest
public baseline is a fixed page extractor composed with continuation classification and vertical
merging; the proposed work must isolate the value of alignment-aware decoding against that
baseline. [1][2]

## Scope and Evidence Base

Review date: 2026-08-02. Unless otherwise noted, all negative-search, citation-count,
artifact-availability, and novelty-absence statements are bounded by this cutoff.

This review covers English born-digital academic PDFs, with PubTables-v2 as the primary public
benchmark. The evidence base comprises 49 screened records, 32 full-read records, 60 logged
searches, two citation-snowball rounds, reviewed claims, and a repository inventory pinned to
PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`. The review uses 25 records as
its numbered reference catalog. [1]-[25]

PubTables-v2 Full Documents supplies logical tables, page-part provenance, adjacent-page pair
labels, page images, PDF words, and page annotations. It does not supply row/column boxes within
multipart table fragments, so direct fine-grained alignment supervision is unavailable in the
public data. [1]

## Task Definition

The target task is document-level table recovery. Given page-level layout and table objects, the
system should form continuation candidates, predict typed cross-page relations, and decode one
logical table with provenance for its page fragments and cells. The final output is therefore not
only a continuation decision or a vertically concatenated sequence; it is a reconstructed,
auditable document-table object. [1][2][5][8]

The intended relation set contains logical-table membership, monotonic column correspondence,
repeated-header identity, and split-row relations. These relations connect page fragments while
retaining their spatial grounding in layout/table objects. [1][2][10]-[17]

## Core Findings

### Finding 1: Cross-page table recovery is a document-level reconstruction task, not continuation classification alone

**Synthesis.** Cross-page recovery should be defined as reconstruction of a logical table across
page fragments, rather than as binary continuation classification alone. Page-level object or grid
recovery is necessary, but it does not by itself resolve document-table topology.

**Reviewed evidence.** PubTables-v2 evaluates reconstructed document tables after continuation and merging,
while its public Full Documents annotations retain logical-table and page-part information. Qin et
al. formulate continuation as semantic matching, but do not output reconstructed structure.
Page-level table methods recover objects or grids inside a page. [1][3][5]-[9]

**Key references.** PubTables-v2 provides the direct document-table setting; Qin et al. provide a
semantic continuation comparator; PubTables-1M, GriTS, GTE, GraphTSR, TGRNet, and TableFormer
clarify the distinction between page/table structure and document reconstruction. [1][3][5][7][8][9][14][15]

**Pending validation / implication for this project.** The headline output and evaluation must be a reconstructed
logical table with fragment and cell provenance. Continuation accuracy is a diagnostic relation,
not the project’s principal result.

### Finding 2: Continuation classification is near saturation on the reported PubTables-v2 official setup and cannot support the main novelty claim

**Synthesis.** Better continuation classification alone is not a defensible primary contribution
on the reported PubTables-v2 official setup; saturation under future template-disjoint evaluation
remains untested.

**Reviewed evidence.** PubTables-v2 reports approximately `F1 = 0.991` for its ViT-B/16 continuation
classifier. POTATR reports continuation recall `0.995` when it is composed with the continuation
classifier and vertical merging. POTATR nevertheless reports a remaining full-document gap,
including `GriTS_Con = 0.964` on Single Pages and Full Documents `0.671` to `0.827` after
cross-page merging. [1][2]

**Key references.** PubTables-v2 is the official continuation and document-reconstruction anchor;
POTATR is the strongest reviewed fixed-page-extractor composition; Qin et al. is a semantic
continuation baseline. [1]-[3]

**Pending validation / implication for this project.** Continuation precision, recall, and F1 should be reported to
diagnose errors, but the primary claim must be structural alignment and final document recovery.

### Finding 3: Among the reviewed public work, the unresolved technical problem is explicit structural alignment across page fragments

**Synthesis.** Among the reviewed public work, explicit cross-fragment column correspondence,
repeated-header identity, and split-row relations remain the unresolved technical problem; this is
not a claim of field-wide absence.

**Reviewed evidence.** PubTables-v2 and POTATR describe merge procedures that use continuation
followed by vertical concatenation. PubTables-v2 public multipart annotations omit internal
row/column boxes. GraphTSR and TGRNet model cell relations and logical coordinates within a table;
the reviewed document-hierarchy methods model document-level hierarchical relations.
[1][2][10][11][12][13][14][15][16][17]

**Key references.** PubTables-v2 and POTATR define the direct gap; GraphTSR and TGRNet motivate
relation-based table structure; DocParser, HRDoc, Detect-Order-Construct, DocHieNet, DocGraphLM,
and Relationformer are relevant relation-modeling comparators. [1][2][10][11][12][13][14][15][16][17]

**Pending validation / implication for this project.** Build a typed document table graph and a constrained decoder that
can return column matches, repeated headers, split rows, and unresolved-alignment or invalid-graph
cases. Create a versioned derived-label protocol or audited subset before treating these relations
as supervised targets.

### Finding 4: Layout analysis and page-level TSR should share objects with the cross-page relation model, but replacing the page extractor is unnecessary for the first paper

**Synthesis.** Layout analysis, page-level table structure recognition (TSR), and cross-page
relations should share spatial objects, but a new page extractor is not required for the first
paper. The reviewed page-level and hierarchy capabilities do not replace cross-page alignment.

**Reviewed evidence.** POTATR jointly predicts page-level tables, rows, columns, cells, captions, footers,
and hierarchical relations, yet its cross-page step remains external continuation classification
and vertical merging. PubTables-1M and GTE show the value of page context and table objects;
DocParser and HRDoc show relevant hierarchy machinery. [2][5][9][10][11]

**Key references.** POTATR is the fixed page-extractor baseline; PubTables-1M and GTE are
page-level object/structure references; DocParser, HRDoc, and DocHieNet are hierarchy references.
[2][5][9][10][11][13]

**Pending validation / implication for this project.** Freeze a reproducible TATR/POTATR-style page parser for the
decisive comparison. Feed its objects, geometry, text, and uncertainty to the relation model, then
compare vertical concatenation with alignment-aware decoding.

### Finding 5: PubTables-v2 is the primary public benchmark, but it lacks direct fine-grained alignment labels

**Synthesis.** PubTables-v2 is the primary public benchmark for the target task, but it cannot
directly supervise all required alignment relations. Among the reviewed datasets, no public
equivalent cross-page alignment benchmark was identified.

**Reviewed evidence.** Its Full Documents collection contains 9,172 documents and 9,492 multi-page tables,
with logical table annotations, page parts, and hard adjacent-page pair labels. The multipart
annotations do not provide internal row/column boxes, column correspondences, repeated-header
identity, or split-row labels. Other reviewed datasets provide page/table structure, hierarchy, or
long-document QA tasks. [1][5][6][7][11][13][14][15][18]

**Key references.** PubTables-v2 supplies the direct public benchmark; PubTables-1M, PubTabNet,
TableFormer, GraphTSR, TGRNet, HRDoc, DocHieNet, and MMLongBench-Doc establish adjacent but
incomplete supervision settings. [1][5][6][7][11][13][14][15][18]

**Pending validation / implication for this project.** Derive high-confidence labels and manually audit a controlled,
diverse subset. Release the label schema, derivation code, confidence rules, and manifests when
licensing permits; do not represent the derived labels as native PubTables-v2 annotations.

### Finding 6: Document-level reconstruction metrics and leakage-resistant splits are necessary for credible evaluation

**Synthesis.** Credible evaluation requires document-level reconstruction metrics and splits that
resist document/template leakage. The reviewed evidence cautions against relying only on IID
results or page-random splits.

**Reviewed evidence.** GriTS evaluates topology, location, and content but has no explicit table-chain or
cross-page alignment component. PubTables-v2 is the official compatibility anchor for document
GriTS/TEDS. Document and layout literature shows that hierarchy and template variation matter,
and the reviewed benchmark-alignment, shortcut-learning, and visual-leakage studies document
generalization and leakage risks. [1][8][11][12][14][21]-[24]

**Key references.** GriTS and PubTables-v2 anchor reconstruction evaluation; DocLayNet,
Aligning Benchmark Datasets, Shortcut Learning, and Data Leakage in Visual Datasets motivate
generalization and leakage controls. [1][8][21]-[24]

**Pending validation / implication for this project.** Report relation-specific metrics, chain/graph diagnostics,
document `GriTS_Con`, `GriTS_Top`, and TEDS, plus exact-chain and invalid-graph rates. Use the
official split for comparability and a deterministic template-disjoint protocol whose clustering
features and thresholds are frozen without inspecting test outcomes.

### Finding 7: VLMs are important competitive baselines, but auditable spatial structure remains a defensible advantage of a typed relation approach

**Synthesis.** VLMs and multi-page document models are important baselines, but their generative
outputs do not by themselves provide auditable spatial table structure. For document-table
recovery, the reviewed work leaves output validity, reproducibility, and spatial attribution as
open comparative concerns.

**Reviewed evidence.** MMLongBench-Doc and mPLUG-DocOwl2 demonstrate multi-page context modeling, but their
reviewed tasks produce answers rather than reconstructed table topology. dots.ocr provides a
strong page-parsing comparator, and POTATR reports its externally merged full-document result.
[2][18]-[20]

**Key references.** MMLongBench-Doc and mPLUG-DocOwl2 are long-document VLM references;
dots.ocr is a document parsing baseline; POTATR supplies a direct page-extractor-plus-merge
comparison. [2][18]-[20]

**Pending validation / implication for this project.** Include a relevant VLM or MLLM baseline where reproducible and
report it fairly. The proposed method’s defensible advantage is typed, spatially grounded
relations with deterministic reconstruction and relation-level error attribution, not a claim that
VLMs are irrelevant.

## Closest-Work Comparison

### Tiered Interpretation of the Current Best Results

As of 2026-08-02, the best large-scale Full Documents content-exact result is Claude Opus 4.6's
`Acc_Con = 0.2452`, and its `Acc_Top = 0.5799` is also the best structure-exact result. Among
explicit page-wise extraction plus merging pipelines, POTATR + merging reaches
`Acc_Con = 0.2176`. FinDocBench reports mean `TEDS = 0.8915` for LingDT-VL-OCR on 472 cross-page
tables, but no exact match. VCCT reports an exact-structure-like `SIR = 82.0%` on 300 private
domain tables, but private data, unreviewed status, and citation-quality problems prevent a
general reproducible SOTA claim. [1][2][4][25]

These values cannot be ranked together: `Acc_Con` requires exact structure and content,
`Acc_Top` requires exact topology only, and TEDS/GriTS are soft similarities. PubTables-v2 Full
Documents also scores single-page tables in the documents, so `0.2452` is not an isolated perfect
cross-page-merging rate. See [`cross-page-table-sota.en.md`](cross-page-table-sota.en.md) for the
full comparison.

| Work | Main capability | Reported evidence | Missing capability | Role in this project |
|---|---|---|---|---|
| Qin et al. (2024) | BERT semantic matching for financial-table continuation | Classification precision/recall/F1 | Layout hierarchy, explicit alignment, and document reconstruction | Semantic continuation baseline |
| PubTables-v2 (2025) | ViT-B/16 continuation plus vertical merging | Approximately `F1 = 0.991`; merging improves document GriTS | Explicit column, repeated-header, and split-row alignment | Primary dataset and official compatibility anchor |
| VCCT (2026) | Cross-page context with header/border cues in a domain OCR pipeline | Structural integrity rises from `77.2%` to `82.0%` | Public data/code and standard document-table evaluation | Domain-specific contextual comparator |
| POTATR (2026) | Lightweight page image-to-graph extraction plus external merging | Single Pages `GriTS_Con = 0.964`; Full Documents `0.671` to `0.827`; continuation recall `0.995` | Joint cross-page optimization and alignment-aware decoding | Strong fixed page-extractor baseline |
| LingDT-VL-OCR (2026) | Page-wise financial-document VLM followed by heuristic consolidation | Mean `TEDS = 0.8915` on 472 cross-page tables; no exact match | Public data/code, same-subset baselines, and learned explicit alignment relations | Direct cross-page soft-metric comparator |

The comparison is evidence of complementary limitations rather than a performance ranking across
incompatible datasets and metrics. [1]-[4]

## Defensible Research Gap

No reviewed public work jointly predicts page-layout relations, logical-table membership across
pages, cross-fragment column correspondence, repeated-header identity, and split-row relations in
one document graph. This gap does not justify a generic graph claim: GraphTSR, TGRNet,
DocParser, HRDoc, DocHieNet, DocGraphLM, Relationformer, and POTATR already establish relevant
graph or relation modeling at adjacent scopes. The contribution must be the explicit, typed
cross-page alignment relations and their effect on reconstructed document tables. [2][10][11][13][14][15][16][17]

The claim is bounded by the available data. Fine-grained labels must be derived or manually
audited, and metrics for the proposed model remain pending experimental validation. [1][2]

**Research question.** For English born-digital academic PDFs processed by a fixed page extractor,
does alignment-aware decoding, compared with vertical merging, improve final reconstructed-table
outcomes under both the official and template-disjoint protocols?

## Recommended Research Direction

**Decision: `revise`.** Target alignment-aware document table recovery over spatially grounded
layout/table objects. Predict logical-table membership, column correspondence, repeated headers,
and split rows, then decode a reconstructed table with page/cell provenance. Hold the page
extractor fixed in the principal experiment and compare its published-style vertical concatenation
with alignment-aware decoding. [1][2]

The evaluation should separate diagnostic edge metrics from final reconstruction: continuation,
column matching, repeated-header, and split-row measures; chain/graph consistency and
invalid-graph rate; then document `GriTS_Con`, `GriTS_Top`, and TEDS. Metric improvements remain pending experimental validation and should not be asserted before the comparison is run. [1][8]

## Three-to-Six-Month Priorities and Kill Criteria

1. Audit PubTables-v2, reproduce the official/closest vertical-merging baseline with frozen page
   objects, and verify document-level evaluation. **Kill criterion:** stop scale-up if the baseline
   cannot be reproduced or its input/output contract cannot be audited. [1][2]
2. Derive high-confidence column, repeated-header, and split-row labels; manually audit 200-300
   diverse multi-page tables; version the schema, confidence rules, and manifests. **Kill
   criterion:** stop relation-model training at scale if label quality, coverage, or agreement is
   inadequate for a defensible benchmark subset. [1]
3. Train typed relations over frozen page objects and implement constrained decoding with
   provenance and unresolved-alignment handling. **Kill criterion:** revise the model scope unless
   alignment-aware decoding produces a predeclared, uncertainty-aware improvement on the primary
   final document-reconstruction metric over the fixed-extractor vertical-merge baseline while
   preserving valid output. Before test evaluation, use validation data to fix the primary metric,
   minimally important difference, confidence method, and invalid-output tolerance. [1][2]
4. Run official-split and template-disjoint evaluations, including cue/modality ablations and
   confidence intervals. **Kill criterion:** do not claim generalization if the split construction
   is not deterministic, auditable, and leakage-resistant. [1][21]-[24]

## Evidence Boundaries and Open Questions

The review is bounded by the 60 logged searches and their documented access failures or search
constraints. Zero indexed forward citations and the absence of a newly found method category are
weak negative evidence, not proof of novelty. The reviewed direct competitors include private or
domain-specific settings, so their metrics should not be treated as directly comparable with
PubTables-v2. [2]-[4]

PubTables-v2 license and metadata facts are dataset-specific. The repository inventory records a
CDLA-Permissive-2.0 dataset license, while the paper is CC BY 4.0; source article content may have
separate PMC Open Access terms. PMCID is available in the repository, but DOI and journal/ISSN are
not exposed in the audited files. A journal/ISSN-disjoint split therefore requires separately
versioned metadata; otherwise template clustering must be the primary disjoint protocol. [1]

Open questions are whether derived labels support adequate confidence and agreement, whether
alignment-aware decoding improves final reconstruction with frozen page objects, how it behaves on
longer chains and out-of-distribution templates, and which VLM baseline is reproducible enough for
a fair comparison. These questions require experiments; they are not answered by the reviewed
literature. [1][2][18]-[20]

## References

`papers.csv` contains no author field. To avoid adding unverified bibliographic information, this
catalog lists the reviewed records without authors.

[1] **PubTables-v2: A new large-scale dataset for full-page and multi-page table extraction.** 2025. arXiv. Paper: https://arxiv.org/abs/2512.10888. Code/data: https://huggingface.co/datasets/kensho/PubTables-v2.
[2] **POTATR: A Lightweight Image-to-Graph Model for Page-Level Table Extraction.** 2026. arXiv. Paper: https://arxiv.org/abs/2606.09788. Code/data: not released as of 2026-07-24.
[3] **Application of BERT-Based Semantic Matching Algorithm for Cross-Page Table Recognition.** 2024. Artificial Intelligence in China. Paper: https://doi.org/10.1007/978-981-99-7545-7_41. Code/data: not reported.
[4] **VCCT: Vocabulary Constraint and Cross-page Context for Table Recognition in Power Grid Fault Reports.** 2026. SSRN preprint. Paper: https://doi.org/10.2139/ssrn.6811737. Code/data: not reported.
[5] **PubTables-1M: Towards comprehensive table extraction from unstructured documents.** 2022. CVPR. Paper: https://arxiv.org/abs/2110.00061. Code/data: https://github.com/microsoft/table-transformer.
[6] **Image-based table recognition: data model and evaluation.** 2020. ECCV. Paper: https://arxiv.org/abs/1911.10683. Code/data: https://github.com/ibm-aur-nlp/PubTabNet.
[7] **TableFormer: Table Structure Understanding with Transformers.** 2022. CVPR. Paper: https://arxiv.org/abs/2203.01017. Code/data: not reported.
[8] **GriTS: Grid Table Similarity Metric for Table Structure Recognition.** 2023. ICDAR. Paper: https://arxiv.org/abs/2203.12555. Code/data: https://github.com/microsoft/table-transformer.
[9] **Global Table Extractor (GTE): A Framework for Joint Table Identification and Cell Structure Recognition Using Visual Context.** 2021. WACV. Paper: https://doi.org/10.1109/WACV48630.2021.00074. Code/data: not reported.
[10] **DocParser: Hierarchical Document Structure Parsing from Renderings.** 2021. AAAI. Paper: https://arxiv.org/abs/1911.01702. Code/data: not reported.
[11] **HRDoc: Dataset and Baseline Method Toward Hierarchical Reconstruction of Document Structures.** 2023. AAAI. Paper: https://arxiv.org/abs/2303.13839. Code/data: https://github.com/jfma-USTC/HRDoc.
[12] **Detect-Order-Construct: A Tree Construction based Approach for Hierarchical Document Structure Analysis.** 2024. Pattern Recognition. Paper: https://arxiv.org/abs/2401.11874. Code/data: not reported.
[13] **DocHieNet: A Large and Diverse Dataset for Document Hierarchy Parsing.** 2024. EMNLP. Paper: https://doi.org/10.18653/v1/2024.emnlp-main.65. Code/data: https://github.com/AlibabaResearch/AdvancedLiterateMachinery.
[14] **Complicated Table Structure Recognition.** 2019. arXiv. Paper: https://arxiv.org/abs/1908.04729. Code/data: https://github.com/Academic-Hammer/SciTSR.
[15] **TGRNet: A Table Graph Reconstruction Network for Table Structure Recognition.** 2021. ICCV. Paper: https://arxiv.org/abs/2106.10598. Code/data: not reported.
[16] **Relationformer: A Unified Framework for Image-to-Graph Generation.** 2022. ECCV. Paper: https://arxiv.org/abs/2203.10202. Code/data: https://github.com/suprosanna/relationformer.
[17] **DocGraphLM: Documental Graph Language Model for Information Extraction.** 2024. SIGIR. Paper: https://arxiv.org/abs/2401.02823. Code/data: not reported.
[18] **MMLongBench-Doc: Benchmarking Long-context Document Understanding with Visualizations.** 2024. NeurIPS. Paper: https://arxiv.org/abs/2407.01523. Code/data: https://mayubo2333.github.io/MMLongBench-Doc.
[19] **mPLUG-DocOwl2: High-resolution Compressing for OCR-free Multi-page Document Understanding.** 2025. ACL. Paper: https://arxiv.org/abs/2409.03420. Code/data: https://github.com/X-PLUG/mPLUG-DocOwl/tree/main/DocOwl2.
[20] **dots.ocr: Multilingual Document Layout Parsing in a Single Vision-Language Model.** 2025. arXiv. Paper: https://arxiv.org/abs/2512.02498. Code/data: https://github.com/rednote-hilab/dots.ocr.
[21] **DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis.** 2022. KDD. Paper: https://arxiv.org/abs/2206.01062. Code/data: https://github.com/DS4SD/DocLayNet.
[22] **Aligning Benchmark Datasets for Table Structure Recognition.** 2023. ICDAR. Paper: https://arxiv.org/abs/2303.00716. Code/data: https://github.com/microsoft/table-transformer.
[23] **Shortcut Learning in Deep Neural Networks.** 2020. Nature Machine Intelligence. Paper: https://doi.org/10.1038/s42256-020-00257-z. Code/data: not reported.
[24] **Data Leakage in Visual Datasets.** 2025. ICCV Workshops. Paper: https://doi.org/10.1109/ICCVW69036.2025.00661. Code/data: not reported.
[25] **LingDT-VL-OCR: Structure-Aware Document-Level Parsing with Fine-Grained Visual Reference.** 2026. arXiv. Paper: https://arxiv.org/abs/2603.11044. Code/data: not found as of 2026-08-02.
