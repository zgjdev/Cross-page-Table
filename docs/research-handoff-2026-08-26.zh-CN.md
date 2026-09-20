# 跨页表格恢复研究交接文档

更新时间：2026-08-26  
项目目录：`D:\paper`（服务器对应 `/data01/public/zhengguojie/paper`）  
数据版本：PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`

## 1. 研究背景

学术论文、技术报告和长文档中的表格经常跨越多个页面。逐页检测可以找到页面上的表格片段，但并不能保证把片段恢复成同一张逻辑表格。跨页恢复的主要困难包括：

- 前页和后页的列边界可能有轻微漂移，不能只按页面坐标直接拼接；
- 后页可能重复、缩短或省略表头；
- 一个单元格或一行可能在页面边界处被拆开；
- 脚注、页眉页脚和正文可能出现在表格片段之间；
- 续表判断正确，也不代表最终列对应、单元格拓扑和内容完全正确。

现有公开结果表明，严格的内容感知完全匹配指标仍然很难。项目中的文献报告指出，PubTables-v2 Full Documents 上的公开结果同时受到页面检测、结构解析、文字识别、续表判断和最终拼接的影响。因此，本研究不能只把问题缩减为“两个页面是否续表”的二分类，而应研究页面片段之间的关系推理和约束重建。

研究依据和已整理的证据位于：

- `docs/table-extraction-and-recovery-research-survey-2026.md`
- `docs/table-extraction-research-execution-plan.md`
- `docs/reports/cross-page-table-core-findings.zh-CN.md`
- `docs/reports/cross-page-table-sota.zh-CN.md`
- `docs/reports/novelty-gate.zh-CN.md`

## 2. 研究目的与拟解决问题

### 2.1 总体目标

在 PubTables-v2 Full Documents 上，建立可复现的、文本感知的文档级跨页表格恢复方法，重点提升跨页表格的结构和内容严格正确率，并以高质量计算机视觉会议或期刊论文为最终交付目标。

### 2.2 核心研究问题

1. 视觉区域、PDF 原生文字 token 和表格结构联合建模，能否超过串行的“结构预测后贴文字”流程？
2. 相比“续表二分类后直接纵向拼接”，文档级关系图推理和联合重解码是否能提升跨页表格的 `Acc-Con`？
3. 改进主要来自原生文字、列对应、重复表头处理、拆分行处理，还是约束解码？
4. 在 image-only 条件下，方法相对于端到端 VLM 的收益和代价如何？

### 2.3 研究边界

本项目不是单纯的 OCR 工程，也不是只追求续表分类 F1 的项目。续表分类是必要的中间任务；最终主张必须由文档级表格重建指标、跨页子集指标、消融实验和错误分析共同支持。

## 3. 数据与环境状态

### 3.1 原始数据

服务器上的 PubTables-v2 `Full Documents` 已完成下载、压缩包校验和解压：

| split | 文档数 | 页面数 |
|---|---:|---:|
| train | 7,359 | 110,347 |
| validation | 935 | 13,871 |
| test | 878 | 12,877 |
| 合计 | 9,172 | 137,095 |

服务器目录：

```text
/data01/public/zhengguojie/paper/data/pubtables-v2/
├── archives/full-documents/{train,val,test}/
└── extracted/Full Documents/{train,val,test}/
```

训练集和验证集的 12 个压缩包均通过精确大小检查和 `gzip -t` 检查；训练集、验证集和测试集的 `images`、`words`、`xml_annotations` 数量均能对应。解压后的 `Full Documents` 约占 49 GB，原始压缩包仍保留在 `archives/` 中。

### 3.2 原始字段

每个 split 的 `Full Documents` 目录包含：

- `images`：页面图像；
- `words`：PDF/OCR 文字 token 与坐标；
- `xml_annotations`：页面级 XML 标注；
- `tables`：逻辑表格、页面片段、单元格和规范化信息；
- `cross_page_table_pairs`：官方页面对续接标签；
- `single_page_table_continuations`：同页表格片段连续关系标签。

### 3.3 Python 环境

- `cptla`：项目 Python 环境，用于标准化、测试、标签构建和后续训练。
- `codex-node`：Codex CLI 的 Node.js 20 环境，不承担项目 Python 任务。
- 当前服务器使用用户账号 `zhengguojie`；禁止使用 root 路径或修改其他账号目录。

## 4. 已完成的软件与预处理

本地已经实现并上传的关键文件：

- `src/cptla/data/pubtables_v2.py`
- `scripts/normalize_pubtables_v2.py`
- `tests/data/test_pubtables_v2.py`
- `tests/test_normalize_pubtables_v2.py`

标准化适配器读取 `tables/*.json`、`words/*.json` 和 `xml_annotations/*.xml`，生成统一的 `DocumentRecord` JSONL。它不会修改原始图片、JSON 或 XML。

实际服务器运行结果：

| split | processed | accepted | rejected | clipped word boxes |
|---|---:|---:|---:|---:|
| train | 7,359 | 7,359 | 0 | 77 |
| validation | 935 | 935 | 0 | 15 |
| test | 878 | 878 | 0 | 9 |
| 合计 | 9,172 | 9,172 | 0 | 101 |

生成文件：

```text
artifacts/normalized/train-documents.jsonl
artifacts/normalized/train-rejects.jsonl
artifacts/normalized/validation-documents.jsonl
artifacts/normalized/validation-rejects.jsonl
artifacts/normalized/test-documents.jsonl
artifacts/normalized/test-rejects.jsonl
```

三个 `*-rejects.jsonl` 当前均为空。`clipped_word_boxes` 表示少量 OCR 文字框轻微越过页面边界，标准化时将文字框限制回页面范围；表格片段框仍使用严格边界校验。原始数据没有被裁剪或覆盖。

## 5. 官方跨页标签审查结果

`cross_page_table_pairs` 的字段统一为：

```json
{
  "page_A": "PMC10120619_page_22",
  "page_B": "PMC10120619_page_23",
  "label": 1
}
```

统计结果：

| split | JSON 文件数 | 页面对记录数 | label=1 | label=0 |
|---|---:|---:|---:|---:|
| train | 7,359 | 15,830 | 9,866 | 5,964 |
| validation | 935 | 2,062 | 1,276 | 786 |

这里的官方监督只直接表示页面对是否属于同一张跨页表格。PubTables-v2 不直接提供跨页片段内部的完整行/列框、重复表头身份或拆分行身份。因此：

- `label` 可以称为官方 continuation relation label；
- 列对应、重复表头和拆分行只能作为 derived/weak labels；
- 派生标签必须保存推断规则、置信度、人工审计状态和版本；
- 未经人工审计，不得把派生标签写成官方 ground truth。

## 6. 当前所处阶段

```text
文献调研与新颖性门禁       已完成初稿
原始数据下载与校验         已完成
数据解压                   已完成
统一格式标准化             已完成
官方跨页标签字段审查       已完成
官方关系样本构建           尚未完成
派生结构标签与人工审计     尚未完成
简单跨页基线               尚未完成
模型训练                   尚未开始
正式测试集评估             尚未开始
```

当前最重要的结论是：**数据准备已经完成，但研究实验还没有开始。** 不能把标准化成功误认为模型训练成功，也不能在没有关系样本和基线的情况下直接占用 GPU 训练。

## 7. 下一步行动计划

### 阶段 A：官方关系样本构建

输入：

- `artifacts/normalized/train-documents.jsonl`
- `artifacts/normalized/validation-documents.jsonl`
- `extracted/Full Documents/{train,val}/cross_page_table_pairs/`

输出：

```text
artifacts/labels/train-continuation.jsonl
artifacts/labels/validation-continuation.jsonl
artifacts/labels/continuation-summary.json
```

每条样本应关联文档 ID、页面 A/B、官方 label、页面上的表格片段 ID 与 bbox，并记录无法关联的记录。验收要求：所有官方页面 ID 都能解析；正负样本计数与官方审查结果一致；train 和 validation 不发生文档交叉。

### 阶段 B：派生结构标签与审计

在 `label=1` 的自然跨页样本上，派生：

- 列对应候选及置信度；
- 重复表头候选；
- 跨页拆分行/单元格候选；
- 宽表横向拆分或异常版式标记。

先从 train/validation 抽取约 200–300 个多样化跨页表进行人工审计，覆盖不同页数、列数、复杂表头、脚注、扫描质量和版式。审计结果应报告派生标签精度、拒绝比例和人工一致性；低置信度样本不能直接用于强监督。

### 阶段 C：简单基线与评测接口

至少实现并记录：

1. 官方 continuation label 的规则/频率基线；
2. 续表判断后直接纵向拼接的 baseline；
3. 包含列数、位置、表头文字相似度的轻量关系基线。

所有基线均在 train 上调参、在 validation 上选定，test 只用于最终一次或预先注册的评估。报告 continuation P/R/F1、跨页表结构指标、`TEDS`、`GriTS` 和 `Acc-Con`，并按跨页页数、列数、拆分行和复杂表头分层。

### 阶段 D：模型路线

候选主线是文本感知的文档表格图模型：

```text
页面图像 + PDF word/token
        -> 页面级表格/标题/脚注候选
        -> 表内行列与单元格结构
        -> 文档级片段关系图
        -> 列对应、表头与拆分行联合重解码
        -> 约束校验和规范化 HTML/JSON
```

模型训练必须由每个模块的可验证问题驱动，并安排以下消融：去除 PDF token、去除视觉特征、串行文字后贴 vs 联合解析、无约束 vs 有约束、二分类直接拼接 vs 图推理联合重解码、无 hard negative vs 有 hard negative。

### 阶段 E：论文级实验

正式实验至少包括：

- PDF-text-assisted 赛道：TATR/POTATR 思路的结构基线和文本感知方法；
- image-only 赛道：dots.ocr 或同规模 VLM 对照；
- 跨页子集：续表分类、列对齐、重复表头、拆分行和最终整表重建；
- 错误分析：漏检、行列错误、span 错误、token 归属错误、文字错误、误连/漏连和跨页特殊情况；
- 复现记录：版本、配置、随机种子、GPU、命令、日志、检查点和最终表格。

## 8. 同步与服务器保护原则

服务器已经有约 80 GB 规模的 PubTables-v2 压缩包和解压数据。同步本地代码时只能更新代码、测试、配置和研究文档，必须排除：

```text
data/
artifacts/
outputs/
logs/
.git/
.codex/
```

同步前要确认目标目录是 `/data01/public/zhengguojie/paper`，同步后要检查 `data/pubtables-v2/archives/` 和 `data/pubtables-v2/extracted/` 仍然存在。同步命令不能带有删除远端文件的选项。

## 9. 交接后的第一项任务

同步完成并确认数据目录未变化后，先构建 train/validation 的官方 continuation 关系样本并生成统计报告。该任务不需要 GPU，不下载数据，不修改原始数据。只有关系样本通过字段关联和泄漏检查，才进入派生结构标签审计；只有基线和标签审计通过，才开始 GPU 实验。
