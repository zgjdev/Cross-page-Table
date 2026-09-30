# 项目研究进度

最后更新：2026-09-30 04:07 UTC

当前分支：`main`（2026-09-30 04:07 UTC 提交前核对；此前记录的分支为历史状态）

提交前 HEAD：`e615493`（2026-09-30 04:07 UTC 核对；此前记录的 `038100f45a4ff16c8bac77dfa2837d2b86ddf0d8` 为历史状态）

## 1. 恢复工作入口

上下文压缩、任务中断或更换 Agent 后，依次阅读：

1. 根目录 `AGENTS.md`；
2. `docs/research-memory.zh-CN.md`（当前状态和下一步）；
3. 本文档；
4. `docs/research-handoff-2026-08-26.zh-CN.md`；
5. `docs/reports/teacher-progress-report-2026-09-22.zh-CN.md`；
6. `docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md`；
7. 与当前任务相关的 `docs/experiments/` 最新记录；
8. 服务器 `/data01/public/zhengguojie/paper` 中本文列出的日志、预测和指标。

本文是状态索引，不替代详细实验记录。服务器保存的原始日志、预测、指标和校验和是实验完成情况的主要证据。

## 2. 当前阶段结论

当前处于“公开基线 validation 复现、评测实现校正与误差分析”阶段。TATR-v1.1-Pub 的 Cropped Tables validation 全量推理已经完成；2026-09-22 发现旧预测 HTML 将表头序列化为缺少 `<tr>` 的 `<thead><th>...</th></thead>`，导致 GriTS 解析时表头行号错误。项目已从保存的 `raw_output.cells` 重建规范 HTML 并完成全量重新评分。dots.ocr 的新严格协议目前只完成 Cropped Tables 和 Full Documents smoke，尚未完成两条全量运行。

接管前已有一次 dots.ocr Full Documents validation 历史运行。该运行覆盖全部 935 篇 validation 文档中的 3,522 个真值表格所在页面，但没有覆盖完整的 13,871 页，也没有进行跨页合并。因此它是有价值的历史基线证据，但不能称为当前严格协议下的 Full Documents 全量端到端结果。

## 3. 状态总表

### 3.0a 2026-09-30 04:07 UTC 提交前检查点

- 本轮只准备提交已有研究代码与文档：全量测试 149 项通过；11 个新增 Python 文件的 Ruff check/format 通过，`git diff --check` 通过；测试临时目录为 `artifacts/test-runs/20260930-precommit-full-01/`。
- 本轮没有启动下载、GPU 推理或训练；OCRFlux 数据、模型权重、日志及生成产物仍留在项目内原路径，不纳入 Git。后续仍须在启动任何 GPU 任务前重新检查资源，并先做短 smoke。

### 3.0 2026-09-29 10:41 UTC 检查点

- GPU 未启动新任务。已完成外部 OCRFlux HTML 补集下载：revision `10f47124646489a33c9c9c049707d7e710b00a31`，9,064 条 JSONL、9,064 张图片，字段和 SHA-256 审计通过；详细记录见 `docs/experiments/2026-09-29-ocrflux-pubtabnet-cross-download.zh-CN.md`。
- 下一步：不把该补集与 PubTables-v2 主指标混算；先在 CPU 上完成 HTML-only 读取/去重审计和 OCRFlux 官方合并接口核验，GPU 可用后再决定是否运行主数据集推理。

| 工作项 | 状态 | 覆盖 | 当前可用结论 |
| --- | --- | ---: | --- |
| PubTables-v2 固定版本数据 | 已完成 | revision `aa575e798cb00a296925e2086addb3e3fd9a1903` | Full Documents train/val/test 已在服务器；Cropped Tables val 四类文件各 13,384 个，关联检查通过 |
| TATR-v1.1-Pub / Cropped Tables smoke | 已完成 | 4/4 | 流程、真值关联和离线复评通过 |
| TATR-v1.1-Pub / Cropped Tables full validation | 已完成推理、HTML 序列化修复与重新评分；有 65 个推理失败待后续分析 | 13,384/13,384；missing/extra/duplicate 均为 0 | 修正后 `Acc-Con=0.3827`，可作为 PDF-text-assisted 正式 validation 基线；旧 `Acc-Con=0.0069` 受序列化缺陷影响，已失效 |
| TATR Cropped Tables 案例分析可视化 | 实时服务已实现并通过本地测试；服务器启动核验待完成 | 13,384 例按需加载；每次只评分当前案例 | 同屏比较原图、GT 和预测；支持前后翻页、ID 跳转和浏览留痕；自动错误标签仅是诊断线索 |
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

