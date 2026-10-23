# 跨页表格片段拼接与完整结构恢复：已有方法、模型、指标和结果

日期：2026-09-25（Asia/Shanghai）

调研问题：给定属于同一张跨页表格的两个片段，如何将它们拼接并恢复为结构和内容完整的逻辑表格？已有研究使用什么方法和模型，采用什么评价指标，结果是多少？

## 1. 结论摘要

现有研究尚未形成一个统一、可直接横向比较的“跨页表格片段恢复”基准。相关工作实际评测了三类不同问题：

1. **续接判断**：判断相邻页面中的两个表格是否属于同一张逻辑表；
2. **纯片段拼接**：已知两个片段需要合并，生成合并后的完整表格；
3. **端到端文档恢复**：从完整页面或文档开始，依次完成页面解析、续接判断和跨页合并。

截至本次核验：

- 最接近“已知两个片段后恢复完整表格”的公开结果来自 **OCRFlux-3B**：在 9,064 对人为拆分的 PubTabNet HTML 表格片段上，合并后平均 `TEDS=0.950`。但输入是已经识别好的 HTML 片段，不是两个自然跨页表格图像，且没有报告严格整表完全匹配率。
- **MinerU-Popo** 是本报告上一版遗漏的直接相关工作：它把跨页表恢复作为 OCR 输出的后处理，先判断片段是否续接，再逐列判断分页边界处的单元格是否应语义合并；其表格任务报告局部 merge-method prediction accuracy `92.7%`。该数字是边界决策准确率，不是整表 `Acc-Con` 或 TEDS。
- 在自然跨页完整文档上，**POTATR + ViT-B/16 continuation classifier + vertical concatenation** 在 PubTables-v2 Full Documents 上报告 `GriTS-Con=0.8269`、`Acc-Con=0.2176`、`TEDS=0.7824`。这包含页面提取和合并的联合误差，不是纯拼接模块的成绩。
- **LingDT-VL-OCR** 在 472 张金融跨页表格上使用逐页 VLM 解析和启发式拼接，报告平均 `TEDS=0.8915`，但未报告 exact match，也未公开同一跨页子集上的完整对照结果。
- PubTables-v2 的 ViT-B/16 续接分类达到 `F1=0.991`，说明“是否续接”已相对容易；端到端 `Acc-Con` 仍低，说明真正未充分解决的是列对应、重复表头、跨页拆分行/单元格和完整结构重建。

因此，目前没有找到同时满足以下条件的成熟公开研究：**输入两个真实跨页表格图像片段、隔离上游页面识别误差、公开模型与数据，并用严格结构/内容完全匹配率评价最终完整表格。**

## 2. 研究与结果总表

