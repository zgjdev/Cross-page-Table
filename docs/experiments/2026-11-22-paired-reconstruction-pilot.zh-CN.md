# 共同结构与直接网格生成的配对试验

2026-11-22，北京时间。研究对象是已知属于同一逻辑表的图像片段。使用 PubTables-v2 Full Documents revision aa575e798cb00a296925e2086addb3e3fd9a1903 的 train_fit 部分，固定 Paddle 页内预测，image-only。

## 首轮输入与预算

从 `artifacts/reconstruction-qwen-smoke/20261115T074229Z-overfit-302/prepared.json` 读取既有 8 个训练组，从 `artifacts/reconstruction-launchers/20261115T123111Z-untrained8-probe/selection.json` 读取 8 个短表评估组。在固定 inputs.jsonl 上交叉核对 document_id 与 cluster_id，两组交集均为空。训练和评估分别包含 4 与 2 张三片段表，其余均为两片段。已观察过这些评估表在旧 HTML 管线上的结果，样本属于开发诊断。

用固定 Qwen tokenizer 编码规范化真值网格，训练目标为 1,857–7,323 tokens，评估目标为 867–4,496 tokens。根据输出表示的长度确定两臂统一 8,192 新 token 的预算，防止沿用 HTML 的 4,096 预算导致已知样本必然截断。两臂使用相同训练顺序、LoRA 配置、种子和 16 个优化步；选择两遍训练作为初筛，不能据此认定方法已收敛。评测保留所有 8 组。

## 检查点完整生成

代码 857bf2d。服务器 `artifacts/reconstruction-prefix-review/20261122T071029Z-paired` 保存冻结 Qwen 及加载单步结构检查点的逐例输出。该例是训练过的 PMC10488684-table-0；两片段，模型 revision 89644892e4d85e24eaac8bacfd4f463576704203。此项用于检查真实完整生成和评分接口。检查点SHA、完整命令与GPU资源见生成目录manifest及gpu-before。配对训练与生成进度将另行追加。

11月22日 20:20（北京时间）离线补评分完成。直接 Qwen 生成 2,102 tokens，加载单步结构检查点后生成 1,383 tokens。两者均自行结束，均未通过规范化网格解析，结构和内容完全匹配都是 0/1。生成使用 4,096 token 预算，未截断。两份原始预测独立保留。首轮评分把 JSON 字符串内的 Unicode 行分隔符误作记录边界，提交 d9f1170 修正。复评未重复 GPU 推理，校对了真值 SHA。评分和来源哈希见 `artifacts/reconstruction-prefix-review/20261122T122021Z-paired-rescore/`。

## 小规模配对训练启动

2026-11-22T12:20:03Z 启动 `20261122T122003Z-paired16`，PID 3986635，commit 0545d1a。两臂各 8 训练表、16 步 FP32 LoRA，结构臂另训 80 个输出前缀位置对应的共同列槽模块，8 张独立文档表生成与离线评分。启动前核对 38/38 片段预测可解析。模型、数据沿用固定版本，无下载或原地修改。以 GPU0 串行执行，启动器保存完整 argv、PID、逐臂日志和退出码，逐臂显存与进程见自身 gpu-before.json。环境 `.venvs/20261114T095359Z-qwen-env/bin/python`，种子 20261122。证据目录为 `artifacts/reconstruction-launchers/20261122T122003Z-paired16/`，结果目录为 `artifacts/reconstruction-paired-pilot/20261122T122003Z-paired16-{direct,structure}/`。完成条件是两臂各 16 步、8 预测、8 真值，通过相同评分后逐表分析。启动状态为运行中。

CPU 使用固定 Qwen tokenizer（不计特殊 token）复核同一批 16 张真值，8 张训练表 HTML/网格总长 14,418/34,053 tokens，8 张评估表 9,789/23,292 tokens。评估组单表长度比中位数 2.405。此结果支持把表示长度作为失败分析变量，不更改已启动的比较。历史同 8 张评估表的直接拼接/内容启发式对齐分别均为合法 8/8、结构 1/8、内容 0/8，报告路径 `artifacts/reconstruction-diagnostics/20261115T123900Z-untrained8-paired/report.json`。

## 200 表误差分解

固定上游的历史 200 表预测已用同一逐表分析重新拆解。两臂各有 170 个可评分结果、30 个失败，失败依然计入所有完全匹配指标。直接拼接在可评分表中有 127 张行数错误、4 张列数错误。内容启发式对齐后为 69 张和 4 张。结构完全匹配净增 46 张（47 改善、1 退化），内容完全匹配净增 2 张。即使行列数都正确，仍分别有 19 和 31 张表的单元格边界不完全一致。现有证据支持优先把错误分解到行数与跨度；它无法单独区分重复表头、漏行、误拼边界行等原因。

逐表结果和两份输入预测的 SHA 见服务器 `artifacts/reconstruction-diagnostics/20261122T123024Z-layout-error-200/report.json`。真值 SHA 已与两臂历史记录核对。CPU 复用当前 `compare` 和原严格评分器，只计算新报告。

20:30（北京时间）基线 16 步完成，训练两遍平均监督交叉熵为 0.031683、0.016916。评估第 1/8 张已生成 3,812 tokens 并自行结束。输出已使用规范化字段，单元格 LaTeX 反斜杠构成非法 JSON 转义，仍计失败。尚无双臂成绩。

按启发式实际动作复核后，170 张两臂均可评分的表中有 91 张触发前缀删行，79 张未触发删行或列插入。可评分表无列插入。47 张结构由错变对、1 张由对变错、2 张内容由错变对，全部发生在删行组。证据为 `artifacts/reconstruction-diagnostics/20261122T123247Z-alignment-actions-200/report.json`，已与上一步逐表报告及 alignment 预测 SHA 绑定。启发式删行基于相同非空开头行，可能误删正文。此分组描述实际动作，不能当作人工标注的重复表头或因果消融。

上一步唯一结构退化案例为 PMC11277303-table-0。真值为 22 行 6 列，直接拼接结构完全匹配，启发式输出少 2 行。该例适合作为未来基于图像的边界误删核验例，当前未进行图像人工复核。

20:34 北京时间启动训练后 CPU 逐表分析，PID 13695，对照两臂成功退出收据后读取两臂完整输出。新目录 `artifacts/reconstruction-diagnostics/20261122T123435Z-paired16-analysis/`，manifest 记录依赖及 PID，成功后生成 command.json、report.json 与 exit.json，失败记录失败状态。无 GPU 使用，最长等待三小时。当前 GPU 作业继续串行运行。首张评估表自训练末步至落盘约 323 秒，近似 12 生成 tokens/s。总用时取决于后续各表的实际生成长度。

增加可选 HTML 输出条件（commit 91dcace），相同入口同时传给训练目标、推理提示及生成输出处理，保持默认网格。CLI 与 Ruff 已验证。该变更已推 GitHub 功能分支，等待当前配对结束再同步服务器，确保两臂读到相同训练代码与 commit。

30 张两臂均落败的表也保留在分析中。直接拼接均因片段列数不一致而中止。启发式中 21 张缺少简单首行列标签，9 张列标签有歧义或找不到对应。按实际动作拆解得到的删行收益仅涵盖可评分样本。这 30 张表是检验学习式列映射能否处理列数不一致的重要分层。
