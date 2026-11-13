# 联合重建 train 数据入口与首批审计材料

日期 2026-11-09，Asia/Shanghai；运行事件使用 UTC。**11 月 13 日恢复核验：完整 train 清单已于 11 月 9 日完成，独立验收与 20 表坐标初查完成**，详见 [完成验收与未解项](2026-11-13-reconstruction-train-data-acceptance.zh-CN.md)。下文保留各阶段检查点，不以历史“待执行/运行中”状态替代最新证据。用户已要求开始首阶段，实施范围见 [G0 实施计划](../superpowers/plans/2026-11-09-reconstruction-data-audit.md)。

## 目的、范围与约束

研究问题是自然跨页 train 数据能否形成可追溯、输入与标签隔离的重建样本，并支持坐标和错误类型审计。本阶段生成数据清单与人工审计材料，不训练模型、不生成预测、不报告模型指标。

数据沿用 PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，只读 Full Documents/train。R0 条件提供 GT parts 框、同表归属和页序，输入赛道为 image-only；不能称为完整文档端到端。模型/权重 revision 不适用，GPU 不使用。新数据产物全部在服务器项目 `artifacts/reconstruction/<新RUN_ID>/` 中，不下载原始数据到本机，不覆盖旧目录。代码基线 `6ee8fcb`，功能分支 `codex/reconstruction-data-audit`。

## 已完成本地实现

- 固定 train 入口核验 parts 与图像，保留非相邻页和同页多片段，输入与整表目标分别保存；图像与标注 SHA 可追溯。
- 仅在 train 内按表文本构造保守重复簇，簇级固定种子 20261109 划分 70/15/15。SimHash 为候选，随后核验完整 shingle Jaccard；文本近重复漏检与短表误聚风险公开保留，视觉/正文/跨官方 split 审计尚未完成。
- 暂定 train_fit 按页数及 span 分层抽取最多 200 张表，保存抽样概率、权重和短缺量，再抽最多 20 表作坐标诊断；不将诊断子集作为代表性性能样本。
- 静态审计页并排显示原始片段与数据集 GT，明确“预测尚未生成”。GT HTML 在 sandbox iframe 和 CSP 内展示；全部审核模板为 pending。
- 输出目录独占创建，源文件结束时重新验 SHA，失败现场保留，只有输入/目标覆盖及产物核验完成才发布 summary。当前划分一律 `provisional_do_not_train`。

## 本地验证证据

Python 3.12.7，项目 `.venv`，新增可选依赖 `reconstruction = ["Pillow>=11,<13"]`，本地实际 Pillow 12.3.0。服务器现有 eval312 具备 Pillow/PyMuPDF/pytest，本轮未安装服务器依赖。

首次旧测试因 Windows 系统 `pytest-of-Z` 临时目录权限失败；定位到 fixture 初始化，改为项目 `tmp/pytest-<新UUID>` 的独占临时目录后，原有相关 19 项通过。未修改产品代码规避断言，也未删除旧临时文件。各新增模块先运行缺失实现的失败测试再实现。

完成本地整合后，命令为设置 `PYTHONPATH=src;third_party/grits-main`，执行 `.venv/Scripts/python.exe -m pytest tests/reconstruction tests/test_build_cross_page_manifest.py tests/evaluation/test_pubtables_v2_manifest.py --basetemp tmp/pytest-g0-ready-<当次新UUID> -q -o addopts='' --tb=short`。结果 **47 passed, 1 skipped**；跳过项是 Windows 无权限创建符号链接的逃逸测试，服务器需执行该项。对新模块、CLI 和测试的 Ruff 检查通过，diff 空白检查通过。

这里是工具验收，不是模型实验或数据质量结论。20 个坐标案例、200 表人工审计、评分契约、重复规则校准、官方 split 污染检查和新模型基线仍未通过。

独立代码审查未发现阻止服务器小范围 smoke 的重要缺陷，已检查输出独占创建、源路径、GT 隔离、簇级划分、采样概率、裁剪及完成标志顺序。实际数据与坐标语义仍需服务器验证，Linux 符号链接逃逸测试仍待执行。

