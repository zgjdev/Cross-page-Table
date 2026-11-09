# OCRFlux完整validation两组CPU评分

日期为2026-11-08（Asia/Shanghai），事件日志使用UTC。当前状态为**两组正式评分完成，输入与结果SHA独立复核通过**。用户明确要求开始评分，历史阶段状态保留下文。

## 实验范围与协议

研究问题为同一批OCRFlux页面预测经跨页重建后的整表质量变化。复用run `20261031T114000Z-ocrflux-resume-a001` 的完整935篇/13,871页image-only预测，对no_merge和merged两组分别完整评分。PubTables-v2 revision为 `aa575e798cb00a296925e2086addb3e3fd9a1903`、validation，全表真值2,587张，跨页真值子集983张。

OCRFlux模型revision `e68592278bbc8ab32edf7b65e6e411f1d878ef72`，官方源码commit `c1b315aa4c8309f8dc436a5d90fc4977bcf0d865`，推理seed0和完整过程见 [推理及恢复记录](2026-10-31-ocrflux-profiling-recovery.zh-CN.md)。本次评分无随机采样，使用CPU。两组均保留13,142个成功页和729个失败页，所有无表页和失败终态均纳入完整覆盖统计。

评分器固定为此前Paddle实验的实际版本，commit `006da5940e61ead3202c0cf168c02a304d851143`。scripts/score_cross_page_predictions.py、cross_page.py及GriTS conversion.py/grits.py的字节SHA与Paddle保存的run-manifest逐项相同。完整冻结源码在服务器 `artifacts/ocrflux-score-launchers/20261107T162300Z/source/`。

环境为 `.venvs/eval312/bin/python`，Python3.12.7、numpy2.5.3、scipy1.18.1、pydantic2.13.5、pylcs0.1.1。PYTHONPATH使用冻结source/src、source/third_party/grits-main和既有bs4依赖目录 `artifacts/runtime-deps/20261023T100100Z-paddle-cpu`。CUDA_VISIBLE_DEVICES为空，OMP/OPENBLAS/MKL线程数各1，user service Nice=10。关键版本和显式环境保存于run-manifest。

## 已通过的启动前核验

输入使用原run的 `adapted/input-manifest.jsonl` 和两组 `page-results.jsonl`、`document-tables.jsonl`。manifest数字页序SHA `1d39ca16b7fcfedf3dabb174c80ef4ae914d90a76a2839617a469c0ba75e90c5`，覆盖935篇/13,871页，两组missing/extra/duplicate均0、状态计数一致。适配audit与export-complete所记SHA相同，936份适配输入及6份输出SHA核验通过。

GT读取 `data/pubtables-v2/extracted/Full Documents/val/tables/` 的935份文档真值，逐项SHA与Paddle完成实验保存值一致，合计2,587张表。gold为 `artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/gold-cross-page.jsonl`，983项，SHA `77797673d5d166e2203f5a5b14cac9661d963c54a6931ea8dda491ca3deb25d9`。GT只进入离线评分。

audit.json共记录1,916份输入/代码/真值文件SHA。评分结束将再次逐项复核，并对两组metrics/matches/failures保存result-hashes。当前输入核验已经完成，评分尚未结束。

## 启动前遇到的换行差异

首个预检ID `20261107T162000Z-ocrflux-full-val-scores` 使用本地git archive导出的相同commit。字节SHA校验拦截四个评分文件差异，任务在audit阶段退出，评分子进程尚未启动。对比确认正文完全一致，archive含CRLF，服务器实际评分文件为LF；完整差异计数保存在新launcher目录freeze-proof.json。首个失败目录和日志保留。

随后将服务器上已用于Paddle的实际评分源码逐文件复制到新的冻结source目录，SHA与旧实验四项记录完全一致。新ID使用同样的严格预检，未放宽字节检查，也未修改原评分器、预测、GT或模型环境。启动封装先本地创建并编译检查，通过既有评分CLI导入检查后上传。该封装只编排命令、核验和新目录写入。

## 正式运行标识及日志

- RUN_ID为 `20261107T162300Z-ocrflux-full-val-scores`。
- 实际启动时间为2026-11-07 16:21:51 UTC，即北京时间11月8日00:21:51。
- unit为 `paper-ocrflux-scores-20261107T162300Z.service`，初始父PID2703956、active/running。Linger=yes，无定期监控。
- 入口为 `artifacts/ocrflux-score-launchers/20261107T162300Z/run.py`，使用 `.venvs/eval312/bin/python -u <该入口>`。
- 事件日志为同launcher目录的events.log，记录audit/no_merge/merged/integrity阶段UTC和耗时。
- 结果根为 `artifacts/cross-page-scores/20261107T162300Z-ocrflux-full-val-scores/`。audit.json、run-manifest.json、每组-command.json及.log、每组metrics.json/matches.jsonl/failures.jsonl、result-hashes.json和run-summary.json均独占新建。

