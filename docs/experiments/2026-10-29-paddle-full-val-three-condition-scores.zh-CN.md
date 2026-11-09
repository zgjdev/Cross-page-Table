# Paddle完整validation三组离线评分

日期：2026-10-29（Asia/Shanghai；事件时间UTC）。状态：**三组完整评分及最终完整性检查已完成；2026-10-30 00:04北京时间只读核验通过**。用户明确要求“开始进行评分”。不下载、不使用GPU、不重跑推理、不修改原输入/结果/官方包；全部输出使用新目录。

## 冻结协议与研究问题

复用run `20261023T152753Z-paddle-val-full` 的935文档/13,871页完整image-only预测，比较 `no_merge`、`native_merge_official`、`native_merge_content_compat`。第三组仅使用已在train冻结的字段兼容桥接，不根据val GT调整规则或HTML。数据PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`、val，包括所有无表页；模型PaddleOCR-VL-1.5 revision `2a4195faa5e7914c12f2fc601d72c81caf8d2da5`，PP-DocLayoutV3 revision `241f8bdfc77a7c7bee915a5057aaee58c235a8d3`。GPU预测seed0，本轮CPU后处理/评分无随机采样。

代码本地/服务器HEAD `006da5940e61ead3202c0cf168c02a304d851143`，分支codex/paddle-merge-compat；服务器工作区干净，本地有累计进度记录未提交。本轮不修改生产评分代码。服务器相关pytest回归全部通过；追加关闭默认addopts的计数核验结果为 **66 passed in 1.09s**（test_document_run/test_paddle_full_entry/test_adapt_paddle_cli/test_paddle_document/test_paddle_v15_smoke及evaluation/test_cross_page、test_scoring）。启动前内存MemAvailable约516GB，项目文件系统空余34TB，无运行中的用户service；不终止任何进程。

输入run根 `artifacts/paddle-document-runs/20261023T152753Z-paddle-val-full/`，使用exported-inputs与exported-predictions。完整哈希验收遍历全部checkpoint引用文件并核对导出/原版重组一致性、清单与页面身份；固定数字页序manifest SHA `1d39ca16b7fcfedf3dabb174c80ef4ae914d90a76a2839617a469c0ba75e90c5`。真值仅进入评分：`data/pubtables-v2/extracted/Full Documents/val/tables/` 和 `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/gold-cross-page.jsonl`（预期983张逻辑跨页表，来源为parts派生子集，不冒称官方细粒度监督）。验收会保存935份truth文件与gold的SHA，结束复核不变。

环境解释器 `.venvs/eval312/bin/python`，numpy2.5.3/scipy1.18.1/pydantic2.13.5/pylcs0.1.1，既有bs4依赖 `artifacts/runtime-deps/20261023T100100Z-paddle-cpu`；PYTHONPATH包含src、vendored grits与该依赖路径。只使用CPU；OMP/OPENBLAS/MKL线程各1。官方合并源码固定安装路径 `.venvs/paddle-v15-20261023T081029Z-paddle-v15/lib/python3.12/site-packages/paddlex/inference/pipelines/layout_parsing/merge_table.py`，adapter核对其冻结SHA，原版回放必须等于保存结果。

## 启动与产物

任务ID `20261029T035007Z-paddle-full-val-scores`；新launcher `artifacts/paddle-score-launchers/20261029T035007Z/run.py`，本地先创建并AST核验，传入服务器新目录后再次AST核验，SHA-256 `180d6881014c85a0d18da9870c30db4e911593f9c7f3edd72f5c184109fd2186`。这是实验命令封装，不改变既有评分实现；完整子命令可由保存的launcher复现。run根 `artifacts/cross-page-scores/20261029T035007Z-paddle-full-val-scores/`，审计audit.json、原参数run-manifest.json、adapter三组、每组metrics/matches/failures、最终result-hashes.json与run-summary.json均新建不覆盖。各阶段stdout/stderr保存到独立日志，launcher主日志保留阶段UTC与耗时。

预定启动命令（实际启动状态须看下方追加证据）：

```bash
cd /data01/public/zhengguojie/paper
systemd-run --user --unit=paper-paddle-scores-20261029T035007Z \
  --property=Type=exec --property=Restart=no --property=Nice=10 \
  --property=WorkingDirectory=/data01/public/zhengguojie/paper \
  --property=StandardOutput=append:/data01/public/zhengguojie/paper/artifacts/paddle-score-launchers/20261029T035007Z/events.log \
  --property=StandardError=inherit \
  --setenv=PYTHONPATH=src:third_party/grits-main:artifacts/runtime-deps/20261023T100100Z-paddle-cpu \
  --setenv=OMP_NUM_THREADS=1 --setenv=OPENBLAS_NUM_THREADS=1 --setenv=MKL_NUM_THREADS=1 \
  /data01/public/zhengguojie/paper/.venvs/eval312/bin/python -u \
  artifacts/paddle-score-launchers/20261029T035007Z/run.py
