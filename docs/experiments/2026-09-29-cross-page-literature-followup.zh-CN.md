# 跨页表格研究补充调研记录

日期：2026-09-29（UTC）

状态：已完成文献补查；未运行模型、未下载数据、未使用 GPU、未修改 `data/`、`artifacts/`、`outputs/` 或 `logs/`。

## 1. 研究问题

核查 `docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md` 是否遗漏了 2026 年前后公开的跨页表格恢复/后处理方法，并区分：

- 局部分页边界决策；
- 已知结构片段的纯拼接；
- 自然跨页文档的端到端恢复；
- 仅声明支持跨页的通用文档解析器。

## 2. 核验来源与方法

采用官方 arXiv HTML、官方 GitHub 仓库和已有项目文档交叉核对。重点检查论文是否给出公开数据、输入输出定义、独立跨页指标以及是否能与 PubTables-v2 `Acc-Con`/`GriTS`/`TEDS` 比较。

本轮核验的主要来源：

1. MinerU-Popo，<https://arxiv.org/abs/2605.24973>；官方仓库 <https://github.com/opendatalab/MinerU-Popo>。
2. MonkeyOCR v1.5，<https://arxiv.org/abs/2511.10390>。
3. PaddleOCR-VL-1.5，<https://arxiv.org/abs/2601.21957>。
4. 项目已有记录：`docs/reports/teacher-progress-report-2026-09-22.zh-CN.md`。

## 3. 核验结果

### 3.1 MinerU-Popo 是上一版遗漏的关键相关工作

**已核验：**MinerU-Popo 将跨页表格恢复作为 OCR 输出的文档级后处理。表格截断任务先判断相邻页片段是否属于同一表，再逐列判断分页边界的两个单元格是否应保持分开或语义合并。论文描述了约 `30K` 的任务化合成数据、轻量 `4B` post-processing model 和面向长文档的 dynamic chunking。

论文在 PostDocBench 表格截断任务上报告 `92.7%` 的 merge-method prediction accuracy，约对应 `1,317` 个 cell-level merge units。该数字是局部边界决策准确率，不是完整逻辑表格的 `Acc-Con`、`GriTS` 或 TEDS；论文摘要中的 title-hierarchy `TEDS=90.6` 也不是表格指标。

**结论：**必须纳入相关工作和候选后处理基线，但不能把 `92.7%` 写成跨页整表恢复率。下一步需审计其输入输出、许可证和评测脚本，再决定是否接入 PubTables-v2 固定页面解析结果。

### 3.2 MonkeyOCR v1.5 提出了明确的跨页合并模块，但缺少可比专用结果

**已核验：**MonkeyOCR v1.5 的 `Type-Guided Table Merging` 覆盖三种模式：重复完整表头、无表头续接、分页处拆分行。方法描述包含列 schema 对齐、span 冲突处理和表头 token 归一化。

**待核验/未发现：**本轮没有找到在 PubTables-v2 或公开跨页专用测试集上报告可复核 `Acc-Con`、跨页子集 TEDS 或局部 merge accuracy 的结果。论文中的能力对比和案例不能替代定量评测。

### 3.3 PaddleOCR-VL-1.5 是工程相关基线，不是当前可比较的跨页研究结果

**已核验：**PaddleOCR-VL-1.5 的文档解析管线包含 cross-page table merging 后处理能力。

**待核验/未发现：**本轮没有找到独立跨页恢复指标、公开同协议数据或可直接复现的 PubTables-v2 Full Documents 结果。因此应列为 image-only/通用 VLM 候选基线，而不是纳入跨页方法排行榜。

## 4. 对原报告完整性的修正判断

原报告的核心判断仍成立：公开研究缺少“真实跨页图像片段输入、隔离上游误差、最终整表严格 exact match”的统一基准；续接分类和局部 merge decision 的高分不能替代整表恢复指标。

需要修正的地方：

1. 补入 MinerU-Popo，并明确其 `92.7%` 的局部决策指标含义。
2. 将 MonkeyOCR v1.5 的 Type-Guided Table Merging 列为方法线索和候选基线，但不虚构其跨页定量结果。
3. 将 PaddleOCR-VL-1.5 列为相关工程系统，不能把“支持 cross-page merging”解释为已公开的跨页 SOTA。
4. 后续实验应增加“固定上游页面输出、只评估跨页后处理”的隔离轨道，以便与 MinerU-Popo 的问题定义对齐。

## 5. 证据边界与下一步

- 已提供：论文/官方项目明确的方法描述和论文报告指标。
- 推断：MinerU-Popo 的局部决策分解可作为本项目的后处理基线设计参考。
- 待核验：MinerU-Popo 合成截断分布与 PubTables-v2 自然分页分布的差异；其官方脚本能否处理本项目的固定页面输出；MonkeyOCR/PaddleOCR-VL 是否提供独立可调用的跨页评测接口。

本轮没有新增项目实验结果，不改变当前 PubTables-v2 validation 基线和数据版本结论。
