# 表格与跨页表格提取研究执行文档

## 1. 研究目标

目标是研究端到端表格提取（End-to-End Table Extraction）与跨页表格重建，在 PubTables-v2 的严格内容感知指标 `Acc-Con` 上建立可复现的改进。

### 1.1 主目标

| 任务 | 基线 | 目标 | 说明 |
|---|---:|---:|---|
| 裁剪单表恢复 | TATR-v1.2-Pub + PDF 原生文字：0.6831 | >= 0.72 | 长表、宽表；结构与单元格内容必须全对 |
| 单页全表提取 | POTATR + PDF 原生文字：0.6454 | >= 0.68 | 页面可能有多张表，包含检测、结构和内容恢复 |
| 全文档表格提取 | Claude Opus 4.6：0.2452 | >= 0.30 | 含多页、多表、无表页和跨页表 |

### 1.2 指标定义与公平比较

`Acc-Con` 是内容感知的严格表格完全匹配指标。预测结果只有在表格拓扑、行列、合并单元格和单元格内容均与标注一致时才计为正确；在页面和文档任务中，还要求预测表与真值表正确对应。

必须分开报告两条赛道：

| 赛道 | 输入 | 可比较对象 | 目标 |
|---|---|---|---|
| PDF-text-assisted | 页面图像 + PDF 原生 word/token、坐标、字体等 | TATR/POTATR + DT | 用于可解析 PDF 的最强效果 |
| image-only | 页面或表格图像 | Claude、Gemini、dots.ocr 等 | 用于扫描件、图片和视觉端到端能力 |

不得把使用 PDF 原生文字的结果与纯图像结果混合比较。前者绕过了 OCR 文字识别错误，后者才反映扫描件场景的完整端到端能力。

## 2. 已有研究与对比模型

本章只引用论文、技术报告、官方模型卡或官方代码仓库，不使用第三方博客。表中的来源分为两种：方法本身有独立论文时链接原论文；若模型没有独立论文，或该行数值来自统一基准测试，则明确链接官方模型卡、官方仓库或 PubTables-v2 评测论文。一个来源链接不能自动证明模型具备严格完全匹配能力，具体指标仍以“已报告结果”和 2.5 节的统一评测为准。

### 2.1 结构模型与混合式表格提取

这类模型显式预测表格、行、列、单元格和表头等结构对象，通常不负责 OCR。内容恢复依赖 PDF 原生文字或外部 OCR，再根据文字坐标与预测单元格进行匹配。其优势是结构输出可解释、可约束，在 PDF-text-assisted 赛道上通常具有最高的严格完全匹配率。