```

既有用户Linger=yes，本轮不改系统设置；后台服务不依赖当前电脑/对话在线，Restart=no，任何异常不无限重试、不删除重置。没有创建定期监控。

## 完成标准与解释边界

三组均完整val评分（不传--partial），最终run-summary.status=completed且result-hashes通过；adapter原版回放一致、覆盖无缺失/额外/重复、输入输出与truth哈希验收通过。失败保留原目录，不重用相同输出路径。报告full_document与cross_page子集分开，内容网格exact不自动等于来源页正确的完整跨页恢复，须另读matches来源页；不把cross_page格子precision冒称续接precision。HTML拒绝/未匹配表与依赖警告须保留。主指标、失败案例及完整来源页审计尚待产物，不在启动阶段猜测。

时长当前待核验：历史dots两组完整CPU评分约1小时，但Paddle表数量、HTML复杂度与三组适配不同，不能直接承诺同样耗时。预计以小时计，最终根据首次阶段耗时修订。下一步核验audit/adapter与首组评分实际启动，再交接后台任务。

## 03:52 UTC实际启动证据

上述命令已成功执行；systemd记录ExecMainStartTimestamp=2026-10-29 03:52:03 UTC（北京时间11:52:03），unit `paper-paddle-scores-20261029T035007Z.service`、初始MainPID1297157，active/running。03:52:03.713 UTC写出audit running，03:52:09.500 UTC已核验400文档/3,600文件，尚未在此快照据服务active冒称adapter/评分已完成。原结果完整保留。

03:52:33.153 UTC全量audit completed，935文档/13,871页及完整checkpoint文件SHA验收通过，audit.json保存文件和truth哈希；随后同秒进入adapt running。目前没有三组正式分数，不把“评分流水线启动”表述为“评分已完成”。

## 05:28 UTC（北京时间13:28）阶段检查：仅第一组完成

只读核验事件日志、adapter summary、三组metrics及进程。adapter于03:54:02 UTC完成（88.94秒），覆盖13,871页、missing/extra/duplicates=0、official_replay=identical。候选表数no_merge=4,119、official=3,853、compat=3,460；多页来源组分别0/214/536。后两者只是候选合并数，不是正确跨页恢复数。

no_merge于05:02:15 UTC完成，耗时4,093.74秒（68.23分钟）。该组scope=full_validation、13,871页覆盖完整；full_document GriTS-Con=0.6510217379764833，内容网格exact=0.11519134132199459；cross_page子集983张、内容有正重叠匹配979张，GriTS-Con=0.6727107364650778、内容网格exact=0。所有979个匹配跨页项仍缺来源页，不能称为成功恢复979张表。inference_error_pages=0、invalid_table_html=13、unmatched_predicted_tables=1,524。matches.jsonl共983行、failures.jsonl共13行。metrics.json SHA-256 `bedff43c8d91c06103be74e86ed5b3b1964c691c6e710fd0e69e782627b64428`。该组结果已落盘，三组配对结论及结束后的完整哈希复核仍未完成。

同一service active/running、父PID1297157；官方合并组从05:02:15 UTC运行中，05:28快照worker PID1777772、RN、elapsed26:13、CPU time26:11、RSS592,920KiB，表明正在执行CPU计算。compat尚未启动，两组metrics尚无，父run-summary及result-hashes尚未发布。按第一组68分钟粗估，剩余两组共约1.5–2小时，受表格形状和共享CPU影响，不保证时刻。未重启/修改任务、未启动新评分或创建监控；下一步继续既有任务并核验三组完成标志。

## 完成核验：2026-10-29 16:04 UTC（北京时间10月30日00:04）

只读核验原任务，未启动新评分或修改服务器文件。事件日志显示：no_merge耗时4,093.74秒；官方组06:12:52 UTC完成，耗时4,236.23秒；兼容组07:17:24 UTC完成，耗时3,872.15秒；最终integrity结束07:17:35 UTC。`run-summary.json` status=completed，started_utc=2026-10-29T03:52:03.639359+00:00、ended_utc=2026-10-29T07:17:35.332925+00:00，即北京时间10月29日11:52至15:17，总计约3小时25分32秒。服务现inactive/dead、MainPID0；最终完成依据为事件、summary及产物，不单靠ExecMainStatus0。

本次按 `result-hashes.json` 重算三组metrics/matches/failures共9个文件SHA，9/9一致、mismatch=0。既有launcher的final-integrity已复核adapter input/output、truth及评分代码SHA不变，随后才发布completed。三组scope均full_validation、覆盖13,871/13,871页、missing/extra/duplicate=0；跨页真值子集983张，三组matches各983行、failures各13行。三组inference_error_pages=0、invalid_table_html=13，失败未隐藏。

### 指标（已提供：各组metrics.json）

| 条件 | 全表GriTS-Con | 全表内容网格exact | 跨页子集GriTS-Con | 跨页子集内容网格exact | 跨页子集结构网格exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| no_merge | 0.6510217379764833 | 0.11519134132199459 | 0.6727107364650778 | 0 | 0.001017293997965412 |
| native_merge_official | 0.7005742543563604 | 0.11751063007344414 | 0.7346695277562421 | 0.006103763987792472（6/983） | 0.08240081383519837 |
| native_merge_content_compat | 0.774418506544186 | 0.1198299188248937 | 0.8066705067100907 | 0.012207527975584944（12/983） | 0.23296032553407936 |

三组跨页真值正内容重叠匹配均979张；匹配项缺来源页分别979/780/478，额外来源页分别1/1/1。未匹配预测表分别1,524/1,259/868；后两组未匹配多页候选分别3/8，不能把这些计数当完整误连率。预测候选数与多页组数见上方adapter检查点。

已提供的配对结果显示合并后两类GriTS-Con均提高，但严格内容网格exact仍较低；原因尚待抽样诊断，不能据此直接归因特定算法组件。983是跨页子集分母，不与全表或论文不同split的Acc-Con混比；内容网格exact不检查来源页，因此6/983、12/983不能直接宣称已核验的完整跨页恢复成功数。兼容版是独立修改条件，不混称原始官方模型结果。未据val/test调整合并规则，test未进入本轮。

metrics SHA-256：

- no_merge：`bedff43c8d91c06103be74e86ed5b3b1964c691c6e710fd0e69e782627b64428`；
- official：`c5d16f623cad48d2645115ae27420486f3fbcd1fe0d6db2957eda4c5924481f8`；
- compat：`350c4b2d96bfb15a86c55ecfc6d39864fd94663f8a48bf64d774421531e3e67b`。

下一步：整理同输入条件的dots/Paddle对比与协议差异；抽样审计漏连、误连、列错位、重复表头、拆分行和文字/HTML错误，并为内容exact候选追加来源页核验。无需重跑GPU或此次评分。OCRFlux/MinerU-Popo仍需各自环境和train smoke门禁，不由本轮结果推断已测。

### 2026-10-30 计划顺序复核（无新结果）

上述结果交接/抽样工作不替代剩余模型基线。按 `docs/2026-10-23-open-model-priority-and-readiness.zh-CN.md` 第1节，下一模型为OCRFlux-3B，随后MinerU-Popo（固定Paddle页预测，比较无合并/官方合并/Popo），POTATR后置。10月23日下载实验已验收三模型主权重，不需要先重复下载；但本次未重新核验其服务器环境/接口当前状态，不能声称OCRFlux或Popo可立即全量运行。先独立环境、无GT输出adapter/来源页核验、train正负整文档smoke、GPU资源门禁，通过后完整val推理及配对评分。未授权或启动新的安装、推理、训练或评分，不用val/test调规则。
