# 四模型跨页表格恢复实验设计与服务器执行门禁

日期：2026-09-29（America/Los_Angeles）
状态：**阶段 0 数据审计已完成；阶段 1--4 计划中，尚未执行模型测试**；本文不是模型实验结果。
主要数据：PubTables-v2 `Full Documents`，固定 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`。
候选：OCRFlux-3B、MinerU-Popo、dots.ocr、PaddleOCR-VL-1.5。
外部补充数据：`ChatDOC/OCRFlux-pubtabnet-cross`，版本、许可、实际样本数与来源去重审计待固定。

## 1. 研究问题及主次关系

比较四种可获取方法在**真实跨页逻辑表格**上的最终结构与内容恢复能力，隔离并解释页面识别、续接判断和分页边界重建的误差。不能把续接 F1、局部 merge accuracy 或合成 HTML 片段 TEDS 解释成真实跨页整表完全正确率。

本研究为现有页面级基线增加跨页任务评测，不代替 `docs/superpowers/specs/2026-09-21-two-baseline-complete-validation-design.md` 中尚未完成的严格 dots.ocr 全页 validation。论文主要任务仍为文档级跨页结构恢复，而非比较通用 OCR 排行榜。

## 2. 数据与可比较性

### 2.1 主集：PubTables-v2 真实跨页表

原始输入来自 `data/pubtables-v2/extracted/Full Documents/{train,val,test}/` 的 `images/`；真值来自 `tables/` 的逻辑表和 `parts`，`cross_page_table_pairs/` 只用于续接关系诊断和困难负例审计。**真值筛选条件为同一逻辑表的 `parts` 中出现至少两个不同 `page_num`**；同页跨栏虽有多个片段，不计入跨页真值。文档、页、片段和逻辑表 ID 的映射须只读抽样检查并保存关联失败清单；不能把官方页面对标签说成官方列对应或拆分行标签。

主试验在 `Full Documents/val` 的 **935 篇文档、全部 13,871 页** 上推理，不得借助真值挑选“含表页”或提前告知模型哪两张表续接；指标计算时才筛出真实跨页表。空表页、非跨页表、非续接页面对作为误合并/假阳性检查所需的上下文。全量 test 只在代码、规则、提示词、阈值、模型版本和协议全部冻结后做最终评估，不用 test 调参。train 可用于规则设计或轻量校准，必须先按文档检查与 validation/test 无交叉。

保存两个独立视图：

1. **cross-page-only 主指标**：以真实跨页逻辑表为目标，文档内先对预测表与全部真值表做一对一匹配，再提取匹配到跨页真值的预测计分；漏表/非法输出计零。预测合并表匹配到单页真值、匹配不到任何真值、误连多个真值等另计误合并；不允许重复使用一张预测表。此分数明确标为本项目定义的跨页子集协议，**不是**原论文 Full Documents 全表指标。
2. **full-document 辅助指标**：沿用项目/官方文档级评测定义，覆盖同一 13,871 页上的全部真值表和额外预测，便于核查“只在跨页子集变好、却大量误合并单页表”的情况。不能只给正例 oracle 子集分数就称为端到端表现。

新增跨页评分器前应对官方匹配实现做对照测试：多表竞争匹配、两张真值表被错误合并、错误将一张表分开、无表页假阳性、无效 HTML、同页跨栏、三页及以上表。各模型预测表须保存可审计的来源页列表；无法追踪来源页时不能硬算跨页误合并率，应标记该项不可评并阻止声明具备完整端到端跨页评测。对额外预测的归类固定为互斥计数，并分别报告跨页真值覆盖与无关表格误连；不得把仅对真实正例评的分数称为 precision。

### 2.2 补集：OCRFlux 的合成 HTML 拼接样本

`ChatDOC/OCRFlux-pubtabnet-cross` 提供 `table_fragment_1`、`table_fragment_2`、`gt_table` 等 HTML 字段。下载后的归档还提供 `image_name` 对应的**原始完整表格图像**，不是两个自然跨页页面图像；两个 fragment 是从原始表格 HTML 构造出的拆分片段。因此该集可以直接做“已识别 HTML -> 完整 HTML”的**外部纯拼接测试**，不能把同一张完整表图当成两张页面图输入 OCR 模型，否则会绕过分页/识别问题并造成任务错位。OCRFlux-3B 可使用其官方 HTML 合并接口；MinerU-Popo 只有在确认输入/输出能无损映射这些 HTML 片段时才增加适配实验。dots.ocr 和 PaddleOCR-VL-1.5 不在该集上做主图像比较；把 HTML 渲染成两张合成页面图属于另一个实验，不能与 PubTables-v2 主结果合并。

先核对外部数据 revision、许可、字段、样本来源和官方 benchmark/train/validation 命名。**文件叫 `train` 不等于可用于调参**：若用它做报告分数，整套 benchmark 在提示词/规则确定前封存；另用非重叠开发数据调试，并审计源表重复或潜在预训练重合。无法审计时明确标记“官方公开集上的参考分数，独立性待核验”。该数据不与 PubTables-v2 指标合成一个总分。

## 3. 四模型的固定输入与输出契约

| 模型/方案 | 主集输入和运行模式 | 输出与评测前提 | 定位 |
| --- | --- | --- | --- |
| OCRFlux-3B | 文档页图像按原页序输入其官方页面解析/跨页检测与 HTML 合并管线；如仅接受 PDF，可将页面图像**无文字层**地打包成新的派生 PDF，并校验页序、尺寸及渲染内容；不得注入真值或 PDF word | 完整表 HTML；记录解析失败、表格边界和来源页；额外在 OCRFlux HTML 数据上测纯合并 | `image-only` 端到端 + 单独的纯 HTML 拼接 |
| MinerU-Popo | 不直接处理原始页面：以**固定 dots.ocr 页级输出**为主要上游，再提供相邻表格、标题及边界行输入；可另以固定 PaddleOCR 页级输出做敏感性分析，但不得混合入主结果 | 保存它的续接/逐列 merge 判断及组合后的表；原生局部指标只在有审计标签时报告；从输出重建整表若不能可靠实现，标记为“仅局部指标”，不编造整表分数 | 固定上游条件下的后处理，标为 `image-only + fixed parser` |
| dots.ocr | 全文档每页图像；保存逐页输出；先报告“无合并”，再接**固定的非真值**续接判断 + 列数门控 + 纵向拼接作为最小跨页 baseline | 逐页表 HTML 与合并表 HTML；续接器若无已发布权重，应独立训练/规则实现并标明“项目复现”，禁止称为官方 checkpoint | `image-only` 页面基线 + 项目合并基线 |
| PaddleOCR-VL-1.5 | 全文档图像；显式固定 `pipeline_version="v1.5"`，使用官方 `restructure_pages(..., merge_tables=True)`；同时保存关闭合并的对照 | 官方重组结果及原始页级结果；核对确实执行 table merge、页序、结构化输出及版本依赖 | `image-only` 官方工程合并基线 |

必须固定并记录每个模型的 repo/weight revision、许可证、推理参数、原始输出、代码 commit、可用的后处理版本。以上是**拟实施**接口：模型与数据格式的全链路适配、OCRFlux 的图像输入方式及 MinerU-Popo 整表重建接口仍须通过小样本 smoke 核验。不同模型有不同上游时不能把分数差直接解释成“跨页模块更强”。不使用 PubTables-v2 PDF 原生文字注入 image-only 输入；若另做 PDF-text-assisted，单独建表、单独评分。

## 4. 两种实验轨道与指标

**A. 真实文档端到端（主轨道）。**不使用真值筛页/真值续接/真值裁剪；四种方案覆盖相同的 val 文档全集，按模型固定输入比较 cross-page-only 与 full-document 结果。MinerU-Popo 必须报告其固定 dots.ocr 上游的 `dots.ocr + simple merge`、`dots.ocr + MinerU-Popo` 的 paired 差异，不能和另一个模型的端到端分数归因比较。

**B. 已知片段后处理（诊断轨道）。**在 train/val 文档上构建来源可追踪的自然分页、人工审计片段集，向后处理器提供同一组固定页级预测（可另做标记明确的 oracle GT 片段上界）；对负例额外评续接。不得将真值片段/真值表内容喂给主轨道。OCRFlux 合成 HTML 数据形成 B 的**独立外部子任务**，不能与真实分页片段混算。

各轨道报告：样本数与来源文档数、推理覆盖、异常与非法 HTML；跨页表 `GriTS-Top/Con`、`TEDS-S/TEDS`（官方实现或协议一致的固定实现可用时）、结构/内容 exact match；续接 P/R/F1 和误连单页表率另列。定义跨页 exact match 的汇总分母为**所有跨页真值表**，不能只取成功生成的表；paired 方法差异以文档为单位进行固定种子的重采样区间估计，避免把同文档多张表当独立样本。对重复表头、列数不等、拆分行/单元格、跨 3 页以上等仅使用人工审计或置信度标注分层；未审计派生关系不得称官方真值。所有阈值/归一化及空预测规则先在 train 设计、val 核验，test 前冻结；val smoke 仅检查接口、覆盖和资源，不据样例调整提示词或合并规则。

## 5. 资源快照与 GPU 调度门禁

2026-09-29 09:03 UTC 的**只读瞬时快照**（`nvidia-smi --query-gpu=...` 与 compute-apps 查询；未探查进程身份、未终止进程）：

| GPU | 型号 | 总显存 | 已占 | 空余 | 利用率 |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | A100-SXM4-80GB | 81920 MiB | 32302 MiB | 48737 MiB | 0% |
| 1 | A100-SXM4-80GB | 81920 MiB | 80615 MiB | 423 MiB | 0% |
| 2 | A100-SXM4-80GB | 81920 MiB | 63788 MiB | 17251 MiB | 0% |
| 3 | A100-SXM4-80GB | 81920 MiB | 69720 MiB | 11319 MiB | 100% |

四张卡均存在已有 compute 进程，**0% 利用率不表示 GPU 空闲或可抢占**。磁盘挂载层面 `df -h .` 当时显示约 34T 可用，这是共享文件系统余量，**不是项目配额保证**。不根据显存快照估算任何模型一定可以运行，不为抢算力终止/修改他人任务。

GPU 执行按以下门禁顺序：

1. 先只读核对权重大小、许可证、软件依赖、CUDA/推理后端与模型官方显存要求，估计每个新增模型的磁盘占用和输出体积；权重只下载到 `models/` 新目录，外部数据分别保存归档/解压/版本清单，原始数据不覆盖。OCRFlux 官方 README 的显存建议是运行前参考，不能代替实测峰值。
2. 每次启动前重新执行只读 `nvidia-smi` 查询空余、利用率和 compute-apps；核对是否与现有任务共享、是否有经确认的空闲窗口。若无法确认资源归属或会影响已有任务，**暂停 GPU 阶段**，仅执行 CPU 侧审计/评分；需要的话先与资源管理者协调。
3. 每模型先在**单张已确认可用 GPU**上跑完整文档的 1--3 篇 smoke（含 2+ 页跨页表、无表页、困难负例）。记录实测 `peak_allocated`/`nvidia-smi` 峰值、时延、异常和平均预测输出大小；运行中监控外部显存变化。下一轮须满足“启动时可用显存 >= smoke 实测峰值的 1.3 倍 + 8 GiB”且低于设备总量，并有独占/明确同意的共享窗口；阈值是调度**保守策略**，不是模型固有显存需求。不满足就延后、减小 batch/上下文并**重新 smoke**，不自动多卡抢占。
4. 默认**单卡、单模型、单文档或单小批次**串行推进；先复用已保存的 dots.ocr 页级预测做适配 smoke，但其旧筛页运行不得充当严格全页主结果。按照“CPU 样本/评测审计 -> dots.ocr 固定页级全量 -> MinerU-Popo 后处理 -> PaddleOCR-VL-1.5 -> OCRFlux-3B”分阶段投入；最终先全页覆盖，再离线评分。若 GPU 排队较久，CPU 可先实现及测试跨页评分器和 HTML-only 外部数据检查，绝不把部分结果写成完成。
5. 使用稳定文档级分片、每页唯一 key、每个模型独立 UTC 时间戳目录及追加式终止状态记录；重启只补缺失样本，不覆盖预测、日志或已有指标。单样本失败进入 failures，整批覆盖要有 missing/extra/duplicate=0 的清单核验（失败条目也计一次终态）。记录 walltime、吞吐、峰值显存、显卡占用、失败率和额外存储；共享资源突变、OOM、持续影响其他任务或磁盘配额不足时停止新分片、保留产物并回退到 CPU 分析。

不启动训练：关系样本、派生标签审计、泄漏检查和最小规则基线未完成前，不开展大规模微调。任何“续接 ViT”若需自训，应待前述门禁通过后另立训练设计，不能把它隐藏在本次四模型推理实验里。

## 6. 操作手册：按顺序执行，不跳过验收

阶段 0 的 PubTables-v2 validation 审计已完成（证据见 6.3 节）；其余步骤仍为**计划中的服务器操作**，尚未执行下载或推理。工作目录始终为 `/data01/public/zhengguojie/paper`，所有环境、代码、缓存、下载和输出均在该目录内。示例中的 `*_REV`、`RUN_ID` 和 `GPU_ID` 必须在运行当天依据只读审计结果赋值；未提供提交哈希/缺失脚本的步骤不可直接运行。先在仓库内改代码和测试，再执行新的服务器阶段；不要把下面的计划命令写进历史实验记录的“已执行命令”。

### 6.1 步骤 0：确认现有文件与下载缺口（CPU、只读）

| 对象 | 当前项目内状态 | 下一步 |
| --- | --- | --- |
| PubTables-v2 `Full Documents/{train,val,test}` | 已下载并解压；revision 见首段；`val` 全页 manifest 已在 `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl` | **不重下**，核查 revision、各类文件数量和 manifest hash；test 标签不用于设计 |
| dots.ocr | 已有 `checkpoints/dots-ocr`，记录在 `artifacts/model-manifests/dots-ocr.json`，resolved revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951` | **不重下**，先核对清单及实际权重一致性 |
| OCRFlux-3B | 项目内未找到已保存的权重和该项目完整管线 | 新增 `ChatDOC/OCRFlux-3B` 权重及官方代码（代码固定 commit），不下载 `Qwen2.5-VL-3B-Instruct` 来冒充 OCRFlux |
| MinerU-Popo | 项目内未找到权重与官方代码 | 新增 `DreamEternal/MinerU-Popo` 权重及 `opendatalab/MinerU-Popo` 源码（固定 commit） |
| PaddleOCR-VL-1.5 | 项目内未找到完整权重/管线 | 新增 `PaddlePaddle/PaddleOCR-VL-1.5` 权重，**还需**版本固定的 PaddleOCR/PaddleX 管线和其实际调用的版面检测等模型；逐项记录自动下载文件名/路径；仅 VLM 权重不足以运行全页合并 |
| OCRFlux HTML 外部数据 | 项目内未找到 | 新增 `ChatDOC/OCRFlux-pubtabnet-cross` 公开数据；该集约 9,064 条、官方页面约 217 MB，仅 `train` 命名的 split，用作封存的外部 benchmark，不能以 split 名称作调参许可 |

