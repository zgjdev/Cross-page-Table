# 2026-11-15 已知污染整文档隔离层

状态：自动化产物已完成，原划分不变，尚未冻结正式训练划分。目的为落实11月14日污染处置计划，不代表G0/G1通过。

服务器实际完成时间2026-11-15 07:38:05 UTC（15:38北京时间）；run名称 `20261115T074000Z-known-overlap-overlay` 为手动标识，不将名称解释为实际启动时间。代码a2ebcfd；CPU `.venvs/20261114T095359Z-qwen-env/bin/python`，无需GPU/下载，确定性处理无随机种子。源码 `scripts/build_reconstruction_quarantine.py` 与 `src/cptla/reconstruction/quarantine.py`。

输入：固定revision aa575e798cb00a296925e2086addb3e3fd9a1903的既有 `artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/splits.jsonl`、`audit-sample.jsonl`，以及精确文本审计 `artifacts/reconstruction-leakage/20261113T080000Z-exact-official/{summary,overlaps}.json`。审计overlaps SHA e94f9da68241b3ed538ac8952b9d462fa409b6a0331670977151e613a9be7c3a 已按summary校验；所有输入末尾重算SHA。

完整命令：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venvs/20261114T095359Z-qwen-env/bin/python scripts/build_reconstruction_quarantine.py --project-root /data01/public/zhengguojie/paper --splits artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/splits.jsonl --overlap-run artifacts/reconstruction-leakage/20261113T080000Z-exact-official --observed-sample artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/audit-sample.jsonl --run 20261115T074000Z-known-overlap-overlay
```

新产物 `artifacts/reconstruction-quarantine/20261115T074000Z-known-overlap-overlay/{document-overlay.jsonl,summary.json}`：7359/7359文档，missing/extra/duplicate=0；effective split为fit5123、dev1123、confirm1112、quarantine1。已知train/val精确重合train文档PMC10748512整体隔离，不只排除table2；已有文档簇中任一文档命中则整簇隔离。200审计表的196篇文档均标为已观察，检查其既有簇没有进入unseen confirm。overlay SHA `6c16a222c2c41eacfda4cdbcd9b5944417329da359fa0cfa4cab701fac0ce00c`。

这是供后续数据加载器采用的明确隔离层，不原地改写inputs/splits，也未修改当前训练脚本的数据加载行为；尚未生成或冻结替代训练清单。原官方validation/test分母不变。未校准dHash候选不自动接受、不合并，不声称不存在近重复。正式训练前还须形成最终文档簇划分并让训练/评估清单显式应用该隔离层。

验证：先缺模块收集失败，再实现；3项测试覆盖整文档/既有簇隔离、不修改输入、已观察confirm拒绝、未知或重复文档拒绝；Ruff通过。无新增模型指标。
