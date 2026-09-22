# 跨页表格数据集与拼接方法完整调研

调研截止日期：2026-08-02

## 1. 核心结论

跨页表格处理不是一个单独的二分类问题，而是一条包含四个阶段的文档分析流程：

1. 从每一页中检测表格并识别行、列、单元格和文字；
2. 判断相邻页面上的表格片段是否属于同一张逻辑表；
3. 对齐两页的列，处理重复表头，并合并分页处被截断的行；
4. 输出一张完整表格，并保留每个单元格来自哪一页、哪个位置的溯源信息。

现有工作在第2步“要不要拼”上已经取得很高的结果，例如 PubTables-v2 的 ViT-B/16 续接分类器达到 `F1 = 0.991`；但第3步“怎样准确对齐并拼好”仍主要依赖纵向拼接或启发式规则。公开大规模端到端评测中，表格结构和内容完全匹配的最好结果只有 `Acc_Con = 0.2452`。这说明系统通常能够恢复大部分内容，但列错位、重复表头、拆分行或少量文字错误仍会使整表无法完全正确。[1][2]

数据方面，PubTables-v2 仍是目前唯一同时公开完整文档页面、跨页逻辑表身份、完整表格结构真值和标准评测协议的大规模研究级数据集。其他数据来源分别存在未公开、只有续接标签、只有原始 PDF 或缺少许可证等限制。

## 2. 任务与标注层次

评价一个数据集是否真正适合跨页拼接，需要检查它支持哪一层任务。

| 层次 | 输入与输出 | 最低标注要求 | 典型指标 |
|---|---|---|---|
| 页面表格识别 | 单页图像 -> 页面内表格结构 | 表格框、行列、单元格、文字或 HTML | GriTS、TEDS、单元格 F1 |
| 续接检测 | 两个页面片段 -> 是否同一张表 | 正负片段对或逻辑表身份 | Precision、Recall、F1、AUC |
| 跨页结构对齐 | 两个表格片段 -> 列、表头、拆分行对应 | 列对应、重复表头、拆分行关系 | 关系 F1、对齐准确率 |
| 最终整表重建 | 多个片段 -> 一张完整逻辑表 | 合并后的完整 HTML/网格/单元格内容 | `Acc_Top`、`Acc_Con`、GriTS、TEDS |

只有包含最后一层真值的数据集，才能直接评价“整张跨页表是否拼对”。只有续接标签的数据只能判断两个片段是否相关，不能判断行列是否正确合并。

## 3. 跨页表格数据集总览