现阶段**不需要**额外下载 PubTables-v2 `Cropped Tables`、PDF 原件、PubTabNet、POTATR 或 ViT continuation checkpoint；若之后做 PDF-text-assisted、额外上游或自训 ViT，应单独变更协议。执行前先检查目录是否已存在并记录，禁止对现有数据、模型、日志使用 `--force-download`、`--delete`、覆盖式解压或重名输出。下面只读命令可作为实际操作起点：

```bash
cd /data01/public/zhengguojie/paper
git rev-parse HEAD
git status --short
df -h .
test -d 'data/pubtables-v2/extracted/Full Documents/val/images'
test -d 'data/pubtables-v2/extracted/Full Documents/val/tables'
test -d checkpoints/dots-ocr
test -f artifacts/model-manifests/dots-ocr.json
sha256sum artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=gpu_uuid,pid,used_gpu_memory --format=csv,noheader
```

**验收**：完整页 manifest 应与既有 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd` 一致；现有真值、模型 hash 不一致时停下并补勘误，不能覆盖后再宣称通过。磁盘 `df` 是共享文件系统容量，不代表写入配额；先查询项目可用配额/联系管理员，确认新增权重、缓存、派生 PDF 和结果占用上限。

### 6.2 步骤 1：取得固定版本的公开代码、模型与 HTML 数据（网络、CPU、只新增文件）

下载前先通过**官方** GitHub/Hugging Face 模型卡分别确认许可证、默认分支的 resolved commit、文件列表与大小、Paddle 所需额外权重；用 manifest 保存每个原始 repo ID、resolved SHA、文件字节数、取得时间和来源。在能访问官方 Hub 的项目内环境可用 `HfApi().model_info(repo_id, files_metadata=True)` / `dataset_info(repo_id, files_metadata=True)` 查询各目标的 `sha` 和文件大小；与镜像返回的同一 repo ID/sha 交叉检查，不能只记录 `main`。先查存储预算，再逐个下载，避免重复存放在多个缓存和 local-dir。任何 revision 变量未核验或目标目录已存在则中止。当前项目现有 `scripts/download_models.py` 只支持 TATR、dots.ocr、Qwen 基座，**不能**用 `--models all` 当作四模型下载器，也不能默认它会下载 OCRFlux 等模型。

可采用已在项目使用的 `huggingface_hub` CLI；以下是**版本经官方核实、路径确认全新后**才能执行的命令模板，不预设最新 commit 值：

```bash
cd /data01/public/zhengguojie/paper
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-cross-page-four-model"
unset HF_TOKEN HUGGING_FACE_HUB_TOKEN
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export HF_HOME="$PWD/artifacts/cache/hf-public-${RUN_ID:?set_new_utc_run_id}"
export XDG_CACHE_HOME="$PWD/artifacts/cache/xdg-${RUN_ID}"
export TMPDIR="$PWD/artifacts/tmp-${RUN_ID}"
mkdir -p "$HF_HOME" "$XDG_CACHE_HOME" "$TMPDIR"
# OCRFLUX_REV / POPO_REV / PADDLE_REV / OCRFLUX_DATA_REV:
# 先从官方仓库元信息独立核对并填入准确 40 位 SHA，不能用 main。
test ! -e "models/ocrflux-3b-${OCRFLUX_REV:?set_official_sha}"
.venvs/eval312/bin/hf download ChatDOC/OCRFlux-3B --revision "$OCRFLUX_REV" --local-dir "models/ocrflux-3b-$OCRFLUX_REV"
test ! -e "models/mineru-popo-${POPO_REV:?set_official_sha}"
.venvs/eval312/bin/hf download DreamEternal/MinerU-Popo --revision "$POPO_REV" --local-dir "models/mineru-popo-$POPO_REV"
test ! -e "models/paddleocr-vl-1.5-${PADDLE_REV:?set_official_sha}"
.venvs/eval312/bin/hf download PaddlePaddle/PaddleOCR-VL-1.5 --revision "$PADDLE_REV" --local-dir "models/paddleocr-vl-1.5-$PADDLE_REV"
test ! -e "data/external/ocrflux-pubtabnet-cross-${OCRFLUX_DATA_REV:?set_official_sha}"
.venvs/eval312/bin/hf download ChatDOC/OCRFlux-pubtabnet-cross --repo-type dataset --revision "$OCRFLUX_DATA_REV" --local-dir "data/external/ocrflux-pubtabnet-cross-$OCRFLUX_DATA_REV"
```

镜像策略：优先官方 `huggingface.co`、官方 GitHub 与 Paddle 官方模型源；若官方 Hub 在服务器不可达，可**只对公开模型/公开数据**临时设置 `HF_ENDPOINT=https://hf-mirror.com` 重跑**同一已核验 SHA** 的下载（已有 2026-09-21 项目记录曾使用该镜像）。镜像是第三方传输通道，不是官方来源：不登录、不发送 token、私有凭证或内部未公开文件，不上传 PubTables-v2 原始页面；独立比较官方 repo metadata/哈希或可信发布信息，保存下载后 SHA-256 和 endpoint。镜像无法独立核验版本或内容时停下，标记来源待核验，不把镜像 SHA 伪称官方 SHA。Paddle 管线组件可能另走 Paddle 官方 BOS；若选择 `PADDLE_PDX_MODEL_SOURCE=BOS`，记录来源与下载列表，并**在加载 Paddle 模块之前**固定 `PADDLE_PDX_CACHE_HOME="$PWD/artifacts/cache/paddlex-$RUN_ID"` 到项目内新目录，**该设置不由 HF_ENDPOINT 代替**。先用隔离环境做禁仓库外写入/禁额外下载 smoke；无法重定向的写入路径应停下并改用显式 `*_model_dir`。代码安装依赖另用项目内新的 `.venvs/ocrflux-${RUN_ID}`、`.venvs/popo-${RUN_ID}`、`.venvs/paddle-${RUN_ID}`，不要在已验证的 `.venvs/eval312` 中混装 Paddle、vLLM 或升级 transformers。操作系统缺包时先核查条件，不用 sudo 改服务器系统目录；需要管理员支持则暂停相应模型。