| 模型 | 论文/官方来源 | 核心方法 | 输入与输出 | 优势 | 局限 | 在本研究中的角色 |
|---|---|---|---|---|---|---|
| TATR / Table Transformer | [论文：PubTables-1M](https://arxiv.org/abs/2110.00061) | 基于 DETR 的对象检测式表格模型，分别训练表格检测与结构识别；结构模型预测行、列、表头、投影行和合并单元格等对象 | 输入裁剪表图像；输出结构对象及 bbox；文字由 DT 或 OCR 提供 | 结构明确、推理成本较低；PubTables-1M 上的经典强基线 | 本身不识别文字；通常需要先裁剪表；跨页关系不在模型范围内 | 单表结构主基线 |
| TATR-v1.1-Pub | [论文：PubTables-1M](https://arxiv.org/abs/2110.00061)；[官方模型卡](https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-pub) | 使用 PubTables-1M 训练的公开 TATR 版本 | 同 TATR | 数据规模大、结果稳定、便于复现 | 对极长、极宽和复杂表格的覆盖有限 | 复现基线和初始化权重 |
| TATR-v1.2-Pub | [论文/评测：PubTables-v2](https://arxiv.org/html/2512.10888v3) | 在 TATR-v1.1-Pub 基础上，使用 PubTables-v2 Cropped Tables 中的长表、宽表继续微调 | 裁剪表图像 + DT/OCR；输出规范化结构和内容 | PubTables-v2 裁剪表任务上最强公开严格基线；`+ DT` 的 `Acc-Con=0.6831` | 高分依赖 PDF 原生文字；使用实际 OCR 时严格完全匹配率显著下降 | 必须超过的裁剪单表基线 |
| POTATR / Page-Object Table Transformer | [论文：PubTables-v2](https://arxiv.org/html/2512.10888v3) | 将 TATR 扩展到全页对象层级，在页面中联合检测表格、表结构、表题和表脚注，并预测对象间层级关系 | 输入完整页面；输出一个或多个表及相关页面对象 | 不需要预先裁剪表；适合页面内多表和上下文建模；参数规模较小 | 不自带 OCR；原始模型没有完整的跨页实体关系建模 | 必须超过的单页基线，也是 DTGT 页面检测器的主要起点 |
| TableFormer | [论文：TableFormer](https://openaccess.thecvf.com/content/CVPR2022/html/Nassar_TableFormer_Table_Structure_Understanding_With_Transformers_CVPR_2022_paper.html) | 编码页面或表格图像，通过 Transformer 解码结构 token，并预测单元格位置以对齐文本 | 输入表格图像；输出 HTML 类结构与单元格 bbox | 结构生成与单元格定位结合，适合端到端管线 | 自回归结构输出可能产生非法或不一致序列；跨页能力有限 | 作为“序列生成式 TSR”对照 |

其中 `DT` 表示 Direct Text，即直接从 PDF 内容层提取 word/token 和坐标。`+ DT` 不是纯图像端到端 OCR，必须与 image-only 结果分开报告。

### 2.2 开源端到端文档视觉模型

这类模型从页面或表格图像直接生成 DocTags、HTML、Markdown 等结构化文本，同时承担视觉识别、OCR、阅读顺序和表格序列化。它们适合扫描件，但严格 `Acc-Con` 容易受字符错误和输出格式漂移影响。

| 模型 | 论文/官方来源 | 类型与规模 | 表格输出方式 | 特点 | 主要局限 | 建议用途 |
|---|---|---|---|---|---|---|
| SmolDocling-256M | [论文：SmolDocling](https://arxiv.org/abs/2503.11576) | 约 256M 参数的轻量文档 VLM | 生成 DocTags，再转换为 HTML | 体量小、可本地部署、适合低成本实验 | 复杂长表和整页解析能力有限，输出可能无法完整解析 | 小模型下界、效率基线 |
| GraniteDocling-258M | [官方模型卡](https://huggingface.co/ibm-granite/granite-docling-258M) | SmolDocling 的约 258M 参数后继模型 | DocTags -> HTML | 相比 SmolDocling 页面解析更稳定 | 仍受生成长度、复杂 span 和文字识别限制 | 轻量文档专用 VLM 基线 |
| Qwen2.5-VL-3B | [技术报告：Qwen2.5-VL](https://arxiv.org/abs/2502.13923) | 约 3B 参数通用视觉语言模型 | 按提示输出 QwenVL HTML 或结构化文本 | 通用视觉语义能力强，便于指令微调 | 非专门结构解码器，表格拓扑和严格格式稳定性不足 | 通用 VLM 基线、LoRA 微调候选 |
| Granite-Vision-3.2-2B | [官方模型卡](https://huggingface.co/ibm-granite/granite-vision-3.2-2b) | 约 2B 参数通用文档视觉模型 | 生成结构化文档内容 | 兼顾通用视觉与文档任务 | 严格单元格结构和内容完全匹配仍较弱 | 中等规模开源 VLM 对照 |
| DeepSeek-OCR | [论文：DeepSeek-OCR](https://arxiv.org/abs/2510.18234)；[官方仓库](https://github.com/deepseek-ai/DeepSeek-OCR) | 生成式 OCR/文档解析模型 | 从页面图像生成文本和表格结构 | OCR 与复杂页面理解能力较强 | 生成式文字和结构错误会共同降低 exact match | image-only OCR 基线 |
| DeepSeek-OCR 2 | [论文：DeepSeek-OCR 2](https://arxiv.org/abs/2601.20552)；[官方仓库](https://github.com/deepseek-ai/DeepSeek-OCR) | DeepSeek-OCR 的后继版本 | 同上 | 在部分文档级任务上优于前代 | 不保证合法网格和内容全等 | image-only 强基线 |
| dots.ocr | [论文：dots.ocr](https://arxiv.org/abs/2507.15530)；[官方仓库](https://github.com/rednote-hilab/dots.ocr) | 面向 PDF/页面转 Markdown/HTML 的端到端文档解析模型 | 页面图像直接生成结构化文档 | 在 PubTables-v2 的开源页面模型中表现较强；可接跨页合并模块 | 默认逐页处理；简单纵向合并虽然提升 TEDS，但未提升 `Acc-Con` | 开源端到端主基线、跨页消融基线 |
| OCRFlux-3B | [官方仓库](https://github.com/chatdoc-com/OCRFlux)（未确认独立论文） | 约 3B 参数的页面 OCR 与文档后处理系统 | 页面转 Markdown，再检测并重建跨页表/段落 | 显式支持跨页表重建；提供中英文跨页测试集 | 跨页重建主要报告 TEDS，未报告与 `Acc-Con` 等价的整表严格指标 | image-only 跨页系统对照 |
| PaddleOCR-VL-1.5 | [技术报告：PaddleOCR-VL-1.5](https://arxiv.org/html/2601.21957v1) | 约 0.9B 参数文档 VLM，配合版面模型和后处理管线 | 页面元素识别后输出 Markdown/JSON | 模型紧凑，覆盖文字、表格、公式、印章和跨页表 | 公开论文没有跨页表专属 exact-match 结果 | 工业化 pipeline 对照 |
| MonkeyOCR v1.5 | [论文：MonkeyOCR v1.5](https://arxiv.org/html/2511.10390v2) | 复杂文档解析 VLM/系统 | 页面解析并进行跨页和跨栏重建 | 支持嵌图、复杂表和跨页重建 | 跨页部分主要是案例展示，缺少统一严格指标 | 定性对照和复杂版式测试 |
| LingDT-VL-OCR | [论文：LingDT-VL-OCR](https://arxiv.org/html/2603.11044v2) | 面向长金融文档的结构感知 OCR 系统 | 分页解析后使用自适应策略拼接跨页表 | 强调金融长文档、单元格定位与可审计性 | 跨页表使用自建集和 TEDS，不能直接与 PubTables-v2 `Acc-Con` 横比 | 金融领域外部验证基线 |

### 2.3 闭源前沿多模态模型

闭源模型可一次接收多页图像并利用全文档上下文，不需要显式的续表分类器，但推理成本、版本稳定性和可复现性较弱。

| 模型 | 论文/结果来源 | 使用方式 | 主要特点 | 在本研究中的角色 |
|---|---|---|---|---|
| Claude Opus 4.6 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) | 将完整文档页面一次输入并要求输出全部表格 | PubTables-v2 Full Documents 上 `Acc-Con=0.2452`，是当前必须超过的文档级严格基线 | 全文档主基线、教师模型候选 |
| GPT-5.4 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) | 全文档多图输入并生成表格结构与内容 | 全文档上下文强，但严格输出受 OCR 和生成格式影响 | 闭源横向对照 |
| Gemini 3.1 Pro | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) | 全文档多图输入并生成全部表格 | PubTables-v2 的结构相似度表现强，在裁剪表和单页任务上也有较强 VLM 结果 | 闭源横向对照和效果上界参考 |

闭源模型的结果应固定模型版本、提示词、图像分辨率、解码配置和测试时间；不得将后续版本结果直接覆盖原基线。

### 2.4 跨页关系与拼接专用方法

| 方法 | 论文/官方来源 | 输入 | 核心方法 | 已报告结果 | 与本研究的关系 |
|---|---|---|---|---|---|
| PubTables-v2 ViT-B/16 续表分类器 | [论文：PubTables-v2](https://arxiv.org/html/2512.10888v3)；[ViT 架构论文](https://arxiv.org/abs/2010.11929) | 两张相邻页面图像横向拼接 | 二分类判断前页最后一张表是否延续到后页 | F1=0.991、AUC=0.996 | 续表判断强基线；不能代表合并后的整表正确率 |
| dots.ocr + ViT merging | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3)；[dots.ocr 论文](https://arxiv.org/abs/2507.15530) | 逐页 dots.ocr 输出 + ViT 续表结果 | 预测续表且列数相同后直接纵向拼接 | TEDS 和 GriTS 上升，但 `Acc-Con` 仍为 0.1180 | 必须超过的简单拼接基线 |
| OCRFlux 跨页合并 | [官方仓库](https://github.com/chatdoc-com/OCRFlux)（未确认独立论文） | 相邻页 Markdown 元素和表格片段 | 先定位需合并元素，再由模型重建完整表 | 合并检测 Accuracy=0.986；表格合并 TEDS=0.950 | 跨页检测和重建对照；需在 PubTables-v2 上重新评测 `Acc-Con` |
| VCCT | [论文：VCCT](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6811737) | 电力故障报告中的相邻页表格 | 表头检测、边框分析、前序页和文档上下文融合 | Cross-page structural integrity=82.0% | 行业领域专用对照；指标不等价于内容 exact match |

### 2.5 PubTables-v2 上的直接可比结果

以下结果用于确定实验下界和主对照。数值均为内容感知严格指标 `Acc-Con`；不同输入赛道不能混为同一排行榜。

| 模型 | 输入赛道 | 裁剪单表 | 单页 | 全文档 | 结果来源 |
|---|---|---:|---:|---:|---|
| TATR-v1.2-Pub + DT | PDF-text-assisted | **0.6831** | - | - | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| POTATR + DT | PDF-text-assisted | - | **0.6454** | - | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| TATR-v1.2-Pub + docTR OCR | image + external OCR | 0.0191 | - | - | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| POTATR + docTR OCR | image + external OCR | - | 0.0683 | - | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| SmolDocling-256M | image-only | 0.0250 | 0.0298 | 0.0335 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| GraniteDocling-258M | image-only | 0.0555 | 0.0829 | 0.0728 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| Qwen2.5-VL-3B | image-only | 0.0064 | 0.0619 | 0.0452 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| Granite-Vision-3.2-2B | image-only | 0.0067 | 0.0331 | 0.0218 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| DeepSeek-OCR | image-only | 0.0264 | 0.1671 | 0.0921 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| DeepSeek-OCR 2 | image-only | 0.0294 | 0.1120 | 0.0933 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| dots.ocr | image-only | 0.0566 | 0.1872 | 0.1180 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| Claude Opus 4.6 | image-only，多页上下文 | 0.1060 | 0.2713 | **0.2452** | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| GPT-5.4 | image-only，多页上下文 | 0.0988 | 0.2074 | 0.1636 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |
| Gemini 3.1 Pro | image-only，多页上下文 | **0.1613** | **0.3524** | 0.2025 | [PubTables-v2 评测论文](https://arxiv.org/html/2512.10888v3) |

这张表揭示两个关键事实：第一，PDF 原生文字能显著提高严格内容完全匹配率；第二，在 image-only 赛道中，OCR 字符错误、结构错误和序列化错误会相乘，导致 `Acc-Con` 远低于 TEDS/GriTS。

### 2.6 最低对比实验集合

为控制算力与复现成本，正式论文至少保留以下对比：

1. [`TATR-v1.2-Pub + DT`](https://arxiv.org/html/2512.10888v3)：裁剪单表 PDF-text-assisted 主基线。
2. [`POTATR + DT`](https://arxiv.org/html/2512.10888v3)：单页 PDF-text-assisted 主基线。
3. [`dots.ocr`](https://arxiv.org/abs/2507.15530)：开源 image-only 页面和文档主基线。
4. [`Qwen2.5-VL-3B`](https://arxiv.org/abs/2502.13923) 或同规模开源 VLM：通用 VLM 微调基线。
5. [`Claude Opus 4.6`](https://arxiv.org/html/2512.10888v3)：全文档闭源主基线，引用 PubTables-v2 公开评测结果；若重新测试需固定版本和提示词。
6. [`ViT-B/16 + 直接纵向拼接`](https://arxiv.org/html/2512.10888v3)：跨页两阶段基线。
7. DTGT 的无关系图版本、无文本版本和无约束解码版本：验证各创新模块的实际贡献。

## 3. 核心假设

1. 严格完全匹配的主要瓶颈不是表框检测，而是文字 token 的单元格归属、行列拓扑、合并单元格和跨页断裂单元格。
2. 将视觉区域、PDF 文字 token 和表格结构联合建模，优于“先预测结构、再把文字后贴进去”的串行方案。
3. 跨页续表不应被视为孤立二分类，而应作为文档内表格片段之间的关系图预测问题。
4. 对续表的简单纵向拼接可以提升 TEDS，却不一定提升 `Acc-Con`；最终必须对合并后的全表重新解码和校验。

## 4. 研究路线

### 4.1 主路线：文本感知的文档表格图模型

建议实现一个暂名为 `Document Table Graph Transformer`（DTGT）的模型。模型不直接自回归生成 HTML，而是显式预测可验证的结构对象与关系。

```text
PDF 页面图像 + word/token 及坐标
              |
              v
页面级对象检测：表格 / 标题 / 脚注 / 文字块
              |
              v
表内视觉-文本联合结构解析：行 / 列 / 单元格 / span / 表头
              |
              v
文档级表格片段图：续表、标题归属、脚注归属
              |
              v
跨页联合重解码、规则校验、规范化 HTML/JSON 输出
```

### 4.2 为什么不以大 VLM 直接生成 HTML 为主线

纯 VLM 适合 image-only 赛道和复杂扫描件，但 `Acc-Con` 会受到微小字符误差、HTML 格式漂移、行列错位和幻觉影响。建议将 VLM 作为对照、教师模型或困难样本标注辅助，而非主系统唯一输出层。

## 5. 模型设计

### 5.1 页面级对象检测器

在 POTATR 的页面级思想上扩展，检测以下对象：

- 表格框与表格片段。
- 表题、表脚注和页眉页脚。
- 表内文字块与表外说明文字。

候选实现：DETR 风格对象查询 + 多尺度视觉主干。保留端到端匈牙利匹配训练，但将标题、脚注与表格关系作为辅助监督。

### 5.2 表内视觉-文本联合结构解析器

输入为表格区域的视觉特征与 word token 序列。每个 token 至少包含文本、bbox、页号、字号、字体样式和阅读顺序；image-only 赛道则使用 OCR token 替代。

输出包括：

- 行边界、列边界与表格网格。
- 单元格的行列区间及 `rowspan/colspan`。
- 单元格角色：列头、行头、数据单元格、投影行等。
- token-to-cell 归属和单元格内 token 排序。

推荐结构：视觉编码器、文本布局编码器、交叉注意力层，以及用于单元格和关系预测的图解码器。视觉编码器负责边线、空白、对齐与合并单元格；文本布局编码器负责内容连续性和表头语义。

### 5.3 约束解码器与规范化器

在输出阶段加入硬约束，避免产生无法组成合法表格的局部预测：

- 一个文字 token 最多归属于一个单元格。
- 单元格对应连续的行区间和列区间。
- 单元格覆盖集合不得重叠，且完整覆盖预测网格。
- 合并单元格、表头和文本顺序按照 PubTables 的 canonicalization 规范输出。

将预测结果转换为规范化 HTML 和 JSON，统一空白、连字符、换行和页码噪声处理后再评测。规范化规则必须在训练、验证和测试中固定。

### 5.4 文档级跨页关系图

将每个页面中的表格片段视为节点，针对相邻或近邻页面构造候选边。边类型至少包括：

- `continues_to`：下一页是同一张表的纵向续表。
- `horizontal_split_to`：宽表的横向拆分片段。
- `caption_of` 和 `footer_of`：表题、脚注归属。

边分类器应同时使用：

- 表格在页面中的位置，例如前页靠近页底、后页靠近页顶。
- 列数、列边界和列宽签名。
- 重复表头的语义和结构相似度。
- 前页表尾与后页表首的 token、字号、边线和背景特征。
- 表题编号、脚注标识及文档上下文。

跨页表被判定后，不直接拼接 HTML。将涉及页面的表格 token、行列候选和视觉特征输入联合重解码器，输出一张完整表，显式处理重复表头、跨页断裂单元格和跨页合并单元格。

## 6. 数据与训练

### 6.1 数据使用顺序

| 阶段 | 数据 | 目标 |
|---|---|---|
| 预训练 | PubTables-1M、PubTabNet、FinTabNet | 通用表格检测、网格结构和单元格 span |
| 单表微调 | PubTables-v2 Cropped Tables | 长表、宽表和复杂结构 |
| 页面微调 | PubTables-v2 Single Pages | 页面检测、表题/脚注、页面内多表 |
| 文档微调 | PubTables-v2 Full Documents | 续表关系和全文档重建 |
| 领域适配 | 目标行业的人工标注文档 | 目标版式、语言和表格语义 |

所有切分必须以文档为单位。不得将同一文档的不同页面、同一表的不同片段或同一 PDF 的相似版本同时分配到训练与测试集。

### 6.2 合成跨页增强

从高质量单页表格或 HTML 表格生成受控的跨页样本：

- 随机行分页与不同页边距。
- 重复、缩略或省略表头。
- 表脚注、页眉页脚和正文插入。
- 单元格内断行和跨页续写。
- 相邻独立表格作为 hard negative。
- 宽表横向分页和多栏论文版式。

合成数据只用于预训练或难例增强；最终主结果必须在天然 PDF 跨页表上评测。

## 7. 损失函数与优化目标

| 模块 | 监督目标 |
|---|---|
| 页面对象检测 | bbox、类别、表题/脚注关系 |
| 网格结构 | 行列边界、cell span、表头角色、单元格邻接关系 |
| 内容归属 | word-to-cell assignment、单元格内排序 |
| 跨页关系 | 续表边分类、hard-negative 对比损失 |
| 联合表重建 | 合并后行列/单元格/文本的结构化损失 |

`Acc-Con` 本身不可直接微分。训练中使用“结构正确、内容正确、关系正确”三个必要条件的联合代理损失，并始终以验证集 `Acc-Con` 作为模型选择主指标。

## 8. 实验设计

### 8.1 必做主实验

1. Cropped Tables：报告 `Acc-Top`、`Acc-Con`、GriTS、TEDS。
2. Single Pages：报告同一组指标，并给出检测漏检、结构错误、内容错误的分解。
3. Full Documents：报告同一组指标及跨页表子集指标。
4. 分别报告 PDF-text-assisted 和 image-only 两条赛道。

### 8.2 必做消融

| 消融项 | 要回答的问题 |
|---|---|
| 去除 PDF token | 原生文本对严格正确率贡献多少？ |
| 去除视觉特征 | 仅布局和文本能否恢复结构？ |
| 串行文字后贴 vs 联合解析 | 联合建模是否提升 token-to-cell 准确率？ |
| 无硬约束 vs 有硬约束 | 结构合法化是否提升 exact match？ |
| 二分类续表 + 直接拼接 vs 图推理 + 联合重解码 | 跨页重解码是否真正提升 `Acc-Con`？ |
| 无 hard negative vs 有 hard negative | 相邻独立表误拼接是否下降？ |

### 8.3 错误分析口径

每个 `Acc-Con` 失败样本必须归入一个主因：

- 表格漏检或误检。
- 行列边界错误。
- `rowspan/colspan` 错误。
- 表头角色错误。
- token 漏分配、错分配或顺序错误。
- 文字识别错误。
- 续表漏连、误连。
- 重复表头、脚注或跨页断裂单元格处理错误。

## 9. 里程碑与验收

| 阶段 | 产出 | 验收标准 |
|---|---|---|
| M0：评测复现 | PubTables-v2 评测脚本和基线复现 | 重现 TATR/POTATR、dots.ocr 的公开量级结果 |
| M1：单表结构 | 文本感知单表模型 | Cropped Tables `Acc-Con >= 0.70` |
| M2：单页提取 | 页面检测和结构联合模型 | Single Pages `Acc-Con >= 0.68` |
| M3：跨页关系 | 续表图模型和联合重解码 | 跨页子集 `Acc-Con` 高于直接拼接基线 |
| M4：全文档 | 文档级完整系统 | Full Documents `Acc-Con >= 0.30` |
| M5：目标域验证 | 人工标注的领域测试集 | 给出业务场景的 exact match、字段级准确率和人工复核成本 |

## 10. 主要风险与应对

| 风险 | 应对 |
|---|---|
| PDF 原生文字质量高，造成 image-only 结论失真 | 双赛道独立报告；扫描件单独设测试集 |
| 文档级显存和延迟过高 | 候选边只在相邻/近邻页构造；仅对候选续表局部联合解码 |
| 精确指标长期不提升 | 按错误类型定位；优先优化 token 分配和结构约束，不盲目放大模型 |
| 合成跨页数据与真实文档差异大 | 合成数据仅作增强；以自然跨页表的文档级测试为最终结论 |
| 基准泄漏 | 按 PDF 文档 ID 切分；记录数据来源和重叠检查 |

## 11. 最终论文或报告应回答的问题

1. 联合视觉-文本结构解析是否超过 TATR/POTATR 的严格单表和单页基线？
2. 相比“续表判定后直接拼接”，文档图推理和联合重解码是否提升跨页表 `Acc-Con`？
3. 改进主要来自 PDF 原生文字、结构模型、跨页关系模型还是约束解码？
4. 在 image-only 条件下，方法相对端到端 VLM 的收益与成本如何？
5. 在不同版式、语言、扫描质量及领域文档上，严格全对率是否稳定？
