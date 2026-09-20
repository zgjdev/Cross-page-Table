# 融合版式分析的跨页表格识别与结构恢复：研究设计

**日期：** 2026-07-24  
**研究周期：** 3-6 个月  
**目标文档：** 英文原生 PDF 学术论文  
**主要数据集：** PubTables-v2  
**目标投稿方向：** 文档分析/版式分析会议优先，计算机视觉会议或期刊作为备选

## 1. 研究摘要

本项目研究英文原生 PDF 学术论文中的跨页表格恢复。核心观点是：跨页表格不应被处理为独立的页面对分类或识别后的机械拼接，而应被建模为文档级版式关系解析问题。模型需要同时理解表格与 caption、footer 等页面元素的层级关系，判断跨页表格片段的归属，并显式预测列对应、重复表头和断裂行，最终恢复统一的逻辑表格。

项目以 PubTables-v2 的 Full Documents collection 为主要训练和评测数据，使用官方划分保证结果可比，同时建立 journal/template-disjoint 测试划分验证跨模板泛化。最小可行方法固定或轻量适配 POTATR/Table Transformer 风格的强页面解析器，在其空间化版式与表格对象上训练分层文档关系图和约束解码器；页面编码器端到端联合微调属于增强项。主要评价目标是文档级完整表格恢复，而不是已经接近饱和的 continuation 二分类指标。

## 2. 背景与研究机会

传统表格抽取通常逐页完成表格检测和结构识别，再通过规则判断相邻页表格是否属于同一逻辑表格。这种流程存在三个问题：

1. 页内识别丢失了表格周围的 caption、footer、阅读顺序和文档模板信息。
2. “列数相同则拼接”无法处理重复表头、断裂行、跨页单元格、列边界漂移和层级表头。
3. 独立 continuation 分类可以利用页底/页顶位置等视觉捷径取得很高分数，却不能保证最终结构正确。

PubTables-v2 在 2025 年底首次发布，并于 2026-06-02 更新到 v3。其 Full Documents collection 包含 9,172 篇文档、137,095 页和 24,862 张表格，其中有 9,492 张跨页表格，最长跨 13 页。论文已经给出 ViT-B/16 continuation 分类器与简单拼接基线：continuation F1 为 0.991；原论文中，在页级 `dots.ocr` 输出上加入拼接后，文档级 `GriTS_Con` 从 0.577 提升到 0.684。

2026-06 发布的 POTATR 是创新性审查后必须新增的最近工作。POTATR 用 29M 参数的 image-to-graph 模型联合预测页级表格、结构、caption/footer 和层级关系，在 Single Pages 上达到 `GriTS_Con = 0.964`。其附录将同一 continuation/纵向拼接方法用于 Full Documents：`dots.ocr` 从 0.577 提升到 0.750，POTATR 从 0.671 提升到 0.827；论文同时报告 continuation recall 0.995。POTATR 明确将多页训练优化和页内 table-part merging 留作未来工作，所用跨页操作仍是简单纵向拼接。这意味着单独研究 continuation 分类或再训练一个通用页级解析器都缺少足够的新颖性，而显式列/行对齐、结构恢复、版式关系集成和模板外泛化仍有空间。

## 3. 研究目标与非目标

### 3.1 研究目标

- 从连续 PDF 页面中检测表格及其 caption、footer 等相关版式元素。
- 恢复每个表格片段的页内行、列、表头和单元格结构。
- 判断跨页表格片段是否属于同一逻辑表格。
- 显式预测跨页列对应、重复表头和页边界断裂行。
- 输出拼接后的 HTML 或结构化 JSON 逻辑表格。
- 在官方同分布测试和模板隔离测试上验证端到端性能。

### 3.2 非目标

- 不把 OCR 识别作为研究贡献；原生 PDF 文本及其坐标是允许输入。
- 第一阶段不处理扫描件、手写文档和多语言文档。
- 第一阶段只处理连续页之间的表格延续，不处理跨越多个无关页面的远距离检索。
- 跨栏表格可作为辅助任务，但主要结论聚焦跨页表格。
- 不以训练通用大型多页生成模型为最小可行成果。