OCRFlux/Popo 官方源码分别克隆至新的 `third_party/ocrflux-${RUN_ID}`、`third_party/mineru-popo-${RUN_ID}`，记录实际 Git commit 和许可；安装前只读审计 `requirements`、启动脚本、远程调用、自动下载和所有默认输出路径，改配置使缓存/输出只在项目内。**不直接执行**官方 Docker `--gpus all`、`--network host`、需要云端 `qwen_generate`/`gpt_generate` 的 enrichment 流程。默认仅执行本地跨页表格相关推理，不发数据到外部 API。保存各模型完整文件清单与 `sha256sum` 清单、权重格式和 run manifest；下载不使用 GPU，不触碰已下载 PubTables-v2。

### 6.3 步骤 2：建立严格输入与真值清单（CPU、只读原始数据；已完成）

已有 `scripts/build_validation_manifest.py` 可直接重建/复核全页输入，**输出必须是新文件**：

```bash
cd /data01/public/zhengguojie/paper
PYTHONPATH=src .venvs/eval312/bin/python scripts/build_validation_manifest.py \
  --images 'data/pubtables-v2/extracted/Full Documents/val/images' \
  --collection full_documents \
  --expected-count 13871 \
  --output "artifacts/input-manifests/${RUN_ID:?set_new_utc_run_id}/full-documents-val.jsonl"
sha256sum "artifacts/input-manifests/$RUN_ID/full-documents-val.jsonl"
```

