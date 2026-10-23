# 项目研究进度

2026-10-23 15:30 UTC（北京时间23:30）Paddle全量真实GPU启动已核验：service active、PID3358795，首篇8页文档的前3条JSONL完整，首条15:29:04 UTC；checkpoint尚0，不能称整文档完成。Linger=yes且无自动监控，完整935/13,871仍运行中、无正式指标。见 [全量推理实验](experiments/2026-10-23-paddle-full-val-inference.zh-CN.md)。

2026-10-23 15:28:13 UTC（北京时间23:28:13）Paddle完整val后台启动：935文档13,871页，run20261023T152753Z-paddle-val-full，unit `paper-paddle-full-20261023T152753Z.service`、初始PID3358795，active/running。用户已授权启用并核验Linger=yes；当前启动预检，GPU首条产物待核验。输入只读、GPU0共享，不下载新数据/权重、无定期监控。日志/配置/恢复/完成条件见 [全量实验记录](experiments/2026-10-23-paddle-full-val-inference.zh-CN.md)。

2026-10-23 用户再次询问能否启动时只读核验：代码b203248一致，GPU0空余39,607MiB，技术READY不变，无新实验结果/未启动全量；Linger=no运维边界保持，未修改系统配置。详情见全量启动门禁文档末尾。

2026-10-23 当前优先Paddle模型全量技术门禁READY，尚未启动val。最终76服务器测试及复审通过；完整935/13,871只读预检通过；最终train四页新入口和实际恢复均完成（恢复1文档、无新增GPU、导出SHA一致），导出再次通过三组adapter。代码b390273在codex/paddle-merge-compat，最终文档同步该分支，不改main。用户要求推进到可启动，现达该点；Linger=no导致全会话退出后保活需额外授权。下一步按新RUN_ID启动全量；证据/命令/运维限制见 [全量启动门禁](2026-10-23-paddle-full-validation-readiness.zh-CN.md)。

2026-10-23 最终版门禁检查点：b390273服务器76测试通过，完整val只读预检ready（935/13,871、模型SHA/环境/资源及图片全成员正确）；数字页序派生SHA已留痕。最终版4页train入口pilot已启动，unit/PID1304498与恢复验收待核验；未启动val全量。运维Linger=no边界未擅改，见 [启动门禁](2026-10-23-paddle-full-validation-readiness.zh-CN.md)。

2026-10-23 全量入口阶段检查点：初版72服务器测试通过，完整train四页pilot exit0并产生checkpoint/导出；val只读预检发现词法页序而停止，未启动val GPU。已保留源SHA/成员并新增数字页序清单，补齐checkpoint原子发布与导出SHA重验，独立复审无阻塞；最终回归/pilot恢复/val预检待完成。入口和证据见 [全量启动门禁](2026-10-23-paddle-full-validation-readiness.zh-CN.md)。

2026-10-23 全量门禁扩展：用户要求持续到可启动全量；服务器62回归测试通过。新增train真实负例PMC11626747全4页任务 `paper-paddle-negative-20261023T101200Z.service`（初始PID1156473）已启动，来源/参数/日志见 [Paddle train审计](experiments/2026-10-23-paddle-compat-adapter-and-train-score.zh-CN.md)。GPU0启动前空余39,607MiB，未改数据或其他进程。下一步核验负例、实现全量按文档恢复及清单预检，val全量尚未启动。

2026-10-23 10:02 UTC（北京时间18:02）Paddle三组train评分完成：6页覆盖完整、无非法HTML，官方原版与无合并相同；兼容版两个案例来源页均完整、结构网格exact 2/2，内容网格exact仍0/2，全表GriTS-Con 0.6438514→0.9891835。仅两个选定train正例，不能当全量性能；原输入/输出SHA复核不变。下一步更多train正负例与可恢复val入口，未启动全量。详见 [三组配对评分](experiments/2026-10-23-paddle-compat-adapter-and-train-score.zh-CN.md)。

2026-10-23 Paddle 适配验收检查点：新分支 `codex/paddle-merge-compat` 实现官方原版回放及独立 content-compatible 后处理，服务器60相关测试通过。6/6页无缺失/重复，原版回放一致；compat形成2个跨页来源组，尚无正确率结论。只用CPU，原结果/官方包未改；train三组评分待执行，val全量未启动。见 [Paddle 三组后处理与评分](experiments/2026-10-23-paddle-compat-adapter-and-train-score.zh-CN.md)。