| 研究 | 实际任务与输入 | 模型或方法 | 数据 | 指标 | 结果 | 与目标任务的关系 |
| --- | --- | --- | --- | --- | ---: | --- |
| OCRFlux-3B：表格合并 | 两个已识别的 HTML 表格片段，生成完整 HTML 表格 | 由 Qwen2.5-VL-3B-Instruct 微调的 OCRFlux-3B，以生成方式重建表格 | OCRFlux-pubtabnet-cross：9,064 对人为拆分的 PubTabNet 表格 | 平均 TEDS | simple `0.965`；complex `0.935`；overall **`0.950`** | 最接近纯拼接，但不是自然跨页图片输入，也没有 exact match |
| OCRFlux-3B：跨页元素检测 | 相邻两页 Markdown 元素列表，输出需要合并的元素索引 | OCRFlux-3B 生成合并索引 | OCRFlux-bench-cross：1,000 个人工复核的中英文相邻页样本 | Precision、Recall、F1、Accuracy | `P=0.996`、`R=0.976`、`F1=0.986`、`Acc=0.986` | 只评价找没找对待合并元素，不评价最终表格结构 |
| PubTables-v2 continuation | 两张连续完整页面图像，判断首页末表是否延续至下一页 | 横向拼接双页图像；ResNet-50 或 ViT-B/16 二分类 | 9,866 个正页对、5,964 个负页对 | Recall、Precision、F1、AUC | ViT-B/16：`R=0.995`、`P=0.987`、`F1=0.991`、`AUC=0.996` | 严格续接判断，不回答如何对齐和拼接 |
| PubTables-v2 dots.ocr + merging | 完整页面逐页解析后进行跨页合并 | dots.ocr + ViT-B/16；续接为正且列数一致时纵向拼接 | PubTables-v2 Full Documents | GriTS、Acc、TEDS | `GriTS-Con=0.6844`、`Acc-Con=0.1180`、`TEDS=0.7141` | 自然跨页端到端结果；包含页面解析误差 |
| POTATR + merging | 完整页面逐页解析后进行跨页合并 | 29M POTATR 页面 image-to-graph 模型 + 86M ViT-B/16 continuation classifier + 纵向拼接 | PubTables-v2 Full Documents | GriTS、Acc、TEDS | `GriTS-Top=0.8507`、`GriTS-Con=0.8269`、`Acc-Top=0.4234`、`Acc-Con=0.2176`、`TEDS-S=0.8058`、`TEDS=0.7824` | 当前较明确的轻量端到端跨页流水线；未显式建模列对应和拆分行 |
| dots.ocr + merging（POTATR论文版本） | 与上一项相同 | dots.ocr + ViT-B/16 + 纵向拼接 | PubTables-v2 Full Documents | GriTS、Acc、TEDS | `GriTS-Top=0.7772`、`GriTS-Con=0.7495`、`Acc-Top=0.5059`、`Acc-Con=0.1180`、`TEDS-S=0.8022`、`TEDS=0.7731` | 与 PubTables-v2 原论文同名设置数值不同，需按论文版本分别引用 |
| LingDT-VL-OCR | 金融文档逐页解析后合并真实跨页表格 | 自研 VLM + adaptive heuristic-based splicing | FinDocBench：1,044 张表，其中 472 张跨至少两页 | 跨页拼接 TEDS | **`0.8915`** | 自然跨页表专用结果，但数据、模型和协议不能与 PubTables-v2直接横比 |
| VCCT | 电力故障报告中的跨页表识别与上下文恢复 | 表头检测、边框分析、跨页上下文融合，另结合 YOLOv11 手写检测 | 私有约 300 张跨页表格 | 作者定义 Structural Integrity Rate（SIR） | `77.2% → 82.0%`；另报 cell accuracy `86.3%` | 私有领域、小规模、非标准指标且为 SSRN 预印本，仅作补充证据 |
| MinerU-Popo | OCR/文档解析输出的跨页表格后处理；先判断续接，再逐列判断边界单元格是否合并 | 轻量 `4B` post-processing VLM；任务化输入与动态 chunking | PostDocBench；表格子任务约 `1,317` 个 cell-level merge units | merge-method prediction accuracy | **`92.7%`** | 直接覆盖局部表格截断恢复，但不是整表 exact match；尚未在 PubTables-v2 复测 |
| BERT-Based Semantic Matching | 判断财务 PDF 表格片段是否具有续接关系并合并 | 表头/语义特征 + BERT 语义匹配 | 私有财务 PDF | 分类 Precision/Recall/F1 | 未找到可公开核验的完整表格重建指标 | 属于续接匹配，不足以回答整表恢复效果 |

## 3. 各项研究的论文、方法与结果

### 3.1 OCRFlux-3B

**论文/公开来源状态：**截至 2026-09-25，未找到 OCRFlux 对应的独立正式论文或 arXiv 论文。可核验的一手来源是官方开源仓库、模型卡和公开数据集，引用时不能把仓库误写成论文。