1. 在服务器启动实时案例浏览服务，按 manifest 顺序人工浏览并记录代表案例；不再等待全量预计算。详细记录见 `docs/experiments/2026-09-24-tatr-live-case-browser.zh-CN.md`。
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
- 本地：`docs/experiments/2026-09-24-tatr-case-analysis-visualization.zh-CN.md`
- 本地：`docs/experiments/2026-09-24-tatr-live-case-browser.zh-CN.md`
- 2026-09-22 只读集合核验：Full Documents validation 共 13,871 页；历史预测 3,522 页；真值表格所在页 3,522 页；两集合完全相同；历史预测之外还有 10,349 页
- 2026-09-23：导师汇报文档调整为宏观讨论版，移除运行级实现过程和异常明细；完整技术证据继续保留在实验记录和服务器产物中。

## 9. 2026-09-29 跨页研究补充调研

已完成对 `docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md` 的补查和修订。详细记录见 `docs/experiments/2026-09-29-cross-page-literature-followup.zh-CN.md`。

- **已完成：**补入 MinerU-Popo。论文报告的 `92.7%` 是局部分页边界 merge-method prediction accuracy，不是完整逻辑表格 `Acc-Con`、GriTS 或 TEDS。
- **已完成：**补充 MonkeyOCR v1.5 的 `Type-Guided Table Merging`，覆盖重复表头、无表头续接和拆分行，但没有把能力展示误写成可比较的跨页定量结果。
- **已完成：**记录 PaddleOCR-VL-1.5 的 cross-page table merging 工程能力，标记为相关候选基线，未纳入跨页排行榜。
- **结论边界：**原报告关于“缺少统一、可横向比较的真实跨页整表恢复基准”的核心判断仍成立；补查没有发现可替代 PubTables-v2 严格端到端协议的新公开结果。
- **下一步：**优先审计 MinerU-Popo 的输入输出、许可证和评测脚本；在固定页面解析结果上建立局部边界合并与最终整表恢复的 paired 后处理基线。

## 10. 2026-09-29 四模型跨页评测设计

- **状态：计划中，尚未开始下载、预处理或模型推理。**实验协议及 GPU 资源门禁详见 `docs/2026-09-29-cross-page-four-model-evaluation-design.zh-CN.md`；本轮仅只读查看 GPU 和磁盘快照，未更改数据及产物。
- PubTables-v2 主实验只对跨**不同页面**的真实逻辑表计 cross-page-only 指标，但推理输入仍须为 validation 935 篇文档的全部 13,871 页，同时辅报全表文档指标和误合并。OCRFlux 外部 HTML 数据单列为合成片段纯拼接实验，不与图像端到端结果混排。
- **资源快照（2026-09-29 09:03 UTC）：**4 张 A100-SXM4-80GB 都有已有 compute 进程；GPU 0/1/2/3 空余显存约 48/0.4/17/11 GiB，GPU 3 利用率 100%。仅属瞬时观察，不表示任何卡空闲或可抢占。GPU 实验须在重新检查、确认可用窗口和小样本显存标定之后再开始。
- **下一关口：**只读审计跨页真值与负例清单、完成匹配/评分单元测试并固定四模型接口及版本，然后再决定下载和 GPU smoke；不要把已有 dots.ocr 的真值筛页且未合并的历史结果当作严格全页跨页分数。
- **2026-09-29 执行细化：**同一设计文档第 6 节已增补现有与待下载资源清单、官方固定版本下载命令模板、公开资源镜像与凭证保护、无文字层 PDF 派生、OCRFlux/Popo/Paddle 输入转换、GPU smoke 和全量运行/离线复评的具体步骤；明确已有脚本与待实现 adapter 的边界。该修订仍为计划，尚无新增下载或实验结果。

