# 相关模型下载与基线准备指南

更新时间：2026-08-29  
适用项目：PubTables-v2 文档级跨页表格恢复  
项目根目录：`/data01/public/zhengguojie/paper`

## 1. 当前阶段与目的

本阶段的目的不是立即训练新模型，而是准备一组可复现的页面解析和跨页合并基线，用于：

1. 检查 PubTables-v2 样本能否进入各模型的输入流水线；
2. 固定页面提取器，生成后续跨页关系模型需要的页面对象；
3. 复现公开结果的合理量级；
4. 分开建立 `PDF-text-assisted` 和 `image-only` 两条评测赛道。

模型下载不会修改 `data/pubtables-v2/` 下的原始数据。权重统一保存到项目内被 Git 忽略的 `checkpoints/`，下载清单、revision、命令和校验结果保存到 `artifacts/model-manifests/`，运行日志保存到 `logs/models/`。下载本身不使用 GPU；下载后的推理 smoke test 才可能使用 GPU。

这里的“公开效果”指论文或官方评测已经报告的数值。只有本项目保存了命令、日志、预测文件和评测输出后，才能称为“已复现效果”。

## 2. 首批模型选择

| 优先级 | 模型 | 赛道与作用 | 当前公开状态 | 建议 |
|---|---|---|---|---|
| P0 | TATR-v1.1-Pub | `PDF-text-assisted`；裁剪表结构基线和接口验证 | 官方 Hugging Face 权重已知可用 | 首先下载，体量较小、接口成熟 |
| P0 | dots.ocr | `image-only`；页面解析及简单跨页合并主基线 | 官方代码/模型公开，但下载前仍应核验具体 revision 和模型文件 | 第二个下载，先做少量页面 smoke test |
| P1 | TATR-v1.2-Pub | `PDF-text-assisted`；PubTables-v2 裁剪表强基线 | 调研确认论文结果，具体公开权重仓库仍待核验 | 先查官方制品，不能用 v1.1 冒充 v1.2 |
| P1 | POTATR | `PDF-text-assisted`；最相关的固定页面提取器 | 截至已有调研日期，论文称将发布，但代码和权重未核实 | 暂不下载替代品，定期检查官方发布 |
| P1 | PubTables-v2 ViT-B/16 continuation classifier | 官方续表分类与直接纵向拼接基线 | 论文报告 `F1=0.991`，具体权重制品待核验 | 权重公开后优先于通用 VLM |
| P2 | OCRFlux-3B | `image-only`；显式跨页表重建对照 | 官方代码公开；模型仓库标识、许可证和运行依赖需现场核验 | P0 流程稳定后再下载 |
| P2 | Qwen2.5-VL-3B-Instruct | `image-only`；同规模通用 VLM 对照 | 官方 Hugging Face 权重公开 | 不是首批页面结构基线，后置 |

首批不下载 Claude、GPT、Gemini：它们是闭源 API 模型，不存在可下载权重。LingDT-VL-OCR、FinDocBench 和 VCCT 当前也没有已核验的公开完整制品，不能写入自动下载清单。

首批推荐顺序是：

```text
TATR-v1.1-Pub
    -> 验证权重下载、输入和结构输出契约
dots.ocr
    -> 验证 image-only 页面输出和可解析率
核验 TATR-v1.2 / POTATR / continuation ViT 是否发布
    -> 决定正式固定页面提取器
OCRFlux-3B 或 Qwen2.5-VL-3B
    -> 补充 image-only 对照
```

## 3. 下载前只读检查

### 3.1 阶段说明

- 目的：确认路径、磁盘空间、Python 环境和 GPU 状态；
- 输入：项目目录和服务器环境；
- 输出：终端检查结果，不生成数据；
- 是否下载：否；
- 是否修改原始数据：否；
- 是否使用 GPU：否，仅查询状态。

在项目根目录执行：

```bash
cd /data01/public/zhengguojie/paper
pwd
du -sh data/pubtables-v2 checkpoints artifacts 2>/dev/null
df -h /data01/public/zhengguojie/paper
python --version
python -c "import huggingface_hub; print(huggingface_hub.__version__)"
nvidia-smi
```

`nvidia-smi` 只用于检查可用显存和已有进程。不得终止其他用户进程，也不得把“能够看到 GPU”解释为“GPU 当前可独占使用”。如果当前 Python 环境没有项目依赖，应先进入项目约定的 `cptla` 环境；不要在不明确环境归属时全局安装包。

### 3.2 下载预算

正式下载前，必须从 Hugging Face 元数据计算仓库文件总量，而不是根据参数量猜测磁盘需求。至少预留“权重总大小的两倍”用于缓存、临时文件和模型加载；生成预测还需要额外空间。

只查询元数据的示例：

