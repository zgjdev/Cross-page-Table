# 两个基线模型 validation smoke 记录（2026-09-21）

## 1. 结论

三条 validation smoke 已完成，输入覆盖、真值关联、离线复评一致性和 GPU 显存均已核验。当前结论为“有条件通过”：可以先启动 TATR-v1.1-Pub 的 Cropped Tables 全量 validation；dots.ocr 两条全量运行必须继续使用互斥分片和断点恢复，并结合共享 GPU 的实时空闲量调度。

dots.ocr Cropped 的 4 个刻意困难样本中有 1 个模型输出缺少可用的 table `text`，不是 JSON 修复器或 HTML parser 缺陷。该单例属于已解释的模型输出失败，不构成“未解释的系统性解析失败”，但正式结果必须单列 runner warning，不能只报告 scorer 的 `invalid_table_html=0`。

本报告中的指标均为 smoke 子集指标，不是完整 validation 成绩，不可用于论文结论或与公开榜单直接比较。

## 2. 固定版本与执行环境

- 服务器项目根目录：`/data01/public/zhengguojie/paper`
- 代码 commit：`5d996255a90913b8deb7204b417e78402b3f641e`
- PubTables-v2 revision：`aa575e798cb00a296925e2086addb3e3fd9a1903`
- TATR-v1.1-Pub revision：`372e205368a9b7bd1b9fdcf906c1350999d48939`
- dots.ocr revision：`c0111ce6bc07803dbc267932ffef0ae3a51dc951`
- vendored GriTS 项目 revision：`44951a9ef82c7d2af10bf68e144dd0c698a38200`
- Python：3.12.7
- PyTorch：2.6.0+cu124
- transformers：4.51.0
- CUDA runtime：12.4
- GPU：NVIDIA A100-SXM4-80GB；任务使用逻辑设备 0
- 正式推理环境：项目内 `.venvs/eval312`

所有模型加载均设置 `HF_HUB_OFFLINE=1` 和 `TRANSFORMERS_OFFLINE=1`。run manifest 只记录 `HF_TOKEN` 是否存在；本次三个正式 smoke 均为 `False`，没有保存凭证值。

## 3. 数据下载与审计

Cropped Tables validation 数据直接从服务器通过 `hf-mirror.com` 下载，本地没有数据副本或中转。requested revision 与 resolved revision 均为 `aa575e798cb00a296925e2086addb3e3fd9a1903`。

下载清单：

- `artifacts/data-manifests/20260921T065945Z-cropped-val-download.json`
- images：934,085,674 bytes，SHA-256 `c529c157b99a325cf41d093158b9559a9f199df58ffefdafb4f4a8c5ba7c376e`
- tables：18,111,177 bytes，SHA-256 `eff20be979489b573c0188b25569f177bfad739f632223191afd602f73b9d0c5`
- words：88,229,339 bytes，SHA-256 `7dcf696c77c55ce6df0f8f67d5cc72202b2bd5fe91491352228936c7318cdad6`
- XML：8,635,134 bytes，SHA-256 `ff03ae5ff997c78bda3196aabead9ce308f1e395b2d156a0a4aa22bfe02aa6d8`

四类文件各 13,384 个，按官方 stem 核对后 missing/extra 均为 0。首次下载器把归档自带的 `Cropped Tables/val/...` 前缀再次包在类别目录下，形成冗余嵌套，但文件内容和关联没有损坏。为遵守“不移动、不删除、不覆盖服务器数据”，本次运行直接使用真实叶子目录；下载器已通过 TDD 修正，未来归档统一从数据集 `extracted/` 根解压。

三份全量输入清单及 smoke 子清单位于：

`artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/`

| 清单 | 全量条数 | 全量 SHA-256 | smoke 条数 | smoke SHA-256 |
| --- | ---: | --- | ---: | --- |
| TATR Cropped | 13,384 | `ab669093d57c447429a07c20381dac9a41f437ebf999c1d91844666bec39df70` | 4 | `c7ee7728dd2fd7dd8d530a875b9c809398cd42c3fa2f06b7b0b5bc8af00c899c` |
| dots Cropped | 13,384 | `ab669093d57c447429a07c20381dac9a41f437ebf999c1d91844666bec39df70` | 4 | `c7ee7728dd2fd7dd8d530a875b9c809398cd42c3fa2f06b7b0b5bc8af00c899c` |
| dots Full Documents | 13,871 | `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd` | 3 | `c4d22178526b59384a487bf0274e64c86b6d04312bb0c9fc4476dad7d6afb006` |