2026-10-23 09:51 UTC：Paddle 两个 train 案例未合并原因定位为官方 block 与关键词读取的字段契约不匹配；仅 CPU 内存桥接后两例触发合并，原结果未改，尚无正确率或误连结论。推荐官方原版和独立兼容修正版分开报告，连同严格来源页 adapter 设计待确认；未启动全量、未新增 GPU/下载。证据与下一阶段选择见 [Paddle 官方合并契约审计](experiments/2026-10-23-paddle-native-merge-contract-audit.zh-CN.md)。

2026-10-23 09:47 UTC（北京时间 17:47）：只读核验 Paddle 环境安装及 train GPU smoke 均已 exit 0，任务不再运行；09:15–09:19 UTC 处理 2 文档/6 页共 220.57 秒，missing/extra/duplicate=0，4 个页面表 HTML 格式检查通过。两文档 no_merge/native_merge 相同，未触发官方合并，不能冒称完整跨页恢复成功。最低空余显存 34,103 MiB。下一步核验官方合并判据/来源页及评分 adapter，尚未启动全量 val 或产生正式分数。证据、SHA 与限制见 [Paddle 环境与 smoke](experiments/2026-10-23-paddle-v15-runtime-and-smoke.zh-CN.md) 的完成核验段。

2026-10-23 08:25 UTC：服务器生成并审计完成 2 文档/6 页 image-only PDF；13 项相关测试、bash 语法通过。有限后台 `paper-paddle-smoke-20261023T082900Z.service`、初始 PID 422511 已启动，目前 `WAIT_SETUP`，等独立环境安装完成后自动做官方页面预测与两组跨页重组；GPU 推理与新分数仍未确认。日志/命令/版本与限制见 [Paddle 环境与 smoke](experiments/2026-10-23-paddle-v15-runtime-and-smoke.zh-CN.md)。

2026-10-23 Paddle 执行检查点：独立新环境后台安装运行中，PP-DocLayoutV3 四文件在 08:14:43 UTC 全部校验下载完成；两份 train 完整三页文档拟生成 image-only PDF 进行官方管线与跨页重组 smoke。本地输入打包/下载器合计 10 测试通过；尚无 GPU 推理或新分数。PID、命令、模型 SHA、日志和输入审计见 [Paddle 环境与 smoke](experiments/2026-10-23-paddle-v15-runtime-and-smoke.zh-CN.md)。

2026-10-23 08:06 UTC 检查点：三模型主权重下载已于 07:58:19 UTC 正常结束（status=0），Paddle/OCRFlux/Popo 共50文件均完成下载器大小/哈希校验；本次再核对文件数量、当前大小及权重哈希记录一致。没有启动新模型推理；下一步 Paddle 独立环境与 train smoke。详细记录见 [公开模型下载](experiments/2026-10-23-public-model-downloads.zh-CN.md)。

2026-10-23 06:42 UTC 检查点：三模型后台权重下载已启动，service `paper-public-models-20261023T064109Z`、PID `3915961`、初始 active/running；新目录与50文件逐项校验已留痕。下载未完成、GPU 推理未启动。记录见 [公开模型下载](experiments/2026-10-23-public-model-downloads.zh-CN.md)。

2026-10-23 06:41 UTC 检查点：开始三个公开模型的服务器下载准备；固定 50 文件/约 27.84 GB 的官方清单与校验脚本，未启动模型推理。OCRFlux 权重使用 Qwen Research License（工具代码 Apache-2.0）。状态、命令和产物入口见 [公开模型下载](experiments/2026-10-23-public-model-downloads.zh-CN.md)。

2026-10-23 优先级调整：用户指定先测试 PaddleOCR-VL-1.5、OCRFlux-3B、MinerU-Popo，POTATR 后置；已核验公开权重 SHA/接口并完成服务器只读资源与网络预检。未下载新权重、安装环境或启动推理，尚无新模型分数。执行入口见 [公开模型优先安排](2026-10-23-open-model-priority-and-readiness.zh-CN.md)。

2026-10-23 06:06 UTC 补充检查点：dots.ocr 两层 HTML 过滤 CPU 审计已完成。637 张评分拒绝中 582 为词法兼容候选、55 未解决；前层拒绝中 1,315 条无 text，涉及 1,159 页且原串无任何文字/表格 HTML。拒绝页面集合无交集；全部输入哈希不变，53 项相关测试通过。没有新评分/训练结果，规范化与缺内容推理原因仍待在 train 核验。命令、案例、边界和产物见 [HTML 过滤审计](experiments/2026-10-23-dotsocr-html-filter-audit.zh-CN.md)。

最后更新：2026-10-23 05:16 UTC

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