```bash
python - <<'PY'
from huggingface_hub import HfApi

repo_ids = [
    "microsoft/table-transformer-structure-recognition-v1.1-pub",
    "rednote-hilab/dots.ocr",
    "Qwen/Qwen2.5-VL-3B-Instruct",
]
api = HfApi()
for repo_id in repo_ids:
    info = api.model_info(repo_id, files_metadata=True)
    total = sum((item.size or 0) for item in info.siblings)
    print(repo_id, info.sha, total, len(info.siblings))
PY
```

预期输出是每个仓库的 resolved SHA、总字节数和文件数。若仓库不存在、需要授权或模型 ID 已变化，应停止该模型的下载并在清单中记为“待核验”，不能凭名称猜测替代仓库。

## 4. 统一下载方法

### 4.1 阶段说明

- 目的：把已核验的官方权重固定到本项目；
- 输入：官方模型仓库 ID 和明确的 commit SHA；
- 输出：`checkpoints/<model>/` 与下载日志；
- 是否下载：是；
- 是否修改原始数据：否；
- 是否使用 GPU：否；
- 预期结果：模型文件完整下载，日志记录仓库、revision 和结束状态。

先创建独立目录：

```bash
cd /data01/public/zhengguojie/paper
mkdir -p checkpoints artifacts/model-manifests logs/models
```

推荐使用 `snapshot_download`，并把上一节查到的 SHA 写入 `revision`。以下命令中的 `<RESOLVED_SHA>` 必须替换为实际 SHA：

```bash
python - <<'PY' 2>&1 | tee logs/models/tatr-v1.1-download.log
from huggingface_hub import snapshot_download

path = snapshot_download(
    repo_id="microsoft/table-transformer-structure-recognition-v1.1-pub",
    revision="<RESOLVED_SHA>",
    local_dir="checkpoints/tatr-v1.1-pub",
)
print(path)
PY
```

```bash
python - <<'PY' 2>&1 | tee logs/models/dots-ocr-download.log
from huggingface_hub import snapshot_download

path = snapshot_download(
    repo_id="rednote-hilab/dots.ocr",
    revision="<RESOLVED_SHA>",
    local_dir="checkpoints/dots-ocr",
)
print(path)
PY
```

不要使用浮动的 `main` 作为正式实验 revision。若网络中断，重新运行相同命令应利用已有缓存续传；不得删除现有模型目录后重下，除非先确认目录只含本次失败下载且得到用户授权。

### 4.2 代码仓库

模型权重和推理代码可能来自不同仓库。正式复现 dots.ocr、OCRFlux 或未来发布的 POTATR 时，还需要记录官方代码仓库的 commit SHA。代码应放到 `third_party/<name>/`，但在写入仓库前应先决定是 Git submodule、普通克隆还是依赖锁定；不要把嵌套 `.git` 和大量第三方源码直接提交到本项目。

建议先只做只读查询：

```bash
git ls-remote https://github.com/rednote-hilab/dots.ocr.git HEAD
git ls-remote https://github.com/chatdoc-com/OCRFlux.git HEAD
```

得到 commit 后，把 URL、commit、许可证和访问日期写入模型清单。POTATR 只能在论文或作者官方页面出现可核验链接后加入。

## 5. 下载校验和清单

每个模型至少记录以下字段：

```json
{
  "model_name": "TATR-v1.1-Pub",
  "provider": "Microsoft",
  "repo_id": "microsoft/table-transformer-structure-recognition-v1.1-pub",
  "resolved_revision": "待实际填写",
  "downloaded_at_utc": "待实际填写",
  "local_path": "checkpoints/tatr-v1.1-pub",
  "track": "PDF-text-assisted",
  "license": "待从固定 revision 模型卡核验",
  "file_count": null,
  "total_bytes": null,
  "smoke_test_status": "not_run"
}
```

下载后执行只读检查：

```bash
find checkpoints/tatr-v1.1-pub -type f | sort
du -sh checkpoints/tatr-v1.1-pub
find checkpoints/dots-ocr -type f | sort
du -sh checkpoints/dots-ocr
```

对于 `.safetensors`，优先使用 safetensors API 检查文件头能否读取；不要为了“校验”而反序列化来源不明的 pickle 权重。记录官方提供的 checksum；若官方没有 checksum，至少保存本地 SHA-256 文件清单：

```bash
find checkpoints/tatr-v1.1-pub -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > artifacts/model-manifests/tatr-v1.1-pub.sha256
```

生成清单属于新增产物，不修改模型或原始数据。

## 6. 下载后的最小验证

不要下载完所有模型后才测试。每下载一个模型，先做以下三层验证：

1. **加载检查：**固定代码 commit 和依赖版本，模型能在 CPU 或单卡上完成加载；
2. **单样本检查：**从 validation 选择一个普通单页表和一个自然跨页正样本，只生成预测，不调规则；
3. **小批检查：**在预先固定的 validation smoke 子集上检查成功率、输出可解析率、耗时和峰值显存。

smoke test 的输出应放在：

```text
outputs/baselines/<model>/<revision>/smoke/
logs/models/<model>-smoke.log
artifacts/model-manifests/<model>.json
```

