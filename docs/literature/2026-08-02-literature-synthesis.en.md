# Cross-Page Table Literature Synthesis

Review date: 2026-08-02. The structured evidence base is
[`papers.csv`](papers.csv), and database access, result counts, failures, and two citation
snowball rounds are recorded in [`search-log.csv`](search-log.csv).

## Task Taxonomy

The literature separates into six tasks that should not be treated as interchangeable:

1. **Continuation detection** predicts whether table fragments on adjacent pages belong to the
   same logical table. PubTables-v2 trains a ViT-B/16 pair classifier; Qin et al. use BERT semantic
   matching; VCCT uses header, border, and preceding-page context.
2. **Page-level extraction** detects tables in a page and recovers their internal structure.
   PubTables-1M/TATR, GTE, POTATR, and VLM page parsers belong here.
3. **Fragment merging** combines already extracted page fragments. The published PubTables-v2
   baseline and POTATR appendix apply a continuation decision followed by vertical concatenation.
4. **Structural alignment** determines which columns correspond, whether the first row is a
   repeated header, and whether a logical row is split across a page boundary. No reviewed public
   benchmark directly supervises all of these relations.
5. **Hierarchical document parsing** predicts reading order and parent/child relations among page
   or document objects. DocParser, HRDoc, DocHieNet, and Detect-Order-Construct provide relevant
   machinery but do not recover internal cross-page table topology.
6. **Document-level table recovery** emits one auditable table object per logical table, including
   page membership, cell topology/content, and cross-page correspondences, and evaluates the final
   reconstructed object. This is the target task supported by the evidence.

The practical pipeline is therefore:

`layout objects -> page table structures -> continuation candidates -> structural alignment ->`
`document table graph -> reconstructed table`.

Continuation is one relation in the graph, not the final task.

## Dataset and Annotation Comparison

| Dataset | Document type | Context | Cross-page instances | Structure annotation | Layout relations | License | Public status |
|---|---|---:|---:|---|---|---|---|
| PubTables-v2 Full Documents | English born-digital PubMed academic articles | 9,172 documents / 137,095 pages | 9,492 multi-page tables, up to 13 pages | Table HTML at document level and table detection boxes; no row/column boxes inside multipart tables | Cross-page table identity; adjacent positive/hard-negative pairs; no explicit column or split-row correspondence | CDLA-Permissive-2.0 for the dataset; paper is CC BY 4.0 | Public on Hugging Face |
| PubTables-v2 Single Pages | Same scientific source | 468k pages | Not a cross-page task | Page table objects, structure, captions, footers, and boxes | Hierarchical table-caption-footer relations within a page | CDLA-Permissive-2.0 | Public |
| FinDocBench | Six financial document categories | 1,044 tables in its recognition subset | 472 span at least two pages | Expert-verified table HTML; separate layout, reading-order, heading-hierarchy, and cell-localization subsets | Cross-page merging evaluation but no published fine-grained column/split-row relations | No downloadable license stated in the paper | No public data/code link found as of 2026-08-02 |
| PubTables-1M | English born-digital PubMed academic articles | Table crops and pages | None | Detailed rows, columns, cells, headers, boxes, and canonicalized structure | No document relations | Repository/code is MIT; source-image use also follows PMC terms | Public |
| PubTabNet | English born-digital PubMed academic articles | 568k table crops | None | HTML structure and cell text | None | CDLA-Permissive-1.0 for annotations; images remain under PMC terms | Public |
| FinTabNet | Financial annual reports | Page/table context | None in the standard task | Table/cell structure and text derived from PDF | No cross-page identity | Public repository terms; verify source-report rights before redistribution | Public |
| SciTSR | Scientific PDF tables | 15k table crops | None | Cell graph relations and structure | Cell adjacency only | Public repository terms | Public |
| HRDoc | English scientific multi-page documents | 2,500 documents, nearly 2M line units | Multi-page hierarchy, not multi-page table instances | Semantic line labels | Parent/child and ordering relations | No explicit dataset license found in the reviewed repository metadata | Public scripts/data link in paper |
| DocHieNet | Diverse multi-page documents | Document | Multi-page hierarchy, not table chains | Hierarchical document units | Document parent relations | Repository terms should be checked before redistribution | Public project/repository |
| DocLayNet | Diverse born-digital pages | 80,863 pages | None | 11-class layout boxes | None | CDLA-Permissive-1.0 | Public |
| MMLongBench-Doc | Long real PDF documents | 130 documents, mean 49.4 pages | 33.2% of 1,062 questions require cross-page evidence | QA answers/evidence pages only | Evidence-page links, no table topology | Public benchmark terms | Public |

PubTables-v2 is the only reviewed public benchmark designed specifically for multi-page table
extraction. Its scale is sufficient for continuation and document-level scoring, but the missing
multipart row/column boxes mean that explicit cross-page alignment labels must be derived, weakly
supervised, or manually added to a controlled subset. This is a research contribution and a major
implementation risk, not a preprocessing footnote.

## Page-Level Extraction Methods

Three page-level paradigms are relevant.