### 2026-10-23 05:16 UTC 阶段总结与提交前核验

**状态：已有结果只读复核，未启动新实验。**10 月 20 日 dots.ocr 全页预测任务 `events.log` 记录 13,871/13,871 页完成（2 页 `error`）；离线配对评分 `background-events.log` 记录 `END ... status=0`。本轮对其 7 项评分产物重新执行保存的 SHA-256 校验，全部 `OK`。原始成果、数值、不可直接与论文 test 数值比较的原因和下一步详见 `docs/experiments/2026-10-23-cross-page-stage-summary-and-handoff.zh-CN.md`。当前应先在 train 核验 HTML 两层解析的覆盖损失并冻结修复，再新目录复评 val；POTATR 发布制品审计可并行。旧实验指标和历史检查点不变；本次无新 GPU、下载或重评分。

### 3.0q 2026-10-20 12:26 UTC dots.ocr validation 全页终态推理完成

- 2026-10-20 04:14:23 UTC `20261020T015543Z-dots-full-val` 后台任务正常结束（exit 0，unit 后续 `inactive/dead`）。四分片覆盖固定 PubTables-v2 Full Documents/val **13,871/13,871 页**；按预测 schema 逐条解析并与输入清单逐项对照，missing/extra/duplicate 均为 0。`ok=13,869`、历史 `error=2`，有 1,168 页共 1,324 条 `invalid_table_html` warnings；新末段 SHA-256 `0a0a878f636786a3ff7d72dec423f7943668d389b6bffb1f192e036e760a3349` 与后台保存值一致。**这是 image-only 页级终态全覆盖，不是跨页逻辑表恢复成绩**；下一阶段只读审查适配器/错误页处理，在独立目录配对评估 no-merge 与固定简单合并。详细产物、错误 ID 和结论边界见 `docs/experiments/2026-10-20-dotsocr-full-val-last-240-resume.zh-CN.md`。

### 3.0p 2026-10-20 01:55 UTC 最后 240 页断点补跑已启动

- 用户要求继续执行；入口已加入第三段旧预测只读校验，三段 SHA/行数/前缀核验通过，反序分片被拒、151 项回归通过。GPU0 重查空余 39,559 MiB，4 个既有进程；新任务 `20261020T015543Z-dots-full-val` 用户级 service active/running，wrapper/runner PID `946957`/`947020`。原 13,631 页不动，输出/日志写新时间戳目录；**首条新预测待核验、尚无全量结果**。详细输入版本、命令、环境、产物与保护条件见 `docs/experiments/2026-10-20-dotsocr-full-val-last-240-resume.zh-CN.md`。
- 01:57 UTC 新分片前三页均 `ok`，首条 `PMC12305305_page_0.jpg` 精确接续旧分片；联合四分片 **13,634/13,871 页**、余 237，前缀与 ID 唯一性核验通过。unit 仍 active/running，GPU0 最近余 21,313 MiB，尚无全量页级结果或跨页分数；详细核验见上述实验记录。

### 3.0o 2026-10-20 01:52 UTC GPU0 补跑中断

- 2026-10-19 **17:20:05 UTC**，`paper-dots-full-val-20261017T081912Z.service` 因 GPU0 余量降至 7,589 MiB 触发自身 8 GiB 显存保护，退出码 143、unit failed；**不是仍在运行或已完成**。三分片现累计 **13,631/13,871 页**（98.27%），缺 240 页；全部 JSON 可解析、ID 无重复且严格等于固定清单前缀，新分片 6,844 页均 `ok`，历史 2 页 `error`。第三分片 SHA-256 与后台记录吻合；当前 GPU0 瞬时空余 39,559 MiB，不等于稳定共享窗口。下一步先让恢复脚本接受第三段只读历史输入并验证，再按 GPU 门禁在新目录补最后 240 页，完整覆盖后才做跨页评分。详见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

### 3.0n 2026-10-19 15:19 UTC GPU0 补跑接近完成

- unit `paper-dots-full-val-20261017T081912Z.service` 仍 active/running。三分片 JSON 联合已核验 **13,375/13,871 页**（96.42%），还差 496 页；ID 无重复、严格匹配固定清单前缀。新分片 6,588 页均 `ok`，历史 2 页 `error`；GPU0 最新空余 15,125 MiB，未见结束/保护停机。继续监控并待完整覆盖后审计，**尚无正式跨页评分**。证据见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

### 3.0m 2026-10-19 09:18 UTC GPU0 补跑仍在运行

