# 跨页表格文献综述的核心发现

## 执行摘要

文献支持作出 `revise` 决策，而不支持将续接分类本身宣称为创新。在已报告的 PubTables-v2 官方设置上，续接分类已接近饱和，但本综述并未证实其在未来模板不相交评估上同样饱和。具有可辩护性的目标是面向原生数字化学术 PDF 的**结构对齐感知文档级表格恢复**：在空间定位的版面与表格对象之上构建类型化关系模型，用以预测逻辑表格归属、列对应关系、重复表头及拆分行。该目标的性能指标改进仍属待实验验证。最接近的公开基线是由固定页面提取器、续接分类和纵向合并组成的流程；拟议工作必须相对于该基线分离并检验结构对齐感知解码的价值。[1][2]

## 范围与证据基础

评审日期：2026-08-02。除非另有说明，所有否定性检索、引文计数、研究产物可用性及创新缺失陈述均以此日期为截止时间。

本综述覆盖英文原生数字化学术 PDF，并以 PubTables-v2 为主要公开基准。证据基础包括 49 条初筛记录、32 条全文阅读记录、60 次已记录检索、两轮引文滚雪球检索、经审阅的主张，以及固定至 PubTables-v2 修订版本 `aa575e798cb00a296925e2086addb3e3fd9a1903` 的仓库清单。综述将其中 25 条记录作为编号参考文献目录。[1]-[25]

PubTables-v2 Full Documents 提供逻辑表格、页面分片溯源、相邻页面对标签、页面图像、PDF 词元及页面标注。其不提供多页表格分片内部的行/列边界框，因此公开数据中无法获得直接的细粒度结构对齐监督。[1]

## 任务定义

目标任务为文档级表格恢复。给定页面级版面与表格对象，系统应形成续接候选，预测类型化跨页关系，并解码得到一张逻辑表格，同时保留其页面分片和单元格的溯源信息。因此，最终输出不应仅是续接判断或纵向拼接序列，而应是重建后的、可审计的文档级表格对象。[1][2][5][8]

预期的关系集合包括逻辑表格归属、单调列对应、重复表头同一性及拆分行关系。这些关系在保持对版面/表格对象空间定位的同时连接各页面分片。[1][2][10]-[17]

## 核心发现

### 发现 1：跨页表格恢复是文档级重建任务，而非仅仅是续接分类

**综合判断。** 跨页恢复应定义为跨越页面分片重建一张逻辑表格，而非仅定义为二元续接分类。页面级对象或网格恢复是必要能力，但其本身不能解决文档级表格拓扑问题。

**文献已证实。** PubTables-v2 在完成续接检测和合并后评估重建的文档表格，其公开 Full Documents 标注保留了逻辑表格和页面分片信息。Qin et al. 将续接表述为语义匹配，但不输出重建后的结构。页面级表格方法可恢复单页内的对象或网格。[1][3][5]-[9]

**核心文献。** PubTables-v2 提供直接的文档级表格任务设置；Qin et al. 提供语义续接比较器；PubTables-1M、GriTS、GTE、GraphTSR、TGRNet 和 TableFormer 则阐明页面/表格结构与文档级重建之间的区别。[1][3][5][7][8][9][14][15]

**待实验验证的项目启示。** 项目的核心输出与评估应是一张重建后的逻辑表格，且包含分片和单元格溯源。续接准确率是诊断性关系指标，而非项目的主要结果。

### 发现 2：在已报告的 PubTables-v2 官方设置上，续接分类已接近饱和，不能支撑主要创新主张

**综合判断。** 仅提升续接分类性能，不能构成在已报告的 PubTables-v2 官方设置上具有可辩护性的主要贡献；其在未来模板不相交评估上是否饱和仍有待检验。

**文献已证实。** PubTables-v2 报告其 ViT-B/16 续接分类器的性能约为 `F1 = 0.991`。当 POTATR 与该续接分类器及纵向合并组合时，报告的续接召回率为 `0.995`。但 POTATR 仍报告了完整文档层面的剩余差距，包括 Single Pages 上的 `GriTS_Con = 0.964`，以及跨页合并后 Full Documents 上 `0.671` 至 `0.827` 的结果。[1][2]

**核心文献。** PubTables-v2 是官方续接和文档重建的锚点；POTATR 是经审阅后最强的固定页面提取器组合方案；Qin et al. 是语义续接基线。[1]-[3]

