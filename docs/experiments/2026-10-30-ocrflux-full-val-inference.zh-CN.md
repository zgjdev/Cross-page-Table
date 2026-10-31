# OCRFlux-3B 完整validation推理

日期：2026-10-30启动，2026-10-31复核（Asia/Shanghai）；服务器日志使用UTC。原run已失败停止、32篇/430页保留；**10月31日19:43已同协议新run恢复推理**，见 [恢复实验](2026-10-31-ocrflux-profiling-recovery.zh-CN.md)。尚未完成/评分，历史阶段状态保留下文。

## 目的与固定协议

研究问题：在统一image-only完整文档输入下，OCRFlux逐页解析及官方跨页表重建的完整val结果如何；复用同一批逐页结果比较no_merge/merged，不利用GT修补或筛页。

数据：PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，validation935篇/13,871页，全页输入包括无表页，test不使用。原始JPEG位于 `data/pubtables-v2/extracted/Full Documents/val/images/`，按文档打包成无文字层PDF，原图字节嵌入并审计；原数据不改。

模型OCRFlux-3B revision `e68592278bbc8ab32edf7b65e6e411f1d878ef72`，官方代码 `c1b315aa4c8309f8dc436a5d90fc4977bcf0d865`。本地实现commit `6856155`；运行冻结服务器源码 `artifacts/ocrflux-prep/20261030T015400Z/full-source-v3/`，命名OCRFlux-official-API-instrumented，不冒称原CLI字节级复现。启动wrapper核验7项source_sha与最终预检记录一致，服务器原分支未切换。

环境 `.venvs/20261029T162200Z-ocrflux/`，Python3.11/torch2.5.1+cu124/vllm0.7.3/transformers4.50.0/Poppler26.10.0，freeze SHA `842cb1c8896026a0652a4be982523a4a2c3c40548bfd7f9e7cae2aff4971786e`。单卡GPU0（A10080GB）；TP1/bfloat16/预算0.20/max_model_len16384/max_num_seqs1/enforce_eager/image1/video0，seed0/temp0/max_tokens8192/max_page_retries0，官方最长边1024。每篇独立worker，缓存均在项目输出目录。

输入源清单 `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl`，SHA `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`；数字页序派生SHA `1d39ca16b7fcfedf3dabb174c80ef4ae914d90a76a2839617a469c0ba75e90c5`。模型、环境、官方代码、成员/JPEG头和按文档恢复已于 [验收记录](2026-10-30-ocrflux-runtime-and-smoke-readiness.zh-CN.md) 核验，完整命令见下方保存产物。

## 启动事实与产物

- 用户明确要求开始全量；实际启动时间2026-10-30 03:24:57 UTC（北京时间11:24:57）。
- RUN_ID：`20261030T032500Z-ocrflux-val-full`。
- unit：`paper-20261030T032500Z-ocrflux-val-full.service`；初始父PID477502，启动active。user systemd托管，Linger=yes，断开SSH/关闭本机不依赖当前对话保活；没有创建定期监控。
- 启动前GPU0空余31,143MiB，已有5个计算进程；未终止或改变其他进程。加载前门槛30,000MiB、请求前保护线8192MiB，不假设独占。
- 启动入口：`artifacts/ocrflux-launchers/20261030T032500Z-ocrflux-val-full/launch.py`；systemd完整入口为 `.venvs/eval312/bin/python -u <该入口>`。
- 事件日志：`artifacts/ocrflux-launchers/20261030T032500Z-ocrflux-val-full/events.log`。
- 完整命令/显式环境/源代码SHA/初始GPU进程：`logs/ocrflux-launchers/20261030T032500Z-ocrflux-val-full/launch-manifest.json`。
- 父流水线日志：`logs/ocrflux-launchers/20261030T032500Z-ocrflux-val-full/full.log`，结束时新建exit.json。
- 结果根：`artifacts/ocrflux-document-runs/20261030T032500Z-ocrflux-val-full/`，包含run-manifest.json、documents/、checkpoints/；每篇inputs/、predictions/raw/、native.log保留命令、输入、原始响应和错误。

不下载数据或模型、不修改原始数据/已有实验结果。当前仅验证任务已启动，不以active状态冒称GPU首条预测或全量完成。

## 完成条件、恢复与限制

完成需935文档/13,871页终态、完整checkpoints与SHA校验、manifest覆盖missing/extra/duplicate=0，以及两组适配导出和export-complete.json；GPU任务结束后另执行两次正式CPU评分，当前没有正式全量指标。