**以下功能目前没有项目现成命令，必须先在 `scripts/` 实现并写 `tests/`，不能把示意调用当已可运行：**新增 `build_cross_page_manifest.py` 接收 split `val` 的 `tables/*.json`、`cross_page_table_pairs/*.json` 及全页 manifest；输出 `artifacts/cross-page-manifests/<run-id>/gold-cross-page.jsonl`（文档/逻辑表/所有 part 的页号、bbox、完整 HTML）、`negative-page-pairs.jsonl`、错误清单和清单 hash。同一表跨至少 2 个不同页才标为真实跨页；官方 page-pair 的 label 只用于续接诊断，不作为列对应 GT。另只在 train 构造非重叠的调试案例。对 `val` 的文档集、总页清单、跨页逻辑表/part 一一关联、同页跨栏排除、无表页和官方正负页对做可复核计数，不预写尚未统计的表数。

OCRFlux 补集要单独编写 `audit_ocrflux_cross_dataset.py`：读取下载的**原生 JSON/数据集格式**（不要用正则切 HTML），核对 `table_fragment_1/2`、`gt_table`、`image_name/type`、重复 ID、空 HTML、simple/complex 数与源表去重；只从代码隔离的**非报告用 train 开发样本**调接口，封存该官方 9,064 样本集为报告用补集，不拿来调提示词。