**待实验验证的项目启示。** 应报告续接的精确率、召回率和 F1 以诊断错误，但主要主张必须聚焦于结构对齐和最终文档恢复。

### 发现 3：在经审阅的公开工作中，尚未解决的技术问题是页面分片之间的显式结构对齐

**综合判断。** 在经审阅的公开工作中，显式的跨分片列对应、重复表头同一性和拆分行关系仍是尚未解决的技术问题；这并非对整个领域不存在相关方法的断言。

**文献已证实。** PubTables-v2 和 POTATR 描述的合并流程均采用先续接、后纵向拼接的方式。PubTables-v2 的公开多页标注不含分片内部的行/列边界框。GraphTSR 和 TGRNet 对单张表格内的单元格关系与逻辑坐标进行建模；经审阅的文档层次方法则对文档级层次关系进行建模。[1][2][10][11][12][13][14][15][16][17]

**核心文献。** PubTables-v2 和 POTATR 界定直接缺口；GraphTSR 和 TGRNet 为基于关系的表格结构提供动机；DocParser、HRDoc、Detect-Order-Construct、DocHieNet、DocGraphLM 和 Relationformer 是相关的关系建模比较对象。[1][2][10][11][12][13][14][15][16][17]

**待实验验证的项目启示。** 构建类型化文档表格关系图和受约束解码器，使其能够返回列匹配、重复表头、拆分行，以及未决结构对齐或无效图情形。在将这些关系作为监督目标前，应建立版本化的派生标签方案或经审计的子集。

### 发现 4：版面分析和页面级 TSR 应与跨页关系模型共享对象，但首篇论文无须替换页面提取器

**综合判断。** 版面分析、页面级表格结构识别（TSR）和跨页关系应共享空间对象，但首篇论文不需要新的页面提取器。经审阅的页面级能力和层次结构能力不能替代跨页结构对齐。

**文献已证实。** POTATR 联合预测页面级表格、行、列、单元格、题注、页脚和层次关系，但其跨页步骤仍是外部续接分类与纵向合并。PubTables-1M 和 GTE 展示了页面上下文及表格对象的价值；DocParser 和 HRDoc 展示了相关层次结构机制。[2][5][9][10][11]

**核心文献。** POTATR 是固定页面提取器基线；PubTables-1M 和 GTE 是页面级对象/结构参考；DocParser、HRDoc 和 DocHieNet 是层次结构参考。[2][5][9][10][11][13]

**待实验验证的项目启示。** 在决定性比较中固定一个可复现的 TATR/POTATR 风格页面解析器。向关系模型输入其对象、几何信息、文本及不确定性，再比较纵向拼接与结构对齐感知解码。

### 发现 5：PubTables-v2 是主要公开基准，但缺少直接的细粒度结构对齐标签

**综合判断。** PubTables-v2 是该目标任务的主要公开基准，但不能直接监督所有必需的结构对齐关系。在经审阅的数据集中，未发现与之等价的公开跨页结构对齐基准。

**文献已证实。** 其 Full Documents 集合包含 9,172 份文档和 9,492 张多页表格，并具有逻辑表格标注、页面分片及困难相邻页面对标签。多页标注不提供内部行/列边界框、列对应关系、重复表头同一性或拆分行标签。其他经审阅数据集提供页面/表格结构、层次结构或长文档问答任务。[1][5][6][7][11][13][14][15][18]

**核心文献。** PubTables-v2 提供直接公开基准；PubTables-1M、PubTabNet、TableFormer、GraphTSR、TGRNet、HRDoc、DocHieNet 和 MMLongBench-Doc 确立了相邻但不完整的监督场景。[1][5][6][7][11][13][14][15][18]

**待实验验证的项目启示。** 派生高置信度标签，并人工审计一个受控且具多样性的子集。若许可允许，应发布标签模式、派生代码、置信度规则和清单；不得将派生标签表述为 PubTables-v2 的原生标注。

### 发现 6：可信评估需要文档级重建指标和抗泄漏的数据划分

**综合判断。** 可信评估需要文档级重建指标，以及能够抵抗文档泄漏和模板泄漏的数据划分。经审阅的证据提示，不能只依赖 IID 结果或随机页面划分。

**文献已证实。** GriTS 评估拓扑、位置和内容，但不含显式表格链或跨页结构对齐组成部分。PubTables-v2 是文档 GriTS/TEDS 的官方兼容性锚点。文档与版面研究表明层次结构和模板差异具有重要性；经审阅的基准对齐、捷径学习和视觉数据泄漏研究记录了泛化与泄漏风险。[1][8][11][12][14][21]-[24]

