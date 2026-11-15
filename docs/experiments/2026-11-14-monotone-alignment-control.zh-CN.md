# 2026-11-14 保守列对齐探索对照：预评估协议

状态：本地合成验证；没有真实数据评估、服务器任务或训练。此协议在本轮真实评分前固定，不使用目标 HTML。

实现 `monotone_first_row_alignment_exact_prefix_v1`。沿输入身份的页面/片段顺序处理，取预测中第一个最宽网格为共同列参照。等宽保持列序（这是位置假设，不是列对应正确的证据）；不等宽仅接受首行每列独立、非空、rowspan=1 的单元格（td/th 均可；首行只是未审计候选标签），各文本必须在参照首行唯一、完全相等且映射严格递增。没有相似度阈值、无文本归一化、无训练参数。拒绝歧义、逆序、未知列和跨新增列的 colspan。缺少列逐行插入显式空单元格，日志记录映射与插入列；源单元格文本保持解析器输出原值。

独立命名启发式 `exact_nonempty_prefix_max3_v1_not_official_labels`：对齐后，与第一片段比较最多 3 行、非全空的完全相同前缀，包括文本、span、header 标志；取最长完整边界，不截断 rowspan，不删除任一整个片段。逐片段记录删除行数，raw_predictions 保留原始 HTML。它可能错误删除重复正文，不能称为官方标签或已审计派生标签。没有实现跨页拆分行恢复，也不是完整 B1 或可学习方法。

覆盖、来源、解析失败保持整组失败及原预测。对齐失败也保留分母，不能回退静默成功。CLI 使用 `scripts/score_reconstruction_baseline.py --baseline monotone_first_row_alignment_exact_prefix_v1`；其余输入与 B0 相同。

验证（本地 Windows、Python 3.14，2026-11-14 Asia/Shanghai）：新增模块缺失时 4 测试收集失败，随后实现；6 个专项测试覆盖缺中列、歧义、重复正文前缀日志、rowspan 边界、后续坏片段、跨插入列 colspan。与已有 CLI、显式表头测试合计 21 通过。命令：`$env:PYTHONPATH='src'; python -m pytest tests/reconstruction/test_alignment_baseline.py tests/reconstruction/test_baseline_cli.py tests/reconstruction/test_header_baseline.py -q -o cache_dir=.test-runs/alignment-20261114-cache --basetemp=.test-runs/alignment-20261114-tmp`。系统 Python 未安装 Ruff，后续使用项目 .venv 核验。无数据/权重 revision、GPU、随机种子或指标：本次仅确定性合成单测，不是正式实验。

修订：真实预测无显式 th，因此列证据改为 `first_row_exact_label_heuristic`，只按预测首行文本唯一精确匹配，不声称是真实表头。新增 all-td 缺列成功测试以及重复正文误删风险/原预测保留测试，先得到两项失败再实现。风险字段 `may_remove_repeated_body_rows` 与未审计状态写入每组日志。

## 已评估版本代码复核（2026-11-14，不修改算法）

证据类型：本地源代码直接核验；主任务提供服务器20表结果 top_exact=6/20（B0 1/20）、con_exact=0、删除26行、2组首行证据不足失败，本子任务未独立读取服务器产物，因此这些数字在此仅标记为“已提供”。

- 网格排序：`grid.py` 的 Grid 构造末尾将 cells 按 `(row_start,col_start)` 排序；合法完整网格无重叠，同一锚点不可能重复。因此 `_prefix` 的 tuple 比较不会因输入 cells 顺序不同造成假阴性。建议补一项直接乱序构造 Grid 的回归测试，冻结此依赖。
- header 布尔值：Cell dataclass 全字段比较包含 header，所以 td 与 th 内容/span 相同也不会删前缀。这是保守假阴性，不是文本篡改。当前 `_top` 与 `_content` 评分不比较 header 标记，故“评分 exact”不意味着 header 语义正确；当前全 td 预测也不能据此证明表头语义。建议冻结 td/th 混合用例并记录预期差异。
- 等宽恒等映射：不检查首行文本或跨片段语义，对等宽列错位、缺一列又多一列、上游拆合抵消均无辨识能力。日志明确 identity，但 completed 仅表示算法可执行，不能称作列对应正确。建议用等宽反序及缺增抵消的负例，确认当前会原样通过，并在将来新版本中设计拒绝/置信策略。
- 删除正文：最大三行 exact prefix 可删除完全合法的重复正文；已有专项测试明确展示这一风险且保留 raw_predictions。也可能将真实表头后恰好相同的1–2行正文一起删除。26行必须逐行人工判断为表头/正文/不确定，记录 fragment_id 与原始行范围；不能把结构 exact 增加直接解释为正确表头恢复。应做固定预测的“仅前缀”“仅列对齐”消融，在新版本/新输出中执行；不得改写旧结果。
- 来源：外层 B0 在开始解析前核验 expected 的全部身份、重复/缺失/额外来源；遇列宽不符提前返回后，本模块逐个再次检查所有预测状态/HTML，不能隐藏后续坏片段。最终 source_pages 为验证后的实际来源集合；source_exact 只证明页集合，不能证明文本未误删或跨页拆分行正确。
- 首行精确匹配：数值正文偶然相同也可被当成列标签；“唯一且保序”只保证本算法唯一，不保证语义真实。两个失败在缺证据时保留分母是合理的保守行为，不能通过查看其 target 选择新规则。

结论：没有发现 tuple 排序或来源覆盖导致这次指标凭空提高的明确代码错误；存在已知、可构造的正文误删和等宽错误静默保留风险。6/20 结构一致、内容0及26行删除只支持小样本可执行性与进一步误差审计，不支持完整 B1、G1 通过、训练放行或论文方法收益。下一步优先审计删除26行及6个结构命中组的内容差异，冻结旧版本后做模块消融。