PubTables-v2 validation 的这一阶段已于 2026-09-29 完成：新增 `scripts/build_cross_page_manifest.py` 与 `tests/test_build_cross_page_manifest.py`；审计记录 `docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md`，固定产物在 `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/`。实际获得 983 张跨不同页的逻辑表、1,276/786 个官方正/负页面对、0 项相邻关系冲突、1 项非相邻片段间隙。OCRFlux 外部数据的审计**尚未开始**，不要将此处“已完成”扩展到它。

### 6.4 步骤 3：准备各模型实际输入（CPU、派生目录）

1. **dots.ocr**：直接用 val 全页清单和原始 `images/`；逐页预测 JSONL 必须保留 `image_id/document_id/page_number`，再由新脚本生成同一文档的页序与来源页。旧的 3,522 个真值筛页历史结果不得作正式全页输出。为后处理将 dots 的表格 HTML、bbox（如原始输出提供）与前后页相邻上下文映射到 Popo 官方标准 schema；字段不存在标记 `unknown`，不从 GT 填补。
2. **OCRFlux-3B**：原始数据只给 JPEG 页图像，不给 PDF 原件。先实现 `scripts/pack_pubtables_document_images.py`：按 manifest 的文档 ID、整数页号从 0 顺序把**全部原图**各封入单独一页的无 OCR/无文字层 PDF，写入 `artifacts/derived-page-pdfs/<run-id>/<document-id>.pdf`。用只读回渲/页数校验记录页数、尺寸/方向、每页来源 JPG 的 SHA-256 和序号映射；实际模型画面因 JPEG->PDF->渲染链路可能改变，要单独留审计图。派生 PDF 不是原始 PubTables-v2 PDF，不允许混称 PDF-text-assisted。逐文档投送 OCRFlux 的 `pdf2markdown` 默认跨页合并与 `--skip_cross_page_merge` 对照；保留 `page_texts`、`document_text` 与 `fallback_pages`。若 Markdown 没有可无歧义转换的整表 HTML/网格，或无法可靠推断来源页，停止该模型的 cross-page-only `Acc-Con`，不得用 GT 补充或伪造指标。
3. **PaddleOCR-VL-1.5**：复用上述**无文字层派生 PDF**（便于 `predict(pdf)` 与 `restructure_pages` 保留页序）；单独保存 `pages_res` 及 `merge_tables=False/True` 两路重组结果。固定 `pipeline_version="v1.5"`、关闭非必要方向/扭曲/标题处理或记录其状态；`layout_detection_model_dir`、`vl_rec_model_dir` 和其他实际加载组件路径显式固定至新模型目录，缺组件按官方版本下载后核对。不得仅 `pipeline.predict` 就声明跨页合并。保留生成表的各来源页；若官方结果不提供，须从保存的原始 page-level 结果建立可审计关联。
4. **MinerU-Popo**：只接收上一步保存的固定 dots.ocr 全页**预测**（不可掺入 GT）；实施字段转换、页顺序和结构一致性断言后，调用官方 `run_label_normalization.sh`、`run_inference.sh`、`build_tree.sh` 所需的本地表格任务部分，改造配置使 `POPO_MODEL_PATH` 指向固定权重、所有输出重定向至带 run-id 目录。默认不启用云端 Qwen/GPT enrichment。保存转换前后 JSON、丢字段清单、逐列判断、合并表结构和错误；如果 tree 不能稳定导出规范完整表，只报告其可核验的局部输出，不与整表 `Acc-Con` 混榜。