- 官方项目：**OCRFlux**，<https://github.com/chatdoc-com/OCRFlux>
- 模型卡：**ChatDOC/OCRFlux-3B**，<https://huggingface.co/ChatDOC/OCRFlux-3B>
- 纯表格合并数据：**OCRFlux-pubtabnet-cross**，<https://huggingface.co/datasets/ChatDOC/OCRFlux-pubtabnet-cross>
- 跨页元素检测数据：**OCRFlux-bench-cross**，<https://huggingface.co/datasets/ChatDOC/OCRFlux-bench-cross>

OCRFlux-3B 是从 `Qwen/Qwen2.5-VL-3B-Instruct` 微调得到的文档 VLM。完整流水线先把页面转换为 Markdown，再判断相邻页中的表格或段落元素是否需要合并；对于表格，模型接收两个拆分后的 HTML 片段并生成完整、结构化的 HTML 表格。

其两项跨页结果必须分开解释：

- `OCRFlux-bench-cross` 的 `F1=0.986`、`Accuracy=0.986` 表示模型是否同时判断对“需要合并与否”和待合并元素索引；
- `OCRFlux-pubtabnet-cross` 的总体 `TEDS=0.950` 才评价合并表与真值表的结构和内容相似度。

局限是纯合并集来自 PubTabNet 完整表格的构造性拆分，字段为 `table_fragment_1`、`table_fragment_2` 和 `gt_table`。它没有覆盖从自然跨页图像到片段结构的识别误差，也没有报告整表 exact match。

### 3.2 PubTables-v2：续接分类与 dots.ocr 合并

**论文：**Ben Smock 等，**PubTables-v2: A New Large-Scale Dataset for Full-Page and Multi-Page Table Extraction**，arXiv:2512.10888。

论文链接：<https://arxiv.org/abs/2512.10888>

HTML：<https://arxiv.org/html/2512.10888>

论文将两张连续页面图像横向拼接，训练 ResNet-50 和 ViT-B/16 二分类器，判断第一页最后一张表是否继续到第二页。ViT-B/16 得到：

- Recall `0.995`
- Precision `0.987`
- F1 `0.991`
- AUC `0.996`

随后，论文把该分类器与 dots.ocr 页面级输出结合：只有当续接分类为正且相邻片段列数相同时，才进行纵向拼接。结果从未合并的 `GriTS-Con=0.5768`、`TEDS=0.5876` 提升到 `GriTS-Con=0.6844`、`TEDS=0.7141`，但 `Acc-Con` 仍为 `0.1180`。

这说明续接分类和简单拼接能显著改善软相似度，但没有提高结构和内容完全正确的整表比例。

**2026-10-20 已知跨页片段的隔离实验范围（计划中，非已完成评测）：**固定 PubTables-v2 Full Documents/val 的逻辑表 `parts` 可提供跨页表身份、每片段 `page_num`、页面 JPEG 上的 `bbox` 与整表 HTML；这些 `bbox` 可用于从原页在新目录派生片段图，但 Full Documents 当前本地归档不直接提供逐跨页片段 JPEG，也没有片段内部逐行/逐列的官方真值。另一个集合 `Cropped Tables` 的单表图片不可直接假定是这些 Full Documents 跨页片段。已审计 validation 真实跨不同页表 983 张，见 `docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md`。向模型提供真值片段框、同表分组及顺序后，评测变成 **oracle 检测/关联条件下的片段图识别与整表恢复**，不是完整文档端到端续接评测；必须分开报告。TATR-v1.1-Pub 可先按既有裁剪表结构识别入口尝试片段推理（输入尺度差异需做 smoke），但本身没有跨页合并模块；POTATR 原生是整页提取器，直接喂紧裁剪片段图的效果待核验，且目前无本地权重；`+ DT` 是附加 PDF 词元的独立输入赛道。所有模型要报告整表得分，仍须实现并冻结合并/行列对齐/重复表头/拆分行处理，且不能用 val 的整表真值或片段框调整规则。此处只读核验原有 `gold-cross-page.jsonl`、两个集合的本地路径及 `parts` 字段，没有生成新裁剪图或模型预测。

