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