## 4. 研究问题与假设

### RQ1：联合版式上下文是否改善完整表格恢复？

**假设 H1：** 在相同强页面解析器输入下，联合使用表格、caption、footer、阅读顺序、视觉、文本和结构特征的文档关系图，比独立页面对分类加纵向拼接产生更高的文档级 `GriTS_Con`、TEDS 和跨页表格链完全正确率。

### RQ2：显式结构对齐是否优于简单拼接？

**假设 H2：** 显式预测列对应、重复表头和断裂行，比“continuation 为真且列数相同则纵向拼接”显著减少结构与内容错误。

### RQ3：模型是否具备模板外泛化能力？

**假设 H3：** 使用结构约束、同文档困难负例和模板隔离训练/评测，可以降低模型对页顶、页底和特定期刊版式捷径的依赖。

## 5. 任务定义

### 5.1 输入

输入为一篇英文原生 PDF 学术论文的有序页面序列。每页包含：

- 页面渲染图像；
- PDF 原生单词文本；
- 单词边界框与页码；
- 页面宽高和旋转信息。

训练和主要推理使用连续两页窗口。文档级解码将相邻窗口的预测串联为任意长度的表格链。对跨 3 页以上表格，关系模块可选用 3-4 页滑动窗口做增强实验，但不作为首个实现的必要条件。

### 5.2 输出

模型输出文档级关系图与恢复后的逻辑表格：

- 版式对象：`table`、`caption`、`footer` 和必要的正文候选；
- 表格结构：`row`、`column`、`column_header`、`projected_row_header`、`spanning_cell`；
- 页内关系：包含、caption/footer 归属、阅读顺序；
- 跨页关系：table continuation、column correspondence、repeated header、split row；
- 逻辑结果：带 `rowspan`/`colspan` 的 HTML，或等价 JSON 网格及单元格文本。

### 5.3 约束

- 表格 continuation 按页码单调连接。
- 每个表格片段最多有一个跨页前驱和一个跨页后继。
- 列对应保持从左到右的单调顺序，但允许缺失列和跨列单元格。
- 重复表头保留 provenance 标记，但默认不重复写入最终逻辑网格。
- 断裂行在保留原页面来源的前提下合并内容。

## 6. 方法设计

### 6.1 共享多模态页面编码器

页面编码器融合页面视觉特征和 PDF 文本/坐标特征。MVP 优先复用并固定 POTATR/Table Transformer 风格的视觉编码器和检测头，在预测对象上增加 PDF 文本、位置、结构统计和置信度特征，从而将实验变量集中到跨页关系与结构对齐。只有在 frozen-page-model 基线稳定后，才尝试解冻关系相关层或加入文本位置嵌入；跨页损失更新共享页面表示是增强实验，不是 novelty gate 后的最小退出条件。

页面编码器输出多尺度页面特征，以及每个候选版式对象和表格结构对象的向量表示。

### 6.2 页面级版式与表格结构头

页面级预测包括：

- table、caption、footer 区域；
- 行、列、表头、projected row header、spanning cell；
- table 到 caption/footer/结构对象的层级关系。

该模块使用 PubTables-v2 Single Pages collection 初始化或训练，并可用 PubTables-1M 扩充页内结构预训练。训练和评测均保留 PDF 直接提取文本版本；OCR 输入只作为鲁棒性附加实验。

### 6.3 分层文档关系图

为避免全局图包含大量单元格而失控，使用两层图：

- **文档层：** table fragment、caption、footer 节点；
- **表格层：** 列边界、表头行、首尾数据行和必要的结构摘要节点。

节点特征包括视觉向量、文本向量、归一化几何、页内位置、结构统计和置信度。边特征包括页码距离、水平重叠、列边界相似度、表头文本相似度、caption 编号模式和页面阅读顺序。

跨页关系 Transformer 对相邻页候选节点执行消息传递，预测：

