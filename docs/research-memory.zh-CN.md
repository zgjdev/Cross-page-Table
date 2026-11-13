# 跨页表格恢复研究长期记忆

2026-11-13 10:47 北京时间：评分契约首轮合成核验完成，服务器21项旧测试通过；错来源或额外预测仍可得到跨页子集grid exact=1，nbsp/省略闭标签被当前解析器拒绝。旧行为已留证，未改历史评分；下一项为版本化网格与严格任务评分契约实现，G0仍未通过。无模型/GPU任务。[探针、结果与复现说明](experiments/2026-11-13-reconstruction-score-contract-preflight.zh-CN.md)。

2026-11-13 同步留痕：数据验收主体提交 `fb0e40e` 已核验本地、GitHub、服务器同一功能分支 `codex/reconstruction-data-audit` 一致；main 未变，数据未纳入 Git。同步后记录补记随后提交，实验事实见 [11月13日验收记录](experiments/2026-11-13-reconstruction-train-data-acceptance.zh-CN.md)。

最近文档更新：2026-11-13（北京时间），联合重建 train 数据清单独立验收与 20 表坐标初查完成；G0/G1 尚未通过，无新模型预测、训练或分数。最近正式模型结果核验仍为 2026-11-08 12:32，OCRFlux推理及两组正式评分完成，1,916输入与6结果SHA复核一致。本文件是仓库内的**可更新恢复入口**，不是隐藏的会话记忆，不代替 `AGENTS.md`、实验日志或原始产物。更新时保留重要历史证据的链接；若与产物冲突，先核对产物，再在实验记录中追加勘误。

## 每次接手先做什么

1. 阅读根目录 `AGENTS.md`、本文件及 `docs/2026-09-22-research-progress.zh-CN.md`。
2. 阅读 `docs/research-handoff-2026-08-26.zh-CN.md` 和当前任务对应的最新 `docs/experiments/` 记录；检查相关产物、未提交更改和仍在运行的任务。
3. 对照本文件“当前状态/下一步”，只以可核验证据更新状态；不根据旧对话推测已完成下载、训练或评估。

## 当前研究状态

- **2026-11-13 数据准备完成验收。**11月9日 full train run 已于北京时间23:53完成，7,359文档/110,347页清单/19,885逻辑表/7,606跨页表；11月13日独立回源核对全部parts与抽样，missing/extra/duplicate 0，893产物SHA一致。暂定fit/dev/confirm为5,123/1,124/1,112文档，跨页表5,322/1,152/1,132；近重复候选1,684、接受0不能证明无泄漏。200表审计材料与20表66片段坐标初查完成，2个侧向表待方向策略验证，所有独立人审仍pending。原run `artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/`；验收 `artifacts/reconstruction-acceptance/20261113T022600Z-train-full-v3/`，exit0，原数据与旧结果不变。**不重跑生成、不放行训练**；下一步重复/污染校准、方向与紧边界检查、grid/评分契约、固定上游小样本与强规则诊断。无GPU/后台任务。[完成证据与逐例记录](experiments/2026-11-13-reconstruction-train-data-acceptance.zh-CN.md)

- **2026-11-09 23:39 北京时间全 train 清单启动（历史检查点，已由11月13日验收关闭）。**G0 工具经独立审查，服务器48项测试通过；20文档smoke完成19跨页表/10审计页/4坐标图，62源SHA与51产物SHA一致。发现拼图底部裁切展示问题并回归修复，代码`63bf468`，服务器新模块30测试通过。当时正式CPU run `20261109T153945Z-reconstruction-train-full` 正在scan，当前已完成；输出根 `artifacts/reconstruction/同ID/`。未训练或生成预测。[执行记录](experiments/2026-11-09-reconstruction-train-data-audit.zh-CN.md)

- **2026-11-09 G0 工具本地实现（历史检查点，后续服务器验收已完成）。**新分支 `codex/reconstruction-data-audit` 已实现 train 清单/输入标签隔离、暂定文档簇划分、200/20 分层抽样及服务器侧静态预览。47 项相关测试通过，1 项 Windows 符号链接权限跳过，Ruff 通过；当时独立审查及服务器 smoke 待完成，后续证据见上方完成条目。划分仍为 `provisional_do_not_train`，无预测、无 GPU，不能宣称 G0/G1 已通过。[实验与实施证据](experiments/2026-11-09-reconstruction-train-data-audit.zh-CN.md)

- **2026-11-09 16:03 北京时间启动就绪性只读核验。**服务器 HEAD 为 `6ee8fcb` 且工作区干净，train/images 110,347 文件、tables 与页对标注各 7,359 文件，三份 train 标注可解析并重算 SHA。可开始 G0 的 train 数据/评价准备。重建专用清单、模块和配置尚不存在；现有 val 清单脚本不可直接改路径用于 train。G0/G1 尚未通过，未启动训练、下载或 GPU 任务，也未核验实时 GPU 资源。下一步实现 train 内划分/片段清单与输入标签隔离，做 20 例坐标核验，再准备 200 表审计及简单基线。[就绪性记录](experiments/2026-11-09-joint-reconstruction-startup-readiness.zh-CN.md)

- **2026-11-09 方案归档与同步核验。**主体提交 `cbb56b9` 使用 `zgjdev <zhengguojie0922@gmail.com>`，包含完整方案及其依赖的历史结果/进度记录。GitHub `origin/codex/paddle-merge-compat`、本地 HEAD 和服务器同名工作分支已核验同为 `cbb56b942768bf55dc363046343816cb91d8524d`，方案 Git blob 同为 `d7a02ccb8070848ee45b494b6c0e6df0f2f6209e`。服务器从 `006da59` fast-forward，同时取得此前本地已提交的 OCRFlux 代码历史；受保护数据目录变更清单为空，工作区干净。本条为后续留痕补记，将另行同步；未修改 main、未启动新任务。

- **2026-11-09 当前技术路线统一入口。**[联合结构重建研究方案 v1](plans/2026-11-09-cross-page-joint-reconstruction-research-plan.zh-CN.md) 已写明数据协议、可学习共同列结构、可编辑整表网格、Qwen3-VL-2B LoRA 主候选、强基线、训练预算、G0–G6 关口和失败纠偏。目标是 CV 顶会所需的可验证方法贡献，效果及录用均不预设。先前规则/MLP/仅关联 Transformer 作为对照，历史建议保留。下一步先做 train 数据/评分审计与可修复空间诊断，再决定是否训练。尚未下载新骨干、实现新方法或启动新任务；预期门槛是研发决策标准，不是已取得分数。官方 val 已反复观察，train 内按文档/近重复簇划分 fit/dev/confirm，test 封存。