### 3.3 POTATR + cross-page merging

**论文：**Ben Smock 等，**POTATR: A Lightweight Image-to-Graph Model for Page-Level Table Extraction**，arXiv:2606.09788。

论文链接：<https://arxiv.org/abs/2606.09788>

HTML：<https://arxiv.org/html/2606.09788v1>

POTATR 本身是一个 29M 参数的页面级 image-to-graph 表格提取模型，并不是专门的跨页模型。跨页流水线在 POTATR 页面输出后增加 PubTables-v2 的 ViT-B/16 continuation classifier，并使用简单的纵向合并规则，不重新训练页面模型。

POTATR 论文附录在 PubTables-v2 Full Documents 上报告：

**2026-10-20 输入赛道核验补注：**`POTATR + merging` 表示在逐页结果之后增加 ViT-B/16 续接判断及纵向合并；`POTATR + DT` 表示给 POTATR 页面结构结果分配 PDF 原生文字，论文主表 2 在 Single Pages 上报告它的成绩。两者是不同处理维度，可以组合，不是两个互斥模型。附录 Full Documents 表 5 的 `POTATR + merging` **没有单独注明该行采用 DT 还是哪一种 OCR**；因此不能直接把附录数值归入 `image-only`，也不能认为它就是已验证的 `POTATR + DT + merging`。本项目如复测，应分别固定文字源（OCR/DT）与合并策略；前者分别对应 `image-only + OCR` 与 `PDF-text-assisted`，两赛道结果分开报告，论文对应关系待源码/作者方法核验。依据 <https://arxiv.org/html/2606.09788> §4.3、附录 0.C。

| 设置 | GriTS-Top | GriTS-Con | Acc-Top | Acc-Con | TEDS-S | TEDS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| POTATR，逐页处理 | 0.6973 | 0.6710 | 0.3285 | 0.2038 | 0.6353 | 0.6128 |
| POTATR + merging | **0.8507** | **0.8269** | **0.4234** | **0.2176** | **0.8058** | **0.7824** |
| dots.ocr，逐页处理 | 0.6054 | 0.5768 | 0.3958 | 0.1180 | 0.6179 | 0.5876 |
| dots.ocr + merging | **0.7772** | **0.7495** | **0.5059** | **0.1180** | **0.8022** | **0.7731** |

论文认为 POTATR 的 `GriTS-Con` 从 `0.6710` 提升到 `0.8269`，相当于减少 47.4% 的剩余误差。但 `Acc-Con=0.2176` 仍表示大多数表格没有达到结构与全部内容完全一致。

PubTables-v2 原论文对 dots.ocr + merging 报告 `GriTS-Con=0.6844`、`TEDS=0.7141`，而 POTATR 论文附录报告 `0.7495` 和 `0.7731`。两文没有充分说明造成差异的全部实现或协议变化，因此两组结果应按论文和版本分别引用，不能合并成唯一数值。

### 3.4 LingDT-VL-OCR

**论文：**Siyi Qian 等，**LingDT-VL-OCR: Structure-Aware Document-Level Parsing with Fine-Grained Visual Reference**，arXiv:2603.11044。

论文链接：<https://arxiv.org/abs/2603.11044>

HTML：<https://arxiv.org/html/2603.11044v2>

该工作先使用自研 VLM 解析每页表格片段，再使用 adaptive heuristic-based splicing 合并：

1. 相邻片段列数必须一致；
2. 两个片段之间除页眉、页脚外不能存在其他语义元素；
3. 下一页无表头或表头与前页一致时，删除重复表头，仅追加 `<tbody>`；
4. 下一页表头不同时，保留整个片段，以表达子表头或类别转换。

