# 项目研究进度

最后更新：2026-09-22（Asia/Shanghai）

当前分支：`codex/two-baseline-validation-local`

本地 HEAD：`038100f45a4ff16c8bac77dfa2837d2b86ddf0d8`（本文档修订尚未提交）

## 1. 恢复工作入口

上下文压缩、任务中断或更换 Agent 后，依次阅读：

1. 根目录 `AGENTS.md`；
2. 本文档；
3. `docs/research-handoff-2026-08-26.zh-CN.md`；
4. `docs/reports/teacher-progress-report-2026-09-22.zh-CN.md`；
5. 与当前任务相关的 `docs/experiments/` 最新记录；
6. 服务器 `/data01/public/zhengguojie/paper` 中本文列出的日志、预测和指标。

本文是状态索引，不替代详细实验记录。服务器保存的原始日志、预测、指标和校验和是实验完成情况的主要证据。

## 2. 当前阶段结论

当前处于“公开基线 validation 复现、评测实现校正与误差分析”阶段。TATR-v1.1-Pub 的 Cropped Tables validation 全量推理已经完成；2026-09-22 发现旧预测 HTML 将表头序列化为缺少 `<tr>` 的 `<thead><th>...</th></thead>`，导致 GriTS 解析时表头行号错误。项目已从保存的 `raw_output.cells` 重建规范 HTML 并完成全量重新评分。dots.ocr 的新严格协议目前只完成 Cropped Tables 和 Full Documents smoke，尚未完成两条全量运行。

接管前已有一次 dots.ocr Full Documents validation 历史运行。该运行覆盖全部 935 篇 validation 文档中的 3,522 个真值表格所在页面，但没有覆盖完整的 13,871 页，也没有进行跨页合并。因此它是有价值的历史基线证据，但不能称为当前严格协议下的 Full Documents 全量端到端结果。

## 3. 状态总表

| 工作项 | 状态 | 覆盖 | 当前可用结论 |
| --- | --- | ---: | --- |
| PubTables-v2 固定版本数据 | 已完成 | revision `aa575e798cb00a296925e2086addb3e3fd9a1903` | Full Documents train/val/test 已在服务器；Cropped Tables val 四类文件各 13,384 个，关联检查通过 |
| TATR-v1.1-Pub / Cropped Tables smoke | 已完成 | 4/4 | 流程、真值关联和离线复评通过 |
| TATR-v1.1-Pub / Cropped Tables full validation | 已完成推理、HTML 序列化修复与重新评分；有 65 个推理失败待后续分析 | 13,384/13,384；missing/extra/duplicate 均为 0 | 修正后 `Acc-Con=0.3827`，可作为 PDF-text-assisted 正式 validation 基线；旧 `Acc-Con=0.0069` 受序列化缺陷影响，已失效 |
| dots.ocr / Cropped Tables smoke | 已完成 | 4/4 | image-only 流程通过；1 个 runner warning |
| dots.ocr / Cropped Tables full validation | 计划中，未启动 | 0/13,384（严格全量） | 尚无正式全量指标 |
| dots.ocr / Full Documents smoke | 已完成 | 1 文档、3/3 页 | 包含无表页；未做跨页合并；仅用于流程验证 |
| dots.ocr / Full Documents 历史筛页运行 | 已完成，但协议不符合当前严格定义 | 935 文档、3,522/13,871 页 | 仅真值表格所在页；未做跨页合并；指标不可与严格全页结果直接等价比较 |
| dots.ocr / Full Documents strict full validation | 计划中，未启动 | 0/13,871（严格全页） | 尚无正式严格全页指标 |
| continuation 与跨页合并基线 | 未开始 | — | 待两个页面抽取基线证据链稳定后单独设计 |

## 4. TATR-v1.1-Pub 正式全量结果

### 4.1 固定条件

