# State of the Art in Cross-Page Table Merging

Review cutoff: 2026-08-02

## Bottom Line

There is **no single cross-dataset SOTA number for cross-page table merging** in the reviewed literature. Existing studies evaluate different scopes: full-document extraction, a cross-page-only subset, merging after page-wise extraction, structural integrity, or continuation classification. Their metrics are not interchangeable.

The verified evidence supports the following tiered conclusions:

1. **Most credible large-scale public content-exact result:** Claude Opus 4.6 reaches `Acc_Con = 0.2452` on PubTables-v2 Full Documents. This is a content-aware table exact-match aggregate. Every test document contains a multi-page or multi-column table, but scoring also includes single-page tables in those documents, so it does not mean that 24.52% of cross-page tables were independently merged perfectly. [1]
2. **Most credible large-scale public structure-exact result:** Claude Opus 4.6 reaches `Acc_Top = 0.5799` in the same setting. It requires exact table topology while ignoring cell text. [1]
3. **Best content-exact result for an explicit page-wise extraction plus merging pipeline:** POTATR + merging reaches `Acc_Con = 0.2176`, with `Acc_Top = 0.4234` and `GriTS_Con = 0.8269`. It uses a continuation classifier and simple vertical concatenation, without explicit column correspondence, repeated-header, or split-row modeling. [2]
4. **Most direct strong soft-similarity result on a cross-page-only subset:** LingDT-VL-OCR reports mean `TEDS = 0.8915` on 472 cross-page tables from FinDocBench. TEDS is an edit-distance similarity, not an exact-match rate. The paper reports neither exact match nor competing methods on that same cross-page subset. [3]
5. **Highest table-level zero-structural-error claim found, but with low confidence:** VCCT reports `SIR = 82.0%` on 300 private cross-page tables from power-grid fault reports. SIR requires no column misalignment, complete row retention, and precise header alignment, but it does not require exact cell content; cell data accuracy is reported separately as `86.3%`. This is an unreviewed SSRN preprint with no public data or code and with notable citation-quality problems, so it is not a general, reproducible SOTA result. [4]

The most rigorous one-sentence answer is:

> The best verified large-scale public content-exact score is Claude Opus 4.6's `Acc_Con = 0.2452` on PubTables-v2; the latest strong result directly evaluated on a cross-page-only subset is mean `TEDS = 0.8915` on FinDocBench, but this is not an exact-match rate; no public reproducible study was found that reports structure-and-content table exact match on a dedicated alignment-only benchmark with fixed page-level predictions.

## Metrics Are Not Interchangeable

| Metric | What it measures | Exact-like | Does it directly mean perfect merging? |
|---|---|---:|---|
| `Acc_Con` | Table topology and cell content must match exactly | Yes | Closest available metric, but PubTables-v2 Full Documents also includes detection, page recognition, and single-page tables |
| `Acc_Top` | Table topology must match exactly; text is ignored | Yes, structural | Measures exact structure, not exact content |
| `SIR` | No column misalignment, no omitted rows, and precise header alignment | Yes, author-defined structural | Close to perfect structural merging, but nonstandard and excludes full content correctness |
| `GriTS_Con` | Soft average grid-and-content similarity | No | A high score can coexist with several row, column, or text errors |
| `TEDS` | Edit-distance similarity of HTML tree structure and content | No | A high score does not mean a zero-error table |
| Continuation F1 | Whether two page fragments belong to the same logical table | No | Decides whether to merge, not how to align and merge correctly |

PubTables-v2 generalizes traditional one-table-to-one-table metrics to matching sets of predicted and ground-truth tables within a document. `Acc_Con` still gives credit only to exact table matches, but the Full Documents value is a table-level exact-match aggregate over the evaluation collection, not an exact-document rate requiring every table in a document to be correct. [1]

## Verified Result Comparison

| Study and setting | Data | Scope | Structure exact | Content exact | Soft similarity | Reproducibility and interpretation |
|---|---|---|---:|---:|---:|---|
| Claude Opus 4.6, PubTables-v2 Full Documents | 9,172 full documents with 9,492 multi-page tables; all tables scored | Full-document end-to-end extraction | `Acc_Top 0.5799` | **`Acc_Con 0.2452`** | `GriTS_Con 0.9079`; `TEDS 0.8798` | Public data/evaluation; proprietary model; not an isolated merging score |
| Gemini 3.1 Pro, PubTables-v2 Full Documents | Same | Full-document end-to-end extraction | `0.4854` | `0.2025` | **`GriTS_Con 0.9309`**; **`TEDS 0.8905`** | Best soft similarity but lower exact score than Claude; not 93.09% perfectly correct tables |
| POTATR + merging, PubTables-v2 Full Documents | Full documents containing multi-page tables | 29M page extractor + ViT continuation classifier + vertical concatenation | `0.4234` | **`0.2176`** | `GriTS_Con 0.8269`; `TEDS 0.7824` | Clearest page-wise extraction and merging pipeline; merging remains heuristic |
| dots.ocr + merging, PubTables-v2 Full Documents | Same | Page-wise VLM + the same external merger | `0.5059` | `0.1180` | `GriTS_Con 0.7495`; `TEDS 0.7731` | Relatively high structural exact score but low content exact score |
| LingDT-VL-OCR, FinDocBench | 1,044 tables, including 472 spanning at least two pages | Page-wise VLM + adaptive heuristic merging | Not reported | Not reported | **Cross-page subset `TEDS 0.8915`** | Direct cross-page evaluation, but no exact metric or same-subset baseline; no public data/code link found |
| VCCT, private power-grid data | 300 cross-page tables; 85% span two pages and 15% span at least three | OCR + header/border pre-recognition + cross-page context | **`SIR 82.0%`** | Not reported | Cell data accuracy `86.3%`, reported separately | Private small domain dataset, unreviewed, and not reproducible; not cross-comparable with public benchmarks |
| Qin et al. | Private financial PDFs | BERT semantic continuation matching | Not reported | Not reported | Classification P/R/F1 | Continuation only; no reconstructed-table metric |