## 服务器执行计划

先在新目录执行 `--limit-documents 20 --sample-size 10 --coordinate-size 4` 的技术 smoke，核对源哈希、模型输入不含目标、失败状态及预览。通过后不设 limit，对全部 train 生成清单和最多 200/20 的审计材料。实际 RUN_ID、完整命令、代码 commit、时间、数量及核验结果在执行后追加，不提前声明运行或成功。

下一步在独立代码审查后部署功能分支，只读原始数据并新建输出。后续应审阅坐标材料、校准重复候选，再进行局部预测与真实错误分析。独立双人审计无法由 Agent 自己复看替代。

## 服务器 smoke 与预览修复

部署 commit `ae59df616628d602307b8a613da0f3c33c71de82`，服务器切换到 `codex/reconstruction-data-audit`。首次 Linux pytest 的新 basetemp 父目录不存在，fixture 初始化失败；创建项目内父目录后换新时间戳子目录，**48 项全部通过**，包括符号链接逃逸测试，没有修改断言。没有删除或复用已有临时目录。

实际 smoke 输出为 `artifacts/reconstruction/20261109T153721Z-reconstruction-train-smoke/`，事件时间 15:37:21–15:37:26 UTC（北京时间 23:37）。实际命令如下。

```bash
cd /data01/public/zhengguojie/paper
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:third_party/grits-main \
  .venvs/eval312/bin/python -u scripts/build_reconstruction_manifest.py \
  --project-root /data01/public/zhengguojie/paper \
  --output-dir artifacts/reconstruction/20261109T153721Z-reconstruction-train-smoke \
  --limit-documents 20 --sample-size 10 --coordinate-size 4
```

smoke 读取 20 文档/315 页清单、54 张逻辑表，得到 19 张跨页表；同页多片段 1，坐标 clamping 0。暂定 fit/dev/confirm 为 13/4/3 文档。生成 10 表审计页与 4 表坐标拼图，62 份源文件结束时 SHA 一致；独立重算 51 项产物 SHA 全部匹配。inputs/targets ID 一致且输入无 HTML/cells，缺失/额外/重复为 0。`result-hashes.json` SHA 为 `1c513be086f4077458fac7323e6c61e7ac2b792c3968b60189dbbe4d56c0d217`。

直接流式查看两张服务器坐标拼图，未把数据集写入本地。发现预览 tile 高 620 而 crop 缩略图底边可到 629，拼图底部少量像素被裁；独立保存的全分辨率 crop 不受影响。新增回归先复现失败，修正 tile 高度为 650；commit `63bf468`。本地新模块 29 passed/1 Windows symlink skipped，服务器新模块 **30 passed**，Ruff 通过。旧 smoke 所有产物保留，正式材料使用修正后的代码新建目录。

## 全部 train 清单已启动

RUN_ID `20261109T153945Z-reconstruction-train-full`，15:39:46 UTC（北京时间 23:39:46）记录 `scan_started`。代码为 `63bf468`，Python PID `288957`；CPU 前台命令由当前 SSH 执行会话持续等待，非 GPU 训练、未设置后台监控。

```bash
cd /data01/public/zhengguojie/paper
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:third_party/grits-main \
  .venvs/eval312/bin/python -u scripts/build_reconstruction_manifest.py \
  --project-root /data01/public/zhengguojie/paper \
  --output-dir artifacts/reconstruction/20261109T153945Z-reconstruction-train-full \
  --sample-size 200 --coordinate-size 20
```

实际参数/源码 SHA/解释器/依赖记于 run-manifest.json，阶段日志 events.jsonl；产物根即上述 output-dir。预期结束条件为完整 7,359 文档进入审计、模型输入与目标 ID 对齐、样本及预览覆盖、全部引用源 SHA 重验、result-hashes 与 summary 完整。最终数量及人工坐标检查待完成，不因任务已启动而宣称完成。
