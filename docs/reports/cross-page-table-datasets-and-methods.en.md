# Cross-Page Table Datasets and Merging Methods: A Comprehensive Review

Review cutoff: 2026-08-02

## 1. Main Findings

Cross-page table processing is not a single binary-classification problem. It is a document-analysis pipeline with four stages:

1. detect tables on each page and recognize rows, columns, cells, and text;
2. decide whether fragments on adjacent pages belong to the same logical table;
3. align columns, handle repeated headers, and merge rows split at a page boundary;
4. output one complete table while preserving the page and spatial provenance of every cell.

Existing work performs strongly on Stage 2, deciding whether to merge. For example, the PubTables-v2 ViT-B/16 continuation classifier reaches `F1 = 0.991`. Stage 3, deciding how to align and merge accurately, still relies mainly on vertical concatenation or heuristic rules. On large-scale public end-to-end evaluation, the best exact match of both structure and content is only `Acc_Con = 0.2452`. Systems usually recover most content, but column shifts, repeated headers, split rows, or a small number of text errors still prevent a completely correct table. [1][2]

PubTables-v2 remains the only large research-grade dataset found that publicly combines full document pages, cross-page logical-table identity, complete reconstructed-table ground truth, and a standard evaluation protocol. Other sources are unreleased, provide continuation labels only, contain raw PDFs only, or lack clear licensing.

## 2. Task and Annotation Levels

The usefulness of a dataset depends on which part of the task it supports.

| Level | Input and output | Minimum annotation | Typical metrics |
|---|---|---|---|
| Page table extraction | Page image -> within-page table structure | Table boxes, rows, columns, cells, text, or HTML | GriTS, TEDS, cell F1 |
| Continuation detection | Two page fragments -> same logical table or not | Positive/negative fragment pairs or logical-table identity | Precision, Recall, F1, AUC |
| Cross-page structural alignment | Two fragments -> column, header, and split-row correspondences | Column matching, repeated-header, and split-row relations | Relation F1, alignment accuracy |
| Final table reconstruction | Multiple fragments -> one logical table | Complete merged HTML/grid/cell content | `Acc_Top`, `Acc_Con`, GriTS, TEDS |

Only datasets with final-table ground truth can directly evaluate whether a whole cross-page table was reconstructed correctly. Continuation labels alone cannot determine whether rows and columns were merged correctly.

## 3. Cross-Page Table Dataset Overview