- 新分片已保存 5,813 页且全部 `ok`；三分片共 **12,600/13,871 页**（90.84%），还剩 1,271 页。联合 JSON 可解析、ID 无重复并严格匹配固定输入清单前缀；unit active/running、GPU0 余 15,125 MiB，尚无 guard/finished 事件。未完成全页覆盖或跨页评分；完整证据见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

### 3.0l 2026-10-18 13:27 UTC GPU0 断点补跑检查点

- `paper-dots-full-val-20261017T081912Z.service` 仍 active/running；三段预测累计 **10,292/13,871** 页（约 74.2%），缺 3,579 页。联合 JSON 可解析、ID 无重复且等于固定清单前缀；第三分片 3,505 页均 `ok`，历史 2 页 `error`。GPU0 约余 16,227 MiB，暂未见保护停机。本轮只读检查、无新增实验启动；无全量跨页评分。详细证据见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`。

### 3.0k 2026-10-17 08:19 UTC 双分片补跑已启动

- 用户明确要求继续在 GPU0 推理；修复双历史分片恢复入口与后台缺失 `rg` 的监控依赖，严格核验前 6,787/13,871 页清单前缀及两段 SHA，反序分片拒绝，151 项回归通过。08:19:12 UTC 新 ID `20261017T081912Z-dots-full-val` 在 GPU0 用户级 service 启动，wrapper/runner PID `2239841`/`2239881`；启动空余 40,579 MiB，4 个既有进程。首条新预测 `PMC11233398_page_5.jpg` 为 `ok`，联合三分片 **6,788/13,871 页**、无重复、与清单前缀相符、旧分片 SHA 不变；08:22:04 UTC 监控累计数同步，新 GPU0 余量 23,411 MiB。**运行中，未完成全量、无正式跨页指标**。unit、输入/代码哈希、完整命令和监控路径见 `docs/experiments/2026-10-17-dotsocr-full-val-two-shard-resume.zh-CN.md`；`Linger=no`，后续持续核查状态及显存保护事件。
- 08:26 UTC 后续检查点：第三分片 7 页均 `ok`、清单前缀匹配，累计 **6,794/13,871**、缺 7,077 页；unit 仍 active，GPU0 最近余 23,411 MiB，无保护停机事件。`progress.csv` 按分钟采样，短时可能落后于即时预测文件。详细证据见上述实验记录；**此时仍未完成**。
- 08:53 UTC 用户询问 VS Code 可否关闭；unit 仍 active/running，新分片已落盘 65 行（合计 6,852/13,871，仅行数检查），`Linger=no`、当时有 7 个用户会话。关闭最后会话可能终止用户级 service，不保证无人值守运行；未更改系统设置或任务。见上述实验记录。
- 11:09 UTC 新检查点：第三分片 364 条均 `ok`，三分片累计 **7,151/13,871**、剩余 6,720 页，ID 唯一并严格匹配输入清单前缀；unit 仍 active/running，GPU0 最近空余 16,227 MiB，暂无显存保护停机。尚未进行完整跨页评分，继续监控；详细证据见上述实验记录。

### 3.0j 2026-10-17 08:14 UTC 本机 GPU 只读快照

- GPU0/1/2/3 空余显存 40,579/423/25,343/22,761 MiB，瞬时利用率均 0%，计算进程数 4/1/10/10；无独占空卡的证据。补跑 unit 仍 failed，预测仍共 6,787/13,871 页，**无新结果**；本轮只读检查，未启动任务。下次恢复前须修复双分片断点与后台监控，并重新核对共享 GPU 状态。详细快照见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。

### 3.0i 2026-10-12 11:29 UTC 本机 GPU 只读快照

- GPU0/1/2/3 空余显存分别 33,993/423/20,569/22,545 MiB，利用率 60/0/33/59%，四张卡均有计算进程；仅为瞬时快照。此前补跑 unit 仍 failed，两分片共 6,787/13,871 页，无新产物或全量结果。本轮未启动任务；继续运行前须修复两个历史分片的断点入口及后台 `rg` 监控、重新核对资源。详细证据见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。

### 3.0h 2026-10-11 远端服务器 73 候选

- 用户提出迁至 `172.17.62.73`。本机只读 SSH 连接因未知远端 ED25519 主机密钥被严格校验拒绝（exit 255）；本机未见指向该 IP 的可用已配置别名。未验证账号/GPU/数据/模型，未传输、未在远端运行；先通过可信渠道核对主机密钥和账号，再评估迁移可行性。详情见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。
- 后续用户从已登录远端提供 ED25519 指纹，本机经 `ssh-keyscan` 核对匹配，信任文件仅保存公钥于 `artifacts/ssh-known-hosts/20261011-server73-ed25519`；严格校验已通过。`BatchMode=yes` 连接仍因本机无免交互认证返回 `Permission denied (publickey,password)`；未运行远端 GPU 命令，仍不能断言该机有空卡。未使用/留存密码、未进行迁移或推理。
- 用户随后在 VS Code 已登录的 73 终端运行 `nvidia-smi`，提供报错 `Unable to determine the device handle for GPU0000:01:00.0: Unknown Error`；这是用户提供的终端证据，不能判断错误根因或其他 GPU 是否可用。当前该机未证实可用，先由用户只读检查 GPU 清单和 PCI 设备，不能直接迁移任务；详见上述实验记录。
- 用户续传 `nvidia-smi -L`/PCI 输出：5 张 RTX 3090 中 GPU 0/2 报设备句柄错误、PCI revision `ff`，GPU 1/3/4 可列出 UUID、PCI revision `a1`。候选卡仍需核查显存、现有进程及计算能力，不等于可以直接迁移；本机还缺远端免交互登录能力。详情见上述实验记录。
- 用户随后提供 73 服务器 GPU/进程快照：GPU1/4 分别剩 24,240 MiB，无列出的计算进程；GPU3 剩 21,765 MiB，有 1 个进程占约 2,472 MiB。GPU1/4 可考虑受控短试跑，但旧 A100 增量 16,644 MiB 粗推下会触及现有 8 GiB 空余保护门限，不能直接承诺 3090 全量可行。仍缺远端安全登录、权重/数据/环境检查与双分片恢复脚本修复；未迁移/启动。证据和限制见上述实验记录。

### 3.0g 2026-10-11 05:17 UTC 断点补跑中断与 GPU 快照

- 2026-10-10 08:59:38 UTC 运行 `20261010T024700Z-dots-full-val` 因 GPU0 瞬时空余显存降至 47 MiB 触发自身保护停止，unit 现为 `failed/failed`、exit 143，**并未完成全量**。旧分片 6,151 页、新分片 636 页，共 **6,787/13,871 页**，6,785 `ok`、2 `error`；两分片严格对应清单前缀，重复 0，尚缺 7,084 页。后台环境找不到 `rg`，OOM/连续错误日志检查未可靠执行，重启前必须修正。详细命令、日志、校验和与下一页见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`。
- 2026-10-11 05:17:05 UTC 瞬时只读 GPU 快照：四张 A100 80GB，GPU0/1/2/3 空余分别 32,289/423/25,967/26,163 MiB，利用率分别 54/0/0/0%；四张卡均列有计算进程。GPU0 的显存余量不等于空卡或稳定运行窗口；本次未启动新任务，不终止其他进程。下一步先修复监控依赖，再重新检查资源并在新目录断点补缺，原有输出保留。