| 数据集 | 公开状态 | 规模 | 提供的内容 | 可直接支持的任务 | 数据链接或论文 |
|---|---|---:|---|---|---|
| PubTables-v2 Full Documents | 公开，可下载 | 9,172 篇文档、137,095 页、9,492 张多页表 | 页面图像、PDF 词元与坐标、表格片段、跨页逻辑表身份、完整 HTML/JSON/网格真值 | 续接检测、文档级表格抽取、最终整表重建 | [Hugging Face](https://huggingface.co/datasets/kensho/PubTables-v2)；[论文](https://arxiv.org/abs/2512.10888) |
| FinDocBench | 论文已公布，未发现公开下载入口 | 1,044 张表，其中472张跨页表 | 专家核验表格结构；另有版面、阅读顺序、标题层次和单元格定位子集 | 跨页表格 TEDS 评测、金融文档解析 | [LingDT-VL-OCR 论文](https://arxiv.org/abs/2603.11044) |
| BioMike/table-continuation-dataset | 公开，可下载 | 14,660 对表格片段 | `premise`、`hypothesis` 两段 Markdown 表格及二分类 `label` | 续接分类训练 | [Hugging Face](https://huggingface.co/datasets/BioMike/table-continuation-dataset) |
| hwyin04/table-cross-page | 公开，可下载 | 30 个 PDF，约 32.6 MB | 原始 PDF 文件 | 人工案例分析、二次标注 | [Hugging Face](https://huggingface.co/datasets/hwyin04/table-cross-page) |
| VCCT 私有数据 | 不公开 | 300 张跨页表 | 电网故障报告表格及作者内部标注 | 结构完整性与内容准确率评测 | [论文](https://doi.org/10.2139/ssrn.6811737) |
| Qin 等人的金融 PDF 数据 | 不公开 | 论文公开元数据未给出可核验规模 | 相邻金融表格片段与续接标签 | 语义续接匹配 | [论文](https://doi.org/10.1007/978-981-99-7545-7_41) |

### 3.1 PubTables-v2

PubTables-v2 来自英文原生数字化 PubMed Central 学术论文，包含三个互补部分：裁剪表格、完整单页和完整文档。与跨页研究最相关的是 Full Documents 子集。

Full Documents 的主要信息包括：

- 9,172 篇完整文档和137,095张页面图像；
- 9,492 张多页表格，最长跨13页；
- 7,817 张跨2页、1,134 张跨3页、302 张跨4页，另有200余张跨5页及以上；
- 9,866 对续接正样本和5,964对困难负样本；
- 页面图像、PDF 提取词元和坐标、页面元素标注、表格片段位置；
- 每张逻辑表格的完整 HTML、网格和单元格 JSON，以及页面片段溯源。

它的主要优势是可以直接进行文档级训练和标准化评测，数据集采用 `CDLA-Permissive-2.0`。主要不足是多页表格片段内部没有像 Single Pages 那样完整的行列边界框，也没有直接标注“第1页第3列对应第2页第3列”“这一行在分页处被截断”等细粒度关系。因此，研究显式列对齐、重复表头和拆分行时，仍需要从 HTML 派生标签或人工补充一个高质量子集。[1]

### 3.2 FinDocBench

FinDocBench 由 LingDT-VL-OCR 提出，面向年报、审计报告、招股书等六类金融文档。表格识别部分共有1,044张表，其中472张跨至少两页：425张跨2页、28张跨3页、19张跨3页以上。论文称标注经过人工和金融专家核验，并在472张跨页表上评价合并后的 TEDS。[3]

它的价值是领域与 PubTables-v2 不同，而且直接建立了跨页表格子集。限制是截至调研日期，论文及其 arXiv 页面没有给出数据集或代码下载链接，也未给出可下载许可证。因此它目前属于“有论文和结果，但不能直接获得”的数据集。可以联系作者询问发布计划，将其作为未来的跨领域外部测试集。

### 3.3 BioMike/table-continuation-dataset

该 Hugging Face 数据集公开了14,660条训练样本，每条包含两个 Markdown 表格片段和一个0/1标签。公开数据卡只给出字段和大小：下载约2.69 MB，解压后约9.29 MB；没有验证集或测试集。[D2]

正样本表示两个片段应当续接，负样本表示不应续接。因此它可以用于训练文本层面的续接分类器，但不能用于训练列对应、表头删除、拆分行恢复或最终 HTML 重建。样本检查还发现完全重复记录。数据卡没有说明来源、构建方法和许可证，正式论文实验使用前必须完成来源核验、去重、文档级重新划分和许可证审计。

### 3.4 hwyin04/table-cross-page

该 Hugging Face 仓库包含30个 PDF，总大小约32.6 MB。仓库没有 README、JSON、CSV、Parquet、HTML 或其他结构标注文件，也没有声明许可证。[D3]

因此它不是可以直接训练或计算准确率的标准数据集。它最多可用于人工观察跨页表格样式、构建小型演示集，或在确认源文件权利后自行标注。仅凭仓库名称还不足以证明每个 PDF 的全部跨页表都已完整收集和核验。

### 3.5 私有数据

VCCT 使用300张电网故障报告跨页表，其中85%跨2页、15%跨3页及以上。论文给出结构完整性和数据准确率，但没有公开数据、代码或标注规范。[4]

Qin 等人使用私有金融 PDF，将跨页表格识别建模为相邻片段的语义匹配。可访问的论文元数据没有提供数据下载入口，也没有足够信息核验规模和完整重建标注。[5]

### 3.6 相关但不能直接用于跨页拼接的数据集

| 数据集 | 有用之处 | 为什么不能直接评价跨页拼接 | 链接 |
|---|---|---|---|
| PubTables-1M | 大规模单页表格检测与结构识别；具有详细行列和单元格标注 | 没有跨页逻辑表身份和片段对应 | [论文](https://arxiv.org/abs/2110.00061)；[代码/数据](https://github.com/microsoft/table-transformer) |
| FinTabNet | 金融年报中的表格结构与内容 | 标准标注按单表或页面组织，没有跨页链与完整合并真值 | [GitHub](https://github.com/microsoft/table-transformer/blob/main/DIRECTORY.md) |
| PubTabNet | 568k裁剪表格及 HTML | 丢失页面和文档上下文 | [数据集](https://github.com/ibm-aur-nlp/PubTabNet) |
| TableBank | Word/LaTeX 弱标注表格，可提供多样模板 | 任务是单页检测/识别，没有跨页身份 | [论文](https://arxiv.org/abs/1903.01949)；[GitHub](https://github.com/doc-analysis/TableBank) |
| DocILE | 多页商业文档与信息抽取标注 | 没有通用表格网格和跨页表结构真值 | [论文](https://arxiv.org/abs/2302.05658)；[GitHub](https://github.com/rossumai/docile) |
| HRDoc | 2,500篇科学文档的行级层次和阅读顺序 | 标注文档层次，不标注跨页表格内部结构 | [论文](https://arxiv.org/abs/2303.13839)；[GitHub](https://github.com/jfma-USTC/HRDoc) |

这些数据可以预训练页面级版面或表格模型，也可以作为挖掘新跨页样本的文档来源，但必须新增逻辑表身份和合并结构标注。

## 4. 已有跨页表格拼接研究

### 4.1 BERT 语义续接匹配

Qin 等人的方法先从金融 PDF 中分割表格，再把相邻表格片段转换为文本，用类似 BERT 下一句预测的语义匹配判断它们是否连续。该方法利用表格内容语义，适合处理表头或数值模式相近的片段，但输出只是是否续接，没有显式恢复列对应、重复表头、拆分行或完整表格结构。论文采用分类 Precision、Recall 和 F1，不报告可与 PubTables-v2 `Acc_Con` 比较的整表结果。[5]

### 4.2 PubTables-v2：ViT 续接分类器与纵向拼接

PubTables-v2 从相邻页面构造正样本和困难负样本，训练 ResNet-50 和 ViT-B/16 图像分类器判断表格是否跨页续接。结果如下：[1]

| 模型 | Recall | Precision | F1 | AUC |
|---|---:|---:|---:|---:|
| ResNet-50 | 0.986 | 0.973 | 0.979 | 0.991 |
| ViT-B/16 | **0.995** | **0.987** | **0.991** | **0.996** |

在合并阶段，如果页面级解析器在相邻两页都识别出表格，并且 ViT 判断为续接，系统就把两个预测表格进行纵向拼接。这个方法很好地解决了“要不要拼”，但没有单独学习列匹配和拆分行关系。

PubTables-v2 论文中，dots.ocr 的 `GriTS_Con` 从0.5768提高到0.6844，TEDS 从0.5876提高到0.7141；`Acc_Con` 仍为0.1180。软指标明显上升而 exact 不变，说明简单拼接恢复了更多内容，但仍经常留下足以破坏整表完全匹配的错误。[1]

### 4.3 POTATR：页面图模型加外部跨页合并

POTATR 是一个29M参数的页面级 image-to-graph 模型，基于 DETR/RelationFormer 风格联合预测表格、行、列、单元格、表头、标题、表尾和页面内层次关系。它的主要模型贡献仍在页面级表格抽取；跨页步骤复用 PubTables-v2 的 ViT-B/16续接分类器，并使用简单纵向拼接，不重新训练页面模型。[2]

在 PubTables-v2 Full Documents 上：

| 方法 | GriTS_Top | GriTS_Con | Acc_Top | Acc_Con | TEDS_S | TEDS |
|---|---:|---:|---:|---:|---:|---:|
| POTATR，不合并 | 0.6973 | 0.6710 | 0.3285 | 0.2038 | 0.6353 | 0.6128 |
| POTATR + merging | **0.8507** | **0.8269** | **0.4234** | **0.2176** | **0.8058** | **0.7824** |
| dots.ocr + merging | 0.7772 | 0.7495 | **0.5059** | 0.1180 | 0.8022 | 0.7731 |

POTATR + merging 是目前核验到的最明确“逐页识别 + 外部拼接”流水线中最高的内容 exact 结果，但 `Acc_Con = 0.2176` 仍说明大多数表格没有达到结构和内容全部完全一致。

### 4.4 整篇文档输入的多模态大模型

PubTables-v2 还把完整文档一次性输入 Claude、GPT 和 Gemini。模型不显式输出“列对应边”，而是利用全文上下文直接生成所有表格。这条路线的优势是上下文范围大，缺点是模型闭源、成本高、输出不一定具有确定的页面和单元格溯源。[1]

| 模型 | GriTS_Top | GriTS_Con | Acc_Top | Acc_Con | TEDS_S | TEDS |
|---|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.6 | 0.9116 | 0.9079 | **0.5799** | **0.2452** | 0.8914 | 0.8798 |
| GPT-5.4 | 0.8865 | 0.8847 | 0.5038 | 0.1636 | 0.8563 | 0.8341 |
| Gemini 3.1 Pro | **0.9365** | **0.9309** | 0.4854 | 0.2025 | **0.9048** | **0.8905** |

Gemini 的 `GriTS_Con = 0.9309` 是最高软相似度，但最高内容完全匹配是 Claude 的 `Acc_Con = 0.2452`。因此不能把0.9309解释成93.09%的跨页表完全拼对。Full Documents 还同时评价文档中的单页表，所以上述结果是端到端文档级表格抽取结果，不是隔离后的纯拼接模块准确率。

### 4.5 LingDT-VL-OCR：自适应启发式拼接

LingDT-VL-OCR 先用 VLM 逐页解析金融文档，再按三个层次的规则合并相邻表格：[3]

1. 两个片段的列数必须严格一致；
2. 两个片段之间不能有除页眉页脚以外的正文或其他语义元素；
3. 如果下一页没有表头或表头与上一页相同，删除重复表头并只追加 `tbody`；如果表头不同，则保留整个片段，把不同表头当作同一结构中的子表头。

该方法在 FinDocBench 的472张跨页表上报告平均 `TEDS = 0.8915`。这是目前找到的最直接跨页表格子集软相似度结果，但论文没有报告 exact match，也没有报告其他方法在同一472张表上的对比结果。因此它证明该规则在作者数据上有效，但不能证明整表完全正确率，也不能形成可复现的公开 SOTA 比较。

### 4.6 VCCT：领域词表、预识别与跨页上下文

VCCT 面向电网故障报告，将领域词表约束、表头/边框预识别、上一页上下文和文档级摘要信息组合进 OCR/表格识别流程。作者定义 Structure Integrity Rate（SIR）：只有同时满足无列错位、所有行完整保留且表头精确对齐，才把整张表计为结构完整。[4]

在300张私有跨页表上，基线 SIR 为77.2%，加入跨页预识别后达到82.0%；单元格数据准确率从78.5%提高到86.3%。论文还称列宽不一致约占40%的错误，续接页表头被误识别为数据行约占25%，跨页单元格内容分割错误约占20%。

SIR 很接近“整表结构是否零错误”，但不检查全部单元格文字是否正确，而且数据私有。该论文是未评审 SSRN 预印本，代码和数据未公开，引用列表还存在明显质量问题，因此82.0%只能作为特定领域内部结果，不能与公开基准直接比较或宣称为通用 SOTA。

## 5. 指标如何理解

| 指标 | 含义 | 是否要求完全正确 | 主要局限 |
|---|---|---:|---|
| 续接 F1 | 是否正确判断两个片段属于同一张表 | 否 | 不检查列、表头和拆分行怎样拼 |
| `Acc_Top` | 表格拓扑必须完全匹配，忽略文字 | 是，结构层面 | 不反映单元格文字准确性 |
| `Acc_Con` | 表格拓扑和单元格内容都必须完全匹配 | 是 | 端到端结果还受页面检测、TSR和OCR影响 |
| `GriTS_Con` | 网格与内容的软相似度 | 否 | 少量严重错误仍可能得到高平均分 |
| TEDS | HTML树结构与内容的编辑距离相似度 | 否 | 0.89不等于89%的表完全正确 |
| SIR | 无列错位、无漏行、表头精确对齐 | 是，作者自定义结构层面 | 非标准指标，不包含全部内容正确性 |

目前最可信的公开大规模内容 exact 证据是 PubTables-v2 上 `Acc_Con = 0.2452`；最好的显式逐页拼接流水线是 POTATR + merging 的0.2176；直接跨页子集上的最新强软指标是 FinDocBench 的 `TEDS = 0.8915`；最高 exact-like 结构声明是 VCCT 的 `SIR = 82.0%`，但其可信度和可复现性较低。这些数字不能混合排名。

## 6. 尚未解决的问题

现有研究已经较好地解决了“相邻两页是不是同一张表”，但仍缺少以下能力：

- 显式预测跨页列的一一对应，而不是只检查列数是否相同；
- 区分真正重复表头、局部子表头和普通数据行；
- 识别一行是否在分页处被截断，并正确合并跨页单元格；
- 处理第二页列合并、列拆分、缺列和多层表头变化；
- 在页面识别有误时进行不确定性感知的对齐，而不是无条件拼接；
- 单独评价拼接模块，区分页面提取错误和跨页对齐错误；
- 在公开数据上报告跨页表结构 exact match 和结构+内容 exact match；
- 进行文档不相交、模板不相交和跨领域泛化评测。

## 7. 对本项目的数据与实验建议

### 7.1 数据使用

1. 以 PubTables-v2 Full Documents 作为主要训练和正式评测数据。
2. 从 PubTables-v2 派生列对应、重复表头和拆分行候选，再人工审计200-300张复杂多页表，形成版本化的对齐子集。
3. BioMike 数据只用于续接分类辅助实验；使用前去重、重新按源文档划分，并确认来源与许可证。若无法确认，不放入正式主实验。
4. hwyin04 的30份 PDF 只用于案例分析或补充人工标注，不能直接作为定量基准。
5. 联系 LingDT-VL-OCR 作者获取 FinDocBench；若成功，可作为金融领域外部测试集。

### 7.2 实验轨道

主论文应同时设置两个轨道：

- **端到端轨道：**固定 POTATR/TATR 等页面提取器，比较“不合并”“ViT续接 + 纵向拼接”“结构对齐感知拼接”，报告官方 `Acc_Con`、`Acc_Top`、GriTS和TEDS。
- **对齐隔离轨道：**输入真实或人工校验的页面表格片段，只评价列匹配、重复表头、拆分行和最终整表 exact match。这能直接证明改进来自拼接模块，而不是页面识别器变化。

### 7.3 必须包含的基线

- 不做跨页合并；
- ViT-B/16 续接分类器 + 简单纵向拼接；
- POTATR + merging；
- LingDT 风格的列数/正文间隔/表头启发式规则；
- 可复现时加入 dots.ocr 或一个文档 VLM；
- 使用真实页面结构的 oracle 拼接上界。

## 8. 总结

现有公开资源足以开始研究，但还不足以直接监督所有跨页对齐关系。PubTables-v2 提供大规模完整文档和最终逻辑表真值，是当前主数据集；FinDocBench 提供重要的金融跨页子集证据，但尚未公开；两个 Hugging Face 社区数据集只能分别支持续接分类或人工二次标注。

方法上，续接判断已经接近饱和，简单纵向拼接能够显著提高软相似度，却不能稳定提高整表完全正确率。最值得研究的部分不是再判断一次“是不是同一张表”，而是利用页面版式和表格结构，明确预测列对应、重复表头和拆分行，最终恢复一张结构与内容都正确且可溯源的完整表格。

## 参考文献与数据链接

[1] **PubTables-v2: A new large-scale dataset for full-page and multi-page table extraction.** arXiv:2512.10888. [论文](https://arxiv.org/abs/2512.10888)；[数据集](https://huggingface.co/datasets/kensho/PubTables-v2)；[GriTS评测代码](https://github.com/kensho-technologies/grits)

[2] **POTATR: A Lightweight Image-to-Graph Model for Page-Level Table Extraction.** arXiv:2606.09788. [论文](https://arxiv.org/abs/2606.09788)

[3] **LingDT-VL-OCR: Structure-Aware Document-Level Parsing with Fine-Grained Visual Reference.** arXiv:2603.11044. [论文](https://arxiv.org/abs/2603.11044)

[4] **VCCT: Vocabulary Constraint and Cross-page Context for Table Recognition in Power Grid Fault Reports.** SSRN preprint. [论文](https://doi.org/10.2139/ssrn.6811737)

[5] **Application of BERT-Based Semantic Matching Algorithm for Cross-Page Table Recognition.** Artificial Intelligence in China, Springer LNEE, 2024. [论文](https://doi.org/10.1007/978-981-99-7545-7_41)

[6] **GriTS: Grid Table Similarity Metric for Table Structure Recognition.** ICDAR 2023. [论文](https://arxiv.org/abs/2203.12555)；[代码](https://github.com/microsoft/table-transformer)

[D1] **PubTables-v2 dataset.** [Hugging Face](https://huggingface.co/datasets/kensho/PubTables-v2)

[D2] **BioMike/table-continuation-dataset.** [Hugging Face](https://huggingface.co/datasets/BioMike/table-continuation-dataset)

[D3] **hwyin04/table-cross-page.** [Hugging Face](https://huggingface.co/datasets/hwyin04/table-cross-page)
