# 2026-11-14 保守列对齐探索对照：预评估协议

状态：本地合成验证；没有真实数据评估、服务器任务或训练。此协议在本轮真实评分前固定，不使用目标 HTML。

实现 `monotone_first_row_alignment_exact_prefix_v1`。沿输入身份的页面/片段顺序处理，取预测中第一个最宽网格为共同列参照。等宽保持列序（这是位置假设，不是列对应正确的证据）；不等宽仅接受首行每列独立、非空、rowspan=1 的单元格（td/th 均可；首行只是未审计候选标签），各文本必须在参照首行唯一、完全相等且映射严格递增。没有相似度阈值、无文本归一化、无训练参数。拒绝歧义、逆序、未知列和跨新增列的 colspan。缺少列逐行插入显式空单元格，日志记录映射与插入列；源单元格文本保持解析器输出原值。

独立命名启发式 `exact_nonempty_prefix_max3_v1_not_official_labels`：对齐后，与第一片段比较最多 3 行、非全空的完全相同前缀，包括文本、span、header 标志；取最长完整边界，不截断 rowspan，不删除任一整个片段。逐片段记录删除行数，raw_predictions 保留原始 HTML。它可能错误删除重复正文，不能称为官方标签或已审计派生标签。没有实现跨页拆分行恢复，也不是完整 B1 或可学习方法。

覆盖、来源、解析失败保持整组失败及原预测。对齐失败也保留分母，不能回退静默成功。CLI 使用 `scripts/score_reconstruction_baseline.py --baseline monotone_first_row_alignment_exact_prefix_v1`；其余输入与 B0 相同。

验证（本地 Windows、Python 3.14，2026-11-14 Asia/Shanghai）：新增模块缺失时 4 测试收集失败，随后实现；6 个专项测试覆盖缺中列、歧义、重复正文前缀日志、rowspan 边界、后续坏片段、跨插入列 colspan。与已有 CLI、显式表头测试合计 21 通过。命令：`$env:PYTHONPATH='src'; python -m pytest tests/reconstruction/test_alignment_baseline.py tests/reconstruction/test_baseline_cli.py tests/reconstruction/test_header_baseline.py -q -o cache_dir=.test-runs/alignment-20261114-cache --basetemp=.test-runs/alignment-20261114-tmp`。系统 Python 未安装 Ruff，后续使用项目 .venv 核验。无数据/权重 revision、GPU、随机种子或指标：本次仅确定性合成单测，不是正式实验。

修订：真实预测无显式 th，因此列证据改为 `first_row_exact_label_heuristic`，只按预测首行文本唯一精确匹配，不声称是真实表头。新增 all-td 缺列成功测试以及重复正文误删风险/原预测保留测试，先得到两项失败再实现。风险字段 `may_remove_repeated_body_rows` 与未审计状态写入每组日志。
