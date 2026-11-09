# PaddleOCR-VL-1.5 独立环境与 train smoke

日期：2026-10-23（Asia/Shanghai；运行时刻使用 UTC）。状态：准备独立环境与补充版面权重，尚未执行模型推理。

本阶段目的：验证完整 v1.5 页面管线、跨页合并接口、输出来源页以及共享 GPU 峰值。模型主权重已经完成，不再下载。计划仅在 train 整文档做小规模检查，不使用 val/test 调规则；主数据 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`、赛道 image-only。原始页面只读，新产物使用独立目录。

## 固定版本与来源

- PaddleOCR `3.4.0`（官方 tag 源码明确提供 `pipeline_version="v1.5"` 和 `restructure_pages`）；PaddleX `3.4.1`（PyPI 依赖与 v1.5 pipeline yaml 已核对）；NumPy `1.26.4`。
- Paddle GPU `3.2.1`、Python 3.12、官方 cu118 wheel；服务器驱动 `550.127.08`。官方 cu118 index 确认存在对应 cp312/linux_x86_64 构建。此选择待实际导入与 smoke 验证，不能凭安装成功宣称 GPU 可用。
- VLM 本地路径 `models/20261023T064109Z-public-models/paddleocr-vl-1.5/`，revision `2a4195faa5e7914c12f2fc601d72c81caf8d2da5`。
- 必要版面组件 PP-DocLayoutV3，官方 repo `PaddlePaddle/PP-DocLayoutV3`，resolved SHA `241f8bdfc77a7c7bee915a5057aaee58c235a8d3`；四文件约 132 MB，官方清单 `configs/paddle-layout-download-2026-10-23.json`，其中 `inference.pdiparams` SHA-256 `70bd316b0582769ec968829fd1feb1a6a58b7c941b938327e551b6b12b45c137`。
- 官方来源：<https://github.com/PaddlePaddle/PaddleOCR/blob/v3.4.0/paddleocr/_pipelines/paddleocr_vl.py>、<https://github.com/PaddlePaddle/PaddleX/blob/v3.4.1/paddlex/configs/pipelines/PaddleOCR-VL-1.5.yaml>、<https://pypi.org/project/paddleocr/3.4.0/>、<https://pypi.org/project/paddlex/3.4.1/>、<https://www.paddlepaddle.org.cn/packages/stable/cu118/paddlepaddle-gpu/>。

安装入口 `scripts/setup_paddle_v15.sh`，任务 `20261023T081029Z-paddle-v15`，新环境 `.venvs/paddle-v15-20261023T081029Z-paddle-v15/`，日志 `logs/paddle-setup/20261023T081029Z-paddle-v15/`。只安装依赖，无 GPU/数据集操作；TMP/pip-cache 均在新日志目录内，不修改 eval312/dots 环境。命令：`bash scripts/setup_paddle_v15.sh 20261023T081029Z-paddle-v15`。完成条件为 pip check 通过、freeze 与 setup-complete.json 写出；不等同于推理通过。

组件下载复用经测试的 `scripts/download_public_models.py --manifest configs/paddle-layout-download-2026-10-23.json --run-id 20261023T081029Z-paddle-layout`；新路径 `models/20261023T081029Z-paddle-layout/pp-doclayoutv3/` 与 `logs/model-downloads/20261023T081029Z-paddle-layout/`。直接下载服务器；固定源 SHA，逐文件大小/哈希检验。不覆盖现有模型/数据/日志。

CPU 源码审计确认 PaddleX `PADDLE_PDX_CACHE_HOME` 可重定向缓存，native 模型加载支持显式目录。实际导入前必须设置项目内的 PaddleX/HF/ModelScope/TMP 缓存，并显式提供 VLM 与版面组件路径；关闭方向与去畸变组件，避免额外隐式模型下载。原生图像文字仍来自 VLM，不读取 PDF words。

启动前只读 GPU 快照：GPU 0/1/2/3 空余 39,607/423/25,343/22,761 MiB，全部存在其他计算进程。当前只执行安装/下载；执行真实 smoke 前须再次核查，不把此快照当独占保证。后台安装与组件下载的实际 PID、日志和结束状态将在启动后追加。

## 后台启动与输入准备检查点

- 已提供：2026-10-23 08:10 UTC 启动用户级 `paper-paddle-setup-20261023T081029Z.service`（初始 PID `330647`）和 `paper-paddle-layout-20261023T081029Z.service`（初始 PID `330651`）。launcher 日志分别为 `logs/paddle-launchers/20261023T081029Z/setup.log`、`layout.log`，安装脚本 commit `b22bc29`。安装仍运行，已开始下载 Paddle/CUDA wheel；不等于安装成功。
- 已提供：组件下载在 **08:14:43 UTC** `end status=0`，unit `inactive/dead`、退出码 0；四文件均由下载器大小/哈希验证通过。证据 `logs/model-downloads/20261023T081029Z-paddle-layout/{events.jsonl,summary.json}`。无需重复下载。
- 输入计划：train 文档 `PMC10235804`、`PMC10311686`，各三页（0、1、2），包括无表页；train 表标签只用于选择小规模跨页烟雾案例（各有 page 1、2 片段），不作为推理输入、不据此裁图。没有查看 val/test 结果选规则。
- 新脚本 `scripts/pack_pubtables_document_images.py` 只读取 `data/pubtables-v2/extracted/Full Documents/train/images/` 的上述完整文档图片，输出新 image-only PDF、页清单和来源 SHA 映射。PDF 页面为原图像素尺寸的一半（points），匹配官方 PDFReader 默认 scale=2；每页无文字层且嵌入 JPEG 字节与原图相同，保持 image-only 赛道。PDF 派生不会修改原图，不使用 GPU。
- 本地打包/下载器合计 10 测试通过（自建新 basetemp）；包含页序、缺页拒绝、已有目录拒绝及原字节/空文字层检查。服务器打包与 GPU smoke 尚未执行；实际输出、推理耗时、峰值、错误和正式指标均待核验。smoke 不是正式 val 分数。

## 整文档输入已完成，smoke 入口就绪

上段“服务器打包尚未执行”是历史检查点：代码 `e7e5418` 在服务器运行打包/下载器 10 测试通过，并生成 `artifacts/paddle-smoke/20261023T081900Z-train-inputs/`，**2 文档/6 页**，`packing-manifest.json` 保存每页来源及 SHA、PDF SHA、空文字层和 JPEG 字节一致性审计。命令：

```bash
.venvs/eval312/bin/python scripts/pack_pubtables_document_images.py \
  --images 'data/pubtables-v2/extracted/Full Documents/train/images' \
  --documents PMC10235804 PMC10311686 \
  --output-dir artifacts/paddle-smoke/20261023T081900Z-train-inputs