- collection / split：PubTables-v2 `Cropped Tables/val`
- 数据 revision：`aa575e798cb00a296925e2086addb3e3fd9a1903`
- 模型 revision：`372e205368a9b7bd1b9fdcf906c1350999d48939`
- 输入赛道：`PDF-text-assisted`
- 输入数：13,384 张裁剪表格图像及对应 PDF Direct Text
- 推理 run ID：`20260921T082639Z-tatr-cropped-val-full`
- 原始评分 run ID：`20260921T163325Z-tatr-cropped-val-offline-score-bg`（受 HTML 序列化缺陷影响，保留作审计，不作为正式结果）
- 修正评分 run ID：`20260922T095039Z-tatr-cropped-val-rebuilt-score`

### 4.2 覆盖与指标

| 指标 | 结果 |
| --- | ---: |
| coverage | 13,384/13,384 |
| missing / extra / duplicate | 0 / 0 / 0 |
| inference errors | 65 |
| predicted tables | 13,317 |
| invalid table HTML | 0 |
| GriTS-Top | 0.8848063827 |
| GriTS-Con | 0.8703867933 |
| Acc-Top | 0.3897190675 |
| Acc-Con | 0.3826957561 |
| Topology precision / recall | 0.8406092444 / 0.9339089889 |
| Content precision / recall | 0.8269099308 / 0.9186891800 |

修正运行正常退出，退出码为 0；重建后的 13,384 条预测覆盖完整，`invalid_table_html=0`。修正 metrics SHA-256 为 `b089d5fd59f4445d41b2348cfccdd5510826a6c73df1e31e8e47c873338b58d0`，重建预测 SHA-256 为 `f762d8017637f4f77e43a7f8f54edeb07630df7186fc1e6513e13577a9e83f2f`，失败清单 SHA-256 仍为 `8db22441ba3f0d7d088931ceb3270b010c3a2e160ee93b330c12bd07b05f15a7`。

旧评分得到 `GriTS-Top=0.7429`、`GriTS-Con=0.7168`、`Acc-Top=0.0164`、`Acc-Con=0.0069`。这些数值可复算，但输入 HTML 语义错误，因此只能用于说明评测实现缺陷的影响，不得继续作为模型能力结论。24 张固定分层样本在修复前为 `0/24` exact，修复后为 `9/24` exact；全量 `Acc-Con` 随后由 `0.0069` 修正为 `0.3827`。

### 4.3 证据路径

- predictions：`outputs/baselines/tatr-v1.1-pub/20260921T082639Z-tatr-cropped-val-full/predictions.jsonl`
- inference log：`logs/baselines/tatr-v1.1-pub/20260921T082639Z-tatr-cropped-val-full/inference.log`
- GPU log：`logs/baselines/tatr-v1.1-pub/20260921T082639Z-tatr-cropped-val-full/gpu-memory.log`
- rebuilt predictions：`outputs/baselines/tatr-v1.1-pub/20260922T095039Z-tatr-cropped-val-rebuilt-score/predictions.jsonl`
- metrics：同目录 `metrics.json`
- failures：同目录 `failures.jsonl`
- checksums 与元数据：同目录 `checksums.sha256`、`run-metadata.json`、`git-commit.txt` 和 `COMPLETE`
- rebuild / score logs：`logs/baselines/tatr-v1.1-pub/20260922T095039Z-tatr-cropped-val-rebuilt-score/`
- 详细实验记录：`docs/experiments/2026-09-22-tatr-html-rebuild-rescoring.zh-CN.md`

修正评分的服务器代码提交为 `8f3e453497389c70909ecb742fc4c7a566b578e6`，运行元数据和完整命令已保存。原始全量推理仍缺少独立的正式 run manifest，需继续依靠原推理日志、预测校验和与同步记录追溯。

## 5. dots.ocr 当前结果边界

### 5.1 新严格协议 smoke

详细记录见 `docs/experiments/2026-09-21-two-baseline-smoke.zh-CN.md`。