两组完整原生命令形如以下模板，MODE依次为no_merge、merged，实际绝对路径与PID以保存的命令JSON为准。

```bash
.venvs/eval312/bin/python -u \
  artifacts/ocrflux-score-launchers/20261107T162300Z/source/scripts/score_cross_page_predictions.py \
  --manifest artifacts/ocrflux-document-runs/20261031T114000Z-ocrflux-resume-a001/adapted/input-manifest.jsonl \
  --page-results artifacts/ocrflux-document-runs/20261031T114000Z-ocrflux-resume-a001/adapted/MODE/page-results.jsonl \
  --document-tables artifacts/ocrflux-document-runs/20261031T114000Z-ocrflux-resume-a001/adapted/MODE/document-tables.jsonl \
  --truth-dir 'data/pubtables-v2/extracted/Full Documents/val/tables' \
  --cross-page-gold artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/gold-cross-page.jsonl \
  --output-dir artifacts/cross-page-scores/20261107T162300Z-ocrflux-full-val-scores/MODE
```

16:21:57.745 UTC audit completed，随即no_merge评分子进程PID2704606启动。后续进程快照为RN、elapsed01:02、CPU time01:01、CPU98.8%、RSS541,572KiB，确认正在CPU计算。merged尚待前组结束，暂无正式指标。历史Paddle每组约一小时，本次表格数量和复杂度不同，粗估两组数小时，实际耗时需以阶段日志为准。

## 完成标准与后续

完成需两组full_validation评分均exit0、cross_page_truth_tables=983、结果文件SHA保存、1,916份输入SHA结束时复核一致，最终run-summary.status=completed。指标包括全表和跨页子集的GriTS-Top/Con及内容网格exact，另外保留HTML拒绝、未匹配和来源页诊断。内容网格exact与来源页完整性分别报告。完成后再与已保存dots/Paddle结果对齐汇总。

本次为CPU离线评测，无数据下载、GPU推理或训练。关闭本机/对话不直接中断服务器user service。异常时保留所有目录和日志，新任务使用新ID，不能在当前输出路径覆盖结果。

## 2026-11-08 12:32北京时间完成复核

run-summary.status=completed，started_utc=2026-11-07T16:21:51.249339+00:00，ended_utc=2026-11-07T17:52:55.949338+00:00，即北京时间11月8日00:21:51至01:52:55，总计约1小时31分钟。no_merge耗时2779.42秒（46.32分钟），merged耗时2677.47秒（44.62分钟），最终integrity completed。服务inactive/dead、MainPID0、ExecMainStatus0。

12:32北京时间只读重取服务器metrics、日志、run-summary与result-hashes，独立重算全部6项结果SHA和1,916项输入/代码/真值SHA，全部匹配。两组scope=full_validation、13,871页覆盖完整、missing/extra/duplicate均0、cross_page_truth_tables=983。

| 条件 | 全表GriTS-Top | 全表GriTS-Con | 全表内容网格exact | 跨页GriTS-Top | 跨页GriTS-Con | 跨页内容网格exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_merge | 0.5906681967 | 0.5354720405 | 4.329339% | 0.5669140991 | 0.5237718073 | 0/983 |
| merged | 0.6417883600 | 0.5963418133 | 4.483958% | 0.6320400900 | 0.5889221407 | 4/983（0.406918%） |

两组inference_error_pages均729。no_merge/merged分别有584/505项invalid_table_html、795/701项跨页正内容重叠匹配、795/339项匹配缺来源页、17/7项匹配多来源页、627/251个未匹配预测。上述来源页诊断不是续接P/R/F1，内容网格exact本身不检查来源页，4/983不能直接表述为已核验的4张完整跨页恢复。

合并后全表Con增加0.06086977、跨页Con增加0.06515033，当前管线在内容相似度上有所提高；正内容重叠匹配数下降，不能据单一聚合分数宣称所有案例均改善。与已有dots/Paddle比较见 [三模型汇总](../reports/2026-11-08-dots-paddle-ocrflux-full-val-results.zh-CN.md)。

metrics SHA为no_merge `19a9a8ebea26d13c99f4ec96b0bbad794a276152ac8b10802720e1e3cc5aa722`、merged `f5dbd7fd0b2208bde29cdd587521ff29de6c744e5060ed0b24e80683d0dd8262`。其余4项matches/failures完整SHA见服务器result-hashes.json。

本轮仅只读复核及本地记录更新。下一步基于已保存结果进行同协议模型比较与有限抽样错误/来源页审计，随后按计划准备固定Paddle上游的MinerU-Popo。当前OCRFlux推理及评分任务均结束，没有创建定期监控。