**核心文献。** GriTS 和 PubTables-v2 是重建评估的锚点；DocLayNet、Aligning Benchmark Datasets、Shortcut Learning 和 Data Leakage in Visual Datasets 为泛化和泄漏控制提供动机。[1][8][21]-[24]

**待实验验证的项目启示。** 报告关系特异指标、链/图诊断、文档 `GriTS_Con`、`GriTS_Top` 和 TEDS，以及精确链和无效图比例。为可比性使用官方划分，同时采用确定性的模板不相交方案；其聚类特征和阈值应在不查看测试结果的前提下固定。

### 发现 7：VLM 是重要的竞争基线，但类型化关系方法的可审计空间结构仍构成可辩护优势

**综合判断。** VLM 和多页文档模型是重要基线，但其生成式输出本身不提供可审计的空间表格结构。对于文档级表格恢复，经审阅的工作仍将输出有效性、可复现性和空间归因留作开放的比较问题。

**文献已证实。** MMLongBench-Doc 和 mPLUG-DocOwl2 展示了多页上下文建模能力，但其经审阅任务输出的是答案而非重建的表格拓扑。dots.ocr 提供了强有力的页面解析比较器，POTATR 也报告了其经外部合并后的完整文档结果。[2][18]-[20]

**核心文献。** MMLongBench-Doc 和 mPLUG-DocOwl2 是长文档 VLM 参考；dots.ocr 是文档解析基线；POTATR 提供直接的页面提取器加合并比较。[2][18]-[20]

**待实验验证的项目启示。** 在可复现的条件下纳入相关 VLM 或 MLLM 基线，并公平报告结果。所提方法可辩护的优势是具有确定性重建和关系级错误归因的类型化、空间定位关系，而非宣称 VLM 无关紧要。

## 最接近工作的比较

### 当前最好结果的分层解释

截至 2026-08-02，公开大规模 Full Documents 设置中最高的内容 exact 是 Claude Opus 4.6 的 `Acc_Con = 0.2452`，最高结构 exact 是其 `Acc_Top = 0.5799`；显式逐页识别加拼接流水线中，POTATR + merging 的 `Acc_Con = 0.2176`。FinDocBench 在 472 张跨页表上报告 LingDT-VL-OCR 平均 `TEDS = 0.8915`，但没有 exact match。VCCT 在 300 张私有领域表上报告结构零错误类 `SIR = 82.0%`，但其私有数据、未评审状态和引用质量问题使其不能作为通用可复现 SOTA。[1][2][4][25]

这些数字不能合并排名：`Acc_Con` 要求结构和内容完全匹配，`Acc_Top` 只要求拓扑完全匹配，而 TEDS/GriTS 是软相似度。PubTables-v2 Full Documents 还同时评分文档中的单页表，因此 `0.2452` 不是仅针对跨页拼接模块的完全正确率。完整对比见 [`cross-page-table-sota.zh-CN.md`](cross-page-table-sota.zh-CN.md)。

| 工作 | 主要能力 | 已报告证据 | 缺失能力 | 在本项目中的角色 |
|---|---|---|---|---|
| Qin et al. (2024) | 面向金融表格续接的 BERT 语义匹配 | 分类精确率/召回率/F1 | 版面层次、显式结构对齐和文档级重建 | 语义续接基线 |
| PubTables-v2 (2025) | ViT-B/16 续接检测加纵向合并 | 约 `F1 = 0.991`；合并提升文档 GriTS | 显式列、重复表头和拆分行结构对齐 | 主要数据集与官方兼容性锚点 |
| VCCT (2026) | 在领域 OCR 流程中结合表头/边框线索的跨页上下文 | 结构完整性由 `77.2%` 升至 `82.0%` | 公开数据/代码和标准文档级表格评估 | 特定领域上下文比较对象 |
| POTATR (2026) | 轻量级页面图像到图提取加外部合并 | Single Pages `GriTS_Con = 0.964`；Full Documents `0.671` 至 `0.827`；续接召回率 `0.995` | 联合跨页优化和结构对齐感知解码 | 强固定页面提取器基线 |
| LingDT-VL-OCR (2026) | 金融文档逐页 VLM 后启发式跨页合并 | 472 张跨页表平均 `TEDS = 0.8915`；未报告 exact match | 公开数据/代码、同子集基线和可学习的显式对齐关系 | 直接跨页子集软指标比较对象 |