5. **非真值续接 + 简单拼接的对照**：针对每文档相邻两页的“前页最后一张表/后页第一张表”，在 train 上固定版面距离、列数和表头相似度的续接规则/阈值；只在判续接且列数一致时做纵向拼接。保留“不合并”和“仅已知续接（oracle，单独标记）”上界；不能把官方 `cross_page_table_pairs` 的 label 当作主轨道预测输入。若无法形成能在负例上检验的非真值续接器，本轮只报告无合并页级结果，简单拼接的端到端成绩标为未完成。

### 6.5 步骤 4：先跑 train 接口检查，再跑 val smoke（单卡、需 GPU 门禁）

先用 train 小样本检查转换逻辑、提示词、合并规则；选出包含 2 页续表、3 页续表、同页跨栏、负例、无表页的**整文档**案例固定 smoke manifest。val smoke 只检验算力/异常/可解析率，不针对其真值调提示词。启动前重复 6.1 的 `nvidia-smi` 查询，确认任务窗口并测显存；OCRFlux 官方建议 >24 GB 显存且其 vLLM 默认 `gpu_memory_utilization=0.8`，在共享卡上须调低并先验证，不允许按整卡默认比例预留或自动 tensor parallel 占其他 GPU。Popo 官方 Docker `--gpus=all` 不用；Paddle 与其他模型用独立环境，禁止加载意料之外的额外预训练模型。

**现在可直接调用的现有脚本**是 dots.ocr 页面推理；其输入清单是整页清单，输出必须指向新路径，且 `--limit` **仅供 smoke**。示例运行前仍须完成上面的资源核验及目录唯一性检查：