FinDocBench 包含 1,044 张表，其中 472 张跨至少两页。作者在这 472 张跨页表上报告平均 `TEDS=0.8915`。该指标是在非首页表头被裁剪、片段连接后，与完整真值计算的端到端 TEDS。

由于论文没有报告相同子集上的 exact match，也没有给出其他方法的同协议跨页对照，所以不能把 `0.8915` 解释为 89.15% 表格完全正确，也不能直接宣称为通用 SOTA。

### 3.5 MinerU-Popo

**论文：** **MinerU-Popo: Universal Post-Processing Model for Structured Document Parsing**，arXiv:2605.24973。

论文链接：<https://arxiv.org/abs/2605.24973>

官方仓库：<https://github.com/opendatalab/MinerU-Popo>

MinerU-Popo 不是独立的页面图像表格识别器，而是接收不同 OCR/文档解析器的页面级输出，进行文档级后处理。与本项目最相关的 table truncation recovery 将任务分解为：判断相邻页表格是否属于同一逻辑表，以及对每一列的分页边界单元格判断“保持分开”还是“语义合并”。论文使用 task-oriented data engine、约 `30K` 合成训练数据和轻量 `4B` VLM，并用 dynamic chunking 处理长文档。

论文在 PostDocBench 的表格截断任务上报告 `92.7%` 的 merge-method prediction accuracy；该任务约包含 `1,317` 个 cell-level merge units。这个结果只评价局部边界决策，不能解释为完整逻辑表格的结构或内容 exact match。论文摘要中的 title-hierarchy `TEDS=90.6` 也不是表格恢复指标，不能混用。

它是本项目必须补入的可复现后处理基线，但仍有三个边界：未报告 PubTables-v2 Full Documents 的 `Acc-Con`/`GriTS`/`TEDS`，上游 OCR 和页面结构误差不在该数值中，且合成截断样本与 PubTables-v2 的自然分页分布是否一致待核验。后续应优先审计其输入输出格式、许可证、官方评测脚本，并在固定页面解析输入上做 paired 复测。

### 3.6 MonkeyOCR v1.5 与 PaddleOCR-VL-1.5

**MonkeyOCR v1.5：** <https://arxiv.org/abs/2511.10390>；**PaddleOCR-VL-1.5：** <https://arxiv.org/abs/2601.21957>。

这两项工作应列为“相关但不等价”的通用文档解析系统。MonkeyOCR v1.5 明确提出 `Type-Guided Table Merging`，覆盖三种模式：完整表头重复、无表头续接、分页处拆分行；其描述还包括列 schema 对齐、span 冲突处理和表头 token 归一化。PaddleOCR-VL-1.5 的工程管线也包含 cross-page table merging 的后处理能力。

但当前核验到的论文证据主要是能力对比、方法描述和定性案例，没有找到在 PubTables-v2 或公开跨页专用测试集上报告可复核的 `Acc-Con`、跨页子集 TEDS 或局部 merge accuracy。因此它们不能替代 MinerU-Popo、POTATR 或 OCRFlux 的定量结果，也不能据能力宣称已解决跨页表格恢复。它们值得作为后续 image-only/通用 VLM 基线，但前提是冻结版本、输入输出协议和评测集。

**2026-10-20 版本补查（保留上文原调研结论的时间边界）：**PubTables-v2 论文 arXiv:2512.10888v3（PDF 页眉标注 2026-06-02）在 Full Documents 表 5 中额外列出逐页图像模型 `DeepSeek-OCR 2`，以及整篇文档图像输入的 `Claude Opus 4.6`、`GPT-5.4`、`Gemini 3.1 Pro`。逐页组的分数不自动表示模型本身完成了跨页合并；整篇组的闭源 API 结果也不能当作可下载的开源基线。论文的 `PaddleOCR` 行不等于 `PaddleOCR-VL-1.5`，这些新增模型不包含“PaddleOCR-VL-2”。Paddle 官方目前公开命名包含 `PaddleOCR-VL-1.6`；先前四模型计划明确固定 **1.5**，若改测 1.6，须独立审计权重/管线和重定协议，不能静默替换。来源：<https://arxiv.org/abs/2512.10888>、<https://arxiv.org/pdf/2512.10888>、<https://github.com/PaddlePaddle/PaddleOCR>。不同版本表格及数值要独立引用；此处仅补充模型范围，不宣称新增实验已完成。