运行 GPU smoke test 前再次执行 `nvidia-smi`。命令中应记录：数据 revision、模型 revision、代码 commit、Python/torch/CUDA 版本、GPU 型号、随机种子、输入文档 ID 和输出路径。

smoke test 通过不等于复现公开指标。正式评测还需要：

- 使用官方任务输入范围和预处理；
- 使用固定 validation 集，不使用 test 调参；
- 输出 PubTables-v2 官方格式；
- 调用同一版本的官方评测实现；
- 分开报告 `PDF-text-assisted` 与 `image-only`；
- 保存 `Acc_Top`、`Acc_Con`、`GriTS_Top`、`GriTS_Con` 和 TEDS 的原始输出。

## 7. 各模型的实际决策

### 7.1 TATR-v1.1-Pub

该模型适合立即下载，用于验证裁剪表结构识别、对象格式和 PDF token 回填接口。但它不是调研中报告 `Acc-Con=0.6831` 的 TATR-v1.2，不能用 v1.1 的运行结果代替 v1.2 基线。

### 7.2 TATR-v1.2-Pub、POTATR 和 continuation ViT

这三个制品对正式研究最关键，但当前项目文档只证明论文结果存在，没有证明权重已经下载或已公开。下一步应核验 PubTables-v2 论文、数据集仓库、作者官方组织和模型卡。只有找到官方 URL、许可证及固定 revision，才能下载。

如果 POTATR 仍未发布，M0 阶段应明确记录“不可复现的论文参考结果”，同时使用可公开复现的 TATR 页面对象或真值页面片段建立隔离式跨页对齐基线，不能自行实现一个近似模型后仍命名为 POTATR。

### 7.3 dots.ocr

dots.ocr 是首批最重要的 `image-only` 基线。先确认官方 README 要求的 transformers/flash-attention/CUDA 组合，再为它建立独立环境，避免改变 `cptla` 数据处理环境。首轮只运行 validation smoke 子集，不运行完整 test。

### 7.4 OCRFlux-3B 与 Qwen2.5-VL-3B

OCRFlux 更贴近显式跨页重建，但它在 PubTables-v2 上的 `Acc-Con` 仍需重新测量；Qwen 是通用 VLM 对照，不是结构化页面提取器的替代品。二者下载量和运行成本较高，应在 dots.ocr 的评测接口跑通后再决定是否下载。

## 8. 推荐执行批次与停止条件

### 批次 A：最小可复现准备

1. 只读核验 TATR-v1.1 和 dots.ocr 的仓库 metadata、revision、许可证和大小；
2. 用户确认下载预算后下载 TATR-v1.1；
3. 用 validation 的极小样本验证加载与输出契约；
4. 用户确认 dots.ocr 的环境和空间预算后下载并 smoke test。

停止条件：模型仓库无法固定 revision、许可证不允许研究使用、磁盘余量不足，或者官方推理代码无法在当前环境稳定加载。

### 批次 B：最相关官方基线核验

1. 检查 TATR-v1.2、POTATR 和 continuation ViT 是否已有官方权重；
2. 若公开，固定模型与代码 revision 后下载；
3. 先复现单页或 continuation 指标，再接文档级纵向拼接。

停止条件：只有论文数值而没有代码/权重/输入输出契约时，不扩大复现投入，转入真值页面片段上的对齐隔离实验。

### 批次 C：扩展 image-only 对照

在 dots.ocr 流程稳定后，从 OCRFlux-3B 和 Qwen2.5-VL-3B 中优先选择一个。选择依据是许可证、显存、完整文档推理成本、输出可解析率和是否能接入统一评测，而不是只比较论文中的异构指标。

## 9. 与当前数据集构建任务的关系

下载模型可以与官方 continuation 数据集构建并行准备，但不能替代它。当前主线仍是：

```text
构建 train/validation 官方 continuation 样本
-> 泄漏和字段关联检查
-> 派生结构标签与人工审计
-> 固定页面提取器和简单拼接基线
-> 训练跨页关系模型
```

首批模型的价值是尽早验证页面对象和统一评测接口。模型不应读取 test 来选择提示词、阈值、合并规则或超参数。

## 10. 证据状态

- **已提供：**项目已有调研将 TATR/POTATR、dots.ocr、ViT 续接分类器列为最相关基线，并给出论文报告指标；PubTables-v2 数据已经下载和标准化。
- **推断：**先用 TATR-v1.1 验证接口、再用 dots.ocr 建立 image-only 流程，是当前成本和复现风险较低的下载顺序。
- **待核验：**TATR-v1.2、POTATR、PubTables-v2 continuation ViT 的官方权重地址与许可证；dots.ocr 和 OCRFlux 当前模型仓库的精确 revision、大小及服务器兼容性。

主要项目依据：

- `docs/research-handoff-2026-08-26.zh-CN.md`
- `docs/table-extraction-research-execution-plan.md`
- `docs/reports/cross-page-table-core-findings.zh-CN.md`
- `docs/reports/cross-page-table-sota.zh-CN.md`
- `docs/reports/novelty-gate.zh-CN.md`