| Dataset | Availability | Scale | Content | Directly supported task | Dataset link or paper |
|---|---|---:|---|---|---|
| PubTables-v2 Full Documents | Public and downloadable | 9,172 documents, 137,095 pages, 9,492 multi-page tables | Page images, PDF words and coordinates, fragments, cross-page logical identity, complete HTML/JSON/grid ground truth | Continuation, document table extraction, final reconstruction | [Hugging Face](https://huggingface.co/datasets/kensho/PubTables-v2); [paper](https://arxiv.org/abs/2512.10888) |
| FinDocBench | Described in a paper; no public download found | 1,044 tables, including 472 cross-page tables | Expert-verified table structures; separate layout, reading-order, heading-hierarchy, and cell-localization subsets | Cross-page TEDS evaluation, financial document parsing | [LingDT-VL-OCR paper](https://arxiv.org/abs/2603.11044) |
| BioMike/table-continuation-dataset | Public and downloadable | 14,660 fragment pairs | `premise` and `hypothesis` Markdown fragments plus binary `label` | Continuation-classifier training | [Hugging Face](https://huggingface.co/datasets/BioMike/table-continuation-dataset) |
| hwyin04/table-cross-page | Public and downloadable | 30 PDFs, approximately 32.6 MB | Raw PDF files | Manual case analysis and secondary annotation | [Hugging Face](https://huggingface.co/datasets/hwyin04/table-cross-page) |
| VCCT private data | Not public | 300 cross-page tables | Power-grid fault-report tables and internal annotations | Structural integrity and content-accuracy evaluation | [paper](https://doi.org/10.2139/ssrn.6811737) |
| Financial PDF data used by Qin et al. | Not public | No verifiable scale in accessible metadata | Adjacent financial-table fragments and continuation labels | Semantic continuation matching | [paper](https://doi.org/10.1007/978-981-99-7545-7_41) |

### 3.1 PubTables-v2

PubTables-v2 is derived from English born-digital PubMed Central articles and contains complementary cropped-table, full-page, and full-document collections. Full Documents is the relevant subset for cross-page research.

Its main properties are:

- 9,172 complete documents and 137,095 page images;
- 9,492 multi-page tables, with a maximum span of 13 pages;
- 7,817 two-page, 1,134 three-page, and 302 four-page tables, plus more than 200 spanning at least five pages;
- 9,866 positive continuation pairs and 5,964 hard-negative pairs;
- page images, PDF-extracted words and coordinates, page-element annotations, and fragment locations;
- complete HTML, grid, and cell JSON for each logical table, with page-fragment provenance.

Its main advantage is direct support for document-level training and standardized evaluation. The dataset uses `CDLA-Permissive-2.0`. Its main limitation is that multipart fragments do not have the same complete internal row/column boxes as the Single Pages collection, and relations such as “page-one column 3 corresponds to page-two column 3” or “this logical row is split across pages” are not explicitly annotated. Research on explicit column alignment, repeated headers, and split rows therefore requires derived labels or a manually audited subset. [1]

### 3.2 FinDocBench

FinDocBench was introduced with LingDT-VL-OCR and covers six financial document categories, including annual reports, audit reports, and prospectuses. Its table-recognition portion contains 1,044 tables, of which 472 span at least two pages: 425 span two pages, 28 span three pages, and 19 span more than three pages. The paper states that the annotations were human-labeled and expert-verified, and evaluates merged-table TEDS on all 472 cross-page instances. [3]

Its value is domain diversity relative to PubTables-v2 and an explicit cross-page subset. As of the review cutoff, however, neither the paper nor the arXiv page provides a dataset/code download or downloadable license. It is currently a dataset with published results but no direct access. Contacting the authors about release plans is appropriate if it is to be used as a future out-of-domain financial test set.

### 3.3 BioMike/table-continuation-dataset

This Hugging Face dataset publishes 14,660 training records. Each record contains two Markdown table fragments and a binary label. The public card exposes only its schema and size: approximately 2.69 MB to download and 9.29 MB after materialization, with no validation or test split. [D2]

Positive examples indicate that fragments should continue; negative examples indicate that they should not. It can therefore train a text-based continuation classifier, but it cannot train column correspondence, header deletion, split-row recovery, or final HTML reconstruction. Sample inspection also found exact duplicate records. The card provides no provenance, construction procedure, or license. Before research use, it requires provenance verification, deduplication, document-level re-splitting, and a license audit.

### 3.4 hwyin04/table-cross-page

This Hugging Face repository contains 30 PDFs totaling approximately 32.6 MB. It has no README, JSON, CSV, Parquet, HTML, or other annotation files and states no license. [D3]

It is therefore not a benchmark that can be directly trained on or scored. It may support manual inspection of cross-page styles, a small demonstration set, or new annotation after source-file rights are verified. The repository name alone does not establish that all cross-page tables in every PDF were exhaustively collected and validated.

### 3.5 Private Data

VCCT uses 300 cross-page tables from power-grid fault reports. Eighty-five percent span two pages and 15% span at least three. The paper reports structural-integrity and data-accuracy results but releases neither data, code, nor an annotation specification. [4]

Qin et al. use private financial PDFs and formulate cross-page recognition as semantic matching between adjacent fragments. Accessible metadata provides no dataset download and insufficient information to verify its scale or whether complete reconstructed-table annotations exist. [5]

### 3.6 Related Datasets That Do Not Directly Support Cross-Page Merging

| Dataset | Useful property | Why it cannot directly evaluate cross-page merging | Link |
|---|---|---|---|
| PubTables-1M | Large-scale page table detection and structure recognition with detailed row, column, and cell labels | No cross-page logical identity or fragment correspondence | [paper](https://arxiv.org/abs/2110.00061); [code/data](https://github.com/microsoft/table-transformer) |
| FinTabNet | Financial-report table structure and content | Standard annotations are organized by table/page, without cross-page chains or complete merged ground truth | [GitHub](https://github.com/microsoft/table-transformer/blob/main/DIRECTORY.md) |
| PubTabNet | 568k cropped tables with HTML | Page and document context is discarded | [dataset](https://github.com/ibm-aur-nlp/PubTabNet) |
| TableBank | Weakly labeled Word/LaTeX tables and diverse templates | The task is page-level detection/recognition, without cross-page identity | [paper](https://arxiv.org/abs/1903.01949); [GitHub](https://github.com/doc-analysis/TableBank) |
| DocILE | Multi-page business documents and information-extraction labels | No general table grid or cross-page table-structure ground truth | [paper](https://arxiv.org/abs/2302.05658); [GitHub](https://github.com/rossumai/docile) |
| HRDoc | Line-level hierarchy and reading order for 2,500 scientific documents | Annotates document hierarchy rather than internal cross-page table structure | [paper](https://arxiv.org/abs/2303.13839); [GitHub](https://github.com/jfma-USTC/HRDoc) |

These datasets can pretrain page-level layout/table models or serve as document sources for mining new examples, but logical-table identity and merged-structure annotations must be added.

## 4. Existing Cross-Page Table Merging Research

### 4.1 BERT Semantic Continuation Matching

Qin et al. first segment tables from financial PDFs, linearize adjacent fragments as text, and use BERT next-sentence-style semantic matching to decide whether they continue. This method exploits content semantics and can recognize fragments with similar headers or numerical patterns. Its output, however, is only a continuation decision. It does not explicitly reconstruct column correspondence, repeated headers, split rows, or a complete table. The paper evaluates classification Precision, Recall, and F1 rather than a whole-table metric comparable to PubTables-v2 `Acc_Con`. [5]

### 4.2 PubTables-v2: ViT Continuation Classification and Vertical Concatenation

PubTables-v2 constructs positive and hard-negative pairs from adjacent pages and trains ResNet-50 and ViT-B/16 image classifiers to predict table continuation. [1]

| Model | Recall | Precision | F1 | AUC |
|---|---:|---:|---:|---:|
| ResNet-50 | 0.986 | 0.973 | 0.979 | 0.991 |
| ViT-B/16 | **0.995** | **0.987** | **0.991** | **0.996** |

During merging, if the page parser predicts a table on both adjacent pages and the ViT predicts continuation, the two predicted tables are concatenated vertically. This handles whether to merge well, but it does not separately learn column alignment or split-row relations.

In the PubTables-v2 paper, dots.ocr improves from `GriTS_Con = 0.5768` to 0.6844 and from `TEDS = 0.5876` to 0.7141 after merging, while `Acc_Con` remains 0.1180. Large soft-metric gains with unchanged exact match show that simple merging recovers more content but often leaves enough errors to prevent a completely correct table. [1]

### 4.3 POTATR: Page Graph Extraction Plus External Merging

POTATR is a 29M-parameter page-level image-to-graph model. In a DETR/RelationFormer-style framework, it jointly predicts tables, rows, columns, cells, headers, captions, footers, and within-page hierarchy. Its main learned contribution remains page-level table extraction. The cross-page stage reuses the PubTables-v2 ViT-B/16 continuation classifier and simple vertical concatenation without retraining the page model. [2]

On PubTables-v2 Full Documents:

| Method | GriTS_Top | GriTS_Con | Acc_Top | Acc_Con | TEDS_S | TEDS |
|---|---:|---:|---:|---:|---:|---:|
| POTATR, no merging | 0.6973 | 0.6710 | 0.3285 | 0.2038 | 0.6353 | 0.6128 |
| POTATR + merging | **0.8507** | **0.8269** | **0.4234** | **0.2176** | **0.8058** | **0.7824** |
| dots.ocr + merging | 0.7772 | 0.7495 | **0.5059** | 0.1180 | 0.8022 | 0.7731 |

POTATR + merging is the strongest verified content-exact result among explicit page-wise extraction plus external-merging pipelines. Nevertheless, `Acc_Con = 0.2176` means that most tables are still not exact in both structure and content.

### 4.4 Full-Document Multimodal Large Models

PubTables-v2 also evaluates Claude, GPT, and Gemini with the complete document as one input. These models do not expose explicit column-correspondence edges; they use full-document context to generate all tables. Their advantage is broad context. Their disadvantages include proprietary models, high cost, nondeterministic outputs, and weaker page/cell provenance. [1]

| Model | GriTS_Top | GriTS_Con | Acc_Top | Acc_Con | TEDS_S | TEDS |
|---|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.6 | 0.9116 | 0.9079 | **0.5799** | **0.2452** | 0.8914 | 0.8798 |
| GPT-5.4 | 0.8865 | 0.8847 | 0.5038 | 0.1636 | 0.8563 | 0.8341 |
| Gemini 3.1 Pro | **0.9365** | **0.9309** | 0.4854 | 0.2025 | **0.9048** | **0.8905** |

Gemini has the highest soft `GriTS_Con = 0.9309`, while Claude has the highest content-exact `Acc_Con = 0.2452`. The former cannot be interpreted as 93.09% of cross-page tables being perfectly reconstructed. Full Documents also scores single-page tables in the same documents, so these are end-to-end document table-extraction results rather than isolated merging-module accuracy.

### 4.5 LingDT-VL-OCR: Adaptive Heuristic Merging

LingDT-VL-OCR first parses financial documents page by page with a VLM and then merges adjacent tables with three levels of rules: [3]

1. the two fragments must have exactly the same number of columns;
2. no body text or semantic element other than headers and footers may occur between them;
3. if the next fragment has no header or an identical header, discard the repeated header and append only `tbody`; if it has a different header, append the complete fragment and preserve that header as a subheader.

The method reports mean `TEDS = 0.8915` on 472 cross-page FinDocBench tables. This is the most direct cross-page-only soft-similarity result found, but the paper reports no exact match and no competing methods on those same 472 tables. It demonstrates that the rules work on the authors' data, but it does not establish a reproducible exact-match SOTA.

### 4.6 VCCT: Domain Vocabulary, Pre-Recognition, and Cross-Page Context

VCCT targets power-grid fault reports and combines domain-vocabulary constraints, header/border pre-recognition, previous-page context, and document-summary context in an OCR/table pipeline. The authors define Structure Integrity Rate (SIR): a table counts as intact only if it has no column misalignment, retains every row without omission, and aligns headers precisely. [4]

On 300 private cross-page tables, the baseline SIR is 77.2%, rising to 82.0% with cross-page pre-recognition. Cell data accuracy rises from 78.5% to 86.3%. The paper attributes approximately 40% of errors to inconsistent column widths across page breaks, 25% to continuation-page headers being treated as data rows, and 20% to incorrect segmentation of cross-page cell content.

SIR is close to whole-table zero-structural-error evaluation, but it does not require all cell text to be correct and is measured on private data. The work is an unreviewed SSRN preprint with no public code/data and notable reference-quality problems. Its 82.0% should therefore be treated as a private domain result, not a public general SOTA.

## 5. Interpreting the Metrics

| Metric | Meaning | Exact correctness required | Main limitation |
|---|---|---:|---|
| Continuation F1 | Whether two fragments belong to the same table | No | Does not evaluate columns, headers, or split-row merging |
| `Acc_Top` | Table topology must match exactly; text is ignored | Yes, structural | Does not measure cell-text correctness |
| `Acc_Con` | Table topology and cell content must both match exactly | Yes | End-to-end values also include detection, TSR, and OCR errors |
| `GriTS_Con` | Soft grid-and-content similarity | No | A few serious errors may coexist with a high average score |
| TEDS | Edit-distance similarity of HTML tree structure and content | No | 0.89 does not mean that 89% of tables are perfect |
| SIR | No column misalignment, omitted rows, or header mismatch | Yes, author-defined structural | Nonstandard and excludes full content correctness |

The strongest credible large-scale public content-exact evidence is `Acc_Con = 0.2452` on PubTables-v2. The best explicit page-wise merging pipeline is POTATR + merging at 0.2176. The latest strong soft result on a direct cross-page subset is FinDocBench `TEDS = 0.8915`. The highest exact-like structural claim is VCCT `SIR = 82.0%`, but with low reproducibility and confidence. These values cannot be placed in one ranking.

## 6. Remaining Problems

Continuation detection is strong, but current work still lacks:

- explicit one-to-one column correspondence rather than column-count equality alone;
- distinction among repeated headers, local subheaders, and ordinary data rows;
- detection and merging of logical rows or cells split at page boundaries;
- handling of column merges, splits, missing columns, and multi-level header changes;
- uncertainty-aware alignment when page extraction is imperfect;
- evaluation that separates page-extraction errors from cross-page-alignment errors;
- public cross-page structure exact match and structure-plus-content exact match;
- document-disjoint, template-disjoint, and cross-domain generalization tests.

## 7. Recommendations for This Project

### 7.1 Data Use

1. Use PubTables-v2 Full Documents as the primary training and formal evaluation dataset.
2. Derive column, repeated-header, and split-row candidates from PubTables-v2, then manually audit 200-300 complex multi-page tables as a versioned alignment subset.
3. Use BioMike only for auxiliary continuation experiments. Deduplicate, reconstruct document-level splits, and verify provenance and licensing first. Exclude it from the main experiment if those checks fail.
4. Use the 30 hwyin04 PDFs only for case analysis or supplementary manual annotation, not as a quantitative benchmark.
5. Contact the LingDT-VL-OCR authors about FinDocBench and use it as an external financial-domain test set if released.

### 7.2 Evaluation Tracks

The main paper should include two tracks:

- **End-to-end track:** freeze POTATR/TATR or another page extractor; compare no merging, ViT continuation plus vertical concatenation, and alignment-aware merging; report official `Acc_Con`, `Acc_Top`, GriTS, and TEDS.
- **Alignment-isolation track:** provide ground-truth or manually verified page fragments and evaluate only column matching, repeated headers, split rows, and final whole-table exact match. This directly attributes gains to merging rather than a changed page extractor.

### 7.3 Required Baselines

- no cross-page merging;
- ViT-B/16 continuation plus simple vertical concatenation;
- POTATR + merging;
- LingDT-style column-count/intervening-text/header heuristics;
- dots.ocr or one document VLM where reproducible;
- an oracle upper bound using ground-truth page structures.

## 8. Conclusion

Available public resources are sufficient to start the project, but not to directly supervise every cross-page alignment relation. PubTables-v2 provides large-scale full documents and final logical-table ground truth and should remain the primary dataset. FinDocBench offers important financial-domain cross-page evidence but is not yet public. The two Hugging Face community datasets support only continuation classification or manual secondary annotation.

Methodologically, continuation prediction is near saturation. Simple vertical concatenation substantially improves soft similarity but does not reliably improve whole-table exact correctness. The most defensible research target is therefore not another same-table decision. It is explicit prediction of column correspondence, repeated headers, and split rows over spatially grounded layout/table objects, followed by reconstruction of a complete, correct, and auditable logical table.

## References and Dataset Links

[1] **PubTables-v2: A new large-scale dataset for full-page and multi-page table extraction.** arXiv:2512.10888. [paper](https://arxiv.org/abs/2512.10888); [dataset](https://huggingface.co/datasets/kensho/PubTables-v2); [GriTS evaluation code](https://github.com/kensho-technologies/grits)

[2] **POTATR: A Lightweight Image-to-Graph Model for Page-Level Table Extraction.** arXiv:2606.09788. [paper](https://arxiv.org/abs/2606.09788)

[3] **LingDT-VL-OCR: Structure-Aware Document-Level Parsing with Fine-Grained Visual Reference.** arXiv:2603.11044. [paper](https://arxiv.org/abs/2603.11044)

[4] **VCCT: Vocabulary Constraint and Cross-page Context for Table Recognition in Power Grid Fault Reports.** SSRN preprint. [paper](https://doi.org/10.2139/ssrn.6811737)

[5] **Application of BERT-Based Semantic Matching Algorithm for Cross-Page Table Recognition.** Artificial Intelligence in China, Springer LNEE, 2024. [paper](https://doi.org/10.1007/978-981-99-7545-7_41)

[6] **GriTS: Grid Table Similarity Metric for Table Structure Recognition.** ICDAR 2023. [paper](https://arxiv.org/abs/2203.12555); [code](https://github.com/microsoft/table-transformer)

[D1] **PubTables-v2 dataset.** [Hugging Face](https://huggingface.co/datasets/kensho/PubTables-v2)

[D2] **BioMike/table-continuation-dataset.** [Hugging Face](https://huggingface.co/datasets/BioMike/table-continuation-dataset)

[D3] **hwyin04/table-cross-page.** [Hugging Face](https://huggingface.co/datasets/hwyin04/table-cross-page)