### 3.0f 2026-10-10 02:52 UTC 断点补跑运行中

- 原 6,151 页输出及其 SHA-256 保留不变。推理计时改为单调时钟，151 项回归、Ruff、后台脚本语法与断点预检通过。02:50:03 UTC 新 ID `20261010T024700Z-dots-full-val` 已在 GPU0 通过用户级 service 启动（wrapper/runner PID `3225365`/`3225408`），仅补原剩余 7,720 页。02:52:57 UTC 核对首两条新预测均 `ok`、清单前缀续接、无重复，监控累计 **6,153/13,871**（仍缺 7,718 页），unit 仍 active；后续须监控是否中断并联合审计完整覆盖。详细协议、日志和代码哈希见 `docs/experiments/2026-10-10-dotsocr-full-val-resume.zh-CN.md`；无正式全量结果。

### 3.0e 2026-10-10 02:41 UTC 后台全页任务中断勘误

- **2026-10-09 06:54:01 UTC 已失败退出，非正在运行/完成。** 用户级 unit 为 `failed`、退出码 1；原预测 6,151/13,871 页（6,149 `ok`、2 `error`），缺 7,720 页；已保存记录无重复/清单外页、严格符合清单前缀。最后完成页 `PMC11156423_page_9.jpg`，下一个待推理页 `PMC11157072_page_0.jpg`。`elapsed_sec=-27.142` 导致预测模型校验异常；原因分析和 SHA-256 见 `docs/experiments/2026-10-06-dotsocr-full-val-background.zh-CN.md`。先修复计时，再新目录断点补缺，原文件不能覆盖；暂无跨页正式指标。

### 3.0d 2026-10-07 04:12 UTC 后台任务复核