**同日对用户指认的论文表 3/4 补正：**上段不是用户实际所问的 TATR/POTATR 系列。PubTables-v2 v3 的 `TATR-v1.1-Pub`、`TATR-v1.2-Pub` 属裁剪表结构识别评测（表 3）；`POTATR` 及 `POTATR + DT` 属单页表格提取评测（表 4），其中 `DT` 是 Direct Text（PDF 原生词元辅助），不是新模型权重。`TATR-v1.2-Pub` 是在 1.1 预训练基础上用 PubTables-v2 长/宽裁剪表继续微调，不能把 1.1 权重冒称 1.2；`POTATR` 单独并不解决跨页拼接，完整文档另需续接判别和合并。项目已下载 `checkpoints/tatr-v1.1-pub` 并完成 Cropped Tables/val 的 `PDF-text-assisted` 全量评测；本地没有可确认的 v1.2/POTATR 权重，也未实现其完整文档解析链。论文写未来发布 POTATR 代码/模型并不等于已经找到公开 checkpoint，发布状态后续仍需按官方源核验。依据 <https://arxiv.org/html/2512.10888v3>、<https://arxiv.org/html/2606.09788>、`docs/experiments/2026-09-22-tatr-html-rebuild-rescoring.zh-CN.md`。不得把 Cropped Tables、Single Pages 与 Full Documents 指标直接横比，也不得把 `POTATR + DT` 与 `image-only` 结果混排。

### 3.7 VCCT

**论文：****VCCT: Vocabulary Constraint and Cross-page Context for Table Recognition in Power Grid Fault Reports**，SSRN 预印本。

论文链接：<https://doi.org/10.2139/ssrn.6811737>

SSRN 页面：<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6811737>

该工作面向电力设备故障报告，使用表头检测、边框分析和前序页面上下文来预测并恢复跨页表格，另结合 YOLOv11 处理手写内容。论文在私有约 300 张跨页表格上声称 Structural Integrity Rate 从 `77.2%` 提升到 `82.0%`，并报告 cell accuracy `86.3%`。

SIR 是作者自定义的结构完整性指标，不等价于 PubTables-v2 的 `Acc-Con` 或 TEDS；数据和代码未公开，论文为未同行评审的 SSRN 预印本，因此只能作为领域案例和方法线索，不能作为核心可复现基线。

### 3.8 BERT 语义匹配方法

**论文：****Application of BERT-Based Semantic Matching Algorithm for Cross-Page Table Recognition**，收录于 Springer *Artificial Intelligence in China*。

论文链接：<https://doi.org/10.1007/978-981-99-7545-7_41>

该工作利用表头及语义特征，通过 BERT 判断财务 PDF 中相邻表格是否属于同一张跨页表，再执行合并。它主要解决 continuation matching，没有找到可公开核验的完整结构重建 exact match、TEDS 或 GriTS 结果，因此不能用于回答最终整表恢复达到了什么水平。

## 4. 指标定义与正确解读

### 4.1 TEDS 与 TEDS-S

TEDS 将预测表格和真值表格表示为 HTML 树，根据插入、删除和替换节点的树编辑距离计算归一化相似度，范围为 0 到 1。它同时考虑表格树结构、`rowspan/colspan` 和单元格文字。测试集结果通常是各样本 TEDS 的平均值。

原始定义论文：Xu Zhong、Elaheh ShafieiBavani、Antonio Jimeno Yepes，**Image-based Table Recognition: Data, Model, and Evaluation**，ECCV 2020。

