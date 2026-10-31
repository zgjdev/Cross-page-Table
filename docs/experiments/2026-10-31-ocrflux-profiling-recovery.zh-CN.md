# OCRFlux 显存profiling失败排查与同协议恢复

日期：2026-10-31（Asia/Shanghai，日志UTC）。当前状态：**同协议断点恢复成功，正在GPU推理**，尚未全量完成。用户明确授权“排查一下问题然后继续”。

## 问题、证据与结论边界

原run `20261030T032500Z-ocrflux-val-full` 已在32篇/430页后停止，第33篇PMC10285071共13页，在LLM初始化中发生AssertionError、没有任何页面请求。详见 [原实验记录](2026-10-30-ocrflux-full-val-inference.zh-CN.md)。

只读检查实际安装的 `.venvs/20261029T162200Z-ocrflux/lib/python3.11/site-packages/vllm/worker/worker.py`：142–168行在模型加载前创建baseline_snapshot，204–271行进行profile和KV预算，273–283行以torch.cuda.mem_get_info获取**整卡**已用显存，要求baseline_snapshot.cuda_memory小于profile后cuda_memory。源码274–275行明确假设其他同卡进程在profiling期间不改变显存。

原失败采样从33,683,668,992降到32,503,431,168字节，下降1,180,237,824字节（约1.10GiB），违反此假设；日志显示7.1542GB权重已加载，失败发生在profiling断言而非数据读取、页面生成或评分。由此确定直接触发机制是整卡显存采样不满足单调增长断言；其他进程释放显存是合理解释，但无法回溯逐进程历史分配，具体释放来源仍属推断。没有CUDA OOM证据，也不据此认定模型预测逻辑错误。

本次检查GPU0空余40,661MiB，已有其他用户进程；Linger=yes，无运行中的本项目user service。没有读取项目根目录之外的服务器文件，没有终止其他用户进程。

## 修复方式：外层有限恢复，不改推理协议

新增 `scripts/run_ocrflux_recovery.py`、`src/cptla/evaluation/ocrflux_recovery.py` 和4项测试。保留原full-source-v3、vLLM安装文件、模型、环境、max_tokens、seed、提示及评分公式。没有绕过vLLM显存断言，也没有在原失败目录覆盖数据。

只有子任务summary同时满足status=failed、pages=0、documents=[]，raw请求数0，且error精确匹配显存profiling AssertionError前缀，才允许恢复。等待5次间隔5秒的显存采样，均至少30,000MiB且波动不超过512MiB；最长等待120秒。新RUN_ID执行同一冻结入口，旧检查点由原恢复机制执行SHA核验；每次失败目录保留并加入不重复的resume链。每篇最多3次恢复、累计最多20次；其他错误、缺失summary或等待超限直接停止，不无限重试。

恢复初次会复用旧32篇。之后如果某次运行新增检查点后再次因同类初始化错误中断，只恢复这些新检查点和原链；不更改原生成失败38页的终态。完整run结束仍按原两组适配导出，正式评分另行执行。外层恢复只处理运行可靠性，不作为算法增益。

## 测试与源码部署

先运行缺失模块测试得到失败，再实现纯分类与计数。增加真实CLI模拟验证已知失败才启动、未知错误不启动，以及阶段已有请求/输出时拒绝重试、逐文档与累计次数上限。4项新增测试本地与服务器通过；本地含原OCRFlux/恢复相关测试共33项通过，ruff通过。

独立只读复核按requesting-code-review进行。隔离部署根 `artifacts/ocrflux-recovery/20261031T114000Z/source/`，原冻结推理源码仍 `artifacts/ocrflux-prep/20261030T015400Z/full-source-v3/`。首次测试隔离副本缺少evaluation初始化依赖contracts而未能导入，新增同版本支持文件后通过，失败现场保留。不是GPU推理失败。

预计supervisor ID `20261031T114000Z-ocrflux-resume`，每个实际推理run追加-a001、-a002等。启动/实际PID/恢复与首条请求证据将在下方追加，不以测试通过冒称任务运行中。

## 11:41:08 UTC（北京时间19:41:08）恢复任务启动

独立复核未发现启动阻塞，确认恢复链、独占写入与重试边界；纯函数测试复核通过。建议的多次连续失败集成覆盖属后续非阻塞改进，当前已有新旧协议恢复及原任务实际恢复证据，不据此宣称所有未来资源故障均能恢复。

unit `paper-ocrflux-recovery-20261031T114000Z.service`，初始父PID355605，active。命令：`.venvs/eval312/bin/python -u artifacts/ocrflux-recovery/20261031T114000Z/source/scripts/run_ocrflux_recovery.py --project /data01/public/zhengguojie/paper --supervisor-id 20261031T114000Z-ocrflux-resume`；PYTHONPATH显式指向该隔离source/src，由user systemd托管，Linger=yes。

事件 `artifacts/ocrflux-recovery/20261031T114000Z/events.log`；恢复日志 `logs/ocrflux-recovery/20261031T114000Z-ocrflux-resume/`，supervisor.json记录策略，attempt-NNN.json记录完整原生命令/显存采样/源失败目录/次数/进程快照，attempt-NNN.log为对应原全量入口日志。实际结果根 `artifacts/ocrflux-document-runs/20261031T114000Z-ocrflux-resume-aNNN/`。未新建定期Agent监控，有限恢复是运行进程内部的错误处理。

本次不下载数据，不改原数据/结果，GPU仍仅0；启动前快照40,661MiB空余且有其他进程，逐请求8192MiB保护沿用原worker。外层无新随机算法，模型/data/input赛道/生成/评分/源码均同原run。原32篇恢复及新请求成功仍待后续核验。

## 11:43:54 UTC（北京时间19:43:54）实际恢复与GPU预测验收

首个实际run `20261031T114000Z-ocrflux-resume-a001` 已开始，run-manifest的protocol字典与旧run完全相同，resume明确指向旧run。旧32篇共430页，2,726个checkpoint文件引用已通过原run_batch恢复入口SHA核验，之后新run-manifest才发布并进入worker；不是只按文件名跳过。

新run的documents/仅有PMC10285071，证明未重跑已完成32篇；该第33篇13页图像PDF打包审计通过。native.log显示memory profiling完成4.80秒、引擎初始化完成7.15秒；页0耗时19.95秒、页1耗时18.52秒，当前前3页均终态ok，原始响应完整保存。原38页截断未重算、未调整生成上限。

unit仍active/running、MainPID355605，GPU0快照空余24,747MiB、利用率100%，高于8192保护线。最终验收证据 `logs/ocrflux-recovery/20261031T114000Z-ocrflux-resume/startup-check.json`；当前attempt-001.json及attempt-001.log保存完整命令和资源采样。没有发生本次a001再次初始化失败，后续同类失败的有限重试仅由进程内部执行；未创建定期Agent监控。

恢复层代码本地commit `5e0a89e`，身份zgjdev；服务器使用隔离恢复source，不改旧冻结推理源码或仓库分支。当前累计完整文档检查点仍32篇/430页，第33篇尚未全部完成，不能把3个新页称为新增完整文档。任务依赖服务器systemd+Linger运行，关闭当前电脑/对话不直接影响；资源竞争仍可能发生，有限重试不保证未来无中断。全量完成后仍需覆盖/哈希/两组CPU评分验收，当前无正式指标。