- **Detection/graph models.** PubTables-1M's Table Transformer predicts table objects and row,
  column, cell, and header boxes. TGRNet and GraphTSR predict logical locations or cell relations.
  POTATR extends DETR/TATR to jointly predict page-level tables, rows, columns, cells, captions,
  footers, and hierarchical edges. POTATR is currently the strongest directly relevant small
  component: it reports PubTables-v2 Single Pages `GriTS_Con = 0.964` with 29M parameters.
- **Segmentation and split/merge models.** CascadeTabNet, TableNet, and RobusTabNet recover table
  regions or cell grids. Their "merge" operation combines cells within one table, not fragments
  across pages.
- **Autoregressive structure generation.** PubTabNet EDD, TableFormer, SmolDocling, dots.ocr, and
  larger VLMs generate HTML, markdown, or document tags. They benefit from global visual/text
  context but provide weaker validity and spatial guarantees unless boxes are explicitly emitted.

The main implication is that a new project should not spend its contribution budget replacing a
strong page extractor. POTATR/TATR or another reproducible parser should supply page objects; the
new model should operate on their nodes, uncertainties, geometry, and text.

## Cross-Page Association and Merging Methods

The directly relevant methods are few but important:

- **Qin et al. (2024)** segment financial PDF tables and use BERT next-sentence-style semantic
  matching to recognize continuation. This supplies semantic evidence but is a two-stage,
  domain-specific decision system without layout hierarchy or structural table recovery metrics.
- **PubTables-v2 (2025)** supplies 9,866 positive and 5,964 hard-negative adjacent-page pairs. Its
  ViT-B/16 continuation classifier reaches approximately `F1 = 0.991`. On Full Documents, Claude
  Opus 4.6 has the highest content-exact `Acc_Con = 0.2452` and structure-exact
  `Acc_Top = 0.5799`; Gemini 3.1 Pro's highest soft `GriTS_Con = 0.9309` does not mean that 93.09%
  of tables are perfectly correct.
- **VCCT (2026)** fuses previous-page/document context and performs header/border pre-recognition
  in power-grid fault reports. It reports structural integrity increasing from 77.2% to 82.0%, but
  uses private domain data and a nonstandard composite metric.
- **POTATR (2026)** applies the PubTables-v2 continuation/vertical-merge technique to a stronger
  page extractor. Its Full Documents `GriTS_Con` rises from 0.671 to 0.827; dots.ocr rises from
  0.577 to 0.750 in the updated appendix experiment. POTATR reports continuation recall of 0.995
  and attributes the remaining gap to out-of-distribution multi-page content and within-page part
  merging.
- **LingDT-VL-OCR (2026)** parses pages and then applies adaptive rules involving column count,
  intervening body text, and headers. It reports mean `TEDS = 0.8915` on 472 cross-page tables in
  FinDocBench. This is the most direct cross-page-only soft-similarity result found, but the paper
  reports no exact match, same-subset baseline, or public data/code link.

These results invalidate "better continuation classification" as a sufficient paper claim. They do
not show that explicit column correspondence, repeated-header handling, or split-row recovery is
solved. The published merge is described as simple vertical concatenation.

## Hierarchical and Graph-Based Document Parsing

DocParser demonstrates that page entities and hierarchical relations can be predicted jointly, and
its weak supervision substantially improves both entity mAP and relation F1. HRDoc moves hierarchy
to multi-page documents with line-level category and relation labels. Detect-Order-Construct unifies
object detection, reading order, and tree construction. DocHieNet broadens document hierarchy data
beyond one template family.

GraphTSR and TGRNet show that table structure is naturally represented through cell relations and
logical row/column coordinates. DocGraphLM shows that reconstructed document neighborhoods improve
information extraction. RelationFormer supplies a generic end-to-end image-to-graph formulation;
POTATR confirms that a DETR-derived document image-to-graph model can be efficient and spatially
grounded.

None of these reviewed systems jointly predicts all of the following in a single document graph:

- page layout hierarchy;
- logical-table membership across page boundaries;
- cross-fragment column correspondences;
- repeated-header identity;
- split-row/cell continuation.

This absence is the most defensible model-level research gap, provided the evaluation measures the
reconstructed document table rather than only edge classification.

## Multi-Page Vision-Language Models

MMLongBench-Doc shows that long multimodal documents remain difficult: the best reported model in
that study reaches only 42.7% F1, and 33.2% of questions require evidence across pages.
mPLUG-DocOwl2 compresses each page to 324 visual tokens and uses multi-image training, reducing
first-token latency by more than 50% while improving multi-page QA. These works demonstrate useful
cross-page context modeling but emit answers rather than auditable table structures.

SmolDocling, dots.ocr, olmOCR, Granite Vision, and DeepSeek-OCR represent strong page conversion
baselines. Their primary output is markup or linearized text. PubTables-v2 and POTATR demonstrate
that a full-document frontier MLLM can be very strong, but cost, output validity, reproducibility,
and spatial attribution remain concerns. A fair paper should include a full-document MLLM result
from PubTables-v2 as an upper/competitive baseline, while the proposed method's advantage should be
explicit structure, grounding, trainability, and deterministic evaluation.