论文链接：<https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123660562.pdf>

`TEDS-S` 或 `TEDS-Struct` 忽略单元格文字，仅比较 HTML 树结构。`TEDS=0.950` 表示平均结构和内容相似度较高，**不表示 95% 的表格完全正确**。

### 4.2 GriTS-Top 与 GriTS-Con

GriTS 将表格表示成二维网格并进行软匹配：

- `GriTS-Top` 主要比较拓扑结构和网格位置；
- `GriTS-Con` 同时比较网格结构和单元格内容。

原始论文：Brandon Smock 等，**GriTS: Grid Table Similarity Metric for Table Structure Recognition**，ICDAR 2023。

论文链接：<https://arxiv.org/abs/2203.12555>

GriTS 可以为部分正确的表格计分，因此高 GriTS 不等于整张表完全正确。

### 4.3 Acc-Top 与 Acc-Con

- `Acc-Top`：表格拓扑必须与真值完全一致；
- `Acc-Con`：拓扑和全部单元格内容都必须完全一致。

在 PubTables-v2 的文档级评测中，一个文档可能包含多张预测表和多张真值表。论文先用 Hungarian algorithm 寻找最优一一匹配，再将 exact match 聚合为集合级指标。因此 Full Documents 的 `Acc-Con` 是页面解析、表格检测、跨页关联、合并和文字识别的联合结果，不是单独拼接模块成功率。

### 4.4 continuation Precision/Recall/F1

这些指标只评价“两个页面片段是否属于同一张表”或“待合并元素索引是否正确”，不评价列如何对应、重复表头如何处理、拆分单元格是否恢复，以及最终表格是否完全正确。

### 4.5 Structural Integrity Rate

VCCT 的 SIR 是作者定义的结构完整性比例。它没有形成通用标准，不能直接与 `Acc-Top`、`Acc-Con`、TEDS 或 GriTS 换算。

## 5. 可比较性边界

以下数字不能直接放在同一排行榜中：

1. OCRFlux `TEDS=0.950` 使用构造性拆分的 HTML 片段，隔离了图片识别过程；
2. LingDT `TEDS=0.8915` 包含自研 VLM 的逐页识别和真实金融跨页拼接；
3. POTATR `Acc-Con=0.2176` 和 `TEDS=0.7824` 是 PubTables-v2 完整文档内所有表格的端到端集合级结果；
4. PubTables-v2 continuation `F1=0.991` 只评价是否续接；
5. VCCT `SIR=82.0%` 是私有数据上的作者自定义结构指标。

这些结果分别回答不同问题。后续论文引用必须同时写明输入条件、数据集、任务范围和指标，不能只摘取最高数字。

## 6. 对本项目研究方向的直接启示

已有证据支持以下判断：

1. **续接分类不是主要技术瓶颈。**PubTables-v2 上 ViT-B/16 的 F1 已达到 0.991。
2. **简单纵向连接能提高平均相似度，但不能保证整表完全正确。**dots.ocr 的软指标提高而 `Acc-Con` 保持 0.1180；POTATR 合并后的 `Acc-Con` 也只有 0.2176。
3. **现有纯拼接实验过于理想化。**OCRFlux 证明生成模型可以很好地合并干净 HTML 片段，但没有覆盖自然图像识别误差和真实分页关系。
4. **值得研究的核心是显式关系和约束重建。**包括列对应、重复表头、拆分行/单元格、子表头变化、多页全局表归属，以及在上游识别有误时生成结构有效的完整表格。
5. **应同时设置后处理隔离轨道与端到端轨道。**MinerU-Popo 提供了“固定上游输出、只评估跨页边界决策”的先例；项目应进一步使用真实页面片段评估列对应、重复表头、拆分行和最终整表恢复。端到端轨道仍应使用固定页面提取器，在 PubTables-v2 Full Documents 上评价完整系统。
6. **通用 VLM 的“支持跨页合并”不能视为定量结果。**MonkeyOCR v1.5 和 PaddleOCR-VL-1.5 说明工程上已有相关模块，但缺少公开、同协议、可复核的专用指标，因此只能作为能力边界和候选基线。