1. `P(continuation)`；
2. 前后页列的软对应矩阵；
3. 下一页起始行的 repeated-header 概率；
4. 页边界两行的 split-row 概率；
5. table-caption/footer 的层级关系。

### 6.4 联合训练目标

MVP 在固定页面对象上训练 `L_rel + lambda_align L_align + lambda_aux L_aux`。联合微调增强版的总损失定义为：

`L = L_layout + lambda_struct L_struct + lambda_rel L_rel + lambda_align L_align + lambda_aux L_aux`

其中：

- `L_layout`：版式对象分类和边界框损失；
- `L_struct`：页内表格结构对象和关系损失；
- `L_rel`：continuation、caption/footer 和 split-row 关系损失；
- `L_align`：列对应的单调匹配损失；
- `L_aux`：重复表头等辅助任务损失。

各权重在验证集上选择，并通过消融报告其影响。为缓解真实推理中的错误传播，关系模块训练同时使用真实节点、受控扰动节点和页面模型预测节点。

### 6.5 约束解码器

解码分为三步：

1. 在表格片段图上寻找满足前驱/后继与页码单调约束的高分链；
2. 对链中相邻片段执行单调列匹配，并判断重复表头与断裂行；
3. 合并网格、文本与 `rowspan`/`colspan`，输出 HTML/JSON 和每个单元格的页面 provenance。

解码器必须输出中间置信度和错误类型，使最终错误可以归因到页面检测、continuation、列对齐、表头处理或断裂行处理。

## 7. 数据设计

### 7.1 主数据

PubTables-v2 提供三部分数据：

| Collection | 样本 | 页面 | 表格 | 用途 |
|---|---:|---:|---:|---|
| Cropped Tables | 135,578 | 0 | 135,578 | 长表、宽表的页内结构预训练 |
| Single Pages | 467,541 | 467,541 | 548,414 | 页面级版式、结构和层级关系训练 |
| Full Documents | 9,172 | 137,095 | 24,862 | 跨页关系与文档级抽取 |

Full Documents collection 包含 9,492 张跨页表格、630 张单页跨栏表格和 14,740 张普通单页表格。跨页长度分布以 2 页为主，但包含超过 200 张跨 5 页以上的表格。

### 7.2 细粒度标签派生

Full Documents collection 提供逻辑表格结构、单元格文本和每页表格片段位置，但不提供多片段表格内部每行、每列的页面级边界框。项目通过以下过程派生训练标签：

1. 将逻辑 HTML/JSON 单元格文本规范化；
2. 使用数据集提供的 PDF 单词及坐标与单元格文本做序列对齐；
3. 根据单词所在页确定逻辑行和单元格的页面归属；
4. 从全局列索引派生相邻片段的列对应；
5. 根据重复文本与全局行索引识别 repeated header；
6. 根据同一逻辑行跨页分布识别 split row；
7. 记录对齐置信度，低置信度样本不用于强监督。

人工核验 200-300 个跨页样本，覆盖不同跨页长度、宽表、旋转表、复杂表头和多栏页面。人工核验集用于评估派生标签质量，并作为困难测试子集，不用于训练。

### 7.3 数据划分

- **Official split：** 保留官方 train/validation/test，用于与 PubTables-v2 论文和后续工作直接比较。
- **Template-disjoint split：** 优先按期刊/ISSN 分组；若元数据不足，则根据页面尺寸、栏数、页眉页脚、字体和版式嵌入聚类。一个组只能出现在 train、validation 或 test 之一。
- **Length subsets：** 分别评测跨 2 页、3-4 页、5 页以上表格。
- **Difficulty subsets：** 宽表、旋转表、多栏文档、复杂表头、断裂行、多个相邻表格。

所有划分以文档为最小单位，禁止同一文档的页面进入不同集合。

## 8. 基线与对照方法

### 8.1 规则基线

- 页底/页顶位置加水平重叠；
- 表头文本相似度和 caption 编号；
- 列数相同与列边界距离；
- 匈牙利匹配或单调动态规划拼接。

### 8.2 PubTables-v2 基线

