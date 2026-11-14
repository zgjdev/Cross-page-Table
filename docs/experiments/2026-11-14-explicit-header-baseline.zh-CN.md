# 2026-11-14 保守显式重复表头基线实施

状态：本地实现与合成测试已完成；服务器真实预测 paired 对照待执行。无下载、无服务器访问、无 GPU、无训练。

`src/cptla/reconstruction/header_baseline.py` 的 `explicit_header_exact_v1` 先调用 B0 `concatenate_group`，复用来源、完整覆盖、HTML 合法性和同列数检查。只以第一片预测的连续完整显式表头作为参考：网格每个位置均须来自 th 或 thead，文本原样及行列 span 全等才删除后续片同样的首部。第一片保留；删除边界跨 rowspan 时整段放弃去重；若会删除整个片段则保留。诊断保存原预测、每片删除行数与证据规则。没有目标 HTML 或派生标签进入决策。

这不是完整 B1、学习列对齐或拆分行恢复。依赖上游显式标记，未标记表头不删；若上游把正文误标 th/the​ad，仍可能误删相同正文。全表头片段保留会漏掉重复。列数不一致仍失败并保留评分分母。仅冻结规则对照，不宣称性能改善。

评分脚本新增 `--baseline explicit_header_exact_v1`；默认仍为 `B0_vertical_concat_v1`。两次评分应使用相同 `--upstream-run`、`--targets`，不同全新 `--run`；核对 `input-hashes.json`，不得覆盖旧目录。本模块不读取 GT，脚本仅在合并后评分阶段用 targets。

验证：2026-11-14 Asia/Shanghai，Windows Python 3.14，本地工作树未提交；无数据集样本、模型或随机采样。先观察新模块缺失导致收集失败，再实现；CLI 新参数测试先 TypeError 后通过。最终命令：

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/reconstruction/test_header_baseline.py tests/reconstruction/test_baselines.py tests/reconstruction/test_baseline_cli.py -q --basetemp=.test-runs/header-cli-green
```

结果：20 passed，exit 0。覆盖显式表头、非表头不删、全片保留、rowspan 边界、精确文本、来源校验及 CLI 默认/可选分支。该结果是工程合成验证，不是 PubTables-v2 指标，也不解除全量训练门禁。