## 11. 2026-09-29 阶段 0：跨页数据清单审计

**状态：已完成，只限 PubTables-v2 validation 数据审计；尚未下载新模型/外部数据、尚未做模型推理或 GPU 训练。**完整命令、环境、问题和校验和见 `docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md`。

- 新脚本与测试：`scripts/build_cross_page_manifest.py`、`tests/test_build_cross_page_manifest.py`；最终产物：`artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/`。先前运行 `20260929T093222Z-cross-page-val-audit` 保留作可追溯记录，没有覆盖。
- 输入覆盖：935 篇 validation 文档、全部 13,871 页；全页 manifest SHA-256 仍为 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`；只按文件名检查 train/val/test 文档 ID，不交叉，test 标签内容未读取。
- 按逻辑表 `parts.page_num` 派生出 **983 张真正跨不同页面的表、来自 869 篇文档**；63 张多片段但仅同页的表被排除。官方相邻页续接标签为 **1,276 正例、786 负例**，与逻辑表相邻片段的冲突 0 项；跨页表身份属于源逻辑表信息，列对齐/重复表头/拆分行仍无官方细粒度标签。
- 异常：`PMC12274235-table-1` 的页号为 `[4,5,7]`；第 5→7 页不能冒充相邻续接页对，已写入独立 `nonadjacent-part-gaps.jsonl`。全部生成 JSONL 哈希与 `summary.json` 一致；回归测试 115 项通过、Ruff 通过。
- **下一步：**先在 train 设计并测试文档级一对一匹配与跨页子集评分器，再审核外部 OCRFlux HTML 集和三个新增模型的许可/下载；按现有 GPU 门禁决定 smoke。旧 dots.ocr 真值筛页结果仍不能充当此次全页跨页分数。

## 12. 2026-09-29 阶段 1（部分）：跨页离线评分器

**状态：离线评分器及测试已完成，模型 adapter、四模型实测和 GPU smoke 尚未开始。**协议、核验和边界见 `docs/experiments/2026-09-29-cross-page-offline-scorer.zh-CN.md`。

- 新增 `src/cptla/evaluation/cross_page.py`、`scripts/score_cross_page_predictions.py` 和 `tests/evaluation/test_cross_page.py`；先按文档全部真值与全部合法预测表使用 GriTS-Con Hungarian 一对一匹配，再取真实跨页表子集；要求完整逐页终态和文档表来源页。
- 全量回归 **129 passed**，Ruff 与 `git diff --check` 通过；validation 异常文档 `PMC12274235` 的 16 页/4 真值表/2 跨页表空预测核验通过，`[4,5,7]` 来源页保持原样。此项不是模型性能结果；未运行 GPU、下载、训练或 test 评测。
- **下一步：**对齐四模型官方输出 schema 并做 adapter/mock 测试；语义误合并率、续接指标和 TEDS 尚未实现，不能从当前来源页异常计数冒称已完成。

## 13. 2026-09-29 长期留痕机制

**状态：约束和恢复入口已更新；不代表模型实验有新增结果。**用户明确要求长期任务定期总结、不依赖对话记忆；根目录 `AGENTS.md` 已固化子阶段、连续工作约 60 分钟、后台任务变化及结束/中断前的检查点要求。新增 `docs/research-memory.zh-CN.md` 作为可持续更新的研究记忆和下一步入口；本进度索引保留阶段历史与实验记录链接，`docs/experiments/` 保存复现证据。今后每轮结束核对三者，旧结论更正要保留证据并追加勘误；不能宣称离线自动记录。

## 14. 2026-09-29 dots.ocr 无合并 adapter 与真实 smoke 闭环

**状态：阶段 1 的 dots.ocr `no_merge` 子阶段已验收，四模型完整阶段仍未完成。**详细命令、输入输出 SHA、运行清单、错误及边界见 `docs/experiments/2026-09-29-dotsocr-no-merge-document-adapter-smoke.zh-CN.md`。

- 新增 `src/cptla/evaluation/dotsocr_document.py`、`scripts/adapt_dotsocr_document_predictions.py`、`tests/evaluation/test_dotsocr_document.py`，修订 `scripts/score_cross_page_predictions.py` 的部分文档真值过滤。旧 dots.ocr 三页真预测转换为 3 个覆盖状态、1 张文档表、1 条源布局证据；产物保留在两个独立的带时间戳目录，离线复评哈希逐项一致；**135 passed**、Ruff 及 diff check 通过。无下载、新 GPU 推理或训练。
- **重要勘误：**此前对话中口头误称该 smoke 文档无跨页表。原始 `PMC11977379` 唯一真值表实际跨 `[1,2]` 页；预测只来自第 1 页。因此单文档来源页缺失一页，grid exact 0/1。此处只有 `partial/smoke` 协议检查，不能用局部内容 GriTS 当整表成功率，不能外推为 validation 全量或四模型比较。
- **下一步：**在 train/合成文档设计无真值续接与简单拼接，隔离此 val smoke 不调规则；核验其余三模型官方接口/许可及权重；之后重新检查 GPU 再考虑完整文档推理。

## 15. 2026-09-29 dots.ocr 重复表头简单拼接基线

**状态：代码/结构单测与旧 validation smoke 核验完成，真实 train 正负例误连率仍待评测。**规则、命令、哈希、负例及限制详见 `docs/experiments/2026-09-29-dotsocr-repeated-header-simple-merge-baseline.zh-CN.md`。

- 新增 `src/cptla/evaluation/simple_merge.py`、`scripts/merge_dotsocr_repeated_header.py`、`tests/evaluation/test_simple_merge.py`；只尝试邻页边界表、列数一致、重复表头一致且 bbox 处于预设页底/页顶区域，不凭 GT 指定页对。合成正例/负例与 train 真值整表人工行切分只用于软件正确性；发现“页边、表头和列数都相同的无关表仍可能被误连”这一重要限制。
- 规则冻结后旧 val 三页 smoke 无第 2 页预测表，候选/合并均为 **0**，输出表及评分文件与 `no_merge` 逐项相同；不能因 GT 表跨 `[1,2]` 就假造缺失页。全量回归 **149 passed**，Ruff 与 diff check 通过；无下载、新 GPU 推理或训练。
- **下一步：**真实 train 完整文档的页级预测及官方相邻页正负例审计尚缺，不能报告续接精度或端到端增益；按资源门禁决定是否先做 train 小规模推理，或先核验其余三个模型的官方接口和许可。

## 16. 2026-09-29 全量 GPU 推理启动条件澄清

**状态：只读核验及计划纠偏，未启动 GPU 或全量推理。**先前把“尚无真实 train 预测、无法验证简单拼接误连率”误当成 dots.ocr 页级全量推理的前置限制。实际上本地权重 `checkpoints/dots-ocr/` 和 validation 13,871 页全页 manifest 均已存在；完整清单 SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`。**可以先按全页输入做 dots.ocr image-only 推理；后续再配对复评 no-merge 与简单拼接。**研究上对真实 train 负例审计的缺口仍在，但不阻止保存未筛页的模型输出。

2026-09-29 10:20 UTC 的 `nvidia-smi --query-gpu`/`--query-compute-apps` 只读快照：GPU 0/1/2/3 空余显存分别约 48,737/423/11,033/13,321 MiB；GPU 0 上有 4 个 compute 进程，其他卡亦已有进程，GPU 3 利用率 100%。这不是独占许可或未来运行窗口。启动前须再次核查进程/显存并确认共享使用不会干扰既有任务，先做短显存标定；按完整文档拆互斥新分片，写入独立预测、日志、PID/命令/环境、输入及输出 SHA 和恢复清单。没有达成资源门禁时只准备离线任务，不抢占或终止他人进程；目前**无全量模型分数**。