- `paper-dots-full-val-20261006T172527Z.service` 仍 active，runner PID `3946441` 存活。实时预测 955/13,871 页（954 `ok`、1 `error`），现有 955 个唯一 ID 且与输入清单前缀顺序一致，无清单外页；78 页有共 92 条 `invalid_table_html` 警告。错误页 `PMC10293395_page_18.jpg`：`ValueError: layout list contains a non-object element`。GPU0 约剩余 23,423 MiB，未见保护性停止事件。详细证据与速度粗估见 `docs/experiments/2026-10-06-dotsocr-full-val-background.zh-CN.md`；仍在推理，未做跨页合并与正式评分。

### 3.0c 2026-10-06 17:26 UTC 全量后台推理运行中

- PubTables-v2 Full Documents/val 全 935 篇、13,871 页清单 SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`；后台入口预检、149 项回归通过。首次 `nohup` 尝试 `20261006T172221Z-dots-full-val` 未进入推理，保留空日志。2026-10-06 17:26:41 UTC 以用户级 systemd 新 ID `20261006T172527Z-dots-full-val` 成功启动，unit active，wrapper/runner PID `3946380`/`3946441`，GPU0 启动余量 48,737 MiB、4 个原有进程。运行中，首批预测和最终指标仍待核验；次日检查方式、日志和失败证据见 `docs/experiments/2026-10-06-dotsocr-full-val-background.zh-CN.md`。
- 17:27:46 UTC 首条预测 `status=ok` 刷盘；截至 17:29:22 UTC 2/13,871 页、均 `ok`，`progress.csv` 已按分钟追加检查点，GPU0 约 31 GiB 剩余，unit 仍 active。登录管理器显示 `Linger=no`，若所有用户会话消失，后台 service 可能随之退出；保存的逐页预测可按新目录断点补跑，不保证自动重启，也不代表全量成绩。

### 3.0b 2026-10-06 17:15 UTC GPU 短试跑完成

- 用户要求测试；2026-10-06 17:11:59--17:15:13 UTC 在共享 GPU0 运行 `PMC11977379` 完整 3 页 dots.ocr `image-only` smoke，PID `3837378`，退出码 0。3/3 页 ok、0 错误、0 警告、1 张页级表；峰值占用 48,946 MiB（相对启动前增量 16,644 MiB），结束后回到原有显存占用。与旧 smoke 的原始输出一致，但不表示跨页逻辑表已恢复；完整日志与哈希见 `docs/experiments/2026-10-06-dotsocr-full-documents-gpu0-smoke.zh-CN.md`。未启动全 validation，下一步是更长完整文档的资源核验及共享 GPU 运行窗口评估。

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
| dots.ocr / Full Documents strict full validation | 页级推理及 `no_merge`/`simple_merge` 配对离线评分已完成；解析有效性待审计 | 935 篇、13,871/13,871 页（2 页 error）；跨页真值 983 张 | `simple_merge` 跨页 GriTS-Con 0.5131445386、全表 GriTS-Con 0.5479001476；不等同论文 test 同协议复现 |
| continuation 与跨页合并基线 | 简单规则配对结果已完成，论文 ViT 与其他模型待核验 | 1,213 个规则候选，155 次接受，正确性待审计 | 只可说明同一上游下的简单规则增量；误连率尚缺 |

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
# 2026-10-20 12:36 UTC：dots.ocr 严格 Full Documents/val 离线评分后台接管

**运行中，尚无正式指标。**模型 `rednote-hilab/dots.ocr`（`image-only`，revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`）；固定 PubTables-v2 Full Documents/val 935 篇、13,871 页。四段预测严格适配完整、无缺漏或重复，2,752 张未合并预测表，历史推理 error 2 页。交互评分在产物生成前中止（退出 130），随后新用户级 service `paper-dots-eval-20261020T123212Z.service` 于 12:35:55 UTC 启动，PID `1269023`；依次执行 no-merge 评分、冻结的重复表头简单合并、配对评分，仅 CPU、不下载、不覆盖旧产物。当前 `Linger=no`，不能保证全部登录会话退出后 user service 继续；启用系统级 linger 尚待明确授权。完整输入/命令/日志/状态见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md`；运行完毕必须核验两份 metrics、覆盖与 SHA，追加本索引和记忆页的结果。

## 2026-10-20 12:46 UTC：PubTables-v2 论文版本与候选模型补查

**文献核验，不是模型实验。**PubTables-v2 arXiv:2512.10888v3 Full Documents 表 5 新列出 `DeepSeek-OCR 2`（逐页输入）与 `Claude Opus 4.6`、`GPT-5.4`、`Gemini 3.1 Pro`（整篇输入）。论文 `PaddleOCR` 行并非项目四模型计划的 `PaddleOCR-VL-1.5`，没有由此得到 `PaddleOCR-VL-2` 基线；Paddle 官方已有 `PaddleOCR-VL-1.6` 命名，但不得将四模型计划中的 1.5 静默替换。版本说明和官方来源已追加至 `docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md`。MinerU-Popo 仍为固定页面解析输出上的后处理方案；未下载/测试这些额外模型。

**同日纠正用户原意：**上述表 5 的新模型并非用户指的 PubTables-v2 表 3/4 的 `TATR`、`TATR-v1.1-Pub`、`TATR-v1.2-Pub`、`POTATR` 与 `POTATR + DT`。TATR 结构识别输入裁剪表，POTATR 单独输入完整单页；`+ DT` 只是 PDF 原生文字辅助条件，并非第五个独立权重。项目内仅 v1.1 权重已下载且在 Cropped Tables/val 完成严格复评；其余权重/完整文档适配尚未核验。来源及结论边界见同一报告新增的同日补正，不把论文报告分数误记成已实测。

**同日补充诊断轨道（计划中，无新计算）：**只读检查 Full Documents/val 真实跨页逻辑表的 `parts`，存在页面号及 bbox、整表 HTML，但本地没有对应的单独跨页片段 JPEG 或官方片段内行列真值；`Cropped Tables` 是另一集合，不能当作这些片段。可固定预处理，从原页派生片段裁剪，并在真值已给定片段及同表分组的条件下对 TATR-v1.1-Pub 做 smoke，然后外接冻结的合并器按整表真值评估；POTATR 原生整页和权重尚待核验。此轨道是 oracle 检测/关联下的片段恢复，不等于当前完整文档端到端分数。证据和限制见 `docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md` §3.2、`docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md`；原始数据/旧产物未修改。

**POTATR 文字源与跨页组件澄清：**论文 `POTATR + merging` 是全文档跨页处理配置，`POTATR + DT` 是使用 PDF 原生文字的页面配置，二者不是二选一，也非两个独立权重。Full Documents 附录的 `POTATR + merging` 行没有明确写出 DT/OCR 来源，不能据该表把 `0.8269` 直接归入本项目 image-only，或声称已经证实 DT 与 merging 同用。方案拟设 OCR 与 DT 两条文字源赛道，分别评 no-merge/merge；原论文配置归属继续待核验。勘误入口为上述报告 §3.3；无新模型结果。

## 2026-10-20 13:09 UTC：POTATR 加入端到端候选方案

**状态：计划调整，不是 POTATR 下载/实验启动。**新执行入口 `docs/2026-10-20-cross-page-five-method-evaluation-plan.zh-CN.md`，原 `docs/2026-09-29-cross-page-four-model-evaluation-design.zh-CN.md` 保留原历史版本及通用 GPU/数据安全门禁，并在文件头指向新版。新增 POTATR 作为全页图像提取上游，计划固定同一页面预测做 no-merge/simple-merge paired 对照；如 ViT 续接器权重/版本可核验再单列论文式续接合并，文字源按 image-only + OCR、PDF-text-assisted + DT 两赛道独立报告。POTATR 权重、作者代码和 ViT 发布状态尚未正式核实为可运行，本地未找到 POTATR checkpoint；不能用 TATR 假扮或称已经开始 POTATR 实验。当前先完成 dots CPU 后台两组评分，同时只读核验 POTATR 官方制品；之后才开发 adapter、train smoke、显存门禁、val 全页。PubTables-v2 已知跨页片段裁剪图作为单列 oracle 诊断，不污染完整文档主赛道。无下载、GPU 推理或原有预测/日志修改。证据、执行门槛及失败分叉全部记录于新版计划。

### 同日 13:12 UTC dots.ocr 无合并评分子阶段完成

后台 unit 仍运行，`background-events.log` 已转至 `STEP repeated_header merge`；无合并 `metrics.json` 的全页 coverage=13,871、cross-page GT=983、matched=643，cross-page GriTS-Con=`0.4576991966`、内容网格 exact=`0.0`，full-document GriTS-Con=`0.5077936893`、内容网格 exact=`0.0815616544`；非法 HTML 637。matched 只表示部分内容重叠，全部 643 项都缺预测来源页；不能称 643 张表成功恢复，网格 precision 也不是检测 precision。SHA `ba5e206bb7ac3d4c091d53eea29bc66c2740b6ab6f4de78c63c6d46e22bdff02`，详细 coverage、日志与产物路径见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md`。**仅无合并子阶段完成；简单合并/第二次评分、全套 hash 核验待完成，不报告 paired 增益。**