- ResNet-50 continuation classifier；
- ViT-B/16 continuation classifier；
- `dots.ocr` page-by-page；
- `dots.ocr + merging`；
- POTATR page-by-page；
- `POTATR + ViT continuation + vertical merging`，以论文附录的 `GriTS_Con = 0.827` 为最近公开结果；
- 若 POTATR 代码/权重仍未发布，则严格区分引用结果、可复现的 TATR 代理实现和本项目实测结果。

### 8.3 VLM 基线

- 至少一个可本地部署的页级或多页文档 VLM；
- 在预算允许时加入强多页闭源模型结果作为性能上界；
- 若无法严格复现商业模型，则明确区分引用结果与本项目实测结果。

### 8.4 核心方法变体

- 页面模型冻结 + 关系图；
- 页面模型与关系图联合训练；
- 无文本、无 caption/footer、无列对齐、无 repeated-header/split-row 的消融版本；
- oracle 页面节点与 predicted 页面节点两种设置。

## 9. 评价方案

### 9.1 页面版式层

- table/caption/footer 检测 AP 或 F1；
- table-caption/footer 层级关系 precision、recall、F1；
- 页内结构的 `GriTS_Top`、`GriTS_Con` 和 TEDS。

### 9.2 跨页关系层

- continuation precision、recall、F1、AUC；
- 列对应准确率或边 F1；
- repeated-header F1；
- split-row F1；
- 表格片段链 exact match。

### 9.3 文档级最终任务

- 文档级 `GriTS_Top` 与 `GriTS_Con`；
- 文档级 TEDS-S 与 TEDS；
- topology/content exact match；
- 跨页逻辑表格完全正确率；
- 按跨页长度与困难类型分组的结果。

主要模型选择依据文档级 `GriTS_Con`，并结合 TEDS 和跨页逻辑表格完全正确率。continuation F1 只作为诊断指标，不能单独支持论文结论。

### 9.4 泛化与效率

- official split 与 template-disjoint split 的性能差；
- 视觉遮挡或移除页边界区域后的性能变化；
- 参数量、训练显存、单页/单文档推理时间和吞吐量；
- 不同页窗口长度的性能与成本。

## 10. 核心实验矩阵

| 实验 | 对应问题 | 关键对照 | 主要指标 |
|---|---|---|---|
| 联合版式关系图 vs 独立 continuation | RQ1 | ViT-B/16 + merging | Doc GriTS/TEDS |
| 显式列/行对齐 vs 列数相同拼接 | RQ2 | Simple concat | GriTS_Con、exact match |
| 随机/官方划分 vs 模板隔离划分 | RQ3 | 相同模型不同 split | 泛化差值 |
| 移除 caption/footer | RQ1 | 完整模型 | Doc GriTS、关系 F1 |
| 移除文本或视觉 | RQ1/RQ3 | 完整模型 | Doc GriTS、OOD |
| Oracle vs predicted nodes | 错误传播 | 两种输入节点 | 各层指标 |
| 页边界遮挡与困难负例 | RQ3 | 原始输入 | continuation 与 Doc GriTS |
| 2 页 vs 3-4 页 vs 5+ 页 | 鲁棒性 | 分长度报告 | Doc GriTS/TEDS |

## 11. 项目结构建议

后续实现计划采用以下职责边界：

```text
paper/
  docs/
    literature/          # 文献矩阵、阅读笔记、检索日志
    superpowers/specs/   # 已确认研究设计
    superpowers/plans/   # 分阶段实施计划
  configs/               # 数据、模型和实验配置
  src/
    data/                # PubTables-v2 读取与派生标签
    layout/              # 页面级版式和表格结构接口
    graph/               # 分层文档图与关系模型
    decode/              # 约束解码与表格合并
    metrics/             # 关系与文档级评价
  scripts/               # 数据准备、训练、评测入口
  tests/                 # 数据、图、解码和指标单元测试
  experiments/           # 实验清单与结果摘要，不存大型权重
```

大型 PDF、渲染图像、模型权重和缓存不进入版本控制。配置和数据 manifest 必须记录数据版本、划分、随机种子和派生标签版本。