## 4. Smoke 样本

Cropped Tables 使用固定规则选择：

| 类型 | ID | 选择依据 |
| --- | --- | --- |
| ordinary | `PMC10177577_table_0` | 33×5，无 span，面积等于无 span 样本中位数 165 |
| long | `PMC10316304_table_0` | 78 行 |
| spanning | `PMC10686515_table_0` | 最大 rowspan×colspan 面积 56 |
| wide | `PMC11206412_table_0` | 34 列 |

Full Documents 使用 `PMC11977379` 全部 3 页。官方 continuation 正例为 page 1→2；表格真值覆盖 page 1、2，page 0 是无表页。推理清单仍完整包含 page 0/1/2，没有使用真值筛掉无表页。

## 5. 项目实测结果

不同输入赛道必须分开解释：TATR 是 PDF-text-assisted；dots.ocr 是 image-only。

| 模型与 collection | track | 覆盖 | GriTS-Top | GriTS-Con | Acc-Top | Acc-Con | runner warnings | inference errors | 预测表数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TATR-v1.1-Pub / Cropped | PDF-text-assisted | 4/4 | 0.48456 | 0.33747 | 0.00 | 0.00 | 0 | 0 | 4 |
| dots.ocr / Cropped | image-only | 4/4 | 0.68224 | 0.40857 | 0.25 | 0.25 | 1 | 0 | 3 |
| dots.ocr / Full Documents | image-only | 3/3 页、1 文档 | 0.81967 | 0.81929 | 0.00 | 0.00 | 0 | 0 | 1 |

三条运行的 missing、extra、duplicate 均为 0；两次离线评分的 metrics 和 failures 均字节完全一致。scorer 报告的 `invalid_table_html=0` 只统计进入评分器的 HTML；dots Cropped 的 1 个无效 table 候选已在推理解析层丢弃，因此必须以 runner warning 补充报告。

Full Documents 结果没有跨页合并。较高的 smoke GriTS 不能表述为跨页恢复效果，且只来自一篇短文档。

## 6. 耗时与显存

| 运行 | 总推理时间 | 中位数 | 最小–最大 | GPU 总占用基线→采样峰值 | 近似增量 |
| --- | ---: | ---: | ---: | ---: | ---: |
| TATR Cropped | 0.678 s | 0.068 s | 0.052–0.490 s | 44,837→45,741 MiB | 904 MiB |
| dots Cropped | 354.665 s | 75.495 s | 1.506–202.169 s | 44,837→54,395 MiB | 9,558 MiB |
| dots Full Documents | 127.528 s | 40.548 s | 35.316–51.664 s | 44,837→61,481 MiB | 16,644 MiB |

GPU 上同时有其他用户进程，上表是每 0.1–0.2 秒外部采样的整卡总占用及相对启动前增量，不是进程独占的精确峰值。Full Documents 全量调度至少应在启动时保留高于 16.6 GiB 的已验证增量，并额外留安全余量。

按 smoke 均值机械外推，TATR Cropped 单卡约 0.6 小时，dots Cropped 单卡约 330 小时，dots Full Documents 单卡约 164 小时。Cropped smoke 刻意选择长、宽、span 困难表，Full smoke 也只有一篇文档，因此这些数字只用于容量规划，不是可靠 ETA。

## 7. 发现并修正的问题