```bash
cd /data01/public/zhengguojie/paper
export CUDA_VISIBLE_DEVICES="${GPU_ID:?set_confirmed_available_gpu}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
PYTHONPATH=src .venvs/eval312/bin/python scripts/evaluate_dotsocr_pubtables_v2.py \
  --model checkpoints/dots-ocr \
  --images 'data/pubtables-v2/extracted/Full Documents/val/images' \
  --manifest "artifacts/input-manifests/$RUN_ID/full-documents-val.jsonl" \
  --output "outputs/cross-page/dots-ocr/$RUN_ID/smoke-predictions.jsonl" \
  --limit 3
```

**注意**：上例清单前 3 页不保证包含跨页正例，正式 smoke 应先创建经审计的完整文档子清单再指向它；上例只是接口/显存探测命令。OCRFlux 官方实际可用入口是 `python -m ocrflux.pipeline WORKSPACE --data DOCUMENT.pdf --model MODEL_DIR`（默认合并）及 `--skip_cross_page_merge` 对照；但固定目录/环境与 PDF 派生器未实现前不可运行。Paddle 使用官方 `PaddleOCRVL(pipeline_version="v1.5") -> predict(pdf) -> restructure_pages(pages_res, merge_tables=True)`；Popo 使用其仓库三个 bash 阶段。上述三者的**项目统一 CLI adapter 均待实现**，不能写出伪造的 `scripts/run_*.py` 当现成命令。实现时四个 adapter 应统一支持 `--model-dir`、`--manifest`、`--images` 或 `--derived-pdfs`、`--output-dir`、`--resume-from`，且输出终态 JSONL 必含 `document_id`、`page_number`、`source_pages`、`status`、`tables_html`、`raw_output_path` 和错误字段（文档级表在单独的 doc-table JSONL 中）；每个 adapter 通过 smoke 产出相同的逐页终态、文档表、来源页、HTML validity 后，才允许全量运行。

### 6.6 步骤 5：完整 validation、独立 HTML benchmark、离线复评（GPU/CPU）

先 dots 全 13,871 页运行，`--limit` 去掉；按**文档**拆互斥分片并使用现有 `--resume-from` 恢复机制，每一分片不同新文件；记录 error 条目且不覆盖已有记录。固定 dots 的页面输出之后，分别做简单合并和 MinerU-Popo 结果的 paired 复评。再按可用 GPU 窗口依次执行 Paddle 和 OCRFlux 的全页处理；各模型以文档为单位串行/小批处理，完整保留无表页，校验每文档页数与全部 13,871 页 manifest 一致。外部 OCRFlux HTML 集通过官方 `eval_html_table_merge.py` 的固定版本及可审计 adapter 单独运行，另做简单纵向 HTML 拼接对照；MinerU-Popo 只有接口可无损映射时加入该补集，数据任何样本不得用于本项目阈值优化。所有代码与参数需在 test 前冻结。

**现有** `scripts/score_pubtables_v2_predictions.py` 可用于旧页面级全表离线检查，**尚不支持跨页子集正式评分**；必须新增跨页 scorer、文档级 table provenance 和测试（见 2.1/4 节），按固定实现分别写出 GriTS/TEDS/结构和内容 exact、续接与误合并指标及定义。保存每个模型 `metrics.json`、每真值表的 paired 匹配与失败明细、原始预测、命令/环境/模型/输入清单 hash；完全相同的预测要能在 CPU 上重复评分并得到相同指标，无法复评则不能标记完成。清单覆盖、去重、无表页、漏表、无效 HTML、模型 fallback 和数据来源均有显式计数。

### 6.7 步骤 6：汇总、停止与恢复

任何一个模型未完成全页覆盖，报告表中该模型写“未完成”，可单列分片覆盖但不能冒充 full validation；新模型的下载耗时、大小、来源、镜像、SHA 和许可写入新 `docs/experiments/` 记录。发现 GPU 冲突、额外自动下载、云端 API 调用、原始文件写入、真值泄漏、预测来源页不可审计时停止**新**分片，保留现有目录，不删不挪不覆盖。下次启动只从输入清单求差集，并创建新的追加式日志与预测目录；不能重跑已完成 ID 后覆盖历史结果。

## 7. 分阶段执行表与验收