建议项目后续至少报告：

- 续接 Precision/Recall/F1；
- 列匹配、重复表头、拆分行等关系级指标；
- 合并表的 `TEDS-S`、TEDS、`GriTS-Top`、`GriTS-Con`；
- 严格的结构 exact match 和结构+内容 exact match；
- 按跨页数、列数、复杂表头、跨页拆分行/单元格进行分层结果。

## 7. 证据状态

- **已核验的一手证据：**OCRFlux 官方仓库、模型卡和数据卡；PubTables-v2、POTATR、LingDT-VL-OCR、MinerU-Popo、MonkeyOCR v1.5、PaddleOCR-VL-1.5、TEDS、GriTS 原始论文或官方项目页面。
- **低置信度补充证据：**VCCT，原因是未同行评审、私有数据、私有代码和自定义指标。
- **未得到完整结果的相关工作：**BERT-Based Semantic Matching 只核验到续接匹配方向；MonkeyOCR v1.5 与 PaddleOCR-VL-1.5 核验到跨页合并模块和案例，但未找到可复核的专用定量结果。
- **待核验问题：**PubTables-v2 原论文与 POTATR 论文中 dots.ocr + merging 数值差异的具体实现来源；OCRFlux 构造性拆分规则及其与自然跨页错误分布的差异；MinerU-Popo 合成截断与 PubTables-v2 自然分页的分布差异；MonkeyOCR/PaddleOCR-VL 的跨页模块是否有可公开调用的独立评测脚本。

## 8. 参考文献与官方资源

1. Ben Smock et al. **PubTables-v2: A New Large-Scale Dataset for Full-Page and Multi-Page Table Extraction.** <https://arxiv.org/abs/2512.10888>
2. Ben Smock et al. **POTATR: A Lightweight Image-to-Graph Model for Page-Level Table Extraction.** <https://arxiv.org/abs/2606.09788>
3. Siyi Qian et al. **LingDT-VL-OCR: Structure-Aware Document-Level Parsing with Fine-Grained Visual Reference.** <https://arxiv.org/abs/2603.11044>
4. **VCCT: Vocabulary Constraint and Cross-page Context for Table Recognition in Power Grid Fault Reports.** <https://doi.org/10.2139/ssrn.6811737>
5. **Application of BERT-Based Semantic Matching Algorithm for Cross-Page Table Recognition.** <https://doi.org/10.1007/978-981-99-7545-7_41>
6. Xu Zhong, Elaheh ShafieiBavani, Antonio Jimeno Yepes. **Image-based Table Recognition: Data, Model, and Evaluation.** <https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123660562.pdf>
7. Brandon Smock et al. **GriTS: Grid Table Similarity Metric for Table Structure Recognition.** <https://arxiv.org/abs/2203.12555>
8. **OCRFlux official repository.** <https://github.com/chatdoc-com/OCRFlux>
9. **OCRFlux-3B model card.** <https://huggingface.co/ChatDOC/OCRFlux-3B>
10. **OCRFlux-pubtabnet-cross dataset.** <https://huggingface.co/datasets/ChatDOC/OCRFlux-pubtabnet-cross>
11. **MinerU-Popo: Universal Post-Processing Model for Structured Document Parsing.** <https://arxiv.org/abs/2605.24973>
12. **MinerU-Popo official repository.** <https://github.com/opendatalab/MinerU-Popo>
13. **MonkeyOCR v1.5 Technical Report.** <https://arxiv.org/abs/2511.10390>
14. **PaddleOCR-VL-1.5: Towards a Multi-Task 0.9B VLM for Robust In-the-Wild Document Parsing.** <https://arxiv.org/abs/2601.21957>
