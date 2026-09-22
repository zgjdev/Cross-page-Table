# 使用 PubTables-1M 数据的研究综述

更新日期：2026-08-05

## 1. 调研结论

PubTables-1M 是目前最重要的大规模科学文献表格检测与表格结构识别数据集之一。严格按照“确实使用 PubTables-1M 原始数据训练或评测，或者明确继承其公开模型权重”的标准筛选，相关研究主要集中在 Table Transformer（TATR）技术谱系，而不是一个包含大量独立模型的统一排行榜。

其最重要的研究价值包括：

- 为整页表格检测提供大规模页面级监督。
- 为行、列、表头、投影行表头和合并单元格识别提供结构监督。
- 通过 canonicalization 减少同一视觉表格存在多种结构解释的问题。
- 提供 TATR-v1.1-Pub 等公开预训练权重，成为后续表格研究的初始化模型。
- 为 PubTables-v2 的长表、宽表、整页和跨页研究提供单页结构基础。

需要注意，PubTables-1M 原论文中的高 GriTS 分数是软结构相似度，不能直接与 PubTables-v2 的严格完全匹配指标 `Acc-Con` 比较。

## 2. PubTables-1M 数据集概况

PubTables-1M 来源于 PubMed Central 开放科学论文的 PDF 与结构化 XML。数据构建过程将 XML 中的表格逻辑结构与 PDF 页面中的视觉位置、文字和边界框对齐。

数据集约包含：

- 947,642 张完全标注的表格。
- 575,305 个文档页面。
- 页面级表格检测标注。
- 裁剪表格的结构识别标注。
- PDF 文字、文字坐标以及单元格归属信息。

主要标注对象包括：

- 表格区域。
- 行和列。
- 单元格及其行列跨度。
- 列表头。
- 投影行表头（projected row header）。
- 合并单元格（spanning cell）。
- 单元格文字及位置。

PubTables-1M 的 canonicalization 过程会把结构上等价但表示方式不同的表格转换为统一形式。例如，一个跨两列的表头既可能被标成一个跨列单元格，也可能被错误地拆成多个单元格；规范化可以减少这种标注歧义。

## 3. 直接相关的研究与模型

下表只收录能够从论文、官方模型卡或官方仓库确认使用关系的核心工作。仅在相关工作中引用 PubTables-1M、但没有使用数据或权重的论文不列入。