```

新增 `scripts/run_paddle_v15_smoke.py`，固定官方 v1.5 管线、native backend、随机种子 0；关闭方向/去畸变、图表/印章识别，保持版面检测，page/layout/VLM batch 均 1，其他生成参数使用官方默认值。**没有真值框、真值文字或真值筛页输入。**官方 PDFReader scale=2 源码入口：<https://github.com/PaddlePaddle/PaddleX/blob/v3.4.1/paddlex/inference/utils/io/readers.py>。

对每个文档只预测一次；先逐页 flush 原始 `pages.jsonl` 并核对页号/页数，再复制官方 JSON 分别执行 `restructure_pages(merge_tables=False/True, relevel_titles=False, concatenate_pages=False)`，保留 `no_merge.json`/`native_merge.json` 和官方 `global_group_id`。合并器可能保留空内容 table block，故 summary 分别报告总 block 和非空 block，不将它们直接视为正确逻辑表数量。来源：<https://github.com/PaddlePaddle/PaddleX/blob/v3.4.1/paddlex/inference/pipelines/layout_parsing/merge_table.py>。本地相关 13 测试与 Ruff 通过；包括缺页立即失败并保留完整前缀、已有目录拒绝、同一次推理用于两种合并。

待启动的有限后台入口（不是定期监控）为 `bash scripts/run_paddle_v15_smoke_after_setup.sh 20261023T082900Z-paddle-train-smoke`；等指定安装任务产生 `setup-complete.json` 才执行。如安装失败即退出；GPU 启动门槛空余 ≥20,000 MiB，逐页/文档检查低于 8,192 MiB 安全退出，不终止其他进程。5 秒 GPU 采样为整卡状态，不能冒称本进程峰值。输出 `outputs/baselines/paddleocr-vl-1.5/20261023T082900Z-paddle-train-smoke/`，实验日志/cache/config/manifest 在对应 `logs/baselines/paddleocr-vl-1.5/`。所有 cache/TMP 均在新项目子目录，不新增外部文件访问。安装后 CPU/GPU 实际兼容性、6 页覆盖、官方合并输出契约仍待验证；没有全量评测或正式分数。

实际启动：**08:25:17 UTC**，用户 unit `paper-paddle-smoke-20261023T082900Z.service`、初始 PID `422511`、active/running，日志 `logs/paddle-launchers/20261023T082900Z/smoke.log` 当前为 `WAIT_SETUP`。服务器 13 项相关测试、bash 语法检查通过；入口 commit `49f158c` 已同步 GitHub 与服务器 main。此时环境仍在安装，不把 waiter 的 active/running 解释成 GPU 推理已启动。缓存补充显式 `CUDA_CACHE_PATH` 与 `PPNLP_HOME`，避免驱动/JIT 或 NLP 的默认外部目录。

## 2026-10-23 09:47 UTC（北京时间 17:47）完成后只读核验

**已提供：独立环境安装和 train GPU smoke 已完成，不再是 WAIT_SETUP。**用户询问是否能开始 GPU 推理，本轮未重复启动任务、未启动全量 val、未修改服务器文件。安装日志末尾 `No broken requirements found`；安装与 smoke 两个 unit 均 `inactive/dead`、`ExecMainStatus=0`。原自动任务已运行真实 GPU 推理，页面处理从 **09:15:33 到 09:19:13 UTC（北京时间 17:15–17:19）**；`summary.json` 为 `completed`，6 页共 220.57 秒（不包括安装和模型初始化）。实际代码 commit `2ceceb9`。

- `pages.jsonl` 逐行 JSON 检查通过；与 packing manifest 对账 **6/6 页，missing/extra/duplicate=0，顺序一致**，预测 width/height 与原图逐页相同。两份派生 PDF 当前 SHA 与原 manifest 相同。
- 每文档输出两个非空 table block，共 4 个页面表片段；两组 HTML 均通过 `xml.etree.ElementTree.fromstring` 检查（每组 4/4）。仅证明格式可解析，不是结构/文字正确率，也不是逻辑表恢复成功率。
- 两文档 `no_merge.json` 与 `native_merge.json` **逐对象完全相同**；table 的 `global_group_id` 均等于自身 `global_block_id`。两个案例未触发官方合并，不能称跨页恢复成功；原因待核验，不能仅据此判定模型没有跨页能力。train 案例不代替正式 val 结果。
- GPU 0 采样 47 次、最低空余 **34,103 MiB**，最高整卡占用 46,936 MiB，启动前整卡占用 41,432 MiB。共享卡差值不能作为严格的本任务峰值。检查时 GPU 0 回到空余 39,607 MiB、利用率 0%，smoke 已结束。
- 下一步核验官方合并判据和跨页来源页映射、实现/验收评分适配，再准备可恢复的完整 validation 分片。GPU 基础环境已验证可运行，但全量门禁尚未全部通过；不为提高 train 样例成功数擅自改官方合并器。无正式分数，无新下载或数据更改。

核验方法：读取两个 unit 状态及 launcher 日志；在 eval312 中逐行解析 JSON，按 `(document_id,page_index)` 与 packing manifest 对账、核对维度及 PDF SHA，解析两组 table HTML、比较完整官方输出对象，聚合 `gpu-samples.jsonl`。全部只读。

核验时计算的 SHA-256，产物前缀为 `outputs/baselines/paddleocr-vl-1.5/20261023T082900Z-paddle-train-smoke/`，日志前缀为同 run 的 `logs/baselines/paddleocr-vl-1.5/`：

| 文件 | SHA-256 |
| --- | --- |
| 产物 `summary.json` | `a52e3ce73cc03a5e20e397195bfe93c181891d9823ff2cb11f4dff540739d8a1` |
| 产物 `pages.jsonl` | `791705c3bc866b008f96f3e5ffcee25e2f5af0c9ad257f946bd18987b23e6370` |
| 日志 `run-manifest.json` | `e12aa52c26d1ae319184efb94c67d500c3b6729b82154d0b50f38a20f7c209ce` |
| 日志 `pipeline-config.yaml` | `8e6536d0f224065d63e4a537c48097501c0c456d47b4da63be93703b5f7ab843` |