## Interpreting the Claimed Best Results

### Why Gemini's 0.9309 is not the best merging accuracy

`GriTS_Con = 0.9309` is a soft grid-and-content similarity. A long table can retain a high average score despite a few column shifts, missing rows, repeated headers, or split-row errors. Gemini's `Acc_Con = 0.2025` in the same table shows the difference between looking mostly similar and being entirely error-free. [1]

### Is 0.2452 the strict SOTA for cross-page merging?

It is the strongest verified public large-scale content-aware exact-match evidence, but only for the PubTables-v2 Full Documents end-to-end setting. That evaluation combines:

- within-page table detection and structure recognition;
- matching multiple tables in a document;
- single-page tables;
- multi-column and multi-page recognition and merging;
- cell-text extraction.

It therefore does not isolate the merging module. No reviewed paper reports an independent `Acc_Con` where correct page fragments are supplied and only cross-page column, header, and split-row alignment is evaluated.

### Is VCCT's 82.0% stronger?

Numerically and by its stated definition, `SIR = 82.0%` is the highest whole-table zero-structural-error-like result found in this search. It is not equivalent to `Acc_Con`: SIR does not require every cell string to be correct, and it is measured on 300 private domain tables. It should be treated as a private domain claim, not as evidence that the general public problem is solved. [4]

### Why LingDT-VL-OCR matters

LingDT-VL-OCR provides important recent direct evidence because it explicitly evaluates reconstructed tables on 472 cross-page instances and reports mean `TEDS = 0.8915`. However, the paper gives only its own result, no exact-match metric, and no competing scores on that cross-page subset. A strict SOTA claim on FinDocBench is therefore not verifiable. [3]

## Remaining Research Opportunity

The results show a consistent gap: soft similarity is around `0.89-0.93`, while large-scale public content exact match remains around `0.20-0.25`. Models usually recover most of a table, but a small number of structural errors still cause whole-table exact failure. Public methods do not make all of the following relations primary supervised and separately evaluated targets:

- column correspondence across page boundaries;
- repeated-header deletion versus retention;
- split-row continuation at a page break;
- column merging, splitting, or local subheaders after a page boundary;
- attribution of error to page extraction versus cross-page merging.

This leaves a defensible research problem for alignment-aware cross-page table recovery with a fixed page extractor.

## Direct Recommendation for This Project

The main evaluation should have two tracks:

1. **End-to-end track:** use POTATR/TATR or another fixed page extractor, compare with the published continuation-classifier plus vertical-concatenation baseline, and report the official PubTables-v2 `Acc_Con`, `Acc_Top`, `GriTS_Con`, and TEDS metrics.
2. **Alignment-isolation track:** provide ground-truth page fragments or manually verified page structures and evaluate only cross-page column matching, repeated headers, split rows, and final reconstruction. Add cross-page-table structure exact match and structure-plus-content exact match, stratified by page span, column count, split rows, and header complexity.

The first track establishes integration with layout/table analysis; the second identifies whether the proposed method actually solves merging rather than inheriting page-extraction errors.

## Search Boundary and Confidence

Building on the existing systematic search, this update queried OpenAlex, arXiv, and focused web searches with combinations of `cross-page table`, `multi-page table`, `table continuation`, `table merging`, `table stitching`, `exact match`, and `structure integrity`. The source papers for PubTables-v2, POTATR, LingDT-VL-OCR, and VCCT were checked directly. No other public study was found that reports a reproducible structure-and-content whole-table exact match on a dedicated public cross-page benchmark.

Failure to find a paper is not proof that none exists. Non-English work, unindexed papers, private industrial reports, and unpublished evaluations may be missing. The report therefore uses “best verified evidence by the cutoff date,” not an unconditional worldwide SOTA claim.

## References

[1] **PubTables-v2: A new large-scale dataset for full-page and multi-page table extraction.** arXiv:2512.10888, v3. https://arxiv.org/abs/2512.10888

[2] **POTATR: A Lightweight Image-to-Graph Model for Page-Level Table Extraction.** arXiv:2606.09788, v1. https://arxiv.org/abs/2606.09788

[3] **LingDT-VL-OCR: Structure-Aware Document-Level Parsing with Fine-Grained Visual Reference.** arXiv:2603.11044, v2. https://arxiv.org/abs/2603.11044

[4] **VCCT: Vocabulary Constraint and Cross-page Context for Table Recognition in Power Grid Fault Reports.** SSRN preprint. https://doi.org/10.2139/ssrn.6811737

[5] **Application of BERT-Based Semantic Matching Algorithm for Cross-Page Table Recognition.** Artificial Intelligence in China, Springer LNEE, 2024. https://doi.org/10.1007/978-981-99-7545-7_41

[6] **GriTS: Grid Table Similarity Metric for Table Structure Recognition.** ICDAR 2023. https://arxiv.org/abs/2203.12555
