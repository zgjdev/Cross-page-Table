# OCRFlux-3B独立环境与整文档smoke准备

日期：2026-10-30 Asia/Shanghai（执行时刻UTC）。状态：**环境级READY：依赖/导入/CLI/真实PDF渲染/CUDA及三任务最小生成全部通过；完整3文档smoke与全量门禁仍待完成**。用户确认按计划开始OCRFlux工作。数据目标为PubTables-v2 Full Documents固定revision `aa575e798cb00a296925e2086addb3e3fd9a1903`、image-only；本阶段只读权重/代码与依赖准备，不读取val/test调规则，不训练，不删除或覆盖数据/旧产物。

## 已提供：预检与官方来源

- 本地/服务器代码HEAD `006da5940e61ead3202c0cf168c02a304d851143`，分支codex/paddle-merge-compat；本地有Paddle完成记录与汇总未提交，服务器工作区干净。没有为了此准备阶段改变主分支或旧代码。
- 模型 `models/20261023T064109Z-public-models/ocrflux-3b/`，revision `e68592278bbc8ab32edf7b65e6e411f1d878ef72`。本轮按冻结下载配置对15个文件重新计算全部LFS SHA256/Git blob SHA1并验证大小，全部通过。权重LICENSE为Qwen RESEARCH LICENSE AGREEMENT，不把工具Apache-2.0许可当成权重许可。
- 官方代码 [chatdoc-com/OCRFlux](https://github.com/chatdoc-com/OCRFlux) 固定commit `c1b315aa4c8309f8dc436a5d90fc4977bcf0d865`；先在本地 `artifacts/ocrflux-prep/20261030-source/OCRFlux/` 取得并只读审计，再git archive传到服务器新目录 `artifacts/ocrflux-prep/20261029T162000Z/source/`。归档SHA256 `da65a3cceca1680dbec87b2465e7360b2c05923b97499d11c09b4e741bdd30b2`，两端一致。未修改官方源码。
- 官方pyproject要求Python>=3.11、transformers4.50.0、vllm0.7.3、torch>=2.5.1；Docker使用cu124/torch2.5的flashinfer源。采用Python3.11独立项目内Conda前缀，pip额外冻结torch2.5.1/numpy1.26.4，其余解析结果保存install report/freeze。此为准备选择，不代表已成功安装或GPU兼容性已验证。
- 当前PATH中缺少pdftoppm：调用返回FileNotFoundError。官方 `ocrflux/image_utils.py` 明确通过pdftoppm以72dpi渲染PDF后缩放至最长边1024，不能默默换成Paddle的渲染实现。因此计划在同一项目内Conda环境补齐poppler，不执行系统apt、不修改系统文件。使用systematic-debugging技能先读取异常与对应源码后才确定这一依赖缺口。
- GPU均共享：本次快照GPU0空余31,143MiB，GPU1/2/3分别423/16,408/14,018MiB，均已有进程；不终止任何进程，此快照不是后续推理资源许可。空余文件系统约34TB、MemAvailable约517GB。安装阶段CUDA_VISIBLE_DEVICES为空，不使用GPU。

## 后台安装设计（待实际启动证据）

任务ID `20261029T162000Z-ocrflux`；环境 `.venvs/20261029T162000Z-ocrflux/`，日志 `logs/ocrflux-setup/20261029T162000Z-ocrflux/`；新安装入口 `artifacts/ocrflux-prep/20261029T162000Z/setup-contained.py`（本地先编辑/AST检查，服务端运行）。先验证Conda支持register_envs=false，禁用项目外环境注册；所有显式pip/conda/HF/Torch/临时缓存均指向本次日志目录，不重设HOME、不修改现有eval312/dots/Paddle环境。安装完整官方工具依赖，不下载新模型/数据集；只下载Python/Poppler及pip运行依赖。失败保留环境和日志，不覆盖或无条件自动重试。

计划服务 `paper-ocrflux-setup-20261029T162000Z.service`；入口：`systemd-run --user --unit=paper-ocrflux-setup-20261029T162000Z --property=Type=exec --property=Restart=no --property=WorkingDirectory=/data01/public/zhengguojie/paper --property=StandardOutput=append:/data01/public/zhengguojie/paper/artifacts/ocrflux-prep/20261029T162000Z/setup-events.log --property=StandardError=inherit /data01/public/zhengguojie/paper/.venvs/eval312/bin/python -u artifacts/ocrflux-prep/20261029T162000Z/setup-contained.py`。每阶段命令、日志路径和UTC写入setup-events.log；最终setup-summary.json区分failed与installed_not_gpu_smoke_tested。完成须pip check、freeze、conda explicit、renderer和imports均通过，不能只据service active说ready。后台启动/结束时追加PID和实际状态。

## 官方输出契约风险与后续门禁

源码审计已提供：官方包含页面识别、元素续接检测、表片段模型重建三阶段；`ocrflux/inference.py::parse` 最终只返回document_text/page_texts/fallback_pages，没有返回完整元素合并边及表来源链，且 `build_document_text` 会修改输入列表。官方pipeline同样未直接输出评测所需的表来源链。因此要保留原页面输出、续接索引和每次表格重建的中间结果才能无GT地适配，不能从最终Markdown/GT反推来源页。

官方两入口对模型返回使用eval，不能直接执行未经检查的模型字符串。后续wrapper需要安全字面量解析、类型/索引边界校验及原始输出留存；此项尚未实现/测试，不修改官方包后冒称原版。当前没有运行该风险代码或读取模型输出。

下一步：完成依赖安装和导入/真实渲染检查；在本地设计可审计wrapper及契约测试（同一页面结果用于no_merge/merge、列/来源链明确、缺页失败显式保留）；复用已审计train完整文档正例PMC10235804/PMC10311686和负例PMC11626747及无表页，重新GPU门禁后才启动小规模推理。seed/生成参数/显存预算待wrapper冻结，不为补齐记录伪造。smoke通过及可恢复全量入口验收后才运行935篇val；本轮尚无OCRFlux预测、指标或全量时间估算。

## 16:20–16:23 UTC（北京时间10月30日00:20–00:23）实际执行检查点

首次服务paper-ocrflux-setup-20261029T162000Z、PID2294328在16:20:26 UTC启动后，因用户systemd的PATH不同于SSH会话而报告 `conda executable not found on PATH`，16:20:26.801 UTC失败；未创建Conda环境。旧logs及setup-summary.json完整保留，未删除或改写。通过SSH此前已核验Conda实际可执行文件位置；只执行该既有程序，不检查其安装目录或其他用户文件。

本地调整实验安装封装为运行时显式Conda路径与新run ID，AST检查通过；传入新文件 `artifacts/ocrflux-prep/20261029T162000Z/setup-explicit-conda.py`，不覆盖首次入口或失败记录。新任务 **20261029T162200Z-ocrflux**，unit `paper-ocrflux-setup-20261029T162200Z.service`、初始PID **2298669**，实际启动 **16:21:05 UTC（北京时间00:21:05）**，active/running。新环境与日志分别 `.venvs/20261029T162200Z-ocrflux/`、`logs/ocrflux-setup/20261029T162200Z-ocrflux/`。入口命令同前，改用新unit、StandardOutput后缀 `setup-162200-events.log`、`--setenv=OCRFLUX_CONDA_EXE=/home/miniconda3/bin/conda`，Python参数改为 `artifacts/ocrflux-prep/20261029T162000Z/setup-explicit-conda.py 20261029T162200Z-ocrflux`。此绝对路径来自只读预检，只执行程序；未改系统文件。

新任务先验证register_envs=false，16:21:55 UTC完成项目内Conda Python3.11/Poppler环境创建并进入pip-install；当前pip日志为官方源码包构建依赖安装中，尚无setup-summary成功标志、pip check/freeze/imports尚待完成。安装设置CUDA_VISIBLE_DEVICES为空，不会自动触发GPU推理；Linger沿用既有yes，没有新建监控或更改系统保活。

复用既有输入打包器，新生成 `artifacts/ocrflux-prep/20261029T162000Z/train-inputs/`，3篇完整train文档PMC10235804/PMC10311686/PMC11626747，共10页，未用GT筛页。命令 `.venvs/eval312/bin/python scripts/pack_pubtables_document_images.py --images 'data/pubtables-v2/extracted/Full Documents/train/images' --documents PMC10235804 PMC10311686 PMC11626747 --output-dir artifacts/ocrflux-prep/20261029T162000Z/train-inputs`。相关真实测试文件为tests/test_pack_document_images.py，3 passed in0.13s（首次误写较长测试名未收集到测试，核对rg文件列表后重新正确运行通过，不冒称首次测试通过）。

packing-manifest SHA256 `1c791f9202ee10781ac9e51632d960713788a4beeacee3569593ebded0052d2e`，pdf_text_audit=empty、embedded_image_audit=byte-identical。项目内Poppler **26.10.0**已实际执行pdftoppm，以官方参数-png/-f1/-l1/-r72渲染首篇第一页，输出334,016字节有效PNG，SHA256 `503f1f0c3495219e8222e6b5500916e410eae68a9af038c6c38173a8cb38cc2a`，证据 `artifacts/ocrflux-prep/20261029T162000Z/renderer-probe.json`。这只证明输入与渲染工具可用，不代表模型推理、页识别质量或跨页恢复已通过。

## 16:35 UTC（北京时间00:35）就绪询问只读复核：安装失败

此前“安装中”是上一检查时刻的真实历史状态，现追加更新，不静默改写。`logs/ocrflux-setup/20261029T162200Z-ocrflux/setup-summary.json` status=failed，ended_utc=2026-10-29T16:28:26.261558+00:00（北京时间00:28:26）；service failed/failed、MainPID0、ExecMainStatus1。Conda/Poppler阶段已完成，失败位置为pip-install的build dependency安装setuptools，日志反复报到pypi.org:443的 `[Errno 101] Network is unreachable`，随后出现No matching distribution。不能据此归因为setuptools不存在或模型/显存错误，pip check/freeze/imports根本未运行。

本轮使用systematic-debugging先核对异常、执行日志及官方pyproject依赖。仅做只读网络HEAD探测以核验替代源，不修改pip源、安装脚本、环境或重启任务。GPU快照空余0/1/2/3分别31,143/423/16,408/14,018MiB，不能替代runtime/smoke验收，未启动GPU任务。权重与3篇10页输入无需重复下载/生成。

下一步需先解决依赖下载链路（完整核验索引、实际wheel与build依赖可达性，保留固定版本及报告），再完成pip check/imports、安全解析/中间来源链wrapper及train smoke；本轮只回答就绪状态，不擅自开启全量或把它标为ready。

只读HEAD复测结果：官方pypi.org/simple/setuptools仍网络不可达；清华与阿里镜像的simple/setuptools入口均HTTP200，官方flashinfer固定cu124/torch2.5链接入口HTTP200。仅证明这些入口可达，不代表所有依赖wheel可下载或已安装；本轮未切换源或重新运行安装。

## 16:40 UTC（北京时间00:40）用户授权持续修复环境

用户明确要求持续工作直到环境可执行。根因已定位为官方PyPI网络不可达，现仅切换本次pip命令的index为已探测HTTP200的清华镜像，不改全局pip配置；保留官方vllm0.7.3/transformers4.50.0、torch2.5.1/numpy1.26.4。复用项目自有162200环境（此前仅Conda/Poppler完成），旧失败日志不覆盖；新日志 `logs/ocrflux-setup/20261029T164100Z-mirror-repair/`。先固定setuptools75.8.0/wheel0.45.1，再用--no-build-isolation避免子构建回到不可达源；源码和模型不改，依赖报告/冻结文件新建保存。

入口本地创建并上传 `artifacts/ocrflux-prep/20261029T164100Z/repair_install.py`，以 `.venvs/eval312/bin/python -u <入口>` 执行；unit `paper-ocrflux-repair-20261029T164100Z.service`，实际启动16:40:48 UTC、初始PID2430136，active。完整pip子命令及UTC写于同目录events.log；CUDA_VISIBLE_DEVICES为空，仅安装无GPU。缓存/TMP/XDG/HF/Torch仍全部项目内。完成必须pip check、freeze、imports与后续CUDA/最小生成验收，安装running不等于ready。

修复阶段build依赖已成功安装，torch wheel真实下载大小持续增长（16:42:50 UTC约274.7MB→16:44:32 UTC约426.8MB），不是索引HTTP200后即宣称安装完成。为减少后续串行大包下载时间，读取官方PyPI torch2.5.1/vllm0.7.3 requires_dist确认精确版本后，启动仅下载不安装的3并发预缓存：`paper-ocrflux-prefetch-20261029T164100Z.service`，入口同artifact目录prefetch.py；固定vllm0.7.3/cudnn9.1.0.70/cublas12.4.5.8/cusparse12.3.1.170/triton3.1.0/cufft11.2.1.3，使用相同项目内pip-cache，下载日志/wheel保存在新prefetch目录。未重下载模型/数据，未修改任何旧结果。

本地已准备有限GPU环境验收脚本 `artifacts/ocrflux-prep/20261029T164100Z/gpu_probe.py`，AST通过，尚未运行。计划仅1个真实train页面识别加2个合成文本续接/表重建请求，调用官方提示和query构建，模型字符串仅JSON/ast.literal_eval解析、绝不eval。最小模型预算gpu_memory_utilization=0.20、max_model_len16384、max_num_seqs1、enforce_eager、bfloat16、seed0；生成temperature0/max_tokens8192。启动前要求GPU0空余至少24,576MiB，每任务前低于8,192MiB保护退出。此为环境验收，不冒充完整3文档smoke/来源页adapter或全量ready；实际GPU启动/完成需另记证据。

### 16:53 UTC去掉非必需索引后继续（保留原现场）

预缓存6项全部exit0，后续安装已命中vllm/CUDA缓存；Torch906.5MB也成功下载。但runtime.log出现flashinfer额外find-links入口ReadTimeout，官方PyPI torch2.5.1/vllm0.7.3 requires_dist不包含该可选依赖。因此16:53 UTC仅停止本Agent创建的 `paper-ocrflux-repair-20261029T164100Z.service`（确认inactive、MainPID0），不停止其他进程，保留原log/cache/tmp，无删除、截断或覆盖旧记录。

本地移除该可选find-links参数，上传新入口 `repair-required-deps.py`，新unit **paper-ocrflux-repair-20261029T165400Z.service**，实际启动16:53:20 UTC、初始PID2513578；日志新目录 `logs/ocrflux-setup/20261029T165400Z-required-deps/`，事件 `artifacts/ocrflux-prep/20261029T164100Z/events-required-deps.log`。仍安装完整官方pyproject必需依赖及原固定核心版本，复用164100 pip-cache，不修改模型/官方源码或全局源。此前安装为主动中断，不因无summary误标成功。正式算子后端需导入/GPU验收再记录，不能据去掉索引便声称可推理。

同阶段只读train真值审计（未把GT提供给模型）：两篇3页正例均在[1,2]有跨页表、[0]无表；4页负例表在[1,2]、无跨页逻辑表、[0,3]无表。共4个无表页，输入仍全10页不筛选。证据 `artifacts/ocrflux-prep/20261029T164100Z/train-scope-audit.json` 保存truth SHA。

### 16:56 UTC兼容性约束收敛（非核心版本升级）

165400安装已推进并命中全部大包缓存，但pip开始下载/回溯多个Gradio6版本。读取官方PyPI版本metadata定位约束冲突：Gradio6.29.1要求huggingface-hub>=1.16.0，而固定transformers4.50.0要求<1.0；gradio_pdf0.0.23/0.0.24要求Gradio>=6。确认Gradio5.23.1允许huggingface-hub>=0.28.1，gradio_pdf0.0.22允许4<=Gradio<6。故只新增UI兼容约束gradio5.23.1/gradio_pdf0.0.22，保留torch/vllm/transformers/numpy核心版本与官方源码，不改变模型行为以迁就安装。

只停止自建165400安装服务以避免无意义回溯，旧日志/缓存全部保留。新入口 `repair-ui-compatible.py`，unit **paper-ocrflux-repair-20261029T165800Z.service**，实际16:56:19 UTC启动，初始PID2533796；日志 `logs/ocrflux-setup/20261029T165800Z-ui-compatible/`，事件events-ui-compatible.log。依然只CPU依赖安装，未GPU推理或全量。metadata来源分别 `https://pypi.org/pypi/gradio/5.23.1/json`、`https://pypi.org/pypi/gradio/6.29.1/json`、`https://pypi.org/pypi/gradio_pdf/0.0.22/json` 及0.0.23/0.0.24同接口；仅元信息在本机读取，不下载模型/数据集到本地。

### 16:59 UTC依赖安装与CPU导入通过

16:59:36 UTC安装结束后pip check通过（No broken requirements found），freeze已保存；16:59:48 UTC imports结束，summary.status=installed_not_gpu_tested。实际torch2.5.1+cu124/CUDA12.4、transformers4.50.0/vllm0.7.3/ocrflux0.1.0，完整传递依赖在freeze.log及runtime-report.json，未把安装通过冒称GPU通过。下一步按此前预算进行有限GPU验收；输入只用一个真实train页面和两个合成合并请求，不读取GT、不使用val/test、不跑整批数据。

### GPU环境验收启动

启动前GPU0为A10080GB、驱动550.127.08，空余31,143MiB，已有5个GPU0计算进程；其他进程未终止。执行 `systemd-run --user --unit=paper-ocrflux-probe-20261029T170000Z --property=Type=exec --property=Restart=no --property=RuntimeMaxSec=900 --property=WorkingDirectory=/data01/public/zhengguojie/paper --property=StandardOutput=append:/data01/public/zhengguojie/paper/artifacts/ocrflux-prep/20261029T164100Z/gpu-probe-events.log --property=StandardError=inherit /data01/public/zhengguojie/paper/.venvs/eval312/bin/python -u artifacts/ocrflux-prep/20261029T164100Z/run_gpu_probe.py 20261029T170000Z-ocrflux-runtime-probe`。

新产物 `artifacts/ocrflux-prep/20261029T170000Z-ocrflux-runtime-probe/` 保存config、三次原始响应与summary，项目内缓存与显式环境在 `logs/ocrflux-probes/20261029T170000Z-ocrflux-runtime-probe/`；模型仅加载既有路径并强制offline。脚本只调用官方query builder/提示与LLM.generate，不调用含eval的parse，检测响应用ast.literal_eval。有限超时仅约束本验收unit，不操作其他进程。实际PID/起止/是否通过待核验，不能以服务启动冒称模型加载通过。

### 17:02 UTC（北京时间01:02）GPU与运行接口验收通过

实际unit `paper-ocrflux-probe-20261029T170000Z.service` 启动17:00:34 UTC，父PID2563300。probe summary.started_utc=17:00:35.018727、ended_utc=17:01:53.345171，status=passed；service已inactive/dead、MainPID0、ExecMainStatus0，非后台仍运行。CUDA矩阵运算通过，既有模型两个safetensors分片成功加载，vLLM报告模型权重7.1542GB，预算15.83GiB、activation profile1.26GiB、KV预算7.41GiB；这是引擎诊断，不是独占GPU严格峰值。

| 验收项 | 输入/参数 | 已提供结果 |
| --- | --- | --- |
| 页面识别 | PMC10235804完整图像PDF第1页（0-based页0），官方query builder、最长边1024 | 33.85秒、963生成token、finish_reason=stop，JSON及官方PageResponse校验通过，natural_text非空 |
| 元素续接检测 | 两个合成HTML表元素列表，官方prompt | 0.30秒、7 token，安全字面量解析得[(0,0)]，类型/索引通过 |
| 表格重建 | 合成表A/1及B/2，重复Name/Value表头 | 1.38秒、50 token，返回单张HTML表，保留一个表头及A/1、B/2两行，HTML存在性核验通过 |

生成参数temperature0/max_tokens8192/seed0，GPU单卡0、engine参数见上方config及保存产物。实际train页为无表页，此最小验收证明页面文本生成/两类合成合并入口可执行，不冒充真实跨页结构性能；未读取GT给模型、未完整执行10页或计算评分。原始响应分别page-raw.json、detect-raw.json、merge-raw.json，均保留不改写。

测试期间整卡空余采样15,151MiB，高于8,192MiB保护线；结束后空余31,143MiB/占用49,896MiB，回到测试前快照。没有终止其他用户进程。未严格连续采样峰值，不将快照作为未来独占资源承诺。引擎日志提示vision使用xformers回退（vLLM内置路径）、多模态最坏情况context警告及退出时NCCL进程组未显式销毁警告；本次三个请求与进程均成功。后续train wrapper需显式清理进程组，并按真实输入冻结图像/视频限额和context协议，不能以最小测试已过假定所有长表输入都可执行。

17:02后追加CPU接口检查：项目环境的pypdf PdfReader.get_num_pages()对train PDF返回3；官方 `python -m ocrflux.pipeline --help` exit0，均将工作目录/缓存指向项目日志，证据pdf-api.log、pipeline-help.log。环境完整freeze SHA256 `842cb1c8896026a0652a4be982523a4a2c3c40548bfd7f9e7cae2aff4971786e`，安装报告包含来源与wheel哈希，均在165800-ui-compatible日志目录。

**验收结论：环境依赖及模型最小执行能力READY，可以进入完整train smoke阶段。**不再需要重复下载安装模型或重建环境；不是“935篇全量已可直接启动”。尚未完成的独立门禁是安全/可审计的跨页中间结果封装、同份页面结果的合并开关配对、来源页adapter契约及完整3文档10页smoke；随后才可建立可恢复全量入口。当前无OCRFlux安装或GPU任务继续运行，无定期监控。

最小验收复现：先重新检查GPU0空余与其他进程（至少24,576MiB），用新的唯一probe ID替换原命令最后参数及unit名，再执行已保存的run_gpu_probe.py；其目标环境固定为 `.venvs/20261029T162200Z-ocrflux/bin/python`，显式环境记录位于logs/ocrflux-probes/对应ID。不能重用已存在的输出ID，不能调用含eval的原始parse作为未审计替代。

同日用户询问能否全量时只读复核：最小probe仍passed，scripts/src/tests没有OCRFlux正式runner/adapter，用户service列表无运行项。无新实验/未启动全量，环境READY与完整流程READY继续分开；下一步需完成真实10页smoke及来源页/配对评分/恢复验收，不再重复安装依赖。

### 2026-10-30（Asia/Shanghai）完整流程设计检查点

用户要求继续后，本轮阅读官方OCRFlux推理接口、现有document_run恢复及统一评分契约，完成 [完整流程设计](../superpowers/specs/2026-10-30-ocrflux-document-baseline-design.md)，自审占位内容、协议一致性和范围，`git diff --check`通过；设计单独本地提交 `91340e7`，未推送。此前未提交记录保留，没有混入该提交。

推荐显式封装固定官方API，保留提示与阶段顺序，用安全字面量解析替换eval并记录逐元素来源链；明确命名instrumented，不冒称原CLI字节级复现。复用同一批逐页预测生成no_merge/merged两组，评分不改公式、GT只进入离线评分。固定train三文档10页用于完整推理、来源页审计、配对评分和实际checkpoint恢复演练，之后才做935篇全量预检。失败时保留现场及原片段，协议差异需披露，不能把封装修正作为研究增益。

**状态：设计待用户审阅；正式代码及以上门禁仍待实现/验证。**本轮没有新模型/数据下载，没有启动服务器任务或GPU计算，也没有新指标。环境最小验收结果沿用前文证据。下一步为审阅设计后编写实现计划并按测试驱动完成封装，不重复环境安装、不直接开始val全量。

### 同日再次询问所有模型能否全量：只读复核，无新结果

SSH只读读取项目代码路径、项目.venvs目录、既有probe summary，并查询GPU和本用户运行service。服务器HEAD006da59；scripts/src/tests按文件名检查无OCRFlux/Popo正式入口，且本地对应代码也未新增。OCRFlux summary仍status=passed、purpose=environment acceptance only，不能代替3文档10页完整测试；项目环境列表无Popo独立环境。systemctl --user运行service列表为空。GPU0空余31,143MiB、占用49,896MiB、利用率39%，只证明本次快照，不证明独占或后续可用。

结论不变：Paddle已有全量推理与评分记录；OCRFlux环境已通过但完整封装、train配对评分和恢复验收尚缺，Popo环境与管线尚待准备，不能称所有模型均可全量。本轮未修改服务器文件、未启动计算、没有新指标；下一步按既有OCRFlux设计补齐完整流程。

### 用户继续后实施与train验收启动（2026-10-30，Asia/Shanghai）

用户批准继续，按同日设计实施。计划 `docs/superpowers/plans/2026-10-30-ocrflux-document-baseline.md`；新增安全索引/逆序表链核心、官方API逐请求落盘入口和CPU两组adapter。先观察核心缺模块的失败，再实现12项测试通过；CLI/adapter先失败再实现，本地共15通过。临时目录默认权限失败改为项目内唯一basetemp；不影响模型协议。ruff检查通过。

代码以隔离archive传到 `artifacts/ocrflux-prep/20261030T015400Z/source/`，不覆盖服务器src/scripts及任何旧结果。首次缺包初始化/支持模块导致测试导入失败，新增对应现有支持文件后服务器12核心测试通过。模型/数据没有下载或改变；正式全量入口仍在实现。代码未提交（基于本地91340e7），逐文件SHA由worker运行manifest记录。

01:53:19 UTC GPU0空余31,143MiB、已有5个计算进程；未终止其他进程。新unit `paper-ocrflux-train-20261030T015400Z.service`，初始PID3302340、active，命令为 `.venvs/eval312/bin/python -u artifacts/ocrflux-prep/20261030T015400Z/launch.py`，systemd user托管、无定期监控。日志 `artifacts/ocrflux-prep/20261030T015400Z/events.log`，环境/命令/freeze位于 `logs/ocrflux-smoke/20261030T015400Z-ocrflux-train-smoke/`。

输入复用162000 train-inputs，PMC10235804/PMC10311686/PMC11626747共10页；目的验证完整流程，不是正式性能。模型/数据/官方源码revision同前；image-only，seed0/temp0/max8192、官方API max_page_retries0、GPU0/TP1/bfloat16/0.20/16384/maxseq1、image1/video0。启动需30,000MiB空余，请求前低于8192MiB停止。输出新目录 `outputs/baselines/ocrflux-3b/20261030T015400Z-ocrflux-train-smoke/`，原始请求/页面/合并证据全部保存。预期3文档10页终态、两组来源链及评分契约通过；完成状态、指标、实际恢复尚待核验，未启动val全量。

### 10页真实流程完成、配对评分完成；恢复入口pilot运行中

原smoke summary completed，结束02:01:22 UTC（北京时间10:01），3文档10页全部status=ok。PMC10235804两片成功合并来源[1,2]；PMC10311686仅预测1个页表[1]、未完成真值续表恢复；负例PMC11626747保持4个单页表。后两者是性能证据，不调整提示/规则，不冒称所有真实续表已正确。

首次CPU adapter失败原因为已有打包器image_id使用stem、冻结val清单使用filename；读取两条真实清单确认后新增失败回归，再改为接受这两种明确格式并保留原始image_id，relative_path仍严格匹配jpg。未修改已有清单或GPU输出；首次 `train-scores/` 失败现场保留。新代码 `full-source-v2/` 与 `accept_train_v2.py`、`train-scores-v2/` 使用新路径。当前本地26项测试（含既有document_run）、ruff通过；服务器上一版18项通过，最终版回归仍需核验。

两组CPU评分均exit0、summary completed；使用统一score_cross_page_predictions.py及--partial，GT仅读取3篇train并派生2项跨页gold，truth SHA前后相同，所有命令与结果SHA见 `artifacts/ocrflux-prep/20261030T015400Z/train-scores-v2/summary.json`。合法三页表链另执行真实官方build_document_text纯函数AST核验通过（不执行含eval的parse）。

| 条件 | 全表GriTS-Con | 跨页GriTS-Con | 跨页内容网格exact | 覆盖/错误 |
| --- | ---: | ---: | ---: | --- |
| no_merge | 0.6561625640 | 0.5791620325 | 0/2 | 10/10页、missing/extra/duplicate=0、页面错误0、非法HTML1 |
| merged | 0.8354940078 | 0.7904655261 | 0/2 | 同上 |

结果仅验证可评分流程，样本为选定train正负例而非随机正式评估。非法HTML来自既有模型输出，保留并由评分器计入诊断；未为了分数清洗或利用GT修补。跨页只匹配1张，不能从合并分数推断两张都恢复。

完整val只读预检已执行固定935/13871输入成员与JPEG头、全部15模型文件SHA、已安装官方4个源码文件对固定提取源码SHA及环境freeze；证据 `acceptance/full-preflight.json`。最终v2源码因适配修正需重做该协议快照，不据旧快照冒称最终ready。

实际full-entry验收unit `paper-ocrflux-entry-20261030T015400Z.service`，初始PID3443480、active；入口 `launch_pilot_v2.py`，事件 `pilot-events.log`。使用负例PMC11626747全部4页，经正式打包→独立worker→checkpoint→适配，再以新run恢复，禁止重复调用GPU；新manifest `acceptance/pilot-filename-manifest.jsonl` SHA `664a07da9bae1194261c2418627eaaa03999da6c8ebcec96d40f1585693f85c8`，只在新派生清单明确统一ID，不改旧清单。首run `artifacts/ocrflux-document-runs/20261030T015400Z-ocrflux-full-entry-pilot/`，后续恢复run尾缀full-entry-resume。详细命令由pilot-events记录；完成/恢复状态仍待验收。未启动val全量，未新建定期监控。

### 独立复核与v3最终验收检查点

v2实际pilot和新run恢复均completed/exit0；恢复resumed_documents=1、无新documents目录，两组输出SHA相同，31份checkpoint产物重算通过，证据acceptance/final-audit.json（02:07:16 UTC）。Linger=yes只读核验，没有更改系统设置。

按requesting-code-review进行独立只读复核，确认两项全量阻塞：detect/merge真实引擎RuntimeError会被当成普通错误继续；原冻结val清单词法页序[0,1,10,...,2]不能直接进入要求数字页序的adapter。两项分别新增CUDA out of memory双阶段和12页清单回归，先观察失败，再修改core传播RuntimeError/MemoryError、页面传播MemoryError，以及adapter先检查整数非负页号后按(doc,page)排序，原manifest SHA及文件保留。复核确认原P1均关闭，无其他已证实阻塞。

最终v3代码本地29项相关测试及ruff通过，服务器22新增+7恢复+3打包共32项通过。新隔离源码full-source-v3/和full-source-v3.tar保存，不改v2及之前代码。v3实际pilot/恢复任务unit `paper-ocrflux-entry-v3-20261030T015400Z.service`，初始PID3556047、启动active，事件pilot-events-v3.log，入口launch_pilot_v3.py，run目录使用pilot-v3/resume-v3，清单pilot-filename-manifest-v3.jsonl（内容及SHA同v2）。新预检final_preflight_v3.py写acceptance/final-full-preflight-v3.json。重复有限pilot是因为代码复核产生实质修复，需要核验最终可执行版本，不复用不兼容checkpoint。

最终adapter已复用原10页预测再次完成两次CPU评分，train-scores-v3/summary.json状态completed、完整命令与SHA保存。原预测没有GPU重跑，没有改HTML；两组各1项未通过当前HTML评分契约，原因尚未分类，不能据此归咎模型或评分器。小样本指标仍只是流程诊断。

v3实际pilot/恢复、最终模型/输入/源代码SHA预检仍待本轮末段验收；未启动935篇val全量。运行与恢复说明见 `docs/2026-10-30-ocrflux-full-validation-readiness.zh-CN.md`。

### 02:14:46 UTC（北京时间10:14）最终v3技术验收通过，未启动全量

最终unit `paper-ocrflux-entry-v3-20261030T015400Z.service` 已inactive/exit0；pilot-v3 completed，1文档4页，恢复run resume-v3 completed、resumed_documents=1，没有新documents目录，未再次加载模型或生成请求。两个run的31份checkpoint文件全部重算SHA一致，且两组导出document-tables.jsonl的SHA均为 `0250fd0a3290ee259387ad3630e56a9f3d0fa872e6422403ca9b22846de401cb`。两组在负例保持相同是模型未合并，不据此声称正例合并效果。

最终v3完整val预检status=input_protocol_verified，935篇13,871页，原清单SHA2782f9ed…、数字页序SHA1d39ca16…均与固定协议一致；15模型文件大小/SHA及完整download-manifest SHA `cf0f4072c37e30e41964ba97aed7b0d38f4e52999f417526759ae32bfc108af8` 通过，环境freeze SHA与此前一致。实际安装的官方inference/prompts/image_utils/table_format四文件与固定源码SHA一致。所有完整SHA和source_sha位于 `acceptance/final-full-preflight-v3.json`、`final-audit-v3.json`，没有仅凭文件存在冒称通过。

最终v3复用10页预测的train指标文件与v2字节相同；no_merge metrics SHA `8efa27af65f16331fdb3a379a0335ba2fb6ad292903f61bacae8dba357f09b73`、merged `363573d6f943ff121359d18a82248af469ff092f4ef34b6b9d5dc7669618ea12`。仍仅为选定train开发验证，原1项非法HTML未改，不能算新正式性能。

最终本地29/服务器32相关测试、ruff均通过；独立复核确认两项P1关闭，无其他已证实阻塞。GPU0空余31,143MiB、利用率38%是退出后快照；Linger=yes，未改系统设置，未终止其他用户进程。没有OCRFlux验收任务继续运行、没有启动val全量或定期监控，Popo准备状态未改变。

**结论：OCRFlux全量技术READY。**下一步可按readiness文档启动固定935篇/13,871页val image-only运行，启动前重查资源，使用新RUN_ID和同一冻结源码full-source-v3。约一周量级仅为10页吞吐外推，正式运行后按文档吞吐更新，不承诺完成时间。正式分数仍需全量推理结束后两组CPU离线评分。
