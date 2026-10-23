# 跨页表格恢复：2026-10-23 阶段成果与交接

核对时间：2026-10-23 05:16 UTC。**状态：已有实验的只读复核与阶段总结；本轮未运行新推理、重评分或训练。**固定主数据为 PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，当前正式范围仅 validation 935 篇、13,871 页；跨不同页的逻辑表真值 983 张。`test` 未用于本阶段调参。输入赛道为 `image-only`；以下 dots.ocr 结果不得与 TATR 的 `PDF-text-assisted` 结果直接排名。

## 已核验的成果

1. **数据与协议：**已保存覆盖全部 validation 页的输入清单和跨页真值审计；全页清单 SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`。跨页表 983 张、官方相邻页关系正/负例 1,276/786；第 5→7 页等非相邻片段未伪装成相邻续表。证据见 `docs/experiments/2026-09-29-pubtables-v2-val-cross-page-manifest-audit.zh-CN.md`。
2. **dots.ocr 全页预测：**`rednote-hilab/dots.ocr` 权重 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`，GPU0 分片与断点恢复后，预测终态覆盖 13,871/13,871 页，重复/缺失/额外页均为 0；13,869 页 `ok`、2 页 `error`。最后一个补跑任务于 2026-10-20 04:14:23 UTC 正常结束；原四段预测均原样保留。计时改用单调时钟及回归测试，以避免墙上时间回拨造成负耗时中断。证据见 `docs/experiments/2026-10-06-dotsocr-full-val-background.zh-CN.md` 至 `docs/experiments/2026-10-20-dotsocr-full-val-last-240-resume.zh-CN.md` 及 `logs/baselines/dots-ocr/20261020T015543Z-dots-full-val/events.log`。
3. **同一预测的两种离线后处理：**冻结的 `no_merge` 与规则式 `simple_merge` 在全页输入上配对评分；后台 `paper-dots-eval-20261020T123212Z.service` 于 2026-10-20 13:48:59 UTC 结束，日志 `status=0`。本轮重新运行 `sha256sum -c logs/cross-page-scores/20261020T123212Z-dots-full-val-offline/background-checksums.sha256`，两组 metrics/matches/failures 与合并 summary 共 **7 项均 OK**。两组均完整覆盖 13,871 页，跨页真值均 983 张；详细运行命令、环境、随机性设定、结果及旧产物校验见 `docs/experiments/2026-10-20-dotsocr-full-val-offline-evaluation.zh-CN.md`，代码运行时 HEAD 为 `007b8fd9a02ae5bf2e8361e1a1a1c074da9bb32d` 加未提交的计时修复。

| validation 指标 | `no_merge` | `simple_merge` |
| --- | ---: | ---: |
| 跨页 GriTS-Con | 0.4576991966 | 0.5131445386 |
| 跨页内容网格 exact / 983 | 0 | 2 |
| 跨页有正重叠匹配数 / 983 | 643 | 639 |
| 全表 GriTS-Con | 0.5077936893 | 0.5479001476 |
| 全表内容网格 exact | 0.0815616544 | 0.0819482026 |
| 预测表（评分解析前） | 2,752 | 2,597 |

规则审查了 1,213 个候选边界，接受 155 次；**155 不是正确合并次数**。有正重叠匹配亦不是跨页整表恢复成功数；格子 exact 没有核对预测表的来源页。数值取自 `artifacts/cross-page-scores/20261020T123212Z-dots-full-val-offline-{no-merge,simple-merge}/metrics.json` 和 `artifacts/cross-page-merges/20261020T123212Z-dots-full-val-offline-simple-merge/summary.json`，原产物未更改。

## 结论边界与待核验

- 页级提取有 **1,324 条 HTML warnings**；adapter 留下的 2,752 张未合并表中，另有 **637 张**在 XML 格式评分解析时被拒绝，仅 2,115 张有效进入评分。两个计数处于不同阶段，不能相加或直接当作独立丢表数；637 条原因只读分类为标签不匹配 520、非法字符 99、多根 12、未知实体 6，模型输出和解析策略各自的责任尚待区分。
- PubTables-v2 论文表 7 的 dots.ocr + merging 报告的是 **test 全部表** GriTS-Con `0.6844` / Acc-Con `0.1180`，使用 ViT-B/16 续接判断；本地为 **validation 全部表** `simple_merge`（`0.5479001476` / `0.0819482026`），另列跨页子集 exact `2/983`。不同 split、合并器及未核实的提示词/解析配置，不能直接称为论文同协议复现或把 `2/983` 与 `0.1180` 对比；本地跨页子集自定义匹配不惩罚全部子集外假阳性。详见 10 月 20 日离线评测记录的 15:50、15:56 核查段。
- 五方案执行计划为 dots.ocr、POTATR + merging、固定页预测上的 MinerU-Popo、PaddleOCR-VL-1.5、OCRFlux-3B，后四者当前均**没有本阶段的全页实测分数**。POTATR 权重、代码、许可与 ViT 续接器的可获得性仍待核验。OCRFlux HTML 补集只作合成片段拼接补充，不与主任务混算；已知真值裁剪的跨页片段实验只作 oracle 诊断。计划入口 `docs/2026-10-20-cross-page-five-method-evaluation-plan.zh-CN.md`。

## 下一步（尚未执行）

1. CPU 只读逐例交叉核对 runner warnings 与评分解析拒绝，按不依赖 GT 的规则区分普通 HTML 格式差异和确实残缺的输出；审阅官方 dots.ocr 输出/提示词和评测处理。仅在 train 样本上制定并冻结内容保真的解析规范，旧 prediction/metrics 原样保留。
2. 规范冻结后，用独立带时间戳的新目录重跑 validation 的 adapter 与配对评分，对照预测有效表覆盖、GriTS 和 exact；若需要改变页级 prompt，必须另立 GPU 任务并先重新检查共享显存及进程，不得把新输出混入本次固定预测对照。
3. 审计 155 次合并决策在真实 train 正负例上的误连/漏连，validation 只作解释、不据其调阈值；并行核验 POTATR 官方权重与许可。之后才决定其余模型 smoke / 全量运行，`test` 仅用于协议冻结后的最终评估。

本轮没有修改原始数据、旧预测、日志或评分产物，没有新下载和 GPU 任务；校验和复核仅证明旧结果的保存状态，不解决评测有效性风险。

提交前验证：`PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python -m pytest -q tests/evaluation/test_dotsocr_runner.py tests/evaluation/test_dotsocr_document.py tests/evaluation/test_simple_merge.py tests/evaluation/test_cross_page.py` 通过（40 项）；两个后台脚本 `bash -n`、受影响 Python 文件的 Ruff check、`git diff --check` 均通过。本轮只提交研究代码、测试和文档，不提交 `data/`、`outputs/`、`artifacts/`、`logs/`、权重或凭证。