## Metrics and Evaluation Protocols

No single existing metric covers the whole target. The evaluation should have three layers:

1. **Diagnostic edge metrics:** continuation precision/recall/F1; column matching F1; repeated
   header F1; split-row relation F1. These reveal failure causes but are not the headline.
2. **Chain and graph metrics:** logical-table clustering/chain F1, edge F1 by relation type, graph
   edit or tree-consistency measures, and invalid-graph rate.
3. **Final reconstruction metrics:** document-level `GriTS_Top`, `GriTS_Con`, TEDS/TEDS-Struct,
   exact topology/content accuracy where feasible, and performance stratified by page span, cell
   count, repeated headers, split rows, and page-layout complexity.

GriTS is preferable to exact match alone because it compares table matrices and separately scores
topology, location, and content. It still needs document-level matching and alignment-aware error
reporting. The PubTables-v2 official matching/evaluation code should be the compatibility anchor.

All splits must use the document as the minimum unit. In addition to the official split, report a
template-disjoint or journal/template-cluster-disjoint split constructed without test leakage. The
clustering features and threshold must be frozen using training data, and near-duplicate pages or
source articles must not cross splits.

## Template Generalization and Shortcut Risks

DocLayNet quantifies the domain problem: scientific-only layout data do not transfer reliably to
diverse layouts. Document Domain Randomization shows that layout style mismatch can reduce accuracy
even when semantic fidelity is low. Aligning Benchmark Datasets shows that annotation conventions
alone can change exact-match results from 69% to 81% with the model held fixed. Shortcut Learning
and Data Leakage in Visual Datasets explain why IID accuracy and page-random splits can be
misleading.

For PubTables-v2, likely shortcuts include journal templates, page position, repeated running
headers, stable table width, adjacent page numbering, and near-identical positive fragments. The
hard-negative adjacent pairs help but do not establish template generalization. Required controls
are:

- document-level splitting only;
- template/journal-cluster-disjoint evaluation;
- ablations for image, geometry, text, page position, header similarity, and page-number cues;
- shuffled-page and non-adjacent negative tests;
- performance by unseen template cluster and table page span;
- duplicate/template similarity audit before training.

## Closest-Work Comparison

| Work | Input | Output | Coupling to layout/TSR | Cross-page structural alignment | Evaluation | Known limitation |
|---|---|---|---|---|---|---|
| Qin et al. 2024 | Adjacent financial-PDF text/table segments | Continuation match | Two-stage semantic matcher after segmentation | No explicit column or split-row alignment | Classification P/R/F1 | Private domain data; not document-level reconstruction |
| PubTables-v2 ViT merging 2025 | Pair of page images plus outputs from a page parser | Continuation label then vertically concatenated table | External ViT classifier composed with parser | No; simple vertical concatenation | Continuation F1 and document GriTS/TEDS | Continuation is near saturated; alignment error is not isolated |
| VCCT 2026 | OCR results, prior page, document summary, header/border cues | Domain OCR/table output | Composite OCR pipeline | Header/border pre-recognition but no public typed alignment graph | Structural integrity and OCR component metrics | Private power-grid reports; nonstandard metric and no public code/data |
| POTATR + merging 2026 | Pages independently processed by POTATR plus pairwise ViT | Page graphs then merged table | Strong joint page layout/TSR graph; cross-page step remains external | No; published experiment uses vertical concatenation | Full-document GriTS/TEDS/accuracy | Trained on single pages; within-page part merging and multi-page optimization out of scope |
| LingDT-VL-OCR 2026 | Page-wise VLM outputs from financial PDFs | Heuristically consolidated document content and tables | External consolidation rules within a document parsing system | Column-count/header rules, but no explicit learned column or split-row relations | Mean `TEDS = 0.8915` on 472 cross-page tables | No exact match, same-subset baseline, or located public data/code |
| Proposed revised target | Full document with page objects, cells, geometry, text, and uncertainty | Typed document table graph plus reconstructed table | Layout, continuation, and alignment relations trained/evaluated together | Yes: columns, repeated headers, split rows, fragment/table membership | Relation + chain + document GriTS/TEDS + disjoint generalization | Requires new derived/manual alignment labels and careful scope control |

## Supported Research Gap

The evidence supports a **revised**, narrower claim:

> Recover multi-page tables in born-digital academic PDFs by predicting a typed document relation
> graph over layout and table objects, with explicit cross-page column, repeated-header, and
> split-row relations, and evaluate the final reconstructed table under document- and
> template-disjoint protocols.

The supported novelty is not using a graph by itself, and not replacing a ViT with a larger model.
It is the combination of (a) explicit structural alignment relations absent from the closest public
baselines, (b) integration with page layout/table objects, (c) structure-aware reconstruction, and
(d) evaluation that attributes document-level gains to those relations under leakage-resistant
splits.

The smallest publishable unit is a reproducible PubTables-v2 alignment subset/protocol, a strong
POTATR/TATR-plus-vertical-merge reproduction, an alignment-aware relation model, and document-level
evaluation/error taxonomy. A monolithic end-to-end full-document VLM or a new universal page parser
is not required for the first paper.
