# 跨页表格恢复：加入 POTATR 后的五方案执行计划

日期：2026-10-20 UTC。**状态：计划更新，不表示新模型已下载或已测。**这是 `docs/2026-09-29-cross-page-four-model-evaluation-design.zh-CN.md` 的增补版本；原四模型计划及其历史结论保留供溯源。本文件用于接下来实际决策；未在此重述的下载安全、镜像核验、环境隔离、GPU 资源门禁和完整留痕要求继续沿用原计划及根目录 `AGENTS.md`。

## 1. 研究问题与不可混同的输入

主任务仍是 **PubTables-v2 Full Documents 的文档级跨页逻辑表恢复**，不是只在已知跨页正例上拼接。固定数据 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`；validation 输入为 935 篇文档 **全部 13,871 页**（含无表页），全页 manifest SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`。真实跨不同页表 983 张；只在离线评分时选择它们，推理不得提供真值框、续接标签或真值筛页。来源和异常见 `docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md`。

- **image-only 赛道：**完整页面图像及从图像自行识别的文字；若使用外部 OCR，固定名称、版本、输出和失败数，标为 `image-only + OCR`。只读 JPEG 封装成无文字层 PDF 不变成 PDF-text-assisted。
- **PDF-text-assisted 赛道：**额外使用官方 PDF 原生 `words/` 和坐标的 Direct Text（`DT`）。绝不拿这一赛道的指标与 image-only 直接作模型优劣排名。
- **诊断轨道（非主结果）：**Full Documents `tables[].parts` 给定来源页、bbox 和同一逻辑表身份后，可从原页派生跨页片段裁剪图，单独测试“已知同表片段 → 完整表”。本地不是现成的跨页片段 JPEG，且没有每片段的官方行/列真值；提供这些真值框及分组相当于 oracle 检测和续接，不得冒称端到端。需有负例才可计算误连；外部 OCRFlux HTML 补集仍独立，不能混入真实图像指标。

## 2. 五方案及配对设置

| 方案 | 完整文档输入和最小配对对照 | 所需模型/管线及现状 | 报告边界 |
| --- | --- | --- | --- |
| dots.ocr | 全页图像；保存逐页输出；同一份预测分别做 `no_merge`、冻结的保守重复表头 `simple_merge` | 权重/全页预测已在本地；2026-10-20 两组 CPU 离线评分已正常结束并核验校验和，待案例/误连审计 | `image-only`；固定解析器，隔离合并增量；不得把全页推理覆盖叫整表恢复 |
| **POTATR（新增，优先页面提取基线）** | 全部完整页面；固定页面预测分别做 `no_merge`、相同简单合并；若取得 PubTables-v2 论文的 ViT-B/16 续接权重或明确复现版本，再单列 `POTATR + continuation + merging` | 官方论文 arXiv:2606.09788 描述 29M 页面图像到表格图模型；**项目内尚无已核实权重/可运行推理管线**，发布状态与许可待核验。还需表格 HTML/网格、bbox 和来源页 adapter | 文字来源必须标出：`POTATR + OCR + merging` 在 image-only；`POTATR + DT + merging` 在 PDF-text-assisted。`+ DT` 不是另一个模型，`+ merging` 才是跨页步骤；并非两者择一。论文 Full Documents 附录 `POTATR + merging` 未明确该行文字来源，不归入任何本项目赛道的直接可比已复现成绩 |
| MinerU-Popo | **同一批固定 dots.ocr 页级预测**分别做项目简单合并与 Popo 后处理；可对固定 POTATR 页输出另做敏感性分析，须明确换了上游 | 权重/源码/转换和完整表输出均待核验；本身不是独立页面识别器 | `image-only + fixed parser` 条件下的配对增量；若只输出局部合并决策，不能编造整表分数 |
| PaddleOCR-VL-1.5 | 全页图像/无文字层派生 PDF；官方重组 `merge_tables=False/True` | 权重、依赖版面组件、固定管线版本、来源页 adapter 尚缺 | `image-only`；其他官方版本不得悄悄替代计划中的 1.5 |
| OCRFlux-3B | 全页图像按文档封装为无文字层派生 PDF；保存官方跨页合并开启/关闭的配对结果 | 权重、固定官方管线版本、PDF 派生和文档表/来源页 adapter 尚缺 | `image-only`；合成 HTML 片段测试单独报告，不把其图片当自然跨页页面 |

TATR-v1.1-Pub 的 `Cropped Tables/val + DT` 已有正式页面结构基线，不属于上述五条 Full Documents 端到端系统；TATR-v1.2-Pub 无本地已核实权重。如将 TATR 用于本轨道，必须另接**非真值**页面检测、裁剪、文字获取和合并，单列新增管线，不能以 oracle 裁剪充当端到端。

## 3. POTATR 专项门禁及实现步骤

