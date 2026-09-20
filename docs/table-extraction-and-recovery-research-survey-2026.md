# 当前表格抽取与恢复研究综述

更新日期：2026-08-06

## 0. 范围与结论

本文总结从文档图像或 PDF 中定位表格、恢复表格结构与单元格内容，以及在完整页面、全文档和跨页场景中重建逻辑表格的主要公开研究。覆盖范围包括有代表性的公开数据集、同行评审论文、技术报告、官方模型卡和开源系统；不把仅做表格问答、表格语言建模或数据库表理解的工作纳入表格抽取研究。

“当前所有研究”无法按字面穷尽每一篇应用论文，因此本文采用以下收录标准：

- 对任务定义、数据集、模型范式或公开效果有实质贡献。
- 论文或官方来源能够核验。
- 明确区分表格检测、表格结构识别、内容识别、端到端表格抽取、文档解析和跨页重建。
- 不把不同数据集、输入条件和指标下的最高数值混为一个 SOTA。

截至 2026-08，核心结论是：

1. 单表结构恢复已较成熟，但 GriTS、TEDS 等高分不等于整表完全正确。
2. 使用 PDF 原生文字的结构模型，在严格完全匹配上仍显著强于纯图像 OCR/VLM。
3. 当前研究重点正在从裁剪单表转向整页、多表、全文档和跨页逻辑表重建。
4. PubTables-v2 是目前最系统地统一裁剪表、单页和多页文档严格评测的基准。
5. 跨页“是否续表”已经可以达到很高的分类 F1，但合并后结构与全部内容完全正确仍远未解决。

## 1. 任务定义

| 层级 | 学术术语 | 输入 | 输出 | 是否包含内容 |
|---|---|---|---|---:|
| 表格定位 | Table Detection（TD） | 完整页面 | 表格 bbox/polygon | 否 |
| 结构恢复 | Table Structure Recognition（TSR） | 裁剪表或页面 | 行、列、单元格、表头、rowspan/colspan | 通常否 |
| 内容识别 | Table Content Recognition（TCR） | 单元格/表格图像 | 单元格文字 | 是 |
| 完整表格识别 | Table Recognition（TR） | 表格图像 | HTML/Markdown/CSV/JSON | 是 |
| 端到端抽取 | End-to-End Table Extraction（TE） | 完整页面 | 所有表格的位置、结构与内容 | 是 |
| 文档级抽取 | Full-Document Table Extraction | 多页文档 | 文档中全部逻辑表 | 是 |
| 跨页恢复 | Multi-page/Cross-page Table Reconstruction | 相邻或完整多页文档 | 续表关系及合并后的完整表 | 是 |

## 2. 数据集与基准

### 2.1 页面布局与表格检测数据集

这类数据集主要监督“表格在哪里”，通常没有完整的单元格拓扑和内容，不能单独训练端到端表格恢复。