- **2026-11-09 联合纠错能力修正。**仅列匹配和表头处理的 Transformer 仍主要解决关联，尚未落实局部结构修复。目标候选应把 Paddle 输出视为可修改结构，支持行列/单元格拆并、跨格修正及可定位视觉依据。冻结识别器权重不等于冻结其预测结构。编辑表示与监督待设计，当前无实现或效果。[能力边界修正](reports/2026-11-05-research-stage-and-feasibility.zh-CN.md#2026-11-09-联合纠错能力边界修正)

- **2026-11-09 模型实现建议。**候选为固定 Paddle 上游、BGE 文本表示、小型跨片段 Transformer 与关系解码，先学习列对应和重复表头。Qwen3-VL-2B 多图 LoRA 输出整表 HTML 作为可训练强对照。细粒度标签、共同列定义及冲突解码待设计和审计，当前无 cell bbox，视觉单元格定位须另行验证。无新实现。[框架建议](reports/2026-11-05-research-stage-and-feasibility.zh-CN.md#2026-11-09-模型实现框架建议)

- **2026-11-09 核心方法定位纠偏。**规则列对齐加 DP/MLP 目前定位为诊断对照，尚无足够方法论文贡献证据。新增直接相关 OvisOCR3（2026-10-20，0.8B，图像加解析结果做两页重建及多页递归），需纳入后续新颖性与强基线核查。候选主假设为局部解析带噪下的整表结构联合推断及多页一致性，待 train 样本验证与监督设计。无新实验。[贡献复核](reports/2026-11-05-research-stage-and-feasibility.zh-CN.md#2026-11-09-方法贡献复核与相关工作补查)

- **2026-11-09 跨页重建方法候选。**固定 Paddle 未合并片段 HTML，先用列特征打分和保序动态规划对齐，再做表头与边界行处理。两层 MLP 可替换列对打分，关系图消息传递待误差和消融支持。第一步为无需训练的列对齐原型，无新实验。[方法候选](reports/2026-11-05-research-stage-and-feasibility.zh-CN.md#2026-11-09-跨页重建方法候选)

- **2026-11-09 论文输入路线建议。**先用 Full Documents 派生的同表片段图做受控重建，固定片段预测，按整表真值评分。再在固定上游的完整文档管线中替换重建器，验证收益及误连。主张范围由两层实验共同决定。无新实验。[论文定位与输入选择](reports/2026-11-05-research-stage-and-feasibility.zh-CN.md#2026-11-09-论文定位与输入选择)

- **2026-11-09 自研方案就绪度复核。**现有 Full Documents 基线及跨页清单足以开始设计。建议先固定页级识别上游，以给定同表分组的跨页片段验证列对应与重建，比较直接拼接和单模块增量，再接入完整文档。train 正负例代表性审计、细粒度派生标签、内容级泄漏核查和严格来源页评价仍待完成，均为扩大训练前的关口。无新实验。[阶段复核](reports/2026-11-05-research-stage-and-feasibility.zh-CN.md) · [跨页清单审计](experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md)

- **2026-11-09 PubTables-v2 v4 分差核查。**v4 dots.ocr 全表无合并/合并 GriTS-Con 0.5768/0.7495，Acc-Con 均为 11.80%。项目 val 0.5078/0.5479 使用不同合并器。既有 637 条 HTML 排除与本地严格 XML 解析相关，上游现已使用容错 HTML 解析，影响需固定预测离线复评。TATR 同名 +DT 论文 0.9585/48.16%，项目 val 0.8704/38.27%，结构分也有差距。POTATR-v1.1-Pub 权重及代码已公开，论文配置映射待核验。分差、边界与后续验证见 [模型汇总的 v4 核查](reports/2026-11-09-tested-models-parameters-inputs-and-results.zh-CN.md#2026-11-09-pubtables-v2-v4-对照与分差核查)。无新推理或评分。

- **2026-11-09 已测模型资料核验。**新增 `docs/reports/2026-11-09-tested-models-parameters-inputs-and-results.zh-CN.md`，汇总三款整文档与TATR裁剪表输入、公开及项目正式结果。Safetensors头部统计dots约3.04B（官方1.7B为语言骨干）、Paddle识别VLM约0.959B（另有版面组件）、TATR约28.8M。OCRFlux官方3B型号的完整模型在meta device核实共享词嵌入后为3.754B，存储张量共4.065B元素。本轮核验已有模型文件及来源，结果分数沿用已完成实验。

- **2026-11-08 12:32北京时间 OCRFlux两组评分完成核验：**run20261107T162300Z-ocrflux-full-val-scores于01:52:55北京时间结束，summary completed、unit inactive/exit0，耗时约1小时31分钟。1,916输入/代码/真值SHA与6结果SHA独立重算全部一致。no_merge/merged全表Con0.535472/0.596342，跨页Con0.523772/0.588922，跨页内容exact0/4（分母983，不含来源页核验）。完整13,871页、missing/extra/duplicate0；729错误页保留，非法HTML584/505。新汇总 `docs/reports/2026-11-08-dots-paddle-ocrflux-full-val-results.zh-CN.md`，正式细节见本日paired-scores实验。当前OCRFlux任务均结束，下一步配对结果/错误来源审计，随后固定Paddle上游Popo；无需重算OCRFlux。未创建监控。

- **2026-11-08 00:21:57北京时间 OCRFlux正式CPU评分已开始：**RUN_ID20261107T162300Z-ocrflux-full-val-scores，unit paper-ocrflux-scores-20261107T162300Z.service，初始父PID2703956/active；no_merge子PID2704606实际CPU98.8%，merged随后自动执行。audit通过完整935篇13,871页、两组729失败页保留、2,587全表/983跨页GT、1,916输入/代码/真值SHA。冻结评分代码与Paddle实际文件SHA相同；首次Git archive CRLF差异已在预检拦截，失败现场保留，新冻结副本用LF实际原文件通过。结果根artifacts/cross-page-scores/同RUN_ID/，事件artifacts/ocrflux-score-launchers/20261107T162300Z/events.log。无正式分数、无定期监控、Linger=yes；详见 `docs/experiments/2026-11-08-ocrflux-full-val-paired-scores.zh-CN.md`。下一步检查两组完成及最终输入/结果哈希。

- **2026-11-08 00:08北京时间 OCRFlux推理及两组导出完成：**a001 summary completed、935/935篇、13,871/13,871页，resumed_documents32；supervisor completed、attempt exit0，结束11月7日15:56:19 UTC（北京时间23:56:19），unit inactive/dead、PID0。页面ok13,142/error729（710截断、18 JSON解析、1 AttributeError）。no_merge/merged各13,871页，missing/extra/duplicate均0，预测表3,223/2,563；export-complete存在，adapter audit SHA93a29e92…与marker一致，936个适配输入、6个输出SHA独立重算全部匹配。检查点身份/协议/冲突/页数无异常，本轮未独立重算全部raw/PDF检查点文件SHA。没有正式评分结果，下一步复用两组导出执行CPU评分，无需重跑GPU。实际输出根artifacts/ocrflux-document-runs/20261031T114000Z-ocrflux-resume-a001/；详细证据见恢复实验11月8日完成段。

- **2026-11-07 14:03北京时间 OCRFlux进度：**a001/supervisor PID355605仍active/running，只有attempt001。新旧检查点累计881/935篇、12,995/13,871页终态（93.68%），较11月5日增加202篇/3,124页；12,294页ok、701页error（682截断、18 JSON解析、1 AttributeError）。身份/协议/冲突及保存页数检查无异常，本轮未重算全部文件SHA。当前PMC12196750共26页，前9页均ok且未计入完整检查点总数。GPU0空余43,337MiB/利用率42%。恢复后162.38小时均速77.38页/小时，余54篇/876页粗估11.32小时，最终覆盖/哈希核验与两组评分另计。export-complete未生成，下一步继续等待推理和导出完成再验收；本次仅只读检查及本地记录。证据见恢复实验11月7日段。

- **2026-11-05 23:10北京时间 OCRFlux进度：**a001及supervisor PID355605仍active/running，只有attempt001。新旧检查点累计679/935篇、9,871/13,871页终态（71.16%），较11月3日新增313篇/4,713页；9,315页ok、556页error（543截断、12 JSON解析、1 AttributeError）。身份/协议/冲突及保存页数检查无异常，本轮未重算全部产物SHA。当前PMC11695376共19页，17页已有终态（16成功/1截断），未计入完整文档进度；GPU0空余35,739MiB/利用率99%。恢复后123.48小时，新增9,441页，均速76.46页/小时，剩4,000页粗估52.32小时（约2–3天，不含评分）。export-complete尚未生成，未完成/未评分。仅只读检查并本地记录，下一步继续检查同supervisor及检查点并集。证据见恢复实验11月5日段。

- 2026-11-03 14:02（北京时间），OCRFlux a001仍运行（PID355605），原任务与恢复任务合计366/935篇、5,158/13,871页已保存检查点（37.19%），较上次增加216篇、2,904页。4,862页成功、296页报错（290截断、5 JSON解析、1 AttributeError）。当前PMC11022528已有4/11页，未计入上述总数。恢复以来平均约71页/小时，余约122小时，不含评分。本次只读统计，未重算文件哈希。

- **2026-11-01 19:21北京时间 OCRFlux进度：**恢复run20261031T114000Z-ocrflux-resume-a001、supervisor PID355605仍active/running，只有attempt001，无新增中断/恢复。跨旧run与新run按文档合并检查点累计150/935篇、2,254/13,871页终态（16.25%），比上次新增118篇/1,824页；2,102页ok、152页error（150截断、2 JSON解析），不冒称全部成功。检查点身份/协议/冲突及页数检查无异常，本轮未重算全部产物SHA。当前PMC10546020共22页，已有页0终态ok、未计入完整文档进度；native日志11:20 UTC仍正常产出，GPU0空余42,153MiB/利用率40%。恢复后23.67小时完整页吞吐约77页/小时，余约150.75小时（约6–7天，不含评分，粗估）。文件mtime出现2024时间，与当前日志不一致，本轮不将mtime作为活跃依据。仅只读检查、未改任务、无正式分数。下一步继续检查同supervisor与完整检查点；证据见恢复实验11月1日段。

- **2026-10-31 19:43:54北京时间 OCRFlux已实际恢复GPU推理：**当前run `20261031T114000Z-ocrflux-resume-a001`，supervisor unit paper-ocrflux-recovery-20261031T114000Z.service、PID355605/active；协议字典与旧run完全一致。原32篇430页、2,726个文件引用经恢复入口SHA核验跳过；新documents仅PMC10285071，前3页status=ok，初始化profiling本次通过。GPU0空余24,747MiB快照；38个旧截断终态保留，不改生成参数。完整文档进度仍32篇，第33篇未完成。恢复层代码5e0a89e，服务器隔离部署，未知错误仍停止、同类初始化失败有限恢复；新日志logs/ocrflux-recovery/20261031T114000Z-ocrflux-resume/，实际结果artifacts/ocrflux-document-runs/同前缀-a001。无定期监控、未评分，下一步检查该supervisor最新attempt和完整检查点。详见 `docs/experiments/2026-10-31-ocrflux-profiling-recovery.zh-CN.md`。

- **2026-10-31 19:41:08北京时间 OCRFlux有限恢复已启动：**排查实际vLLM源码确认profiling断言依赖同卡其他进程显存不变假设；外层恢复不改原full-source-v3/模型/参数，仅读取已知初始化AssertionError且raw0/pages0时换新run恢复，每篇3次/总20，稳定显存门禁、未知错误停止。本地33相关测试、服务器4新增测试与独立复核通过。unit paper-ocrflux-recovery-20261031T114000Z.service，初始PID355605/active；日志logs/ocrflux-recovery/20261031T114000Z-ocrflux-resume/，结果根使用同前缀-a001等。原32篇检查点核验/跳过及GPU恢复待验证。详见 `docs/experiments/2026-10-31-ocrflux-profiling-recovery.zh-CN.md`。无定期监控、原产物保留。

- **2026-10-31 18:11北京时间 OCRFlux进度检查发现已中断：**原run20261030T032500Z-ocrflux-val-full在10月30日10:02:58 UTC（北京时间18:02:58）失败退出，unit failed/failed、MainPID0、exit1；实际运行6.63小时。保留32/935篇检查点、430/13,871页终态（3.10%），392成功、38生成finish_reason=length截断；检查点身份/页数/重复/协议检查无异常，本轮未重算全部文件SHA。第33篇PMC10285071共13页在vLLM初始化显存profiling断言失败，尚无页面预测；已用显存采样33,683,668,992→32,503,431,168字节下降，非已确认OOM，具体外部资源变化未核验。GPU0当前空余40,661MiB快照。此次仅只读核验并更新记录，没有恢复、重启、删除或改协议。下一步先排查初始化稳定性，再用同协议新RUN_ID恢复32篇检查点；38截断按原协议保留，不能凭val调参。此前一周预估不再作为当前完成时间承诺；无正式分数。详见full-val实验10月31日段。

- **2026-10-30 11:26北京时间 OCRFlux全量真实GPU推理已核验：**同一run20261030T032500Z-ocrflux-val-full仍运行，冻结run-manifest确认935文档/13,871页；首篇PMC10154845共8页，页0请求21.04秒、error=null、页面终态ok。完整文档checkpoint暂0（按整文档计），不是无输出。GPU0空余15,227MiB高于8192保护线；父PID477502、systemd+Linger托管。未完成、无正式分数，不更改冻结运行代码、不创建定期监控。详见本日full-val实验末段。

- **2026-10-30 11:24:57北京时间 OCRFlux全量任务已启动：**用户明确授权，RUN_ID `20261030T032500Z-ocrflux-val-full`，unit `paper-20261030T032500Z-ocrflux-val-full.service`，初始父PID477502、active。完整val935/13871、image-only、冻结full-source-v3，入口在artifacts/ocrflux-launchers/同ID/launch.py；父日志logs/ocrflux-launchers/同ID/full.log，结果artifacts/ocrflux-document-runs/同ID。GPU0启动前空余31,143MiB、Linger=yes；无定期监控。首批GPU预测待核验，不冒称已完成。详细协议/命令/恢复见 `docs/experiments/2026-10-30-ocrflux-full-val-inference.zh-CN.md`。未启动Popo或CPU正式评分。

- **2026-10-30 10:14北京时间 OCRFlux全量技术READY（未启动）：**最终v3实际4页pilot及新run恢复均completed/exit0，恢复resumed_documents=1且无新GPU调用；两组表SHA一致、31产物SHA核验通过。3篇10页真实smoke及最终两组CPU评分完整，指标与v2字节相同，均1项HTML评分契约拒绝未修补；小样本非正式结果。服务器32/本地29相关测试和ruff通过，独立复核两项P1关闭。完整val935/13871输入、模型、环境、官方源码及最终代码SHA预检通过；最终证据 `artifacts/ocrflux-prep/20261030T015400Z/acceptance/final-audit-v3.json`。所有验收任务结束，GPU0空余31,143MiB快照，Linger=yes；没有全量/监控运行。启动/恢复说明 `docs/2026-10-30-ocrflux-full-validation-readiness.zh-CN.md`，冻结服务器源码full-source-v3，启动前仍需重查GPU。下一步可启动OCRFlux完整val；Popo环境仍待准备，不冒称全部模型就绪。

- **2026-10-30 OCRFlux独立复核修复检查点：**发现并用失败测试复现两项P1：引擎RuntimeError被合并回调吞掉、原val词法页序导致长文档adapter失败。现已传播RuntimeError/MemoryError并按数字页序适配（保留原SHA）；复核确认两项关闭。本地29/服务器32相关测试通过。冻结源码改为full-source-v3，v3实际4页pilot+恢复unit `paper-ocrflux-entry-v3-20261030T015400Z.service` 初始PID3556047已启动，最终预检及train复用评分重验，不修改旧产物；仍未val全量。见本日实验及新readiness文档。

- **2026-10-30 OCRFlux 10页真实流程及配对评分完成，实际全量入口pilot运行中：**原smoke于02:01:22 UTC完成3/3文档10/10页，页面错误0；adapter首次发现打包器image_id为stem而val为带扩展名，已保留原预测/失败现场，新增回归并修复为保持原ID。新 `train-scores-v2` 两组覆盖missing/extra/duplicate=0，均1非法HTML（模型输出问题未修复），train全表Con0.65616→0.83549、跨页Con0.57916→0.79047、跨页内容exact均0。仅3篇有意选择train，不是正式性能。实际全量入口4页pilot+新目录恢复unit `paper-ocrflux-entry-20261030T015400Z.service` 初始PID3443480已active；val只读输入/模型/官方源码完整预检通过，最终版SHA预检及pilot恢复仍待结束。未val全量。详见本日实验。

- **2026-10-30 01:57 UTC左右 OCRFlux真实train验收已启动：**用户继续即同意既有设计实施；新增CPU核心/官方API入口/两组adapter，本地15测试通过，服务器隔离源码12核心测试通过。unit `paper-ocrflux-train-20261030T015400Z.service`、初始PID3302340，启动时active；输入已有3篇10页train图像PDF，不读GT。输出 `outputs/baselines/ocrflux-3b/20261030T015400Z-ocrflux-train-smoke/`，事件 `artifacts/ocrflux-prep/20261030T015400Z/events.log`。完整完成/评分/实际恢复待验收，未全量；详情见本日OCRFlux实验。

- **2026-10-30 再次全量就绪核验（无新实验）：**SSH只读确认服务器HEAD006da59，scripts/src/tests没有OCRFlux或Popo正式入口/适配代码；OCRFlux最小probe summary仍passed且明确仅环境验收，未完成10页整文档测试。项目环境有OCRFlux/Paddle，无Popo独立环境；用户running service列表为空。GPU0空余31,143MiB但非独占，不能据此越过流程门禁。Paddle已有全量结果；OCRFlux/Popo尚不能全部全量启动。下一步仍是实现OCRFlux封装、train配对评分及恢复验收，本轮未启动或改变服务器任务。

- **2026-10-30 OCRFlux完整流程设计检查点：**已阅读官方接口及现有评分/恢复代码，设计文档 `docs/superpowers/specs/2026-10-30-ocrflux-document-baseline-design.md` 已自审并本地提交 `91340e7`。推荐保留官方提示/API与合并顺序，增加安全解析、逐元素来源链及原始响应留存；同份页面预测导出两组评分输入。正式runner/adapter、3篇10页train smoke、配对评分、实际恢复及全量预检仍未实现/验收。本轮没有新服务器计算或GPU任务；书面设计待用户审阅，后续按批准设计实施。详见本日OCRFlux实验末段。

- **2026-10-30 全量就绪询问复核：**无新结果。服务器最小probe仍passed，但scripts/src/tests尚无OCRFlux正式runner/adapter；完整10页train smoke、同页预测复用配对、来源页与评分契约、可恢复全量入口均未验收。无运行中的用户service，未启动935篇全量；环境级READY不等于全量READY。下一步是实现并验收完整小流程，不再重复安装环境。

- **2026-10-30 01:02北京时间OCRFlux环境级READY：**项目环境 `.venvs/20261029T162200Z-ocrflux/` 安装完成，pip check/imports/freeze/官方CLI/PDF API通过，torch2.5.1+cu124、transformers4.50.0、vllm0.7.3，Gradio兼容约束5.23.1/0.0.22。实际单GPU probe `paper-ocrflux-probe-20261029T170000Z.service`（初始PID2563300）17:00:35–17:01:53 UTC，summary passed、exit0、已结束，真实train无表页识别33.85秒/963token、合成续接0.30秒与表重建1.38秒均通过，无eval。产物 `artifacts/ocrflux-prep/20261029T170000Z-ocrflux-runtime-probe/`；GPU显存已回到启动前31,143MiB空余。环境已可执行，不等于完整3文档smoke/全量ready：安全中间来源链封装、adapter契约、10页train smoke与可恢复全量入口仍待实现/核验。官方原parse含eval不可直接运行。无安装/GPU任务继续运行，详见本日OCRFlux实验最终验收段。

- **2026-10-30 00:53北京时间修复检查点：**Torch及6项预缓存下载成功；额外flashinfer索引超时且非torch/vllm必需依赖，仅停止自建164100安装服务，保留全部日志缓存。新 `paper-ocrflux-repair-20261029T165400Z.service` 初始PID2513578，去掉可选find-links、复用缓存继续完整官方依赖；日志 `logs/ocrflux-setup/20261029T165400Z-required-deps/`，事件events-required-deps.log。仍未GPU验收，不宣称ready；详见本日OCRFlux记录。3篇10页train含2个续表正例、1个无跨页文档及4无表页已只读审计。

- **2026-10-30 00:40北京时间OCRFlux依赖修复运行中：**用户授权持续配好环境；新unit `paper-ocrflux-repair-20261029T164100Z.service` 初始PID2430136，复用项目自有162200环境，改本次命令到已核验清华镜像；先固定build工具、再no-build-isolation装官方固定依赖，不改全局配置或旧结果。新日志 `logs/ocrflux-setup/20261029T164100Z-mirror-repair/`、事件 `artifacts/ocrflux-prep/20261029T164100Z/events.log`。尚未ready，需pip check/imports/CUDA/最小生成通过，不自动全量；详见本日OCRFlux实验。

- **2026-10-30 00:35北京时间OCRFlux尚未ready：**只读复核162200安装任务已在00:28:26失败，summary failed、unit failed/failed、MainPID0。Conda/Poppler成功，但pip构建依赖setuptools访问pypi.org报网络不可达，非模型推理失败；尚无pip check/imports或GPU smoke。旧“安装中”为历史快照。现仅核验替代源网络、不改源或重启；下一步依赖下载修复→导入→安全解析/来源链wrapper→train smoke，不能全量。证据见 `docs/experiments/2026-10-30-ocrflux-runtime-and-smoke-readiness.zh-CN.md` 00:35段，原权重/数据/失败日志保留。

- **2026-10-30 00:23北京时间 OCRFlux准备已执行：**官方代码固定c1b315a、15个模型文件全部重算哈希通过；当前独立环境安装任务 `paper-ocrflux-setup-20261029T162200Z.service`，初始PID2298669、active/running，16:21:55 UTC进入pip依赖安装，尚未完成imports/pip check。项目内Python3.11/Poppler26.10.0已创建，3篇train/10页图像PDF打包与真实Poppler渲染通过。首次162000服务仅因systemd PATH找不到Conda失败，原日志保留，新ID通过显式路径恢复准备。未GPU推理/训练/全量；源码含eval和未保留完整来源链，后续wrapper安全解析/中间证据/adapter需先测试。当前日志 `logs/ocrflux-setup/20261029T162200Z-ocrflux/`，事件 `artifacts/ocrflux-prep/20261029T162000Z/setup-162200-events.log`；详细证据/环境/命令/下一步见 `docs/experiments/2026-10-30-ocrflux-runtime-and-smoke-readiness.zh-CN.md`。不创建监控，安装不会自动启动GPU。

- **2026-10-30 合并含义澄清，无新计算：**复核simple_merge与Paddle replay：当前两模型的合并均为预测表结构级的规则后处理，不是拼像素图/无条件拼接；dots同列/同表头后去首行追加，Paddle为官方规则及表头处理，compat仍同算法仅字段桥接，不重调用VLM联合识别。说明已补入两模型结果报告；不是已训练跨页关系图模型。

- **2026-10-30 两个已测完整文档模型结果汇总：**只读重取dots两组/Paddle三组metrics并核对五份SHA，与历史记录一致；新增 `docs/reports/2026-10-30-dotsocr-paddle-full-val-results.zh-CN.md`，区分全表/983跨页子集、合并条件、覆盖与HTML拒绝、来源页局限。当前Paddle管线指标高于当前dots管线，但合并器/预处理/HTML风险不同，不把差异全归因模型能力；2/6/12内容exact不是已核验完整恢复数。没有新评分/推理/训练，下一模型仍OCRFlux。

- **2026-10-30 计划复核（无新实验）：**按 `docs/2026-10-23-open-model-priority-and-readiness.zh-CN.md` 第1节，Paddle完成后的下一模型是OCRFlux-3B，之后为固定Paddle上游的MinerU-Popo，POTATR后置。OCRFlux/Popo主权重已在10月23日下载记录中验收，但各自独立环境、来源页adapter、train整文档smoke与GPU门禁不能据此冒称通过。先归档Paddle结果/少量来源页与错误审计，可与下一模型准备衔接，不把不断调整Paddle规则作为下一模型前提；按既定门禁通过后才全量。仍处基线阶段，未启动训练/新推理。本次仅审阅计划及更新记录。

- **2026-10-30 00:04北京时间：Paddle三组评分已完成并核验。**原run 20261029T035007Z-paddle-full-val-scores于10月29日15:17:35北京时间结束，summary completed，耗时约3小时26分钟，9份结果SHA重算全部一致、service inactive/dead。三组13,871页完整；no_merge/official/compat全表GriTS-Con=0.651021738/0.700574254/0.774418507，跨页子集Con=0.672710736/0.734669528/0.806670507；跨页内容网格exact=0/6/12（分母983），不等于已核验来源页的完整恢复数。各组13非法HTML，错误页0；匹配跨页项缺来源页979/780/478。完整参数/指标/SHA/限制见 `docs/experiments/2026-10-29-paddle-full-val-three-condition-scores.zh-CN.md` 完成核验段。下一步同赛道配对比较与抽样错误/来源页审计，无需重推理/重评分；本轮未启动新任务。

- **2026-10-29 05:28 UTC（北京时间13:28）评分尚未全部完成：**adapter三组已完成、覆盖13,871页/原版回放一致；no_merge评分05:02 UTC完成、耗时68.23分钟，全表GriTS-Con=0.651021738、内容网格exact=0.115191341；cross_page子集Con=0.672710736、内容网格exact=0（匹配979不等于恢复979）。官方组正在CPU评分，compat待运行；父PID1297157仍active/running，worker1777772实际CPU计算，最终summary/结果哈希尚未发布。粗估余1.5–2小时，非承诺。第一组SHA/错误与边界见 `docs/experiments/2026-10-29-paddle-full-val-three-condition-scores.zh-CN.md` 05:28段。仅只读检查、未改变任务。

- **2026-10-29 03:52:33 UTC评分流水线检查点：**完整935/13,871的checkpoint/导出/GT哈希验收通过、audit.json已保存；进入三组adapter运行中，实际评分进程尚待核验，无新正式分数。66相关回归测试通过。详见本日三组评分实验；unit/PID及新目录同下条，未改变既有推理结果。

- **2026-10-29 03:52 UTC（北京时间11:52）Paddle全量三组CPU评分流水线已启动：**用户明确要求评分，相关回归通过后启动 `paper-paddle-scores-20261029T035007Z.service`，初始PID1297157、active/running；先audit全部checkpoint/导出/GT哈希，再adapter及no_merge、native_merge_official、native_merge_content_compat依次完整val评分。当前audit已核验400文档/3,600文件，尚未宣称评分器已运行/新分数完成。run根 `artifacts/cross-page-scores/20261029T035007Z-paddle-full-val-scores/`，事件日志 `artifacts/paddle-score-launchers/20261029T035007Z/events.log`。只CPU、无下载/重推理/覆盖，Linger=yes，无定期监控。详见 `docs/experiments/2026-10-29-paddle-full-val-three-condition-scores.zh-CN.md`。

- **2026-10-29 输入/流程说明（无新实验）：**本轮为完整文档image-only管线：数据集全页JPEG按原文档/数字页序打包无文字层PDF→PP-DocLayoutV3→PaddleOCR-VL-1.5逐页解析→官方跨页规则合并；不是GT裁剪片段拼接，也不是单个联合训练的跨页网络。官方no_merge/native_merge已保存，独立content-compatible全量CPU后处理/评分仍待执行。下一步先哈希验收再三组配对评分，复用已有预测，不重新GPU推理。本轮只解释流程，未启动评分。

- **2026-10-29 03:39 UTC（北京时间11:39）Paddle全量推理已完成：**原run935/935文档、13,871/13,871页，父summary.status=completed，935个worker summary均completed且无error字段；export-complete存在，导出13,871条JSONL解析/终止换行正确，按(document_id,page_number)核验missing/extra/duplicate=0，输入SHA与冻结数字页序一致。最后文档PMC7617896于00:11:16 UTC（北京时间08:11）结束；服务inactive/dead、MainPID0。本次未重算全部checkpoint文件SHA，未得正式全量评分；下一步哈希验收、三组CPU后处理及配对评分。未启动新计算或修改服务器文件。详情见 `docs/experiments/2026-10-23-paddle-full-val-inference.zh-CN.md` 10月29日段。

- **2026-10-27 15:45 UTC（北京时间23:45）Paddle全量进度：**同一run仍active/running、PID3358795；719/935文档checkpoint覆盖10,450/13,871页（75.34%），较上次增加362文档/5,455页。checkpoint解析错误/文档重复/额外/页数不一致均0。当前PMC11764768共20页，raw已完成18页[0..17]、无解析错误/尾残片，最新事件15:44:32 UTC；未计入完整checkpoint。GPU0空余34,121MiB、利用率22%。无父summary/全量正式指标；按全程均速剩余粗估31.5小时（约1–2天），不含评分，非承诺。仅更新本地记录，未改变任务。详见 `docs/experiments/2026-10-23-paddle-full-val-inference.zh-CN.md` 10月27日段。

- **2026-10-25 14:31 UTC（北京时间22:31）Paddle全量进度：**同一run仍active/running、PID3358795；357/935文档checkpoint覆盖4,995/13,871页（36.01%），较上次增加249文档/3,364页。checkpoint解析错误/文档重复/额外/页数不一致均0。当前PMC11008875共15页，raw已完成5页[0..4]、无解析错误/尾残片，最新页面事件14:31:14 UTC；未计入完整checkpoint。GPU0空余18,581MiB、利用率52%。父summary尚无、无全量正式指标；按全程均速剩余粗估83.6小时（约3–4天），不含后续评分。只读检查并更新本地记录，未重启/改变任务。证据见 `docs/experiments/2026-10-23-paddle-full-val-inference.zh-CN.md` 10月25日段。

- **2026-10-24 07:05 UTC（北京时间15:05）Paddle全量进度：**同一任务20261023T152753Z-paddle-val-full仍active/running、PID3358795；108/935文档已发布完整checkpoint，覆盖1,631/13,871页（约11.76%），checkpoint文档重复/额外/页数不一致均0。当前PMC10436224的9页已有8条完整raw JSONL、页序[0..7]，无解析错误/尾残片，日志07:05:33 UTC仍产出页面；该文档尚未计入完成数。GPU0空余17,343MiB、利用率55%，高于逐页8,192MiB保护线；此为整卡快照。未出最终summary/全量正式分数，未重启/修改任务。按启动以来整页吞吐粗估尚需约5天，非完成承诺。证据见 `docs/experiments/2026-10-23-paddle-full-val-inference.zh-CN.md` 的10月24日检查点。

- **2026-10-23 15:30 UTC 全量GPU推理实际开始：**任务20261023T152753Z-paddle-val-full、unit `paper-paddle-full-20261023T152753Z.service`、父PID3358795仍active/running；首篇PMC10154845全8页图像PDF核验通过，raw JSONL首3页[0,1,2]完整、无尾残片；文档checkpoint目前0，恢复粒度整文档。worker明确val/image-only/seed0；Linger=yes，用户可断开客户端。完整935/13,871尚未完成、无正式分数；不安排自动监控。详细证据及恢复入口见 `docs/experiments/2026-10-23-paddle-full-val-inference.zh-CN.md`。只做文档提交同步，不修改运行中的冻结代码。

- **2026-10-23 15:28 UTC Paddle全量已启动（启动预检）：**用户明确确认启动及后台保活，服务器zhengguojie Linger已从no核验为yes。任务20261023T152753Z-paddle-val-full，unit `paper-paddle-full-20261023T152753Z.service`、初始PID3358795，active/running；完整val935/13,871，启动GPU0空余39,607MiB。日志 `logs/paddle-launchers/20261023T152753Z/full.log`；run根 `artifacts/paddle-document-runs/20261023T152753Z-paddle-val-full/`。GPU首条预测待核验，不冒称已完成。详见 `docs/experiments/2026-10-23-paddle-full-val-inference.zh-CN.md`。未创建定期监控，未改原输入/官方包，任务中止可新RUN_ID恢复。

- **2026-10-23 启动询问只读复核：**技术READY不变，无新结果/未启动全量；本地和服务器代码b203248，GPU0空余39,607MiB、利用率0%、仍有4个既有计算进程；无运行中的paper-paddle用户service，Linger仍no。仅回答能否启动，未擅自启动或修改系统保活。

- **2026-10-23 PaddleOCR-VL-1.5 全量技术门禁 READY（未启动）：**最终代码b390273，服务器76相关测试通过、代码复审无阻塞；完整val935/13,871图片/JPEG/模型SHA/依赖/资源只读预检通过，报告 `logs/paddle-launchers/20261023T103500Z/full-val-preflight.json`。最终train四页完整入口pilot已exit0；实际恢复run104000 resumed_documents=1且无新增GPU工作，导出SHA不变并通过三组adapter。原/恢复artifact均保留。用户要求直到可启动，现停在验收点，不冒称val运行中。启动/恢复精确命令及证据在 `docs/2026-10-23-paddle-full-validation-readiness.zh-CN.md`。分支codex/paddle-merge-compat已同步两个远程，未合并main；Linger=no，全登录退出后持续运行需另获系统保活授权。此READY不代表OCRFlux/Popo各自门禁已过。

- **2026-10-23 最终全量门禁验收运行中：**`b390273`分支已同步两个远程，服务器76测试通过；完整val只读预检ready，935/13,871全成员、模型SHA/环境/资源通过，数字页序SHA `1d39ca16b7fcfedf3dabb174c80ef4ae914d90a76a2839617a469c0ba75e90c5`。最终版train pilot `paper-paddle-full-entry-pilot-20261023T103500Z.service`初始PID1304498，输出 `artifacts/paddle-document-runs/20261023T103500Z-paddle-train-pilot/`，完成/实际恢复/导出适配待核验；尚未启动val。Linger=no，不能承诺全部登录断开仍继续，未修改系统设置。见全量readiness文档。

- **2026-10-23 全量入口验收中间检查点：**新增按文档独占输出+checkpoint恢复入口，服务器初版72测试通过；train四页完整入口pilot `20261023T102500Z-paddle-train-pilot`已exit0，未运行val。只读val预检发现固定清单是词法页序，已改为保留原SHA/成员并单列数字页序派生SHA；并修复审查发现的checkpoint原子发布/导出清单再核验，复审无阻塞。最终版服务器回归、pilot恢复及完整val只读预检仍待完成。详见 `docs/2026-10-23-paddle-full-validation-readiness.zh-CN.md`；不可据初版pilot声称已ready或全量运行中。

- **2026-10-23 进一步全量门禁准备：**用户要求持续推进到可开始全量推理；新CLI集成回归服务器62测试通过。额外train负例文档PMC11626747全4页（官方负对[1,2]、无正对，且两页对应不同逻辑表）已打包，GPU0门禁空余39,607MiB后启动 `paper-paddle-negative-20261023T101200Z.service`，初始PID1156473；输出 `outputs/baselines/paddleocr-vl-1.5/20261023T101200Z-paddle-train-smoke/`、launcher `logs/paddle-launchers/20261023T101200Z/smoke.log`，完成状态待核验。无val推理启动。接下来有限真实负例验证及全量按文档断点入口/固定清单预检。

- **2026-10-23 10:02 UTC Paddle 三组 train 评分完成：**CPU复用6页预测；官方原版与无合并相同，全表 GriTS-Con=0.6438514；content-compatible 全表/跨页子集 GriTS-Con=0.9891835、结构网格exact=2/2、内容网格exact=0/2，两表匹配来源页均[1,2]完整。60相关测试通过、原输入及适配输出SHA全部核验不变。仅两个选定train正例，不是正式性能/负例误连率。评分 `artifacts/paddle-smoke/20261023T100300Z-three-condition-train-scores/`，详细命令/指标/限制见 `docs/experiments/2026-10-23-paddle-compat-adapter-and-train-score.zh-CN.md`。下一阶段更多train正负例审计及可恢复val入口；目前无GPU/后台评分运行、val全量未启动。

- **2026-10-23 Paddle 兼容版/评分适配已实现，train 评分待执行：**用户已确认设计；新分支 `codex/paddle-merge-compat`、代码 `9e6c5fa`，服务器60测试通过，6页覆盖完整、原版回放一致，兼容版形成2个[1,2]来源组而官方保持4个页表。原始预测/官方包未改、无GPU重跑；不等于2表恢复正确。新适配产物 `artifacts/paddle-smoke/20261023T100500Z-three-condition-adapter/`，详细命令/环境/已知限制见 `docs/experiments/2026-10-23-paddle-compat-adapter-and-train-score.zh-CN.md`。下一步三组train评分，val全量未启动。

- **2026-10-23 09:51 UTC Paddle 合并原因已核验：**两个 train 案例宽度/列数/边界行均通过，但续页 `figure_title` 的 Continued 被拒；PaddleX 3.4.1 合并器关键词分支读 `.text` 等字段，实际 block 文字保存在 `.content`。原类/原合并器 CPU 内存复现拒绝，仅桥接 text=content 则两例触发合并，原文件哈希不变。不是模型没识别出标题，也不代表合并网格正确。尚未修改官方包/实现补丁/评分 adapter 或启动全量。建议保留原官方基线并单列 content-compatible 修正版；设计待确认，详见 `docs/experiments/2026-10-23-paddle-native-merge-contract-audit.zh-CN.md`。

- **2026-10-23 09:47 UTC Paddle GPU smoke 完成核验：**自动任务已于 09:15–09:19 UTC（北京时间 17:15–17:19）运行完 2 文档/6 页，220.57 秒，安装与 smoke 均 exit 0、inactive/dead；缺失/额外/重复为 0，4 个 table HTML 均格式可解析。两份文档 no_merge/native_merge 完全相同，官方合并没有触发；这是 train 小规模可运行性验证，不是正式跨页分数或恢复成功。GPU 0 最低空余 34,103 MiB；当前推理已结束，无需重跑。下一步核验官方合并条件/来源页与评分适配，尚不能直接声称全量门禁通过。本轮只读核验，未启动全量或新任务，详细证据/产物 SHA 见 `docs/experiments/2026-10-23-paddle-v15-runtime-and-smoke.zh-CN.md` 完成段。

- **2026-10-23 08:25 UTC Paddle train smoke 后台入口已启动：**`paper-paddle-smoke-20261023T082900Z.service`、初始 PID 422511，当前 `WAIT_SETUP`，不是已开始推理；安装完成后自动执行 2 文档/6 页 native 管线与 no_merge/native_merge。输入 PDF 已在服务器生成并审计，13 项相关测试通过。launcher 日志 `logs/paddle-launchers/20261023T082900Z/smoke.log`；下一步先核验安装与 smoke 实际终态/来源页、HTML/耗时，不直接启动全量。完整记录 `docs/experiments/2026-10-23-paddle-v15-runtime-and-smoke.zh-CN.md`。

- **2026-10-23 Paddle 下一阶段运行中：**独立环境安装后台 `paper-paddle-setup-20261023T081029Z.service`（初始 PID 330647）；PP-DocLayoutV3 四文件已于 08:14:43 UTC 校验下载完成（status=0），新目录 `models/20261023T081029Z-paddle-layout/pp-doclayoutv3/`。计划将 train 两个完整三页文档打包成无文字层 PDF，核验官方 v1.5 页面管线与跨页重组；尚未启动 GPU 推理。代码/环境/日志/固定模型 SHA 见 `docs/experiments/2026-10-23-paddle-v15-runtime-and-smoke.zh-CN.md`。不得据安装运行中声称测试成功。

- **2026-10-23 08:06 UTC 下载完成核验：**三个模型主仓库的 50 文件均已下载并通过下载器大小/哈希校验；07:58:19 UTC `end status=0`，service 正常 inactive/dead。当前文件数量/大小及 LFS 哈希记录与官方配置再核对通过，本次未重算全部权重哈希。权重在 `models/20261023T064109Z-public-models/`。未启动新模型推理；下一步是 Paddle 独立环境、额外版面组件和 train smoke，不再重复下载这三个主仓库。详见 `docs/experiments/2026-10-23-public-model-downloads.zh-CN.md`。

- **2026-10-23 06:42 UTC 三模型后台下载已启动：**代码 `6c58a64`，用户 service `paper-public-models-20261023T064109Z` 为 active/running，PID `3915961`，06:42:43 UTC 开始。新目录 `models/20261023T064109Z-public-models/`，日志 `logs/model-downloads/20261023T064109Z-public-models/`；Paddle LICENSE 首文件已校验，三模型仍待 complete/summary 核验。下载无 GPU、无数据集变更；并未启动模型推理或修改已有 eval312 环境。完整命令/版本/许可见 `docs/experiments/2026-10-23-public-model-downloads.zh-CN.md`。

- **2026-10-23 06:41 UTC 公开模型下载准备：**用户已要求开始三个公开模型测试。已固化 50 个文件的官方 revision/大小/哈希清单，总计约 27.84 GB，下载器本地 7 项测试通过；计划服务器后台任务 `20261023T064109Z-public-models`，尚待启动确认。OCRFlux 权重 LICENSE 为 Qwen Research License，与工具 Apache-2.0 分开记录。日志/完整命令及后续阶段见 `docs/experiments/2026-10-23-public-model-downloads.zh-CN.md`。本轮不下载数据集、不使用 GPU。

- **2026-10-23 06:06 UTC HTML 审计已完成：**13,871 页/两层清单对账、输入前后 SHA 不变、旧评分 7 项哈希通过。637 张评分拒绝中 582 为词法兼容候选，55 未解决；前层 1,324 候选拒绝中 1,315 无 text，对应 1,159 页原串没有任何 text/HTML。两个拒绝页面集合交集 0；不能把候选数等同于 GT 丢表数。服务器相关 53 测试通过。产物 `artifacts/html-audits/20261023T060500Z-dots-html-filter-audit-v3/`；详细命令/哈希/案例/限制见 `docs/experiments/2026-10-23-dotsocr-html-filter-audit.zh-CN.md`。下一步在 train/合成样本冻结保真规范，并核验官方 prompt 的小规模推理；本轮没有新分数、GPU 或后台任务。

- **2026-10-23 HTML 审计准备：**用户授权直接操作服务器推进下一步。新增 CPU 两层过滤审计脚本，旧输入只读、确定性分桶抽样、输入前后哈希对账；服务器执行与结果待核验。无新模型指标，未改评分协议。详见 `docs/experiments/2026-10-23-dotsocr-html-filter-audit.zh-CN.md`。

- **2026-10-23 阶段交接（无新实验）：**已重新核对 dots.ocr 全量推理的结束日志（13,871/13,871 页）与离线评分结束日志（`status=0`）；7 项评分产物 SHA-256 复核全 `OK`。已将进度总表中过期的“断点补跑中/合并未开始”修正为**页级推理及配对评分已完成、解析有效性待核验**。成果、边界与下一步集中记录于 `docs/experiments/2026-10-23-cross-page-stage-summary-and-handoff.zh-CN.md`；原结果不变。下一项优先 CPU 审计两层 HTML 过滤，train 上冻结修正规则，旧预测新目录复评 val；并行只读核验 POTATR 制品，未经 GPU 门禁不启动新全量任务。

- **2026-10-20 15:56 UTC dots 评测链路风险确认：**val 真值 2,587 表；自定义提取器有 1,324 条 HTML 警告；adapter 留下 2,752 张表，XML 严格解析再剔除 637，真正评分 2,115 张。637 错误只读分类：标签不匹配 520、非法字符 99、多根 12、未知实体 6，未归因到模型 vs 解析策略。全表 GriTS 聚合使用 vendored evaluator，未见已证实公式 bug；自定义 cross_page 按 Con 先匹配再抽 GT 子集、不对额外预测罚 precision，cross Top 复用 Con 匹配；2/983 格子 exact 不验证来源页。先按 train/官方管线冻结 HTML 处理、prompt 和合并协议，再在**新目录**复评 val；不得修改旧指标或混称论文同协议。详见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 15:56 段。

- **2026-10-20 与原论文对比纠偏：**原 PDF 表 7 的 `dots.ocr + merging` 为 Full Documents **test、全部表**，GriTS-Con `0.6844`、Acc-Con `0.1180`；使用 ViT-B/16 续接预测、列数相同则纵向拼接。本地是 **val** 全表 `simple_merge` GriTS-Con `0.5479001476`、内容网格 exact `0.0819482026`，另列 983 张跨页真值子集 exact `2/983`；不可用 `2/983` 对照论文的 `0.1180`。仍有全表差距，原因待核验：split、续接器与 HTML/提示词/评估预处理；本地 2,752 未合并预测中 637 条 HTML 评分无效。详情和 PDF 页码、待核验步骤见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 15:50 核查段；不得把格子 exact 直接当成已核准的跨页恢复成功数。

- **2026-10-20 13:59 UTC dots.ocr 全页配对评分已完成：**后台 13:48:59 UTC exit 0，unit `inactive/dead`，两组完整覆盖 val 13,871 页；后台列出的 7 项 SHA 校验均通过。跨页 GriTS-Con `no_merge 0.4576991966` → `simple_merge 0.5131445386`，跨页内容网格 exact `0` → `2/983`；匹配跨页表却 `643` → `639`，不能称为无条件改进。预测表 `2752` → `2597`，155 次规则接受正确性尚未核验。完整结果/命令/限制见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 完成核验段。接下来审计配对差异、错误和真实 train 误连；并行只读核验 POTATR 公开制品；不要凭 validation 调合并规则。

- **2026-10-20 社交文章补查（第一篇已核验/第二篇待核验）：**微信文章介绍 TeleOCR（官方论文 arXiv:2608.12898、公开约 1.2B 模型），证据支持它作为页级解析器可选上游，未见可核验的跨页逻辑表合并/完整文档跨页指标；不自动加入五方案核心。小红书链接仅获取通用/失效页面，无正文，待用户提供截图或模型名。详情和来源 `docs/experiments/2026-10-20-social-posts-teleocr-baseline-audit.zh-CN.md`；五方案和 dots CPU 任务均不变。

- **2026-10-20 13:17 UTC 后台评分转入第二组：**dots.ocr 固定简单合并已完成，1,213 候选边界、规则接受 155 次、预测表 2,752→2,597；这是规则动作数，**不是正确合并数**。`paper-dots-eval-20261020T123212Z.service` 仍 active/running，已进入 `STEP simple_merge score`；第二组指标和最终退出码尚无。合并 SHA/路径及限制见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 13:17 检查点。

- **2026-10-20 13:12 UTC dots.ocr 评分阶段检查点：**后台 no-merge 严格全页评分已生成 `artifacts/cross-page-scores/20261020T123212Z-dots-full-val-offline-no-merge/metrics.json`；13,871 页完整，983 跨页真值、内容有正重叠匹配 643、跨页 GriTS-Con `0.4576991966`、跨页内容网格 exact `0.0`，全表 GriTS-Con `0.5077936893`、全表内容网格 exact `0.0815616544`，非法 HTML 637。所有 643 个匹配跨页表都存在预测来源页缺失；**不等于成功恢复 643 张表**。service 仍 `active/running`，已转 `STEP repeated_header merge`；简单合并与 paired 评分未结束。单组 SHA、失败明细与定义见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 的 13:12 检查点。下一步核验最终 unit 退出码、第二组结果/校验和后再报告 paired 增益，不能用 val 调规则。

- **2026-10-20 POTATR 纳入候选方案（计划，不是已测）：**新当前执行入口 `docs/2026-10-20-cross-page-five-method-evaluation-plan.zh-CN.md`，原四模型计划保留历史和资源门禁。完整文档基线新增 `POTATR + merging`，分别规定 OCR（image-only + OCR）与 PDF DT（PDF-text-assisted）文字输入；PDF-text-assisted 和 image-only 分开报告。论文附录 `POTATR + merging` 行文字来源尚待官方代码/作者确认。当前仅 dots.ocr 全页预测完成、CPU paired 评分在运行；POTATR 代码/权重/续接器在本地未核实可用，不得标成已启动。次序：先验收 dots 配对评分；并行只读核验 POTATR 公开制品；权重门禁通过后实现无真值全页 adapter、train smoke、GPU 门禁，再 val 全页配对评测。已知同表片段裁剪另立 oracle 诊断轨道。没有更改已有运行任务/数据。

- **2026-10-20 文献版本补查：**PubTables-v2 论文 arXiv:2512.10888v3 的 Full Documents 表 5 含逐页 `DeepSeek-OCR 2` 及整篇 `Claude Opus 4.6`、`GPT-5.4`、`Gemini 3.1 Pro`；`PaddleOCR` 行不能解释为 `PaddleOCR-VL-1.5`。项目四模型计划仍固定 `PaddleOCR-VL-1.5`，`PaddleOCR-VL-1.6` 需另审计，未确认有官方 `PaddleOCR-VL-2`。详见 `docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md` 的 2026-10-20 版本补查；没有为这些模型启动新实验。

- **2026-10-20 用户指认模型纠正：**上一条回应误把用户指的 PubTables-v2 表 3/4 的 TATR/POTATR 系列理解成表 5 的通用模型。`TATR-v1.1-Pub` 裁剪表 PDF-text-assisted validation 已在本项目完成；`TATR-v1.2-Pub`、`POTATR` 当前项目内无已核实权重；`POTATR + DT` 是同一页面模型加 PDF Direct Text，不是新 checkpoint，三种赛道不可混比。详见上述报告同日补正；后续核验官方发布再决定是否下载或复现，不得冒充现成可跑。

- **2026-10-20 已知跨页片段实验边界：**Full Documents/val 官方逻辑表 `parts` 有跨页表身份、来源页和每片段页面 bbox；本地没有配套的独立跨页片段图，须从只读原页派生到新目录，且片段内无官方逐行/逐列标签。给模型真值框和同表分组属于 oracle 检测/关联后的片段恢复诊断，不能与完整文档端到端结果混称。已保存的 TATR-v1.1-Pub 可先 smoke 片段识别，但无自带跨页合并；POTATR 权重缺失、原生整页输入，裁剪片段可用性待核验。详情追加在 `docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md` §3.2。

- **2026-10-20 POTATR 赛道澄清：**跨页主任务需要 `POTATR + merging`；`+ DT` 是额外 PDF 原生文字输入条件，不是合并器。论文 Full Documents 附录 `POTATR + merging` 表未明确该行文字源，不得未经核验就归类为 image-only 或写作已验证的 `POTATR + DT + merging`。复现实验应将文字源和合并策略拆成两维并标记赛道，详见上述报告 §3.3 输入赛道补注。

- **2026-10-20 12:36 UTC 全量离线评测运行中：**dots.ocr `image-only` 四分片严格适配成功：13,871/13,871 页全覆盖，2,752 张未合并表，历史 2 页 error。用户要求后台运行；无合并评分已由用户级 `paper-dots-eval-20261020T123212Z.service` 启动，PID `1269023`，后续自动做固定简单合并与配对评分。输出和运行日志位于 `artifacts/cross-page-{adapters,merges,scores}/20261020T123212Z-dots-full-val-offline-*`、`logs/cross-page-scores/20261020T123212Z-dots-full-val-offline/`。**当前无正式分数。**`Linger=no`：关闭当前 VS Code 若其他登录会话仍在，后台任务可独立运行；全部登录会话退出后则不能保证。详细命令/中断前景评分/限制见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md`。下一步核验 unit `END ... status=0`、两组 metrics/覆盖/哈希，并记录指标；系统级 linger 需用户明确授权。

- **2026-10-20 12:26 UTC 阶段完成：**`20261020T015543Z-dots-full-val` 已于 04:14:23 UTC 正常退出（exit 0），最后 240 页均 `ok`。四段合计固定 PubTables-v2 Full Documents/val **13,871/13,871 页终态全覆盖**，JSON 验证、清单逐条顺序、唯一性审计通过，missing/extra/duplicate 均为 0；总计 `ok=13,869`、历史 `error=2`，1,168 页带 1,324 条 `invalid_table_html` warnings。末段 SHA `0a0a878f636786a3ff7d72dec423f7943668d389b6bffb1f192e036e760a3349` 与后台 SHA 文件一致。**仅页级推理完成，尚未进行跨页整表合并和离线评分**。下一步先只读审查完整预测的适配/合并契约及 error 处理，再在独立目录做配对离线评测；不得使用 val 调参。详细证据见 `docs/experiments/2026-10-20-dotsocr-full-val-last-240-resume.zh-CN.md`。

- **2026-10-20 01:57 UTC 运行中：**用户要求继续补齐剩余 240 页。三段固定历史分片的路径、行数和 SHA 均通过预检，联合 13,631 页严格匹配输入前缀；后台入口已支持三分片，151 项回归通过。GPU0 启动余 39,559 MiB、有 4 个已有进程；新 `20261020T015543Z-dots-full-val` 用户级 service active/running（wrapper `946957`、runner `947020`）。首条新页 `PMC12305305_page_0.jpg` 与清单一致，已存新页 3 条均 `ok`；联合 **13,634/13,871**，缺 237 页、无重复，GPU0 最近余 21,313 MiB。只读旧分片，新时间戳输出；持续查 unit/监控/页数，完整覆盖后再评分。`Linger=no`；无完整评测/跨页评分。完整命令及路径见 `docs/experiments/2026-10-20-dotsocr-full-val-last-240-resume.zh-CN.md`。

- **2026-10-20 01:52 UTC 状态修正：**`20261017T081912Z-dots-full-val` 已于 **2026-10-19 17:20:05 UTC** 因 GPU0 空余跌至 7,589 MiB 触发保护中断（unit failed，exit 143），**当前未运行、未完成全量**。三分片累计 **13,631/13,871 页**（98.27%），前缀完整、无重复，缺 240 页；`ok=13,629`、历史 `error=2`，新分片 SHA `90209757ffa3bf1b6ac6e3682b89a4acce46a67243227d5b67660732af43bbfa`。下一个 ID `PMC12305305_page_0.jpg`。下一步先修订后台入口接受三个固定只读分片并测试，重新核对 GPU 资源后在全新目录补缺，完整覆盖审计后再离线跨页评分；**现无正式全量或跨页分数**。详细证据见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

- **2026-10-19 15:19 UTC：**GPU0 上 `20261017T081912Z-dots-full-val` 仍 active/running，三段联合 **13,375/13,871 页**（96.42%），余 496 页；全部 JSON 可解析、ID 唯一且匹配固定清单前缀。新分片 6,588 条均 `ok`，历史共 2 条 `error`，GPU0 最近空余 15,125 MiB，未见完成/保护停机。任务继续运行；完成后必须联合审计完整覆盖及错误，再离线跨页合并评分。证据见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

- **2026-10-19 09:18 UTC：**GPU0 上 `20261017T081912Z-dots-full-val` service 仍 `active/running`。三段预测合计 **12,600/13,871 页**（90.84%），剩 1,271 页；新分片 5,813 页均 `ok`、历史共 2 页 `error`；全部 JSON 可解析、ID 无重复且严格匹配固定清单前缀。GPU0 最近余 15,125 MiB，无 guard/finished；继续监控，完成后审计全覆盖，再进行跨页合并与评分。证据见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

- **2026-10-18 13:27 UTC：**`20261017T081912Z-dots-full-val` 用户级 service 仍 `active/running`（wrapper `2239841`）。三段累计 **10,292/13,871 页**，约 74.2%，剩余 3,579 页；联合 JSON 可解析、ID 无重复并严格匹配 manifest 前缀。新分片 3,505 页均 `ok`，历史共 2 页 `error`；GPU0 最近空余 16,227 MiB，未见保护停机。持续监控，完成后再联合审计和离线跨页评分；无正式全量结果。详情见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

- **2026-10-17 11:09 UTC：**`20261017T081912Z-dots-full-val` 在 GPU0 的用户级 service 仍 `active/running`；第三分片 364 条全 `ok`，三段合计 **7,151/13,871 页**，联合 ID 唯一且与固定清单前缀吻合，剩余 6,720 页。GPU0 最近空余 16,227 MiB，未见 guard 事件；继续监控资源及页数，结束后审计全覆盖和离线跨页评分。检查证据见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

- **2026-10-17 08:53 UTC：**补跑 `20261017T081912Z-dots-full-val` 用户级 unit 仍 active/running；新分片 65 行，和两段旧分片合计 6,852/13,871（仅行数检查）。`Linger=no`，检查时尚有 7 个用户会话；关闭 VS Code 若导致最后一个用户会话退出，service 可能停止。未更改系统设置；当前仍需监控。证据见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

- **2026-10-17 08:26 UTC 运行中：**用户要求继续在本机 GPU0 补足 PubTables-v2 Full Documents/val。双分片恢复入口已修复、前 6,787 页前缀校验通过、后台 `rg` 依赖已消除，151 项回归通过；新任务 `20261017T081912Z-dots-full-val` 用户级 service active/running（wrapper `2239841`、runner `2239881`），GPU0 启动余 40,579 MiB，已有 4 个计算进程。新分片已保存 7 页且均 `ok`，累计 **6,794/13,871 页**、无重复、旧分片 SHA 未变，仍缺 7,077 页；GPU0 最近余 23,411 MiB。接下来持续检查 unit、`events.log`、`progress.csv`、`gpu-memory.csv`、新预测和显存；三段合并审计后再离线跨页评分。`Linger=no`，不能保证所有登录会话退出后任务继续。完整命令、哈希与路径见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

- **2026-10-17 08:14 UTC 本机只读检查：**四张 A100 GPU0/1/2/3 空余显存 40,579/423/25,343/22,761 MiB，瞬时利用率均 0%，但分别有 4/1/10/10 个计算进程，不可视为独占空卡。补跑仍 failed，累计 6,787/13,871 页，**无新结果**；未启动任务。后续若恢复，仍须先修复双分片断点入口及后台监控并重新检查资源。证据见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。

- **2026-10-12 11:29 UTC 本机检查：**四张 A100 GPU0/1/2/3 分别空余 33,993/423/20,569/22,545 MiB，利用率 60/0/33/59%，均有计算进程。补跑 unit 仍 failed、两分片合计 6,787/13,871 页无新增；只读检查，未启动实验。需先修复双分片断点入口与 `rg` 监控并确认稳定的共享 GPU 窗口。详细快照见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。

- **2026-10-11 远端候选待核验：**用户提议 `172.17.62.73` GPU。主机 ED25519 指纹已核对一致，但当前机器无免交互 SSH 登录。用户从已登录 73 终端提供快照：5 张 RTX 3090 中 GPU0/2 句柄报错；GPU1/4 各剩 24,240 MiB、无列出的计算进程，GPU3 剩 21,765 MiB、有现存进程。**仅 GPU1/4 可列为试跑候选，未证明能承载全量**：旧 A100 smoke 增量 16,644 MiB，在 3090 上若相近会使余量低于当前 8,192 MiB 保护阈值。先核验远端模型/数据/环境及安全认证，修复两旧分片续跑和缺失 `rg` 监控，再做受控 GPU 短试跑；未经批准不迁移/启动。仅主机公钥保存在 `artifacts/ssh-known-hosts/20261011-server73-ed25519`，不保存密码。详见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。

- **2026-10-11 05:16 UTC 状态更新：**10 月 10 日断点补跑已于 08:59:38 UTC 因 GPU0 空余显存降至 47 MiB 触发保护而中断（unit failed，exit 143），当前**没有运行中的补跑**。两分片累计 **6,787/13,871 页**（约 48.9%，6,785 `ok`、2 `error`），严格匹配清单前缀、无重复，剩余 7,084 页；下一页 `PMC11233398_page_5.jpg`。后台环境缺失 `rg`，导致两项日志告警检查未可靠执行；重启前须修正并测试监控、重查 GPU 资源，只用全新目录并只读复用旧分片。没有完整评分；日志、SHA 和限制见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。

- 2026-10-10 02:52:57 UTC：负耗时缺陷已修复为单调时钟，151 项回归、Ruff 和断点预检通过；原 6,151 页预测 SHA 未变。补跑 `20261010T024700Z-dots-full-val` 用户级 service 仍 active/running（wrapper `3225365`、runner `3225408`）；新分片首两页已按固定清单续接、均 `ok`，进度共 **6,153/13,871**，仍缺 7,718 页；GPU0 最近余 32,593 MiB。下一步持续查 unit/日志/显存，结束后联合两分片审计全覆盖与离线评分，**目前没有完整结果**。详情与中断/恢复入口见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。

- **2026-10-10 02:41 UTC 重要状态修正：全页后台推理已在 2026-10-09 06:54:01 UTC 失败退出（exit 1）**，不是仍在运行或已完成。保存了 6,151/13,871 条唯一、清单前缀一致的预测，6,149 `ok`、2 `error`，还差 7,720 页。日志显示 `time.time()` 计算得到负的 `elapsed_sec=-27.142`，导致 Pydantic 校验在成功与错误记录两条分支均失败；墙上时间回退的原因待核验。原始输出不动；先补单调时钟回归测试与修复，再在新的输出目录用 `--resume-from` 补缺。证据与 SHA-256 见 `docs/experiments/2026-10-06-dotsocr-full-val-background.zh-CN.md` 的 10 月 10 日中断核验；尚无完整跨页结果。

- 2026-10-07 04:12 UTC：后台全页推理 unit/runner 仍运行；`outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl` 已刷盘 955/13,871 页，954 `ok`、1 `error`、78 页有 92 条 `invalid_table_html` 警告，无重复或清单外页，前缀顺序一致；GPU0 尚余 23,423 MiB。详见 `docs/experiments/2026-10-06-dotsocr-full-val-background.zh-CN.md` 04:12 UTC 检查点；尚无全量结果与跨页成绩。

- 2026-10-06 17:26:41 UTC：dots.ocr `image-only` PubTables-v2 Full Documents/val **全 935 篇/13,871 页页级推理后台运行中**。用户级 service `paper-dots-full-val-20261006T172527Z.service`，wrapper PID `3946380`、runner PID `3946441`；GPU0 初始空余 48,737 MiB，4 个既有进程。17:29 UTC 已刷盘 2 页，均 `ok`，周期进度正常；次日检查 `logs/baselines/dots-ocr/20261006T172527Z-dots-full-val/{events.log,progress.csv,gpu-memory.csv,inference.log}`，详见 `docs/experiments/2026-10-06-dotsocr-full-val-background.zh-CN.md`。**`Linger=no`，若全部登录会话结束，service 可能停止；没有自动重启保证。**最初 `nohup` 尝试未进入推理，保留空日志；不与 OCRFlux HTML 数据混算，完成后仍需离线合并与评分。

- 2026-10-06 17:11:59--17:15:13 UTC：共享 GPU0 上 PubTables-v2 val `PMC11977379` 完整 3 页 dots.ocr 短试跑**已正常结束**（PID `3837378`；3/3 页 ok，无解析警告，1 张页级表；整卡采样峰值占用 48,946 MiB，增量 16,644 MiB，结束后恢复原用量）。新旧同文档逐页原始输出相同；**仍未恢复跨页整表**，不代表正式得分。产物/哈希/限制见 `docs/experiments/2026-10-06-dotsocr-full-documents-gpu0-smoke.zh-CN.md`。未启动全量；下一步另选较长完整文档测资源，且全量启动前重新确认共享运行窗口。

- 2026-09-30 04:07 UTC：本轮准备提交截至目前的研究代码与文档，提交前 HEAD `e615493`，分支 `main`；全量测试 149 项和 Ruff 检查通过。未启动 GPU 任务或新下载；后续 GPU smoke 前必须重新检查资源。进度索引记录了本轮检查点。

- 目标是可投稿的**文档级跨页逻辑表恢复**，不仅是续表二分类；固定主基准 PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`。`image-only` 和 `PDF-text-assisted` 分开报告。现行五方案计划见 `docs/2026-10-20-cross-page-five-method-evaluation-plan.zh-CN.md`，历史四模型协议见 `docs/2026-09-29-cross-page-four-model-evaluation-design.zh-CN.md`。
- 阶段 0 已完成：val 935 篇、13,871 页全部纳入输入清单；按不同 `parts.page_num` 得到 983 张跨页表（869 篇文档）；同页多片段 63 张不计跨页；官方相邻页对正/负例 1,276/786。`PMC12274235-table-1` 是 `[4,5,7]`，不能捏造第 6 页片段。证据：`docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md` 和 `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/`。
- 阶段 1 **部分完成**：离线跨页评分器已实现文档内全真值一对一匹配，再评分跨页真值子集；要求全部页的终态和预测表来源页；129 项回归测试通过，validation 异常文档的空预测仅验证协议，不是模型得分。证据：`docs/experiments/2026-09-29-cross-page-offline-scorer.zh-CN.md`；源码 `src/cptla/evaluation/cross_page.py`、`scripts/score_cross_page_predictions.py`。
- 阶段 1 的 dots.ocr **`no_merge` 适配器和真实旧三页 smoke 离线评分链路已完成**：输入输出哈希在两次独立目录复算一致，全量回归 135 项通过。**勘误：**该 smoke 的唯一真值表实际上跨 `[1,2]` 页（此前口头误认无跨页表），旧预测仅来自第 1 页；结构/内容 grid exact 0/1，局部 GriTS 不能代表跨页整表恢复。见 `docs/experiments/2026-09-29-dotsocr-no-merge-document-adapter-smoke.zh-CN.md` 及 `artifacts/cross-page-adapters/20260929T100115Z-dots-smoke-no-merge/`、`artifacts/cross-page-scores/20260929T100115Z-dots-smoke-no-merge/`。
- **简单拼接基线已实现和验证，但尚无真实 train/val 大范围效果：**固定邻页/页边位置/同列/完全重复表头才合并；train 整表人工分行仅测结构；合成负例证实即使全部条件成立也能误合并。冻结后在旧 validation smoke 的候选数、合并数均为 0（后页无预测表），结果与 `no_merge` 相同；全套回归 149 项通过。依据 `docs/experiments/2026-09-29-dotsocr-repeated-header-simple-merge-baseline.zh-CN.md` 和 `artifacts/cross-page-merges/20260929T101235Z-dots-val-smoke-simple-merge/`。
- 2026-09-29 10:41 UTC：已从 `https://hf-mirror.com` 下载 `ChatDOC/OCRFlux-pubtabnet-cross` 固定 revision `10f47124646489a33c9c9c049707d7e710b00a31`。9,064 条 JSONL 全部可解析，字段完整且 HTML 不为空；图片归档包含 9,064 张图片。日志、SHA-256 和详细审计见 `docs/experiments/2026-09-29-ocrflux-pubtabnet-cross-download.zh-CN.md`。该数据仍只作为 HTML 片段拼接补集，不是自然跨页页面图像；官方 endpoint 本轮超时，镜像来源限制保留。
- 重要协议澄清：OCRFlux 补集中的图片是原始完整表格图，不能直接当作两张跨页页面图送入 OCR 模型；主用途是把 `table_fragment_1/2` 输入 HTML 合并接口，单独报告合并结果。其结果不能与 PubTables-v2 的文档级 image-only 跨页恢复指标直接合并比较。
- **2026-09-29 10:20 UTC 计划纠偏：**真实 train 页级预测用于研究简单合并误连率，**不是**启动 dots.ocr validation 全量页级推理的前置门槛。已有 dots.ocr 本地权重和 val 全页清单（SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`）；可以先运行 13,871 页的 `image-only` 页级推理，保存全量终态，之后再离线进行配对后处理。全量未启动。10:20 UTC 的只读 GPU 快照：GPU 0 约 48,737 MiB 空余但有 4 个 compute 进程，GPU 1/2/3 约 423/11,033/13,321 MiB 空余且都有进程；不能把显存数字当作可独占授权，启动前重新检查并确认与现有任务互不冲突。

## 下一步与约束

**2026-10-23 最新优先级：**先 PaddleOCR-VL-1.5 → OCRFlux-3B → MinerU-Popo，POTATR 后置。三个官方权重候选 SHA、接口及服务器预检已完成；权重/新环境/adapter/smoke 尚未准备，未启动新 GPU 任务。Popo 优先核验官方 Paddle 页输出转换，并对同一上游比较不合并/原生合并/Popo；不能把不同上游增益混为后处理提升。服务器 HF 官方 API 不通、镜像 API 部分 403，但固定 SHA config 解析 URL 均 200；下一步逐文件固定清单并在服务器下载、独立环境、train smoke，不能把小文件可达称为权重已下载。入口 `docs/2026-10-23-open-model-priority-and-readiness.zh-CN.md`。下列 dots 工作仍有效但不再作为公开模型准备的前置条件。

1. **HTML 审计已完成，先验证修正：**在 train/合成样本上核验明确版本的 HTML 规范化及文字/网格保真，通过后从旧预测以新目录重评 val。原串无 text 的 1,159 页无法靠解析恢复，须在 train 完整文档上检查官方 prompt/chat 模板的受控短推理；不能按 val GT 调 prompt，也不立即全量重跑。之后审计 155 次接受边界及真实 train 负例误连率；不能宣称合并全正确。本轮无持续运行的任务。
2. 并行只读核验 POTATR 作者公开代码/权重、许可证及续接器；未取得可核实制品前不启动该支 GPU，不把未测写成 0。随后按五方案计划建立全页无真值 adapter 与 OCR/DT 独立文字赛道；完善不足的评分指标/误合并诊断，再根据重新检查的 GPU 显存与已有进程决定 smoke。不能凭旧 GPU 快照认定资源空闲。
3. 正式 validation 必须输入全部 13,871 页，只在评分阶段选真实跨页表；test 仅用于协议冻结后的最终评估。每个运行使用新带时间戳目录，不删除或覆盖已有数据、产物、日志。

## 留痕机制（必须执行）

- 每个可验收子阶段结束、连续工作约 60 分钟、后台任务启停/状态变化、失败/方案改变、会话结束/可能中断前都要检查和更新记录；每轮结束至少核对本文件与进度索引是否仍准确。无实质变化记检查点，不编造新结果。此要求不意味着离线自动定时执行。
- 细节与可复现证据写入 `docs/experiments/YYYY-MM-DD-任务.zh-CN.md`；进度索引追加阶段状态和链接；本文件只更新“当前状态、限制、下一步”及必要证据入口。重要更正追加勘误并保留旧证据。长任务启动即记 PID/命令/日志/输出和完成条件，结束时补记覆盖/失败/指标/校验和。
- 仓库之外的隐式记忆不保证可读或持久；**以仓库文档、日志及原始产物为唯一跨会话恢复依据**，不访问仓库外文件来写“长期记忆”。

## 2026-11-05 本地研究阶段与可行性复核

仅审阅本地计划、代码和保存记录，无新实验/服务器访问。判断：完整文档基线部分完成，仍处 M0 评测复现向跨页核心方法验证过渡；不能把全文档基线运行视作 M4 自研系统完成。OCRFlux 最新保存状态仍为11月3日366/935篇，当前实时状态待核验。主要缺口为细粒度派生标签审计、严格来源页/误合并评价、自研方法与消融；建议固定上游先验证跨页结构贡献。完整证据与边界见 [阶段复核](reports/2026-11-05-research-stage-and-feasibility.zh-CN.md)。无新结果，未改变服务器任务。

## 2026-11-06 2B–4B候选模型补查

只读核验官方模型页/论文，新增 [候选报告](reports/2026-11-06-small-vlm-cross-page-candidates.zh-CN.md)：Qwen3-VL-2B/4B、DeepSeek-OCR-2约3B、MonkeyOCR-pro-3B、InternVL3_5-4B。区分页解析、多图输入和明确跨页合并；MonkeyOCR v1.5模块与公开权重/代码对应仍待核验。无新实验/服务器访问，不改OCRFlux→Popo既有安排，也不更新任务实时状态；下一步如选型，先固定revision及train完整文档正负例smoke。