- Cropped Tables：4/4，`GriTS-Top=0.68224`，`GriTS-Con=0.40857`，`Acc-Top=0.25`，`Acc-Con=0.25`；仅为困难样本 smoke。
- Full Documents：文档 `PMC11977379` 的全部 3 页，包含 1 个无表页；`GriTS-Top=0.81967`，`GriTS-Con=0.81929`，`Acc-Top=0`，`Acc-Con=0`；未做跨页合并，仅为单文档 smoke。
- 严格 Full Documents 全量输入清单已固定为 13,871 页，SHA-256 为 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`。

### 5.2 接管前历史 Full Documents 运行

详细核验见 `docs/experiments/2026-09-22-historical-dots-full-documents-audit.zh-CN.md`。

历史指标为 `GriTS-Top=0.6563578710`、`GriTS-Con=0.6216124466`、`Acc-Top=0.2759953614`、`Acc-Con=0.1379976807`，但输入恰好等于真值表格所在的 3,522 页，漏掉 10,349 个 validation 页面，并有 838 个非法 table HTML。旧评分器虽然写出 `scope=full_validation`，当时并没有严格全页覆盖门禁，因此该字段不能作为严格全量完成证明。

## 6. 当前限制与决策

- TATR 的 65 个推理失败暂时不阻塞下一阶段，但必须继续保留失败清单，论文中不得隐藏；它们约占 0.49%，不能解释剩余约 61.7% 的 `Acc-Con` 非完全匹配样本。
- 修正后 `Acc-Top=0.3897` 与 `Acc-Con=0.3827` 仅相差约 0.7 个百分点，说明当前 PDF Direct Text 设置下，严格失败主要来自结构而不是额外的内容错误；precision 仍低于 recall，后续优先检查额外行列、列过分割、复杂表头和 span。
- TATR 是 `PDF-text-assisted`，dots.ocr 是 `image-only`，两者不能作为同输入条件的直接优劣排名。
- dots.ocr 两条全量任务预计耗时较长，必须使用可恢复分片、互斥输入清单和新的时间戳目录；启动前重新检查共享 GPU 状态。
- 旧 dots.ocr Full Documents 指标只能标注为“真值表格页筛选、无跨页合并的历史结果”，不得用于声称已经完成严格 Full Documents 评测。
- 当前阶段只使用 validation；不得使用 test split 调整提示词、规则、阈值或模型。

## 7. 后续工作

1. 对修正后的 TATR 失败结果做 60–80 张分层抽样，并按长表、宽表、长且宽、复杂表头和 spanning cell 报告错误类型。
2. 做 oracle 行数、列数、表头、span 和文字归属消融，确定严格正确率的首要瓶颈。
3. 将列过分割、表头层级和 span 一致性纳入约束化结构修复基线，并保留修复前后 paired 结果。
4. 建立 continuation 与直接纵向拼接基线，随后研究跨页列对应、重复表头和拆分行的多关系约束重建。
5. dots.ocr 两条全量任务继续作为算力决策项，不阻塞上述结构分析；如启动，仍须按严格全页协议运行。

## 8. 本次更新依据

- 本地：`docs/experiments/2026-09-21-two-baseline-smoke.zh-CN.md`
- 本地：`docs/superpowers/specs/2026-09-21-two-baseline-complete-validation-design.md`
- 服务器：本文件第 4、5 节列出的原始预测、日志、指标与校验和
- 服务器：`20260922T095039Z-tatr-cropped-val-rebuilt-score` 的重建预测、metrics、failures、checksums、运行元数据和退出码
- 本地：`docs/experiments/2026-09-22-tatr-html-rebuild-rescoring.zh-CN.md`
- 2026-09-22 只读集合核验：Full Documents validation 共 13,871 页；历史预测 3,522 页；真值表格所在页 3,522 页；两集合完全相同；历史预测之外还有 10,349 页
