# 跨页表格恢复研究长期记忆

最近检查：2026-09-30 04:07 UTC。本文件是仓库内的**可更新恢复入口**，不是隐藏的会话记忆，不代替 `AGENTS.md`、实验日志或原始产物。更新时保留重要历史证据的链接；若与产物冲突，先核对产物，再在实验记录中追加勘误。

## 每次接手先做什么

1. 阅读根目录 `AGENTS.md`、本文件及 `docs/2026-09-22-research-progress.zh-CN.md`。
2. 阅读 `docs/research-handoff-2026-08-26.zh-CN.md` 和当前任务对应的最新 `docs/experiments/` 记录；检查相关产物、未提交更改和仍在运行的任务。
3. 对照本文件“当前状态/下一步”，只以可核验证据更新状态；不根据旧对话推测已完成下载、训练或评估。

## 当前研究状态

- 2026-09-30 04:07 UTC：本轮准备提交截至目前的研究代码与文档，提交前 HEAD `e615493`，分支 `main`；全量测试 149 项和 Ruff 检查通过。未启动 GPU 任务或新下载；后续 GPU smoke 前必须重新检查资源。进度索引记录了本轮检查点。

- 目标是可投稿的**文档级跨页逻辑表恢复**，不仅是续表二分类；固定主基准 PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`。`image-only` 和 `PDF-text-assisted` 分开报告。研究与四模型协议见 `docs/2026-09-29-cross-page-four-model-evaluation-design.zh-CN.md`。
- 阶段 0 已完成：val 935 篇、13,871 页全部纳入输入清单；按不同 `parts.page_num` 得到 983 张跨页表（869 篇文档）；同页多片段 63 张不计跨页；官方相邻页对正/负例 1,276/786。`PMC12274235-table-1` 是 `[4,5,7]`，不能捏造第 6 页片段。证据：`docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md` 和 `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/`。
- 阶段 1 **部分完成**：离线跨页评分器已实现文档内全真值一对一匹配，再评分跨页真值子集；要求全部页的终态和预测表来源页；129 项回归测试通过，validation 异常文档的空预测仅验证协议，不是模型得分。证据：`docs/experiments/2026-09-29-cross-page-offline-scorer.zh-CN.md`；源码 `src/cptla/evaluation/cross_page.py`、`scripts/score_cross_page_predictions.py`。
- 阶段 1 的 dots.ocr **`no_merge` 适配器和真实旧三页 smoke 离线评分链路已完成**：输入输出哈希在两次独立目录复算一致，全量回归 135 项通过。**勘误：**该 smoke 的唯一真值表实际上跨 `[1,2]` 页（此前口头误认无跨页表），旧预测仅来自第 1 页；结构/内容 grid exact 0/1，局部 GriTS 不能代表跨页整表恢复。见 `docs/experiments/2026-09-29-dotsocr-no-merge-document-adapter-smoke.zh-CN.md` 及 `artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge/`、`artifacts/cross-page-scores/20260929T100115Z-dots-smoke-no-merge/`。
- **简单拼接基线已实现和验证，但尚无真实 train/val 大范围效果：**固定邻页/页边位置/同列/完全重复表头才合并；train 整表人工分行仅测结构；合成负例证实即使全部条件成立也能误合并。冻结后在旧 validation smoke 的候选数、合并数均为 0（后页无预测表），结果与 `no_merge` 相同；全套回归 149 项通过。依据 `docs/experiments/2026-09-29-dotsocr-repeated-header-simple-merge-baseline.zh-CN.md` 和 `artifacts/cross-page-merges/20260929T101235Z-dots-val-smoke-simple-merge/`。
- 2026-09-29 10:41 UTC：已从 `https://hf-mirror.com` 下载 `ChatDOC/OCRFlux-pubtabnet-cross` 固定 revision `10f47124646489a33c9c9c049707d7e710b00a31`。9,064 条 JSONL 全部可解析，字段完整且 HTML 不为空；图片归档包含 9,064 张图片。日志、SHA-256 和详细审计见 `docs/experiments/2026-09-29-ocrflux-pubtabnet-cross-download.zh-CN.md`。该数据仍只作为 HTML 片段拼接补集，不是自然跨页页面图像；官方 endpoint 本轮超时，镜像来源限制保留。
- 重要协议澄清：OCRFlux 补集中的图片是原始完整表格图，不能直接当作两张跨页页面图送入 OCR 模型；主用途是把 `table_fragment_1/2` 输入 HTML 合并接口，单独报告合并结果。其结果不能与 PubTables-v2 的文档级 image-only 跨页恢复指标直接合并比较。
- **2026-09-29 10:20 UTC 计划纠偏：**真实 train 页级预测用于研究简单合并误连率，**不是**启动 dots.ocr validation 全量页级推理的前置门槛。已有 dots.ocr 本地权重和 val 全页清单（SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`）；可以先运行 13,871 页的 `image-only` 页级推理，保存全量终态，之后再离线进行配对后处理。全量未启动。10:20 UTC 的只读 GPU 快照：GPU 0 约 48,737 MiB 空余但有 4 个 compute 进程，GPU 1/2/3 约 423/11,033/13,321 MiB 空余且都有进程；不能把显存数字当作可独占授权，启动前重新检查并确认与现有任务互不冲突。

## 下一步与约束

1. **优先准备并启动 dots.ocr validation 全页推理**：沿完整文档边界分片、固定环境/模型 revision 和唯一新输出目录；重新检查共享 GPU 与进程、做短显存标定并确认运行窗口，再持久化运行清单和分片日志。此阶段可先于 train 合并规则评测和其他模型开展。真实 train 全文档页级预测仍缺失，故 `simple_merge` 的误连率与正式增益暂不可报告；禁止用旧 val smoke 调参。
2. 检查模型能否无真值泄漏地覆盖完整文档及无表页；完善不足的评分指标/误合并诊断，再根据重新检查的 GPU 显存与已有进程决定 smoke。不能凭旧 GPU 快照认定资源空闲。
3. 正式 validation 必须输入全部 13,871 页，只在评分阶段选真实跨页表；test 仅用于协议冻结后的最终评估。每个运行使用新带时间戳目录，不删除或覆盖已有数据、产物、日志。

## 留痕机制（必须执行）

- 每个可验收子阶段结束、连续工作约 60 分钟、后台任务启停/状态变化、失败/方案改变、会话结束/可能中断前都要检查和更新记录；每轮结束至少核对本文件与进度索引是否仍准确。无实质变化记检查点，不编造新结果。此要求不意味着离线自动定时执行。
- 细节与可复现证据写入 `docs/experiments/YYYY-MM-DD-任务.zh-CN.md`；进度索引追加阶段状态和链接；本文件只更新“当前状态、限制、下一步”及必要证据入口。重要更正追加勘误并保留旧证据。长任务启动即记 PID/命令/日志/输出和完成条件，结束时补记覆盖/失败/指标/校验和。
- 仓库之外的隐式记忆不保证可读或持久；**以仓库文档、日志及原始产物为唯一跨会话恢复依据**，不访问仓库外文件来写“长期记忆”。
