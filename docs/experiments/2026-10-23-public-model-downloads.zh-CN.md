# 三个公开模型的服务器权重下载

日期：2026-10-23（Asia/Shanghai；运行时间记 UTC）。状态：启动准备。用户已要求开始 PaddleOCR-VL-1.5、OCRFlux-3B、MinerU-Popo 测试，当前先执行权重下载，尚未新模型推理。

任务标识：`20261023T064109Z-public-models`。目的：将固定版本官方权重直接保存在服务器项目内，并按官方元信息验证每个文件。网络/CPU 操作，无 GPU、无数据集下载、无原始数据或旧产物修改。

## 固定输入与输出

- 配置：`configs/public-model-downloads-2026-10-23.json`，来自本机访问官方 HF `/api/models/<repo>/revision/<40位SHA>?blobs=true` 的逐文件元信息。只保存公开文件名、大小、LFS SHA-256 或 Git blob SHA-1，不包含凭证或模型权重。
- PaddleOCR-VL-1.5：`PaddlePaddle/PaddleOCR-VL-1.5@2a4195faa5e7914c12f2fc601d72c81caf8d2da5`，18 个文件、1,930,460,966 bytes。
- OCRFlux-3B：`ChatDOC/OCRFlux-3B@e68592278bbc8ab32edf7b65e6e411f1d878ef72`，15 个文件、8,145,545,983 bytes。
- MinerU-Popo：`DreamEternal/MinerU-Popo@af75342abdc5cbd461264521c9ef46719ff74190`，17 个文件、17,767,303,848 bytes。
- 新权重目录：`models/20261023T064109Z-public-models/{paddleocr-vl-1.5,ocrflux-3b,mineru-popo}/`。合计 27,843,310,797 bytes，不含额外 Paddle 页面检测权重与运行依赖。
- 下载状态与结果：`logs/model-downloads/20261023T064109Z-public-models/{events.jsonl,summary.json}`；每个模型全文件通过才写其 `download-manifest.json`。同名任务目录已存在则拒绝启动，保留已下载文件，不覆盖重置。
- 传输通道为 `https://hf-mirror.com` 的固定 SHA 单文件 URL；官方仓库枚举 API 在服务器不可用，故使用本机官方元信息的明确文件清单，逐项 `hf_hub_download(..., token=False)`，所有缓存/TMP 均在该任务日志目录下。关闭隐式 token 和 Xet；不上传任何项目数据，不本地下载权重。

## 许可与边界

Paddle 模型卡 Apache-2.0、Popo 模型卡 MIT。**OCRFlux 权重仓库固定 revision 的 LICENSE 实际为 Qwen RESEARCH LICENSE AGREEMENT**，其文本授权 non-commercial research/evaluation，不能因为工具代码 Apache-2.0 就称权重也是 Apache-2.0。本项目本轮用途为科研评测，保留原 LICENSE，不发布权重。官方证据：<https://huggingface.co/ChatDOC/OCRFlux-3B/blob/e68592278bbc8ab32edf7b65e6e411f1d878ef72/LICENSE>。没有进行商业部署或法律适用性推断。

环境：服务器已有 `.venvs/eval312/bin/python`、`huggingface_hub=0.36.2`，不在该环境安装/升级依赖。只导入下载库、不执行模型仓库 Python。数据集/赛道/种子不适用于下载；后续模型实验仍固定 PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`、`image-only`、train smoke 与 validation 全量隔离。

本地校验：7 项测试通过，覆盖文件大小、LFS SHA、Git blob hash、路径越界与实际清单固定版本；Ruff 和 `git diff --check` 通过。新入口 `scripts/download_public_models.py` 不自动启动 GPU 或安装环境。

## 完整命令与完成条件

服务器根目录执行下载入口：

```bash
.venvs/eval312/bin/python scripts/download_public_models.py \
  --manifest configs/public-model-downloads-2026-10-23.json \
  --run-id 20261023T064109Z-public-models
```

计划使用独立用户 service `paper-public-models-20261023T064109Z`，launcher 日志为 `logs/model-download-launchers/20261023T064109Z-public-models/launcher.log`。启动后补记实际 PID/状态。三模型均 complete、50 个文件全部大小/哈希通过且总状态 0 才算下载完成；网络/哈希失败会记录失败类别、保留部分文件，不把 partial 写成 ready。该下载不代表运行环境/adapter/smoke 完成。

后续顺序：Paddle 完成后另建独立运行环境，核对必要版面检测组件与缓存，执行 train 整文档小样本及显存标定；再安排 OCRFlux 和固定 Paddle 上游的 Popo。不可因主权重完成就直接宣布全页管线可运行。