| 阶段/状态 | 目的、输入与最小操作 | 输出与验收 | 数据下载/原始数据修改/GPU |
| --- | --- | --- | --- |
| 0：已完成（2026-09-29） | train/val 只读核验 `tables.parts`、官方页面对、完整页清单、跨页定义；确认文档级无交叉；用含同页跨栏案例的单元测试验证匹配 | 带 revision/hash 的 val 跨页 GT 清单、负例及全页 manifest；实测结果及异常见 6.3 节与独立审计记录 | 否 / 否 / 否 |
| 1：部分完成（2026-09-29） | 已实现跨页 GriTS/全表 GriTS 离线评分、来源页诊断、dots.ocr `no_merge` 适配器及保守重复表头 `simple_merge` 对照；另外三模型适配器、TEDS/续接指标和许可审计待完成 | 评分器/adapter 测试及旧三页 smoke CPU 离线复评已通过；`simple_merge` 的 train 人工片段仅验结构，val smoke 0 次合并，合成负例能误连，尚无真实 train 正负例指标或四模型完整 validation 得分；证据见 `docs/experiments/2026-09-29-cross-page-offline-scorer.zh-CN.md`、`docs/experiments/2026-09-29-dotsocr-no-merge-document-adapter-smoke.zh-CN.md`、`docs/experiments/2026-09-29-dotsocr-repeated-header-simple-merge-baseline.zh-CN.md` | 否 / 否 / 否 |
| 2：计划中 | 固定 1-3 篇 val 完整文档与非续接负例，4 个模型各做可恢复 smoke；分离 oracle 输入 | 峰值显存与吞吐实测、HTML 有效率、覆盖及接口失败报告；不将 smoke 数字称正式结果 | 缺模型时需下载 / 否 / 资源门禁通过才使用 |
| 3：计划中 | 固定代码及模型 revision；相同 val 全文档输入，分片逐模型推理；另外单独做纯 HTML 拼接实验 | 13,871/13,871 页的终态覆盖，missing/extra/duplicate=0；完整 prediction/metrics/checksum；外部实验单独报告 | 否（除阶段 2 明确补齐） / 否 / 门禁通过才使用；外部 HTML 适配可先用 CPU |
| 4：计划中 | 统计 paired 比较、人工审计错误类型；冻结协议后才做 test | 中文实验记录、按页数/表头/边界错误分层与可比性说明；正式 test 仅最终评估 | 否 / 否 / CPU 复评分，最终推理才用 GPU |

每次运行至少保存：数据/model/代码 revision、赛道、split、页/文档/表 ID manifest 及 SHA-256、完整命令和环境版本、种子（无随机性则注明）、GPU 快照与 peak、开始/结束 UTC 时间、运行状态、预测与失败清单、输出校验和、真值匹配/重复/漏样统计、指标和协议差异。原始输入保持在 `data/` 不原地改动；新生成物放在新的 `artifacts/`、`outputs/`、`logs/` 子目录，长期任务开始/结束均更新进度索引及 `docs/experiments/` 正式记录。第 6 节只有**命令模板**，记录中不得补写尚未实际执行的命令、样本数或指标。

## 8. 停止条件与尚待核验

只要发生真值片段到文档/页 ID 无法一一对应、推理使用了 GT 筛页、test 被用于调参、赛道混淆、公共评测代码与官方指标行为冲突、模型协议/许可无法固定、GPU 与现有进程冲突、无法离线复评、外部数据有未消除的泄漏疑点，即暂停该阶段并保存证据；无法确认的模型标为“未测/不可比”，绝不填零或编造结果。

尤其待核验：PubTables-v2 val 的真实跨页逻辑表数及同页跨栏分布；MinerU-Popo 能否输出完整合并表；OCRFlux 图像到表格的完整本地接口和 HTML 外部集版本/独立性；PaddleOCR-VL-1.5 重组页输入契约及合并后的表来源页；当前跨页评分器与官方文档级匹配/归一化细节。

## 9. 依据

- 项目数据字段及历史结果：`docs/research-handoff-2026-08-26.zh-CN.md`、`docs/2026-09-22-research-progress.zh-CN.md`、`docs/reports/2026-09-25-cross-page-table-fragment-reconstruction-methods-and-results.zh-CN.md`、`src/cptla/data/pubtables_v2.py`、`scripts/build_validation_manifest.py`、`scripts/score_pubtables_v2_predictions.py`。
- PubTables-v2 论文与数据集：<https://arxiv.org/abs/2512.10888>、<https://huggingface.co/datasets/kensho/PubTables-v2>。
- OCRFlux 官方仓库、模型、外部数据：<https://github.com/chatdoc-com/OCRFlux>、<https://huggingface.co/ChatDOC/OCRFlux-3B>、<https://huggingface.co/datasets/ChatDOC/OCRFlux-pubtabnet-cross>。
- MinerU-Popo：<https://github.com/opendatalab/MinerU-Popo>、<https://arxiv.org/abs/2605.24973>。
- dots.ocr 官方仓库：<https://github.com/rednote-hilab/dots.ocr>。
- PaddleOCR-VL 官方管线文档：<https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL.html>。
- Hugging Face `hf download` 与 revision 文档：<https://huggingface.co/docs/huggingface_hub/en/guides/download>；MinerU-Popo 官方下载入口：<https://github.com/opendatalab/MinerU-Popo/blob/master/README.md>；Paddle OCR 官方模型源切换说明：<https://www.paddleocr.ai/main/en/update/update.html>。
- 服务器 2026-09-29 09:03 UTC 的只读 `nvidia-smi` GPU/compute-apps 与 `df -h .` 输出；仅用于资源计划，不作为未来可用性保证。