## 12. 时间计划

| 周次 | 交付物 | 退出条件 |
|---|---|---|
| 1-2 | 文献地图、数据审计、问题定义 | 核心论文表和 PubTables-v2 样本报告完成 |
| 3-4 | 数据读取、标签派生、评测脚本 | 小样本端到端评测可重复，人工审计开始 |
| 5-7 | 规则与学习基线 | 官方 merging 基线或等价结果复现 |
| 8-11 | 文档关系图 MVP | continuation + 列对齐端到端结果完成 |
| 12-14 | 对齐关系完整模型 | repeated header、split row 和约束解码完成；联合微调为可选增强 |
| 15-17 | 消融、OOD 和错误分析 | 主表、消融表和错误分类稳定 |
| 18-20 | 论文初稿和补实验 | 完整论文草稿及可复现实验清单完成 |
| 21-24 | 可选增强 | 多页 VLM、蒸馏或跨数据源验证 |

## 13. 风险与降级路径

### 13.1 Continuation 分类饱和

不把 continuation F1 作为主要贡献；重点转向文档级结构、内容恢复和 OOD 泛化。

### 13.2 视觉捷径

使用同文档困难负例、模板隔离划分、页边界遮挡和位置扰动验证模型是否真正使用结构与语义。

### 13.3 派生标签噪声

保存对齐置信度，只对高置信度样本施加强监督；人工审计覆盖困难类型，并单独报告人工子集结果。

### 13.4 页面模型错误传播

训练时混合真实、扰动和预测节点；报告 oracle/predicted 差距，明确后续性能瓶颈。

### 13.5 实现超期

最小可投稿版本限定为“固定强页级模型 + 显式对齐标签/协议 + 分层结构关系图 + 约束解码”。重新训练通用页级模型、端到端联合微调、大型多页 VLM、蒸馏和额外数据源均为增强项，不阻塞主线。

## 14. 预期论文贡献

1. 将跨页表格恢复形式化为带版式层级和结构约束的文档级关系解析问题。
2. 在统一文档图中联合预测跨页归属、列对应、重复表头、断裂行以及与既有页内版式对象的关系。
3. 从 PubTables-v2 派生列对应、重复表头和断裂行标签，并建立 template-disjoint 评测协议。
4. 系统量化视觉、文本、caption/footer 和显式结构约束对完整跨页表格恢复的贡献。

最小成功标准是在同一页级识别输入下，核心方法相对官方简单 merging 在文档级 `GriTS_Con`、TEDS 或跨页表格完全正确率上取得稳定提升，并在 template-disjoint 测试中保持优势。统计报告需要包含至少三个随机种子或可行的 bootstrap 置信区间，避免仅凭单次小幅提升得出结论。

## 15. 投稿定位

优先考虑文档分析、版式分析和文档智能方向的会议或专题赛道；若完整联合模型、OOD 评测和数据派生协议均形成较强结果，可进一步考虑计算机视觉主会/Workshop。若研究周期更长并加入跨数据源、多语言或扫描件扩展，可整理为期刊版本。具体 venue 和截止日期应在完成第 5-7 周基线后，根据实验强度与当期征稿信息确定。

## 16. 关键参考资源

- Smock et al., **PubTables-v2: A new large-scale dataset for full-page and multi-page table extraction**, arXiv:2512.10888, v3, 2026-06-02: <https://arxiv.org/abs/2512.10888>
- PubTables-v2 数据集：<https://huggingface.co/datasets/kensho/PubTables-v2>
- Smock et al., **PubTables-1M: Towards comprehensive table extraction from unstructured documents**, CVPR 2022: <https://arxiv.org/abs/2110.00061>
- Microsoft Table Transformer：<https://github.com/microsoft/table-transformer>
- POTATR：<https://arxiv.org/abs/2606.09788>
- DocLayNet：<https://github.com/DS4SD/DocLayNet>

这些资源是第一轮调研起点；正式文献综述还需覆盖页面级表格抽取、层级文档解析、图关系预测、多页文档理解、结构化生成和跨模板泛化。