1. 新建评测环境首次依赖安装中止；重跑后主项目和 `pylcs` 安装成功。vendored GriTS 的旧打包配置与新版 `setuptools_scm` 不兼容，正式评测改用固定 `PYTHONPATH=third_party/grits-main`，未修改第三方源码。
2. 官方 Hugging Face 端点从服务器不可达；`hf-mirror.com` 可达。数据仍直接下载到服务器，缓存也限制在项目根内。
3. Cropped 归档路径冗余问题已通过失败测试和修复提交解决；现有服务器数据不移动、不删除。
4. TATR legacy processor 只有 `longest_edge=800`，transformers 4.51 不接受单键配置。根据 Microsoft 固定源码的 `MaxResize(800)` 语义，runner 仅在该 legacy 形式下补同值 `shortest_edge=800`，并固定 `use_fast=False`；checkpoint 未修改。
5. smoke 评分最初错误地把清单外全部真值也纳入评分，导致 4 个样本显示 `units_scored=13384`。已通过失败测试修正为 manifest 定义评分范围，manifest 内缺真值立即报错；旧 metrics 已标记无效，正式路径引用修正后结果。
6. dots.ocr transformers 推理按固定源码在缺少 flash-attn 时回退 eager。日志还有 SDPA sliding-window 兼容提示；模型固定配置 `use_sliding_window=false`，但该提示及与官方 vLLM 0.9.1 环境不等价仍需在最终报告披露。

服务器评测回归最终为 63 项通过，Ruff、`git diff --check` 和工作区清洁检查均通过。

## 8. 证据路径

### TATR Cropped

- run ID：`20260921T075629Z-tatr-cropped-smoke-final`
- run manifest：`artifacts/run-manifests/20260921T075629Z-tatr-cropped-smoke-final.json`
- predictions：`outputs/baselines/tatr-v1.1-pub/20260921T075629Z-tatr-cropped-smoke-final/predictions.jsonl`
- metrics：`outputs/baselines/tatr-v1.1-pub/20260921T075629Z-tatr-cropped-smoke-final/metrics-1.json`
- predictions SHA-256：`235166f46ef94d49df315e38fcd9416f8bc228898c7831633e5e6d142012203c`
- metrics SHA-256：`421f865eae121838579d10e975db86c5965153d4f5242b76e512c4a37f1237f1`

### dots.ocr Cropped

- run ID：`20260921T080303Z-dots-cropped-smoke`
- run manifest：`artifacts/run-manifests/20260921T080303Z-dots-cropped-smoke.json`
- predictions：`outputs/baselines/dots-ocr/20260921T080303Z-dots-cropped-smoke/predictions.jsonl`
- metrics：`outputs/baselines/dots-ocr/20260921T080303Z-dots-cropped-smoke/metrics-1.json`
- predictions SHA-256：`0684f570c6f39d9c4d23ef70ae8b7c3b5d7c8c9b9166e485567bafba1e66df3a`
- metrics SHA-256：`5ee297dfe02cbe19064f8dc8c2671a43e649182a630fe2306e4c396a9b9c30f6`

### dots.ocr Full Documents

- run ID：`20260921T081448Z-dots-full-documents-smoke`
- run manifest：`artifacts/run-manifests/20260921T081448Z-dots-full-documents-smoke.json`
- predictions：`outputs/baselines/dots-ocr/20260921T081448Z-dots-full-documents-smoke/predictions.jsonl`
- metrics：`outputs/baselines/dots-ocr/20260921T081448Z-dots-full-documents-smoke/metrics-1.json`
- predictions SHA-256：`8f3fc49e1eda6950512d28195fd6e73743dddbeb914e8ec4c4d68ce709a9d597`
- metrics SHA-256：`fc527b5e7707df09aa5df5db3f2d4d3c5219e8201e2d38b6113848d8159c057c`

## 9. 下一步

1. 先启动 TATR-v1.1-Pub Cropped Tables 全量 validation，完成 13,384/13,384 覆盖和两次离线复评。
2. dots.ocr Cropped 与 Full Documents 分别建立互斥、可恢复分片；启动每个分片前重新检查 GPU 显存和其他用户进程。
3. dots Full Documents 必须覆盖全部 13,871 页，不按真值筛页。
4. 完整结果分开报告 PDF-text-assisted 与 image-only，不把 TATR 与 dots 分数合并排名。
5. 完整结果明确区分“项目实测”“论文报告”“待核验”，并声明 TATR-v1.1 不等于 v1.2、dots Full Documents 未做跨页合并。
