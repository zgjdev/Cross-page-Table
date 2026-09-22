# 项目研究进度

最后更新：2026-09-22（Asia/Shanghai）

当前分支：`codex/two-baseline-validation-local`

本地 HEAD：`db0f4ecd81036db972a0c27f14c3b9a39d4b3efa`

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

当前处于“两个公开基线 validation 复现与协议校正”阶段。TATR-v1.1-Pub 的 Cropped Tables validation 全量推理与两次离线评分已经完成；dots.ocr 的新严格协议目前只完成 Cropped Tables 和 Full Documents smoke，尚未完成两条全量运行。

接管前已有一次 dots.ocr Full Documents validation 历史运行。该运行覆盖全部 935 篇 validation 文档中的 3,522 个真值表格所在页面，但没有覆盖完整的 13,871 页，也没有进行跨页合并。因此它是有价值的历史基线证据，但不能称为当前严格协议下的 Full Documents 全量端到端结果。

## 3. 状态总表

| 工作项 | 状态 | 覆盖 | 当前可用结论 |
| --- | --- | ---: | --- |
| PubTables-v2 固定版本数据 | 已完成 | revision `aa575e798cb00a296925e2086addb3e3fd9a1903` | Full Documents train/val/test 已在服务器；Cropped Tables val 四类文件各 13,384 个，关联检查通过 |
| TATR-v1.1-Pub / Cropped Tables smoke | 已完成 | 4/4 | 流程、真值关联和离线复评通过 |
| TATR-v1.1-Pub / Cropped Tables full validation | 已完成，有 65 个推理失败待后续分析 | 13,384/13,384；missing/extra/duplicate 均为 0 | 可作为 PDF-text-assisted 正式 validation 基线；65 个失败已按空预测计入指标，用户于 2026-09-22 决定现阶段先忽略，不代表问题已解决 |
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
- 评分 run ID：`20260921T163325Z-tatr-cropped-val-offline-score-bg`

### 4.2 覆盖与指标

| 指标 | 结果 |
| --- | ---: |
| coverage | 13,384/13,384 |
| missing / extra / duplicate | 0 / 0 / 0 |
| inference errors | 65 |
| predicted tables | 13,317 |
| invalid table HTML | 0 |
| GriTS-Top | 0.7429088739 |
| GriTS-Con | 0.7167619958 |
| Acc-Top | 0.0163628213 |
| Acc-Con | 0.0068738793 |

两次离线评分均正常退出，指标文件 SHA-256 同为 `95a4388b5387cb63e09538716447ec2e51c9f168314506fd4735556086bbffb8`；失败清单 SHA-256 同为 `8db22441ba3f0d7d088931ceb3270b010c3a2e160ee93b330c12bd07b05f15a7`。

### 4.3 证据路径

- predictions：`outputs/baselines/tatr-v1.1-pub/20260921T082639Z-tatr-cropped-val-full/predictions.jsonl`
- inference log：`logs/baselines/tatr-v1.1-pub/20260921T082639Z-tatr-cropped-val-full/inference.log`
- GPU log：`logs/baselines/tatr-v1.1-pub/20260921T082639Z-tatr-cropped-val-full/gpu-memory.log`
- metrics：`outputs/baselines/tatr-v1.1-pub/20260921T163325Z-tatr-cropped-val-offline-score-bg/metrics-1.json` 和 `metrics-2.json`
- failures：同目录 `failures-1.jsonl` 和 `failures-2.jsonl`
- checksums：同目录 `checksums.sha256`
- score logs：`logs/baselines/tatr-v1.1-pub/20260921T163325Z-tatr-cropped-val-offline-score-bg/`

证据缺口：服务器 `artifacts/run-manifests/` 中目前只发现 TATR smoke manifest，没有发现上述全量推理的正式 run manifest。完整命令、代码 commit 和环境应从现有日志及当时同步记录继续核验，未核验前不得补写为事实。

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

- TATR 的 65 个推理失败暂时不阻塞下一阶段，但必须继续保留失败清单，论文中不得隐藏；如后续分析或对比依赖这些样本，需要单独做错误分类。
- TATR 是 `PDF-text-assisted`，dots.ocr 是 `image-only`，两者不能作为同输入条件的直接优劣排名。
- dots.ocr 两条全量任务预计耗时较长，必须使用可恢复分片、互斥输入清单和新的时间戳目录；启动前重新检查共享 GPU 状态。
- 旧 dots.ocr Full Documents 指标只能标注为“真值表格页筛选、无跨页合并的历史结果”，不得用于声称已经完成严格 Full Documents 评测。
- 当前阶段只使用 validation；不得使用 test split 调整提示词、规则、阈值或模型。

## 7. 后续工作

1. 补齐 TATR 全量运行的 manifest/命令/代码版本证据；只追加元数据，不修改现有预测和指标。
2. 设计并启动 dots.ocr Cropped Tables 全量可恢复分片运行。
3. 设计并启动 dots.ocr Full Documents 13,871 页严格全页运行，不依据真值筛页。
4. 完成两条 dots.ocr 全量离线复评、覆盖检查、manifest 和中文实验记录。
5. 在页面抽取基线稳定后，单独设计 continuation、纵向拼接及对齐感知跨页重建实验。

## 8. 本次更新依据

- 本地：`docs/experiments/2026-09-21-two-baseline-smoke.zh-CN.md`
- 本地：`docs/superpowers/specs/2026-09-21-two-baseline-complete-validation-design.md`
- 服务器：本文件第 4、5 节列出的原始预测、日志、指标与校验和
- 2026-09-22 只读集合核验：Full Documents validation 共 13,871 页；历史预测 3,522 页；真值表格所在页 3,522 页；两集合完全相同；历史预测之外还有 10,349 页
