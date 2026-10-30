# OCRFlux完整文档基线实施计划

> **For agentic workers:** 使用 executing-plans 在当前会话逐项执行；每阶段核验并留痕。

**Goal:** 实现可审计的OCRFlux页面识别、跨页重建和两组评分输入，完成train验收后才全量。

**Architecture:** CPU核心负责安全索引、元素身份和逆序合并，GPU入口只调用固定官方接口并逐请求落盘。复用document_run按文档哈希检查点，新目录恢复；GT仅离线评分读取。

**Tech Stack:** Python3.11、固定OCRFlux/vLLM0.7.3、pytest、现有评分器。

## 全局限制

遵循同日design全部固定revision及参数；image-only、train开发、不读取test。不覆盖服务器旧数据/结果，不修改官方源码。保留当前工作分支及既有未提交文档。

## 任务1：安全元素与来源链

文件：src/cptla/evaluation/ocrflux_document.py、tests/test_ocrflux_document.py。
接口：parse_pairs(text,left_size,right_size)返回索引对；reconstruct(document_id,pages,detect,merge)返回no_merge/merged/decisions。

- [x] 写失败测试：拒绝表达式、bool、越界、冲突；三页逆序链、重复HTML独立身份、失败保留输入。
- [x] 执行 `.venv/Scripts/python -m pytest tests/test_ocrflux_document.py`，确认缺失模块导致失败。
- [x] 实现literal_eval校验、深拷贝节点、仅成功表重建传播来源页；生成前后不改变原页。
- [x] 同命令验证全部通过，并核对真实官方helper。

## 任务2：原始推理与适配

文件：scripts/run_ocrflux_document.py、scripts/adapt_ocrflux_document_predictions.py、tests/test_ocrflux_cli.py。

- [x] 写CLI无GPU导入/help及适配覆盖拒绝测试，运行确认失败。
- [x] 实现独占输出、逐请求响应/prompt/token/错误保存、GPU门槛及清理、官方PageResponse/表转换；使用任务1核心。
- [x] 适配输出两组page-results/document-tables以及manifest与输入输出SHA，不传GT。
- [x] 运行测试并验证同页预测复用、哈希和错误覆盖。

## 任务3：train与可恢复全量入口

文件：scripts/run_ocrflux_document_full.py、tests/test_ocrflux_full_entry.py。

- [x] 先测试协议不同拒绝恢复、完整checkpoint不调用worker、篡改产物拒绝恢复。
- [x] 复用document_run.run_batch，冻结源代码/环境/模型/manifest并新目录发布。
- [x] 同步特定代码到服务器新目录；检查GPU后执行已有3篇10页train图像PDF，不下载数据，不改原输入。
- [x] 独立CPU配对评分、来源链审计、新run实际恢复，全部通过后做935篇/13871页只读全量预检。
- [x] 更新三层记录；未达门禁不宣称READY，未获启动意图不冒称全量运行中。