该比较证明的是互补性局限，而不是对不兼容数据集和指标上的性能排序。[1]-[4]

## 可辩护的研究缺口

没有经审阅的公开工作能在一个文档图中联合预测页面版面关系、跨页逻辑表格归属、跨分片列对应、重复表头同一性和拆分行关系。该缺口并不支持泛泛的图模型主张：GraphTSR、TGRNet、DocParser、HRDoc、DocHieNet、DocGraphLM、Relationformer 和 POTATR 已经在相邻任务范围内确立了相关的图或关系建模。贡献必须在于显式、类型化的跨页结构对齐关系及其对重建文档表格的影响。[2][10][11][13][14][15][16][17]

该主张受可用数据限制。细粒度标签必须派生或经人工审计，所提模型的指标仍属待实验验证。[1][2]

**研究问题。** 对于由固定页面提取器处理的英文原生数字化学术 PDF，与纵向合并相比，结构对齐感知解码能否在官方协议和模板不相交协议下改进最终重建表格的结果？

## 建议的研究方向

**决策：`revise`。** 面向空间定位的版面/表格对象开展结构对齐感知文档级表格恢复。预测逻辑表格归属、列对应、重复表头和拆分行，然后解码得到具有页面/单元格溯源信息的重建表格。在主要实验中固定页面提取器，并将其已发表风格的纵向拼接与结构对齐感知解码进行比较。[1][2]

评估应将诊断性边指标与最终重建分开：续接、列匹配、重复表头和拆分行度量；链/图一致性及无效图比例；然后是文档 `GriTS_Con`、`GriTS_Top` 和 TEDS。指标改进仍属待实验验证，不应在完成比较之前加以断言。[1][8]

## 三至六个月的优先事项与终止标准

1. 审计 PubTables-v2，利用固定页面对象复现官方/最接近的纵向合并基线，并验证文档级评估。**终止标准：** 若该基线无法复现，或无法审计其输入/输出契约，则停止扩大工作规模。[1][2]
2. 派生高置信度的列、重复表头和拆分行标签；人工审计 200-300 张多样化多页表格；对模式、置信度规则和清单进行版本化。**终止标准：** 若标签质量、覆盖度或一致性不足以构成可辩护的基准子集，则停止大规模关系模型训练。[1]
3. 在固定页面对象上训练类型化关系，并实现具有溯源和未决结构对齐处理的受约束解码。**终止标准：** 除非结构对齐感知解码在保持有效输出的同时，相对于固定提取器纵向合并基线，在主要最终文档重建指标上取得预先声明且考虑不确定性的改进，否则应修订模型范围。在测试评估前，须使用验证数据固定主要指标、最小重要差异、置信度方法和无效输出容忍度。[1][2]
4. 开展官方划分和模板不相交评估，包括线索/模态消融及置信区间。**终止标准：** 若划分构造并非确定性、可审计且抗泄漏，则不得主张泛化能力。[1][21]-[24]

## 证据边界与开放问题

本综述受 60 次已记录检索及其已记录的访问失败或检索限制所约束。零条已索引的前向引用以及未发现新的方法类别，均只是较弱的否定性证据，而不是新颖性的证明。经审阅的直接竞争工作包括私有或领域特定设置，因此不应将其指标视为可与 PubTables-v2 直接比较。[2]-[4][25]

PubTables-v2 的许可和元数据事实具有数据集特异性。仓库清单记录数据集采用 CDLA-Permissive-2.0 许可证，而论文采用 CC BY 4.0；源文章内容可能另有 PMC Open Access 条款。仓库中可获取 PMCID，但经审计文件未公开 DOI 和期刊/ISSN。因此，期刊/ISSN 不相交划分需要单独进行版本化的元数据；否则，模板聚类必须是主要的不相交方案。[1]

开放问题包括：派生标签能否支持充分的置信度和一致性，结构对齐感知解码能否在固定页面对象条件下改进最终重建，其在更长表格链和分布外模板上的表现如何，以及哪一种 VLM 基线具有足够可复现性以供公平比较。这些问题需要实验；经审阅文献尚未给出答案。[1][2][18]-[20]

## 参考文献

`papers.csv` 不含作者字段。为避免添加未经核验的书目信息，本目录不列作者，仅列出经审阅的记录。

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