异常中断保留全部产物；使用新RUN_ID、相同源码/环境/输入协议及 `--resume <旧结果根>` 恢复，已完成文档跳过，不完整文档在新目录重跑。不能在旧目录截断、覆盖或重置。GPU/引擎RuntimeError与MemoryError停止任务，不当成普通模型失败创建completed checkpoint。

生成截断、页面解析失败和非法HTML按既有协议记录，不能为分数清洗输出。此封装的表格失败回退和非表格分支边界见 [全量readiness说明](../2026-10-30-ocrflux-full-validation-readiness.zh-CN.md)。按10页train吞吐粗估约一周量级，正式吞吐待首批完成文档核验后再估；不承诺结束时间。

## 03:26:20 UTC（北京时间11:26）启动后GPU推理核验

run-manifest.json实际包含935篇、13,871页，父unit仍active/running、MainPID477502；第一篇PMC10154845全8页输入打包审计完成。native.log确认权重加载7.1542GB、引擎初始化完成，首个请求stage=page、identity=[PMC10154845,0]、elapsed_sec=21.04082357、error=null；raw/PMC10154845-page-0.json的终态status=ok。已证实GPU产生真实预测，不仅是服务启动。

此时checkpoints数量0，因为第一篇8页及跨页后处理尚未全部完成；不能把1页预测称为1篇已完成。GPU0空余15,227MiB、利用率73%，高于8192MiB保护线；仍有其他用户进程，没有终止其他进程。已知多模态最坏情况context警告与train验收相同，当前首请求成功，无证据表明资源失败。

任务由服务器user systemd及Linger=yes保活，关闭当前对话、断开SSH或关闭本机不直接中断任务；服务器重启/资源异常仍可能中断，届时按新RUN_ID恢复。不安排定期监控，也不承诺对话关闭后自动收到通知。结束后需核验全覆盖、SHA及两次CPU正式评分，当前无全量指标。

## 2026-10-31 10:11 UTC（北京时间18:11）只读进度检查：任务已失败停止

用户询问完成进度，本轮仅SSH读取原run产物和进程/GPU状态，没有启动、重启、终止任务或修改服务器文件。unit为failed/failed、MainPID0、ExecMainStatus1。父exit.json记录结束于2026-10-30T10:02:58.486086+00:00（北京时间10月30日18:02:58），实际运行6.6336小时；不是持续运行至本次检查。没有定期监控，因此本轮才发现失败。

已保存32/935篇完整文档检查点，对应430/13,871页终态（3.09999%）；392页status=ok、38页status=error。逐请求原始响应核验finish_reason为stop392、length38，38页均报Generation truncated or incomplete。该覆盖不能称430页全部成功。完成文档的续接/重建decision统计detect:ok339、merge:ok19、detect:error1；这些是接口状态而非恢复正确率，没有评分。

本轮遍历检查点身份、预期页数、重复、protocol一致性，以及每篇保存pages数量，未发现异常。没有重算完整raw/PDF等产物的全部SHA，因此不能称已通过最终完整性验收；恢复入口会执行SHA核验。原始输入、结果、失败日志均保留。

第33篇PMC10285071（预期13页）已打包，但在模型初始化期间退出，predictions/summary.json状态failed、documents=[]、pages=0。native.log明确报错：`AssertionError: Error in memory profiling`，initial used memory=33,683,668,992 bytes、currently used memory=32,503,431,168 bytes，触发vLLM要求profiling期间显存占用增加的断言。断言发生在引擎初始化而非表格评分或该文档生成；无证据表明本次是CUDA OOM。

已提供证据是两次显存采样下降约1.10GiB；共享GPU上其他任务释放显存是可能解释（推断），也可能涉及本引擎自身释放/初始化行为，具体来源待核验，不能仅按官方通用报错认定是本任务未清理显存。检查时GPU0空余40,661MiB、利用率56%，仅当前快照，不能反推昨晚状态。

证据路径：根summary.json（status=failed/completed_documents32/pages430）、父日志full.log及exit.json、checkpoints/*.json、第33篇documents/PMC10285071/native.log和predictions/summary.json。请求截断证据在各已完成文档predictions/raw/数字序号.json；本轮未改写任何产物。

下一步是排查初始化资源稳定性，再使用同一冻结协议和新RUN_ID从本run恢复；32篇检查点核验后跳过，第33篇仅在新目录重新执行。不得修改或清理旧数据。38页生成截断属于原协议的失败终态，不能用val结果调max_tokens、提示或重试策略后混为同一实验；若需研究应先在train另立协议和记录。此次未自动恢复，当前没有运行中的OCRFlux任务。由于任务已经中断，不能将包含停机时间的线性外推当成剩余时间；恢复后再按实际吞吐更新估算。