| 研究或模型 | 时间 | PubTables-1M 的使用方式 | 任务与方法 | 主要结果或意义 | 论文/官方来源 |
|---|---:|---|---|---|---|
| PubTables-1M / Table Transformer（TATR） | 2021/2022 | 使用官方训练集训练表格检测和结构识别模型，并在官方测试集评测 | 基于 DETR 的对象检测式模型；分别预测表格、行、列、表头、投影行表头和合并单元格 | 原论文结构识别结果约为 `GriTS-Top=0.9849`、`GriTS-Con=0.9848`、`GriTS-Loc=0.9782`；建立了经典强基线 | [PubTables-1M 论文](https://arxiv.org/abs/2110.00061)；[微软官方仓库](https://github.com/microsoft/table-transformer) |
| TATR-v1.1-Pub | 后续公开版本 | 使用 PubTables-1M 训练的公开结构识别权重 | 延续 TATR 的对象检测式结构输出；可与 PDF 原生文字或 OCR 结合恢复内容 | 是后续研究最常用的 PubTables-1M 初始化权重之一；属于官方模型发布，不是独立新论文 | [官方模型卡](https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-pub) |
| TATR-v1.2-Pub | 2025/2026 | 以 TATR-v1.1-Pub 为基础，再使用 PubTables-v2 的长表、宽表继续微调 | 保留 TATR 结构建模方式，针对超出 PubTables-1M 常规尺寸分布的复杂表格做迁移 | 在 PubTables-v2 Cropped Tables 上结合 PDF Direct Text 得到 `Acc-Con=0.6831` | [PubTables-v2 论文](https://arxiv.org/html/2512.10888v3) |
| POTATR（Page-Object Table Transformer） | 2025/2026 | 继承 TATR/PubTables-1M 的对象检测式建模思想和权重体系，再扩展到完整页面 | 在页面中联合预测表格、表结构、表题、脚注及对象关系 | 在 PubTables-v2 Single Pages 上结合 PDF Direct Text 得到 `Acc-Con=0.6454` | [PubTables-v2 论文](https://arxiv.org/html/2512.10888v3) |
| PubTables-v2 续表与全文档研究 | 2025/2026 | 将 PubTables-1M/TATR 作为单页结构基础，进一步研究长宽表、跨页表和完整文档 | 单页结构解析、页面对象识别、续表分类和全文档表格重建 | 说明 PubTables-1M 的单页能力可以迁移，但数据本身不能直接监督跨页关联与合并 | [PubTables-v2 论文](https://arxiv.org/html/2512.10888v3) |

## 4. 主要研究方向

### 4.1 表格检测

输入完整页面，预测页面中的表格边界框。这部分通常采用 PubTables-1M 的页面图像和表格区域标注训练。TATR 的检测模型基于 DETR，通过对象查询和匈牙利匹配进行端到端训练。

研究重点包括：

- 有边框与无边框表格检测。
- 页面内多表检测。
- 表格与图片、公式、正文区域的区分。
- 不同尺寸和纵横比表格的召回率。

### 4.2 表格结构识别

输入裁剪后的表格图像，预测行、列、表头和合并单元格等结构对象。这是 PubTables-1M 最核心的研究用途。

TATR 将表格结构识别转化为对象检测问题：

```text
表格图像
  -> 行对象
  -> 列对象
  -> 列表头对象
  -> 投影行表头对象
  -> 合并单元格对象
  -> 规范化网格结构
```

模型本身通常不识别文字。表格内容由 PDF Direct Text 或外部 OCR 提供，再依据文字坐标与结构对象进行单元格分配。

### 4.3 领域迁移与微调

许多下游工作并不重新下载和训练完整 PubTables-1M，而是使用 TATR-v1.1-Pub 权重，再在财务报表、票据、政府报告或企业内部文档上微调。

这类工作应描述为“使用 PubTables-1M 预训练权重”，不能等同于“在 PubTables-1M 官方测试集上取得新结果”。如果论文没有报告官方测试集指标，也不能纳入 PubTables-1M 排行榜。

### 4.4 从单表到整页和全文档

PubTables-v2 是这条路线最明确的后续研究：

```text
PubTables-1M
  -> 通用表格检测和单表结构预训练
PubTables-v2 Cropped Tables
  -> 长表、宽表和复杂结构微调
PubTables-v2 Single Pages
  -> 页面内多表、表题和脚注关系
PubTables-v2 Full Documents
  -> 续表关系、跨页拼接和完整逻辑表重建
```

这说明 PubTables-1M 更适合作为底层结构能力的预训练集，而不是跨页研究的最终评测集。

## 5. 指标与结果的可比性

| 指标 | 评测内容 | 是否严格完全匹配 | 典型使用场景 |
|---|---|---:|---|
| 检测 AP | 表格或结构对象的类别与边界框 | 否 | 表格检测、行列对象检测 |
| GriTS-Top | 网格拓扑相似度 | 否 | 表格结构识别 |
| GriTS-Con | 结构与内容的网格匹配相似度 | 否 | 表格内容感知结构评测 |
| GriTS-Loc | 单元格位置和几何关系相似度 | 否 | 单元格定位 |
| TEDS | HTML 树编辑相似度 | 否 | 生成式表格识别 |
| Acc-Top | 表格拓扑完全匹配 | 是 | PubTables-v2 严格评测 |
| Acc-Con | 表格拓扑和全部单元格内容完全匹配 | 是 | PubTables-v2 严格评测 |

因此：

- PubTables-1M 上约 `0.98` 的 GriTS 表示整体结构高度相似，但允许局部错误。
- PubTables-v2 上 `Acc-Con=0.6831` 表示 68.31% 量级的严格表格集合匹配表现，结构或任意内容错误都可能导致该表不能形成 exact match。
- 两个数字不能直接比较，也不能据此认为 PubTables-1M 任务更容易或模型已有 98% 的整表完全正确率。

## 6. 常见误区

### 6.1 PubTabNet 不是 PubTables-1M 的子集

PubTabNet、FinTabNet 和 PubTables-1M 是不同的数据集。它们的数据来源、结构表示、标注生成方式和主要指标均不同。

### 6.2 引用数据集不等于使用数据集

TableFormer、LORE、VAST、UniTable 等表格结构识别研究可能在相关工作中引用 PubTables-1M，但是否实际使用其训练数据或官方测试集，必须以论文实验设置和数据说明为准。不能仅凭参考文献将它们列入 PubTables-1M 结果表。

### 6.3 使用 TATR 权重不等于重新训练 PubTables-1M

如果研究只下载 `TATR-v1.1-Pub` 并在私有数据上微调，应标为“继承 PubTables-1M 预训练权重”。除非重新在官方测试集评测，否则不能宣称取得新的 PubTables-1M SOTA。

### 6.4 TATR 不是完整 OCR 模型

TATR 主要输出表格结构。`TATR + Direct Text` 使用 PDF 内嵌文字，`TATR + OCR` 才需要从图像识别内容。这两种输入设置必须分开报告。

## 7. 对当前研究的建议

如果研究目标是超过 PubTables-v2 上的单表、单页和全文档严格 `Acc-Con`，建议这样使用 PubTables-1M：

1. 使用 TATR-v1.1-Pub 作为结构模型初始化，先复现官方结构输出。
2. 在 PubTables-1M 上训练或继续训练表格检测、行列、表头和合并单元格识别。
3. 使用 PubTables-v2 Cropped Tables 微调长表、宽表和复杂 span。
4. 使用 PubTables-v2 Single Pages 训练页面内多表检测及表题、脚注关系。
5. 使用 PubTables-v2 Full Documents 单独训练续表关系和跨页联合重建。
6. 将 PDF-text-assisted 与 image-only 两条赛道分开，避免把原生文字优势误认为 OCR 能力。
7. 最终模型选择以 PubTables-v2 `Acc-Con` 为主，GriTS 和 TEDS 仅用于错误分析和软性能观察。

推荐定位是：

> PubTables-1M 用于获得通用、可解释的单页表格结构能力；PubTables-v2 用于验证长宽表、整页和跨页表格的严格端到端恢复能力。

## 8. 主要参考资料

1. Smock, B., Pesala, R., and Abraham, R. [PubTables-1M: Towards Comprehensive Table Extraction From Unstructured Documents](https://arxiv.org/abs/2110.00061).
2. Microsoft. [Table Transformer 官方仓库](https://github.com/microsoft/table-transformer).
3. Microsoft. [TATR-v1.1-Pub 官方模型卡](https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-pub).
4. [PubTables-v2: A New Large-Scale Dataset for Full-Page and Multi-Page Table Extraction](https://arxiv.org/html/2512.10888v3).