| 数据集 | 年份与规模 | 场景与标注 | 主要用途 | 局限 | 论文/来源 |
|---|---|---|---|---|---|
| ICDAR 2013 Table Competition | 2013，小规模竞赛集 | 科学/商业 PDF 页面；表格区域及结构评测 | 早期表格检测与结构识别统一对比 | 规模小、版式单一 | [ICDAR 2013 Table Competition](https://doi.org/10.1109/ICDAR.2013.292) |
| Marmot | 约 2,000 页，中英文 | PDF 页面表格区域；后续工作补充行列标注 | 表检测、跨语言迁移 | 标注较旧，复杂结构覆盖有限 | [TableNet 论文中的使用与扩展](https://arxiv.org/abs/2001.01469) |
| ICDAR 2019 cTDaR | 2019 | 现代文档与历史档案；检测和结构识别赛道 | 有线/无线表、历史文档 | 规模仍有限，适合测试而非大规模预训练 | [cTDaR 论文](https://doi.org/10.1109/ICDAR.2019.00243) |
| TableBank | 2019，约 417K 张表 | Word/LaTeX 弱监督生成；表格区域和 HTML/结构线索 | 大规模表检测与识别预训练 | 数字原生、模板偏差明显 | [TableBank](https://arxiv.org/abs/1903.01949) |
| PubLayNet | 2019，约 360K 页面 | PubMed 页面布局；含 table 类 bbox | 文档布局和表格区域检测 | 只有区域级标签，没有表内结构 | [PubLayNet](https://arxiv.org/abs/1908.07836) |
| DocBank | 2020，约 500K 页面 | LaTeX/PDF 弱监督布局标注 | 布局预训练、表格区域识别 | 弱标注噪声；缺少单元格拓扑 | [DocBank](https://arxiv.org/abs/2006.01038) |
| DocLayNet | 2022，80,863 页、11 类 | 多领域人工布局标注，包含 table 类 | 通用文档布局检测 | 不是 TSR/内容恢复数据集 | [DocLayNet](https://arxiv.org/abs/2206.01062) |

### 2.2 单表结构与内容恢复数据集

| 数据集 | 年份与规模 | 主要标注 | 适合任务 | 常用指标 | 论文/来源 |
|---|---|---|---|---|---|
| SciTSR / SciTSR-COMP | 2019，15,000 张科学表格 | PDF 文字块、单元格及邻接关系；COMP 强调合并单元格 | 图关系式 TSR | adjacency Precision/Recall/F1 | [Complicated Table Structure Recognition](https://arxiv.org/abs/1908.04729) |
| PubTabNet | 2019/2020，约 568K 张表 | 表格图像、HTML 结构和单元格文本 | 图像到 HTML 的端到端 TR | TEDS、TEDS-Struct | [PubTabNet/EDD](https://arxiv.org/abs/1911.10683) |
| FinTabNet / FinTabNet.c | 2020/2021，约 112K 张财务表格 | 单元格 bbox、结构、内容；FinTabNet.c 进一步规范化 | 财报复杂表 TSR/TR | TEDS、GriTS、exact match | [GTE/FinTabNet](https://arxiv.org/abs/2005.00589)；[对齐与修订研究](https://arxiv.org/abs/2303.00716) |
| WTW | 2021，14,581 张自然场景表格 | 单元格 polygon、行列和复杂形变 | 拍摄、弯曲、旋转和无线表 TSR | cell adjacency F1 等 | [官方数据仓库](https://github.com/wangwen-whu/WTW-Dataset) |
| PubTables-1M | 2021/2022，947,642 张表、575,305 页 | 检测、行列、单元格、表头、合并单元格、文字与 bbox | 大规模 TD、TSR、功能分析 | AP、GriTS-Top/Con/Loc | [PubTables-1M](https://arxiv.org/abs/2110.00061) |
| TableGraph-350K | 2021，约 350K 表格 | 单元格空间位置和逻辑位置图 | 图重建式 TSR | cell detection/逻辑位置指标 | [TGRNet](https://arxiv.org/abs/2106.10598) |
| TabRecSet | 2023，38.1K 张中英文表格 | table/cell polygon、逻辑结构和文字；扫描与拍摄场景 | 真实场景端到端 TD+TSR+TCR | 检测、结构和内容指标 | [TabRecSet](https://arxiv.org/abs/2303.14884) |
| SynthTabNet | 合成大规模表格集 | 可控 HTML、文本和复杂 span | 生成式/指针式 TSR 预训练与消融 | TEDS/TEDS-Struct | [TFLOP 中的使用](https://arxiv.org/abs/2501.11800) |

### 2.3 整页、全文档与跨页数据集

| 数据集 | 年份与规模 | 场景与标注 | 主要任务 | 指标与局限 | 论文/来源 |
|---|---|---|---|---|---|
| OmniDocBench | 2024/2025，9 类文档来源 | 完整页面的文字、表格、公式、阅读顺序等多层标注 | 通用 PDF 页面解析 | Overall、Edit/文本/表格子指标；Overall 不是表格 exact match | [OmniDocBench](https://arxiv.org/abs/2412.07626) |
| PubTables-v2 Cropped Tables | 2025/2026 | 长表、宽表及复杂裁剪表 | 单表结构+内容恢复 | GriTS、TEDS、`Acc-Top/Acc-Con` | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| PubTables-v2 Single Pages | 2025/2026 | 完整页面、多表、表题和脚注；跨页表按当前页片段标注 | 页面级 TE | 单页表集合的严格 `Acc-Con`；不要求跨页拼接 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| PubTables-v2 Full Documents | 2025/2026，9,172 篇文档、9,492 张跨页表 | 完整文档、续表关系和完整逻辑表 | 全文档/多页 TE | 集合级 exact-match F1；不是“整篇文档全对率” | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| OCRFlux-bench-single | 2025，2,000 页中英文人工标注 | 页面到 Markdown | 单页文档解析 | EDS；不是表格专属 | [OCRFlux 官方仓库](https://github.com/chatdoc-com/OCRFlux) |
| OCRFlux-bench-cross | 2025，1,000 对中英文相邻页 | 是否存在需跨页合并的元素及正确索引 | 跨页表/段落合并检测 | Accuracy、P/R/F1；不衡量合并后全表内容 | [OCRFlux 官方仓库](https://github.com/chatdoc-com/OCRFlux) |
| OCRFlux-pubtabnet-cross | 2025，9,064 对构造性拆分表 | 两个表格片段和完整合并真值 | 跨页表生成式合并 | TEDS；样本由单表人工拆分，不等同自然跨页 PDF | [OCRFlux 官方仓库](https://github.com/chatdoc-com/OCRFlux) |
| Real5-OmniDocBench | 2026 | 扫描、倾斜、弯曲、屏摄、照明等真实扰动 | 鲁棒文档解析 | 综合分，不是表格完全准确率 | [PaddleOCR-VL-1.5](https://arxiv.org/abs/2601.21957) |
| FinDocBench | 2026，六类金融文档 | TOC、跨页表、单元格位置及专家复核标注 | 金融全文档和跨页恢复 | TocEDS、跨页拼接 TEDS、C-IoU；没有统一 Acc-Con | [LingDT-VL-OCR](https://arxiv.org/abs/2603.11044) |
| XDocParse | 2025/2026，126 种语言 | 多语言完整文档布局解析 | 多语言 OCR/布局/表格解析 | 综合解析指标 | [dots.ocr](https://arxiv.org/abs/2512.02498) |
| Infinity-Doc2-5M | 2026，500 万中英文合成/渲染样本 | bbox、Markdown/HTML/LaTeX、阅读顺序等 | 多任务文档与表格解析预训练 | 训练语料，不是独立 exact-match 榜 | [Infinity-Parser2](https://arxiv.org/abs/2607.07836) |

### 2.4 数据集选择建议

| 目标 | 首选数据集 | 补充数据 |
|---|---|---|
| 表格检测 | PubTables-1M、TableBank | DocLayNet、PubLayNet、cTDaR |
| 裁剪表结构 | PubTables-1M、PubTabNet、FinTabNet.c | SciTSR、WTW、TabRecSet |
| 图像到 HTML | PubTabNet、FinTabNet、TabRecSet | SynthTabNet |
| 真实拍摄/形变表 | WTW、TabRecSet | Real5-OmniDocBench |
| 完整页面多表 | PubTables-v2 Single Pages | OmniDocBench |
| 跨页表 | PubTables-v2 Full Documents | OCRFlux-bench-cross、FinDocBench |

## 3. 评价指标

| 指标 | 含义 | 是否允许局部得分 | 适合任务 | 主要风险 |
|---|---|---:|---|---|
| Precision/Recall/F1 | 检测对象、单元格或邻接关系的分类正确率 | 是 | TD、cell detection、关系 TSR | 无法表示完整表是否全对 |
| AP/mAP | 不同 IoU 阈值下检测精度 | 是 | 表格/单元格 bbox 检测 | 与结构、内容无直接关系 |
| TEDS | 预测 HTML 与真值 HTML 的树编辑相似度 | 是 | 图像到 HTML TR | 0.95 仍可能没有一张表完全正确 |
| TEDS-Struct | 去除单元格文字后的 HTML 结构相似度 | 是 | TSR | 不衡量 OCR 内容 |
| GriTS-Top | 网格拓扑相似度 | 是 | 行列、span 结构 | 高分不等于 exact match |
| GriTS-Con | 网格结构与内容相似度 | 是 | 内容感知 TSR/TE | 可被大量局部正确拉高 |
| GriTS-Loc | 单元格空间位置相似度 | 是 | 空间结构与 bbox | 不衡量完整语义结构 |
| CER/NED/EDS | 字符错误率或编辑相似度 | 是 | OCR/Markdown 文本 | 结构错误可能被弱化 |
| Acc-Top | 表拓扑必须完全一致的集合级 F1 | 否 | 严格 TSR/TE | 不检查内容 |
| Acc-Con | 表拓扑和全部单元格内容必须完全一致的集合级 F1 | 否 | 严格端到端表格恢复 | 对任一字符或 span 错误极敏感 |
| Continuation F1/AUC | 相邻页是否续表 | 否/分类层面 | 续表关系判断 | 不证明合并后的表正确 |

`Acc-Con` 的计算可概括为：完全匹配的预测表是真阳性，未匹配真值表是假阴性，多余预测表是假阳性，再计算集合级 Precision、Recall 和 F1。它不是“有多少篇文档的所有表都完全正确”。

## 4. 研究方法与模型

### 4.1 表格检测、显式网格与图关系方法

| 模型/研究 | 年份 | 数据集/场景 | 核心方法 | 指标与效果 | 论文 |
|---|---:|---|---|---|---|
| DeepDeSRT | 2017 | ICDAR、扫描文档 | CNN 检测表格；FCN 分割行列 | 早期统一深度检测+结构基线 | [DeepDeSRT](https://doi.org/10.1109/ICDAR.2017.192) |
| GraphTSR | 2019 | SciTSR | 将单元格作为图节点，预测同行/同列等关系 | 在 SciTSR 与复杂子集上超过当时基线 | [GraphTSR/SciTSR](https://arxiv.org/abs/1908.04729) |
| TableNet | 2020 | ICDAR 2013、Marmot | 编码器-双解码器分割表格与列，再用规则恢复行 | 论文报告两个数据集上的当时 SOTA | [TableNet](https://arxiv.org/abs/2001.01469) |
| CascadeTabNet | 2020 | ICDAR 2013/2019、TableBank | Cascade Mask R-CNN + HRNet，同时检测表格和单元格 | 论文报告 ICDAR 2013/TableBank 检测及 cTDaR 结构强结果 | [CascadeTabNet](https://arxiv.org/abs/2004.12629) |
| GTE | 2021 | ICDAR、PubTabNet、FinTabNet | 表格/单元格层级检测，加入单元格包含约束 | 完整抽取提升 5.8%；FinTabNet cell structure 相对 vanilla RetinaNet 提升超过 45% | [GTE](https://arxiv.org/abs/2005.00589) |
| TGRNet | 2021 | TableGraph-350K 等 | 联合检测单元格并回归逻辑行列位置 | 将 TSR 直接建模为表格图重建 | [TGRNet](https://arxiv.org/abs/2106.10598) |
| LGPMA | 2021 | PubTabNet 等 | 局部/全局金字塔 mask 对齐单元格边界，再恢复空单元格 | 多个公开基准取得当时竞争性/SOTA 结果 | [LGPMA](https://arxiv.org/abs/2105.06224) |
| TATR / Table Transformer | 2021/2022 | PubTables-1M | DETR 对象查询分别预测表、行、列、表头、span | `GriTS-Top≈0.9849`、`GriTS-Con≈0.9848`、`GriTS-Loc≈0.9782`；不是 exact match | [PubTables-1M/TATR](https://arxiv.org/abs/2110.00061) |
| TSRFormer / DQ-DETR | 2022/2023 | SciTSR、PubTabNet、WTW、FinTabNet | DETR 式分隔线回归 + spanning-cell 合并；后续加入动态点查询 | 在形变、无线、空白和合并单元格上表现强 | [TSRFormer](https://arxiv.org/abs/2208.04921)；[DQ-DETR](https://arxiv.org/abs/2303.11615) |
| LORE / LORE++ | 2023/2024 | 多个标准 TSR 集 | 同时回归单元格空间 bbox 和逻辑行列坐标；LORE++ 加空间/逻辑预训练 | 论文报告准确率、泛化和少样本能力持续提升 | [LORE](https://arxiv.org/abs/2303.03730)；[LORE++](https://arxiv.org/abs/2401.01522) |
| GrabTab | 2023 | 复杂表格基准 | 多组件候选 + Component Deliberator 自适应选择结构线索 | 特别针对不规则、形变和复杂表取得显著增益 | [GrabTab](https://arxiv.org/abs/2303.09174) |
| Benchmark Alignment | 2023 | PubTables-1M、FinTabNet、ICDAR 2013 | 不改 TATR，只修正与对齐数据标注 | ICDAR exact match：PubTables 训练 `65→75%`，FinTabNet `42→65%`，联合 `69→81%` | [Aligning benchmark datasets](https://arxiv.org/abs/2303.00716) |
| ClusterTabNet | 2024 | PubTables-1M、PubTabNet、FinTabNet | 从 OCR word 出发预测同表/同行/同列/同表头邻接矩阵 | 与 DETR/Faster R-CNN 相当或更好，但模型显著更小 | [ClusterTabNet](https://arxiv.org/abs/2402.07502) |
| SEMv3 | 2024 | WTW、cTDaR Historical 等 | KOR 关键点偏移回归分隔线 + merge actions | 多个无线/历史表基准报告 SOTA | [SEMv3](https://arxiv.org/abs/2405.11862) |
| SepFormer | 2025 | SciTSR、PubTabNet、WTW | 粗到细 DETR 分隔线/线带回归 | 约 25.6 FPS，同时保持接近 SOTA 的结构效果 | [SepFormer](https://arxiv.org/abs/2506.21920) |
| POTATR | 2026 | PubTables-v2 Single Pages | 29M 参数 image-to-graph；把 TATR 扩展到表格、表题、脚注和层级关系 | `GriTS-Con=0.964`；论文称比测试的生成模型快 130 倍以上、成本低约 300 倍 | [POTATR](https://arxiv.org/abs/2606.09788) |

### 4.2 自回归、指针与统一端到端表格识别

| 模型/研究 | 年份 | 数据集 | 核心方法 | 指标与效果 | 论文 |
|---|---:|---|---|---|---|
| EDD | 2019/2020 | PubTabNet | 图像编码器 + 结构/内容双解码器，直接生成 HTML | 相对此前方法 TEDS 绝对提升 9.7 个百分点；同时提出 TEDS | [EDD/PubTabNet](https://arxiv.org/abs/1911.10683) |
| TableMaster | 2021 | ICDAR 2021 PubTabNet 赛道 | MASTER 风格结构生成 + PSENet 文字检测/识别 + box assignment | 验证集 TEDS `0.9684`，最终测试 `0.9632` | [TableMaster 方案](https://arxiv.org/abs/2105.01848) |
| TableFormer | 2022 | PubTabNet、FinTabNet | Transformer 结构 token 解码 + 单元格 bbox；PDF 文字可直接赋值 | 简单表 TEDS 从约 0.91 提升到 `0.985`，复杂表从 0.887 提升到 `0.950` | [TableFormer](https://arxiv.org/abs/2203.01017) |
| UniTable | 2024 | 四个大规模 TR 数据集 | 结构、内容和 cell bbox 全部统一为语言建模；表图自监督预训练 | 论文报告四个大规模数据集上的 SOTA，并优于当时通用 VLM | [UniTable](https://arxiv.org/abs/2403.04822) |
| UniTabNet | 2024 | PubTabNet、PubTables-1M、WTW、iFLYTAB | image-to-text；物理/逻辑双解码器 + Vision/Language Guider | 论文报告多个 TSR 基准的新 SOTA | [UniTabNet](https://arxiv.org/abs/2409.13148) |
| TFLOP | 2024/2025 | PubTabNet、FinTabNet、SynthTabNet | Layout Pointer 直接把 HTML token 指向文本区域，加入 span 对比监督 | 三个基准报告 SOTA，减少结构与文本区域错配 | [TFLOP](https://arxiv.org/abs/2501.11800) |
| GAP Loss | 2026 | PubTabNet、SynthTabNet | 按空间距离重加权 pointer loss，强化相邻错配样本 | 发现 79.6% pointer 错误发生在曼哈顿距离≤2 的邻格；零推理开销取得新 SOTA | [Geometry-Aware Pointer Loss](https://arxiv.org/abs/2606.18721) |
| TDATR | 2026 | 七个公开基准 | “先感知、再融合”；联合结构/内容任务 + cell-level visual alignment | 无数据集专门微调仍取得 SOTA 或竞争性结果 | [TDATR](https://arxiv.org/abs/2603.22819) |
| TRivia-3B | 2026 | 三个流行 TR 基准 | 用无标注表图和问答奖励进行自监督 GRPO 微调 | 论文报告超过 Gemini 2.5 Pro、MinerU2.5 等系统 | [TRivia](https://arxiv.org/abs/2512.01248) |

### 4.3 文档 VLM 与完整页面解析

这些模型通常直接输出 Markdown、HTML 或统一标记，能同时处理表格、文字、公式和阅读顺序，但综合文档分数不能当作表格完全准确率。

| 模型/系统 | 年份/规模 | 方法与表格能力 | 已报告效果 | 表格研究中的定位 | 论文/来源 |
|---|---|---|---|---|---|
| SmolDocling | 2025，256M | 单模型生成 DocTags，覆盖表格、公式、代码和 bbox | 论文报告可与大 27 倍的 VLM 竞争 | 轻量页面解析基线 | [SmolDocling](https://arxiv.org/abs/2503.11576) |
| Qwen2.5-VL | 2025，3B/7B/72B | 动态分辨率 ViT，按提示输出结构化表格 | 通用文档/表格能力强；PubTables-v2 严格结果见第 5 节 | 通用 VLM 微调基线 | [Qwen2.5-VL](https://arxiv.org/abs/2502.13923) |
| Dolphin / Dolphin-v2 | 2025/2026 | analyze-then-parse：先生成布局锚点，再并行识别元素；v2 区分数字原生与拍摄文档 | v2 在 OmniDocBench 相对 v1 总分提升 14.78，拍摄文档错误下降 91% | 高效两阶段文档解析 | [Dolphin](https://arxiv.org/abs/2505.14059)；[Dolphin-v2](https://arxiv.org/abs/2602.05384) |
| dots.ocr | 2025/2026 | 单 VLM 联合布局、OCR 和关系建模；覆盖 126 种语言 | OmniDocBench/XDocParse 报告 SOTA；严格表格结果见第 5 节 | 开源 image-only 主基线 | [dots.ocr](https://arxiv.org/abs/2512.02498) |
| DeepSeek-OCR / OCR 2 | 2025/2026 | 高比例视觉 token 压缩；OCR 2 以 Visual Causal Flow 重排视觉 token | 在 OmniDocBench 上以较少视觉 token 超过 GOT-OCR2.0/MinerU2.0；非表格 exact | 高压缩 OCR/VLM 对照 | [DeepSeek-OCR](https://arxiv.org/abs/2510.18234)；[OCR 2](https://arxiv.org/abs/2601.20552) |
| OCRFlux-3B | 2025，3B | 页面转 Markdown，再检测并重建跨页表/段落 | 单页 EDS 约 0.967；跨页结果见第 5 节 | 开源跨页工程基线 | [官方仓库](https://github.com/chatdoc-com/OCRFlux) |
| MonkeyOCR v1.5 | 2025 | 布局/阅读顺序 + 局部识别；render-and-compare RL；跨页/跨栏表合并 | OmniDocBench v1.5 报告优于当时 PPOCR-VL 和 MinerU2.5 | 复杂表与跨页定性/综合对照 | [MonkeyOCR v1.5](https://arxiv.org/abs/2511.10390) |
| PaddleOCR-VL-1.5/1.6 | 2026，0.9B | 多任务紧凑 VLM；1.6 用弱区域定向数据优化和渐进后训练 | OmniDocBench v1.5 `94.5%`；v1.6 `96.33%`，均为综合分 | 工业化紧凑模型；不能代替表格 Acc-Con | [1.5](https://arxiv.org/abs/2601.21957)；[1.6](https://arxiv.org/abs/2606.03264) |
| MinerU2.5-Pro | 2026，1.2B | 保持架构不变，通过 65.5M 数据、难例和 GRPO 提升 | OmniDocBench v1.6 `95.69`，为综合解析分 | 数据工程路线对照 | [MinerU2.5-Pro](https://arxiv.org/abs/2604.04771) |
| LingDT-VL-OCR | 2026 | 金融全文档解析、跨页内容整合、TOC 重建、CellBBoxRegressor | OmniDocBench/FinDocBench 强结果；跨页表 TEDS 见第 5 节 | 金融跨页与可审计定位基线 | [LingDT-VL-OCR](https://arxiv.org/abs/2603.11044) |
| Infinity-Parser2 | 2026 | 500 万双语合成语料 + 八任务可验证联合 RL | olmOCR-Bench `87.6%`、ParseBench `74.3%`；非表格专属 | 最新通用文档解析对照 | [Infinity-Parser2](https://arxiv.org/abs/2607.07836) |

## 5. 可直接比较的公开结果

### 5.1 PubTables-v2 严格内容完全匹配

下表均为同一论文统一评测的 `Acc-Con`，但 PDF 原生文字辅助和纯图像输入仍必须分开。

| 模型 | 输入赛道 | 裁剪单表 | 单页 | 全文档 | 来源 |
|---|---|---:|---:|---:|---|
| TATR-v1.2-Pub + Direct Text | PDF-text-assisted | **0.6831** | - | - | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| POTATR + Direct Text | PDF-text-assisted | - | **0.6454** | - | [PubTables-v2](https://arxiv.org/abs/2512.10888)；[POTATR](https://arxiv.org/abs/2606.09788) |
| TATR-v1.2-Pub + docTR OCR | image + external OCR | 0.0191 | - | - | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| POTATR + docTR OCR | image + external OCR | - | 0.0683 | - | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| SmolDocling-256M | image-only | 0.0250 | 0.0298 | 0.0335 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| GraniteDocling-258M | image-only | 0.0555 | 0.0829 | 0.0728 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| Qwen2.5-VL-3B | image-only | 0.0064 | 0.0619 | 0.0452 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| Granite-Vision-3.2-2B | image-only | 0.0067 | 0.0331 | 0.0218 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| DeepSeek-OCR | image-only | 0.0264 | 0.1671 | 0.0921 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| DeepSeek-OCR 2 | image-only | 0.0294 | 0.1120 | 0.0933 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| dots.ocr | image-only | 0.0566 | 0.1872 | 0.1180 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| Claude Opus 4.6 | image-only，多页上下文 | 0.1060 | 0.2713 | **0.2452** | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| GPT-5.4 | image-only，多页上下文 | 0.0988 | 0.2074 | 0.1636 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| Gemini 3.1 Pro | image-only，多页上下文 | **0.1613** | **0.3524** | 0.2025 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |

解释：

- `0.6831` 是裁剪单表、结构模型加 PDF 原生文字的 strict exact-match F1，不是纯 OCR。
- `0.6454` 是 Single Pages 中页面局部表格集合的严格结果；跨页表只按当前页片段评测，不要求拼接。
- `0.2452` 是 Full Documents 设置下逻辑表集合的严格 exact-match F1，不是 24.52% 文档逐篇全部表都正确。

### 5.2 跨页续表与重建结果

| 方法 | 数据/场景 | 指标 | 结果 | 是否表示合并后整表全对 | 来源 |
|---|---|---|---:|---:|---|
| PubTables-v2 ViT-B/16 续表分类器 | 相邻页续表判断 | Recall / Precision / F1 / AUC | 0.995 / 0.987 / **0.991** / **0.996** | 否 | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| dots.ocr + ViT 直接纵向拼接 | PubTables-v2 Full Documents | GriTS-Con / TEDS | `0.5768→0.6844` / `0.5876→0.7141` | 否，`Acc-Con` 仍为 **0.1180** | [PubTables-v2](https://arxiv.org/abs/2512.10888) |
| OCRFlux 合并检测 | OCRFlux-bench-cross | Accuracy / F1 | **0.986 / 0.986** | 只表示合并对象及索引全对 | [OCRFlux](https://github.com/chatdoc-com/OCRFlux) |
| OCRFlux 表格重建 | OCRFlux-pubtabnet-cross | TEDS | **0.950**（简单 0.965，复杂 0.935） | 否，软相似度且为构造集 | [OCRFlux](https://github.com/chatdoc-com/OCRFlux) |
| LingDT-VL-OCR | 472 个金融跨页表 | TEDS | **0.8915** | 否 | [LingDT-VL-OCR](https://arxiv.org/abs/2603.11044) |
| VCCT | 电力故障报告跨页表 | Cross-page structural integrity | **82.0%** | 只检查领域结构完整性，不要求所有文字全等 | [VCCT](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6811737) |

### 5.3 为什么不存在一个统一的“最高分模型”

以下数字不能横向排序：

- TableFormer 的 `TEDS≈0.95-0.985`：裁剪表、软树相似度。
- TATR 的 `GriTS≈0.98`：网格软相似度，并可使用 PDF 文字。
- PaddleOCR-VL-1.6 的 `96.33%`：完整文档解析综合分。
- OCRFlux 的 `Accuracy=0.986`：跨页合并对象检测，不是表内容。
- Claude 的 `Acc-Con=0.2452`：全文档逻辑表集合的严格结构+内容完全匹配。

只有数据集、输入条件、输出规范和指标都一致时，才能声称模型优于另一个模型。

## 6. 方法演进与当前研究空白

### 6.1 方法演进

```text
规则/线条与投影分析
  -> CNN 分割（DeepDeSRT、TableNet）
  -> 单元格检测与图关系（GraphTSR、GTE、TGRNet）
  -> DETR 对象/分隔线查询（TATR、TSRFormer、SepFormer）
  -> HTML 自回归与指针对齐（EDD、TableMaster、TableFormer、TFLOP）
  -> 统一结构+内容+位置生成（UniTable、UniTabNet、TDATR、TRivia）
  -> 整页/全文档 VLM 与跨页重建（POTATR、dots.ocr、OCRFlux、LingDT）
```

### 6.2 当前主要瓶颈

1. OCR 字符错误会被整表 exact match 放大。
2. token-to-cell 归属仍是结构模型与 OCR 组合中的关键误差源。
3. 合并单元格、层级表头、空单元格和无线表仍是 TSR 难点。
4. 自回归 HTML 容易产生非法序列、漏单元格和文本错位。
5. 整页任务增加了表格漏检、多表匹配、表题和脚注归属问题。
6. 跨页任务还需要处理重复表头、跨页断裂单元格、横向分页和误拼接。
7. 许多新文档 VLM 只报告综合分或 TEDS，缺少严格表格 exact match。
8. 不同数据集的 canonicalization 不一致会产生虚假的模型差异。

## 7. 对后续研究的建议

若目标是同时研究单表、单页和跨页表格恢复，推荐采用两条独立赛道。

### 7.1 PDF-text-assisted 主赛道

```text
PubTables-1M 预训练 TATR/POTATR 式显式结构模型
  -> PubTables-v2 长表/宽表微调
  -> PDF word/token + bbox 联合结构建模
  -> 文档级表片段关系图
  -> 跨页联合重解码与硬约束
  -> Acc-Con 作为主指标
```

这一赛道最有希望超过裁剪表 `0.6831`、单页 `0.6454` 和全文档 `0.2452`，但必须明确不属于纯 OCR。

### 7.2 Image-only 扩展赛道

采用文档 VLM 或 OCR + 显式结构头：

- 以 Qwen2.5-VL、dots.ocr、DeepSeek-OCR 2、PaddleOCR-VL 为基础模型。
- 增加 cell query、逻辑位置、pointer alignment 或 constrained decoder。
- 将生成文字与结构合法化解码分离。
- 使用 PubTables-v2、TabRecSet、WTW 和 Real5-OmniDocBench 评测。
- 分别报告 CER、TEDS/GriTS 和 `Acc-Con`，避免只展示软指标。

### 7.3 最低对比集合

1. TATR-v1.2-Pub + Direct Text。
2. POTATR + Direct Text。
3. TableFormer 或 TFLOP，作为序列/指针对齐 TSR 对照。
4. UniTable/UniTabNet/TDATR，作为统一端到端 TR 对照。
5. dots.ocr 或 PaddleOCR-VL，作为开源页面 VLM 对照。
6. Claude Opus 4.6，引用 PubTables-v2 全文档公开结果。
7. ViT 续表分类 + 直接拼接。
8. OCRFlux 式检测后重建。
9. 所提方法的无文本、无关系图、无约束解码消融。

## 8. 最终结论

当前表格抽取研究不存在一个跨任务、跨数据集、跨指标统一有效的 SOTA 数字。应按任务层级分别表述：

- 表格检测：成熟度较高，主要比较 AP/mAP 和跨领域泛化。
- 单表结构识别：TATR、TableFormer、UniTable、TFLOP、TDATR 等均有强结果，但主流仍以软指标为主。
- 严格裁剪表恢复：PubTables-v2 中 `TATR-v1.2-Pub + Direct Text` 的 `Acc-Con=0.6831` 是关键公开基线。
- 严格单页恢复：`POTATR + Direct Text` 的 `Acc-Con=0.6454` 是关键结构模型基线；纯图像统一评测中 Gemini 3.1 Pro 为 0.3524。
- 严格全文档恢复：PubTables-v2 统一评测中 Claude Opus 4.6 的 `Acc-Con=0.2452` 是当前关键公开结果。
- 跨页续表判断：ViT-B/16 的 F1 0.991 已很高，但不代表表格合并成功。
- 自然跨页表的结构与全部文字完全匹配：仍缺少跨领域统一排行榜，是最明确的研究空白之一。

