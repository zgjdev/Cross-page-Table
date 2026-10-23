# 跨页表格恢复研究长期记忆

最近检查：2026-10-23 09:47 UTC。本文件是仓库内的**可更新恢复入口**，不是隐藏的会话记忆，不代替 `AGENTS.md`、实验日志或原始产物。更新时保留重要历史证据的链接；若与产物冲突，先核对产物，再在实验记录中追加勘误。

## 每次接手先做什么

1. 阅读根目录 `AGENTS.md`、本文件及 `docs/2026-09-22-research-progress.zh-CN.md`。
2. 阅读 `docs/research-handoff-2026-08-26.zh-CN.md` 和当前任务对应的最新 `docs/experiments/` 记录；检查相关产物、未提交更改和仍在运行的任务。
3. 对照本文件“当前状态/下一步”，只以可核验证据更新状态；不根据旧对话推测已完成下载、训练或评估。

## 当前研究状态

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