### 同日 13:17 UTC 简单合并子阶段完成

后台仍 active/running，已切换至 `STEP simple_merge score`。`artifacts/cross-page-merges/20261020T123212Z-dots-full-val-offline-simple-merge/summary.json` 记录候选边界 1,213、规则接受 155、表格由 2,752 变成 2,597；**接受数不是合并正确数**，误连及配对差异仍待第二组评分和人工/负例审计。该 summary SHA-256 `0a6ae6ae494b3fdd7b32dd2f2267ad2b960a319b4f6d486bb202b360a9a254c6`，详细日志/来源见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md`。未下载/修改原始数据，也未启动 POTATR GPU。

### 同日 13:27 UTC 社交平台候选方法筛选

**文献筛选已完成第一篇，第二篇待核验；没有新增实验。**微信文章中的 TeleOCR 官方论文、代码和公开模型卡可核验，但只支持将其作为 image-only **可选页级解析上游**；暂无依据作为独立跨页续接/逻辑表恢复模型列入五方案，也不能将 OmniDocBench 页面解析成绩混入 PubTables-v2 跨页成绩。小红书公开链接未提供可核验笔记正文，未确认论文/模型，须请用户提供截图或名称。公开来源、证据边界和可选扩展条件见 `docs/experiments/2026-10-20-social-posts-teleocr-baseline-audit.zh-CN.md`。现行五方案不变；dots CPU service 最近只读检查仍处 `STEP simple_merge score`、`active/running`，无第二组分数，不改变其独立实验记录。

### 同日 13:59 UTC dots.ocr 严格全量配对评分完成

**已完成，旧“运行中”段落保留为历史检查点。**后台 `END 2026-10-20T13:48:59Z status=0`，unit `inactive/dead`，两组 13,871 页全覆盖、983 张跨页真值；`background-checksums.sha256` 7 项全通过。`no_merge` → 冻结 `simple_merge` 跨页 GriTS-Con `0.4576991966` → `0.5131445386`，跨页内容网格 exact `0` → `2/983`；匹配数 `643` → `639`，因此不能只报提升。155 次规则接受不能视为 155 次正确续接。全表 GriTS-Con `0.5077936893` → `0.5479001476`；错误页 2、非法 HTML 637。命令、完整数值、SHA 和结论边界见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 完成核验。下一步只读配对案例审计、train 正负例误连核验，且并行核验 POTATR 作者权重/许可/续接器；不以 val 调规则，无新 GPU 任务。

### 同日 15:50 UTC 原论文结果与本地指标范围核查

**对先前口头比较的勘误，不改原实验结果。**原论文根目录 PDF 表 7 的 dots.ocr `0.6844/0.1180` 是 Full Documents test **全部表**的 GriTS-Con/Acc-Con，合并器为 ViT-B/16 预测续接、同列数纵向拼接；本地全表 validation 简单合并为 `0.5479001476/0.0819482026`，跨页子集内容网格 exact `2/983` 不可对照论文全表 `0.1180`。两套全表分数仍有差距，但不同 split/续接器/推理或解析策略尚未控制；本地 637 条 HTML 评分无效亦需归因检查。PDF 页码、代码路径、失败样本和先 train 后 val 的核验步骤见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 新增 15:50 核查段；未启动重评分、GPU 任务或 test 评测。

### 同日 15:56 UTC dots 推理/评价链路只读核验

**存在应优先解决的有效性风险，旧结果不改。**val 真值 2,587 表；本地两层 HTML 处理依次记录 1,324 个 runner warnings、adapter 2,752 预测表中再有 637 条被 XML 解析拒绝（520 标签不匹配、99 非法字符、12 多根、6 未知实体），最终参与评分 2,115 张预测表。解析规则可能导致正常 HTML 被跳过，影响分数的大小仍未确定。full_document Hungarian + micro GriTS/格子 exact 未发现已证实聚合公式 bug，但 cross_page 自定义 Con 匹配后只取 GT 子集，`Top` 沿用 Con 匹配、未对全部假阳性处罚，source_pages 不参与 grid exact；不得与论文全表直接对比，亦不能称 2/983 已核实续表正确。先在 train 核验解析/预测格式与官方代码，冻结统一规则后在新目录复评 val，ViT 官方合并器未复现。只读统计、代码入口和边界详见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md` 15:56 段。