1. **先只读核验公开制品（CPU、无下载）：**从论文/作者官方代码与模型页确认实际发布的源码、权重、许可、revision、文件/显存需求及 ViT 续接器是否发布。论文“将发布”不是已可下载的证据。项目内当前只见 `checkpoints/tatr-v1.1-pub` 与 `checkpoints/dots-ocr`；不得用 TATR 或自行写的替代网络冒称 POTATR。未找到可验证权重则记“待复现/未测”，**不启动该模型全量 GPU**；需要自训必须另写训练计划，先过派生标签/泄漏/简单基线门禁。
2. **取得权重后才准备真实输入（CPU、仅新目录）：**权重放 `models/` 的新版本目录；固定来源、SHA、许可、依赖。检查官方 POTATR 使用何种图片预处理、页面对象输出及文本分配，优先完整页面推理；`val` 935 篇的 13,871 张原图不可用 GT 框裁剪。对 `+ DT` 从该页 `words/` 只读读取文本/坐标，对 image-only 单列冻结 OCR 版本与文字定位，绝不把 PDF words 当 OCR。先在 train 上实现并单测结构图→表 HTML、bbox→页码、跨页前后状态的无真值 adapter；字段/来源页无法无损映射时停下并留失败清单。
3. **固定合并矩阵（CPU）：**同一份 POTATR 页面预测先做 `no_merge` 和项目规则 `simple_merge`，评两条赛道时各自固定文字源；若复现论文的 ViT 续接器，需从官方权重或明确训练/复现记录获得，并与 `simple_merge` 分开命名、记录输入和阈值。合并仅看预测、相邻页面及版面，不得根据 val GT 选择表格或调阈值；保留各输出表 `source_pages`、表头/列/行处理决策及失败原因。论文 `POTATR + merging` 的文字来源在附录未明确，正式声称“复现论文分数”之前须经官方实现或作者确认。
4. **小样本资源门禁（GPU）：**使用 train 的包含续表、负例及无表页的完整文档检查接口、GPU 峰值和输出；再做固定 val 整文档 smoke 只核对覆盖/解析，不按其 GT 调规则。每次重新检查 `nvidia-smi` 显存及已有进程，共享卡不能视为独占；保守调度沿用原四模型计划的 `smoke 峰值 × 1.3 + 8 GiB` 与可确认窗口门槛，不终止其他进程。独立环境、独立新目录、每页终态和时间戳日志，失败/中断按文档缺口只补新分片。
5. **严格全量与离线复评：**仅在前四关通过后，对 val 全 13,871 页推理；保证 missing/extra/duplicate=0，error 单列。沿用公共 `scripts/score_cross_page_predictions.py` 的全部真值表文档内一对一匹配，再报告跨页子集与全部表；不足的 TEDS、续接 P/R/F1、误合并类别必须先实现/核验，未实现标“不可评”，不能虚填。按文档配对比较同一上游 `no_merge`、`simple_merge`、可用的 ViT 合并结果；校验输出 SHA 与运行元数据。不用 test 选模型或调参。

## 4. 从当前状态往下的实际顺序

| 顺序 | 下一项可执行工作 | 完成判据 / 分叉 |
| --- | --- | --- |
| A，已完成 | dots.ocr CPU 后台 `paper-dots-eval-20261020T123212Z.service` 已正常结束；全页配对评分与 7 项哈希完成核验 | `END 2026-10-20T13:48:59Z status=0`；跨页 GriTS-Con `0.4576991966`→`0.5131445386`，匹配数 `643`→`639`；详细记录 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` |
| B，可与 A 并行，仅只读 | POTATR 官方权重/代码/续接器/许可/版本核验，以及现有离线评分是否足够表达 POTATR 来源页 | 产出有官方证据的可用性清单；无可用权重则停在 POTATR 这一支，不以验证集自行训练补缺 |
| C，A 完成后 | 复核 dots 的配对 `no_merge/simple_merge`；审计真实 train 页级基线在负例的误连缺口，以及分数定义/失败案例 | 记录正式 cross-page/full-document 结果、差异、局限；不可直接拿它和 PDF-text-assisted 或论文输入不明的 POTATR 数值比较 |
| D，B 通过后 | POTATR 项目 adapter 和 HTML/来源页/文字源单测，train 完整文档烟测及显存检查 | 通过无真值输出契约和 GPU 门禁后再启动新 GPU 任务；没有权重/算力就保持“未测” |
| E，条件具备后 | POTATR 严格全页 paired 评测；固定 dots 输出的 Popo 后处理；Paddle、OCRFlux 各独立 smoke/全量；OCRFlux 外部 HTML 补集单独评测 | 每种方案完整覆盖、赛道清楚、日志/哈希/环境/失败完整，不能把未完成方案填零或混成单榜 |
| F，待主协议冻结 | 根据 train 规则和人工审计设计“已知跨页片段图”诊断子集与负例；最终才使用 test | 先固定裁剪策略/页序和输出；图片仅派生到新目录，oracle 片段结果与完整文档结果分表；test 只做最终评估 |

## 5. 结果表与限制

预留两个**独立**结果表：`image-only`（需要 OCR 时明确名称）与 `PDF-text-assisted`；每个方法至少记录模型 revision、上游解析器/文字源、页面覆盖、失败数、跨页真值数/匹配数、跨页 GriTS 与 exact、全表 GriTS 与 exact、输出来源页及不能计算的指标。额外列“已知片段诊断”和 OCRFlux HTML 合成补集，不纳入两个主表的联合平均。仅在定义/输入完全一致时报告 paired 增益；未检查 POTATR 权重/发布状态前**没有**它的实测结果。本次计划修订不更改已保存 dots 预测、评分任务及任何旧产物。

依据：`docs/2026-09-29-cross-page-four-model-evaluation-design.zh-CN.md`、`docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md` §3.3 的文字源补注、`docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md`、POTATR 原论文 <https://arxiv.org/html/2606.09788> 与 PubTables-v2 原论文 <https://arxiv.org/html/2512.10888v3>。模型下载可用性须以**实际**作者公开制品核验，搜索未找到不构成从未公开的证明。
