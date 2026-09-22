# 导师阶段进展汇报文档 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一份可直接发送给导师、同时可作为现场讲稿依据的完整中文阶段进展报告。

**Architecture:** 报告由主报告、口头讲稿、导师追问和证据附录组成。所有项目数字从已保存记录提取，模型开放状态只使用截至 2026-09-22 核验过的官方来源，并用证据标签隔离项目实测、论文报告、分析推断和待核验内容。

**Tech Stack:** Markdown、Git、项目已有 JSON/JSONL 指标与日志、官方 arXiv/GitHub/Hugging Face 页面。

## Global Constraints

- 默认使用中文，模型名、指标名、路径和配置保留英文。
- 不把 `PDF-text-assisted` 与 `image-only` 分数直接排名。
- 不把 GriTS 解释为完全正确率。
- 不把历史 dots.ocr 3,522 页结果写成严格 13,871 页全量结果。
- 不把论文报告结果写成项目复现结果。
- 不把所有未测模型笼统称为“没有开源”。
- 不使用 test split 的结果支持开发决策。

---

### Task 1: 建立报告事实矩阵

**Files:**
- Read: `docs/research-progress.zh-CN.md`
- Read: `docs/experiments/2026-09-21-two-baseline-smoke.zh-CN.md`
- Read: `docs/experiments/2026-09-22-historical-dots-full-documents-audit.zh-CN.md`
- Read: `docs/reports/result.md`
- Read: `docs/superpowers/specs/2026-09-22-teacher-progress-report-design.md`

**Interfaces:**
- Consumes: 已保存的样本量、指标、错误数、证据路径和模型开放状态。
- Produces: 主报告使用的四类事实：项目实测、论文报告、推断、待核验。

- [ ] **Step 1: 核对项目实测数字**

核对 TATR 的 `13,384/13,384`、65 个失败、四项主指标，以及 dots.ocr 历史运行的 935 文档、3,522 页、838 个非法 HTML 和四项主指标。

- [ ] **Step 2: 核对协议边界**

确认 TATR 是 `PDF-text-assisted` Cropped Tables；dots.ocr 是 `image-only`；历史 Full Documents 使用真值表格页筛选且没有跨页合并。

- [ ] **Step 3: 核对外部来源**

只使用以下官方页面：PubTables-v2 arXiv 与 Hugging Face、Microsoft Table Transformer GitHub、POTATR arXiv。预期官方 TATR 仓库只列出 TATR-v1.0/v1.1 权重；PubTables-v2 与 POTATR 论文仍表述 code/models will be released。

### Task 2: 撰写主报告

**Files:**
- Create: `docs/reports/teacher-progress-report-2026-09-22.zh-CN.md`

**Interfaces:**
- Consumes: Task 1 的事实矩阵。
- Produces: 可直接发送给导师的正式正文。

- [ ] **Step 1: 写执行摘要和研究问题**

明确 TATR 全量已完成、dots.ocr 严格全量未完成、最相关未测模型缺少已核验官方制品，以及需要导师讨论的算力和研究主线问题。

- [ ] **Step 2: 写数据与评测协议**

解释三个 collection、固定 revision、validation 范围、两条输入赛道和 GriTS/Acc 差异。

- [ ] **Step 3: 写项目结果表**

分别呈现 TATR 正式结果、dots.ocr smoke、dots.ocr 历史筛页结果；在表内标明可比性和限制。

- [ ] **Step 4: 写未测模型说明**

按未发布官方权重/完整制品、商业 API、权重可得但未纳入当前阶段三类说明。

- [ ] **Step 5: 写失败原因与改进方向**

将观察、证据支持解释和待验证推断分段，使用 precision/recall、长宽表分布、exact-match 敏感性和模型能力边界解释结果。

- [ ] **Step 6: 写下一阶段和导师决策项**

提出 TATR 误差分析、continuation、直接纵向拼接、oracle/predicted continuation、对齐感知重建和消融，并列出三个导师决策问题。

### Task 3: 添加现场汇报材料

**Files:**
- Modify: `docs/reports/teacher-progress-report-2026-09-22.zh-CN.md`

**Interfaces:**
- Consumes: Task 2 正文。
- Produces: 3–5 分钟讲稿和至少 8 个追问答复。

- [ ] **Step 1: 写口头汇报稿**

按“目标—完成工作—关键结果—未测原因—问题—下一步—请老师决策”组织，数字与正文一致。

- [ ] **Step 2: 写导师追问与回答**

覆盖为什么只测两个模型、为什么不测 POTATR、TATR 为何分低、GriTS 与 Acc 差异、65 个失败、dots.ocr 暂停、论文可行性、创新点和下一步最小实验。

- [ ] **Step 3: 添加证据附录**

列出本地文档、服务器 predictions/metrics/logs/checksums 路径和官方外部来源。

### Task 4: 一致性核验与进度索引更新

**Files:**
- Modify: `docs/research-progress.zh-CN.md`
- Verify: `docs/reports/teacher-progress-report-2026-09-22.zh-CN.md`

**Interfaces:**
- Consumes: 完整报告。
- Produces: 可恢复的项目进度入口和通过检查的报告。

- [ ] **Step 1: 将报告加入进度索引**

在恢复入口加入正式汇报文档链接，不改变已有实验结论。

- [ ] **Step 2: 扫描未完成标记和禁用表述**

Run: `rg -n "TODO|TBD|待补|所有模型都没有开源|已经完成 dots.ocr 全量" docs/reports/teacher-progress-report-2026-09-22.zh-CN.md`

Expected: 无输出。

- [ ] **Step 3: 核对关键数字出现且一致**

Run: `rg -n "13,384|0\.7429|0\.7168|0\.0164|0\.0069|65|3,522|13,871|838|0\.6216|0\.1380" docs/reports/teacher-progress-report-2026-09-22.zh-CN.md`

Expected: 所有关键数字均能定位到结果或限制说明。

- [ ] **Step 4: 检查 Markdown 和 Git 差异**

Run: `git diff --check`、`git diff --stat`、`git status --short --branch`

Expected: `git diff --check` 无错误；差异只包含目标报告和进度索引。

- [ ] **Step 5: 提交报告**

Run: `git add docs/reports/teacher-progress-report-2026-09-22.zh-CN.md docs/research-progress.zh-CN.md`，然后 `git commit -m "docs: add advisor progress report"`。
