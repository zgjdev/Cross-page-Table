# 联合重建自动化就绪检查与R0试运行

日期2026-11-13，Asia/Shanghai；服务器事件以UTC保存。用户要求持续推进到全量实验可开始，并明确暂时没有两位独立审计者，先完成自动化部分。本记录不放宽独立审计、G0/G1和训练门槛。

## 实现与验证

代码 `40c3beb`，分支 `codex/reconstruction-data-audit`。新增版本化grid、固定group诊断评分、B0纯纵向拼接、精确文本污染审计及Paddle裁剪推理入口。所有修改本地完成，服务器通过保护路径为空的fast-forward获取；原始数据与历史结果未覆盖。

本地Python3.12.7整合测试111 passed/2 Windows symlink skipped；服务器eval312同组113 passed，Ruff通过。测试命令为 `PYTHONPATH=src python -m pytest tests/reconstruction -q -o addopts= --basetemp <新目录>`；服务器目录 `artifacts/reconstruction-test-tmp/20261113T080000Z-auto`。各模块先失败测试后实现；upstream补齐page_num/part_index时先观察KeyError，再验证通过。

grid v1保留原文、实体、span、空cell、header；明确支持单表及可选纯html/body包装，拒绝外部正文、多表、截断、重叠/缺格。限制HTML 2,000,000字符、10,000行、1,024列、100,000网格位置。限制是资源预算，尚非全体train分布校准结论。R0评分为项目诊断，不冒称已核准官方Acc-Con；全部目标N分母、缺失/非法/重复预测失败，额外group单列。B0保持重复表头与文字，不是强规则基线。

## 真实train目标检查

固定PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，暂定train_fit分层200表。首次新网格全部因html外包装拒绝，现场 `artifacts/reconstruction-grid-audits/20261113T075512Z/` 保留；只增加严格包装支持后，`artifacts/reconstruction-grid-audits/20261113T134909Z/audit.json` **200/200解析与语义往返通过**。没有预测分数，也不等于GT逐字正确。原目标未修改。

## 精确文本污染审计

命令：

```bash
cd /data01/public/zhengguojie/paper
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venvs/eval312/bin/python scripts/audit_reconstruction_leakage.py --project-root /data01/public/zhengguojie/paper --run 20261113T080000Z-exact-official --official-splits --splits-path artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/splits.jsonl
```

13:50:17 UTC结束，输出 `artifacts/reconstruction-leakage/20261113T080000Z-exact-official/`。train/val/test分别7359/935/878文档、19885/2587/2390表，总9172文档/24862表；源文件结束复验，结果SHA在summary。test仅规范文本哈希对账，不看模型成绩、不调阈值。

发现一组跨官方split精确表文本重复：train `PMC10748512` table2（暂定train_dev）与val `PMC10721971` table2。完整按序表文本的文档重复0组；train内部精确重复跨暂定划分0组。无表文档49篇，不互相合并为空文本重复。**这不能证明无近重复/视觉污染或预训练污染。**当前仅列污染清单，不移动/删除数据、不改变划分，正式去污染分析方案待冻结。

## R0小范围Paddle试运行

输入来自 `artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/inputs.jsonl`，选 `PMC10488684-table-0`、`PMC12072187-table-1`，共2表4片段，image-only，GT提供框/同表组，预测入口不读targets。方向preserve_original；两例均来自已完成坐标初查的暂定train_fit，不含侧向表，不能据此宣称方向门槛通过。

CPU prepare-only目录 `artifacts/reconstruction-upstream/20261113T080200Z-r0-prepare/` 已完成4片段，原图SHA前后验证，crop及source mapping保存。真实推理使用新目录 `artifacts/reconstruction-upstream/20261113T135100Z-r0-pilot/`，当前执行会话等待，尚待终态核验。

```bash
cd /data01/public/zhengguojie/paper
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venvs/paddle-v15-20261023T081029Z-paddle-v15/bin/python scripts/run_reconstruction_upstream.py --project-root /data01/public/zhengguojie/paper --inputs artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/inputs.jsonl --run 20261113T135100Z-r0-pilot --group-id PMC10488684-table-0 --group-id PMC12072187-table-1 --gpu 0
```

PaddleOCR3.4.0/PaddleX3.4.1/PaddleGPU3.2.1/numpy1.26.4，现有VLM权重revision `2a4195faa5e7914c12f2fc601d72c81caf8d2da5`，启动前完整模型校验。native、seed0、关闭layout与方向/去畸变/额外模型、prompt_label=table；已从安装源码确认接口存在，真实行为待输出验证。GPU0预检空闲60950MiB，存在其他进程未干预；入口要求20000MiB启动、加载和每片前后8192MiB保护线。无新下载，无训练。

## 尚未满足的条件

近重复/视觉污染、方向与紧边界处理、强规则与200表可修复空间诊断、独立人审、训练实现/小规模对照仍未完成。自动化接口成功不放行全量训练；各项失败保留原始结果并另建run修正。

## 2026-11-13 后续自动化检查点

代码465add6修正显式失败预测计分、KeyboardInterrupt终态及片段文件名身份验证。新增可复现CPU入口scripts/score_reconstruction_baseline.py，完整保留失败分母并复验源图、裁剪和预测快照SHA。当前本地129 passed/2 Windows symlink skipped，Ruff通过；前两次复测分别遇默认临时目录权限和自选临时目录父路径不存在，修正测试目录后通过，未修改实现来绕过测试。

全暂定train_fit目标审计已完成：artifacts/reconstruction-grid-audits/20261113T142332Z/audit.json中5322/5322解析与语义往返通过、errors为空。existing-image-hash-overlap.json显示既有train跨页引用图像SHA共17299个不同值，无精确重复组；仅复用原清单哈希，未重读图像，不覆盖近重复。

原2表4片段GPU试运行已于13:55:29 UTC完成。B0诊断目录artifacts/reconstruction-baselines/20261113T135721Z/，两组均可拼接，top/con/joint exact均0，来源页exact为1；只是技术pilot，不是代表性效果结论。

侧向2表9片段run为20261113T140000Z-r0-orientation-pilot，14:05:53 UTC完成9/9。launcher为artifacts/reconstruction-launchers/20261113T140318Z/，exit0。B0诊断artifacts/reconstruction-baselines/20261113T141755Z/：一组片段列数一致，另一组列数4/5/4/3/4，按约定column_mismatch保留失败；两表top/con/joint均0。未旋转原图，不能据此宣称方向质量通过。

20表66片段R0试运行于14:27 UTC启动，run为20261113T142500Z-r0-20table-pilot，GPU0、seed0、代码465add6、相同权重/环境/方向策略。20个group来自原coordinate-sample.jsonl，全部暂定train_fit。完整argv在artifacts/reconstruction-launchers/20261113T142727Z/command.json，PID2998949，stdout.log与pid.json同目录；预测根artifacts/reconstruction-upstream/20261113T142500Z-r0-20table-pilot/。检查时46/66已保存，尚无summary，不记为完成；当前SSH执行会话仍等待，不声称已配置独立后台服务。完成条件为66个片段终态、完成summary和覆盖/哈希核验，再运行B0评分。无新下载、无训练、原数据和旧结果未修改。
