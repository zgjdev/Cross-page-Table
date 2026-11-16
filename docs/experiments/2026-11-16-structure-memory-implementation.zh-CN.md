# 共同列槽独立模块实现记录

- 日期：2026-11-16，Asia/Shanghai；状态：本地实现完成，真实 torch 运算待核验。
- 依据：`docs/plans/2026-11-09-cross-page-joint-reconstruction-research-plan.zh-CN.md` §4.3–4.4。
- 新增 `src/cptla/reconstruction/structure_memory.py`，默认512维、4块、8头、64有序列槽与16摘要。输入仅视觉tokens、局部节点特征与有效mask；位置与片段编码由调用者负责。count类别1..64、start类别0..63、exclusive end类别1..64；uncertain为二分类。
- 每块执行slots读联合证据、自交互、nodes读slots；预测列数概率累积为P(C>=i)软门控，训练和推理接口相同且无target参数。摘要池化节点关系向量，无节点样本回退slot池化。拒绝无有效证据样本；padding在投影前清零。
- 边界关系未实现（无候选行/边输入）；Qwen位置编码、cache和真实生成前缀集成未实现。无模型有效性结论。
- TDD证据：`$env:PYTHONPATH='src'; python -m pytest tests/test_structure_memory.py::test_module_exists` 在实现前因模块不存在失败（1 failed）。首次系统Python调用另遇包路径和临时目录权限问题，修正命令后获得上述预期失败。
- 验证：`.venv/Scripts/ruff.exe check src/cptla/reconstruction/structure_memory.py tests/test_structure_memory.py` 通过；`.venv/Scripts/python.exe -m pytest tests/test_structure_memory.py --basetemp=.tmp-structure-memory-venv-20261116` 为1 passed、2 skipped。跳过原因是本地无torch。
- 待核验测试覆盖：batch1/2、padding含NaN不改变前缀、有效跨片段证据扰动影响前缀、无证据拒绝、无节点fallback、梯度、optimizer更新与保存重载。随机种子17，小维合成数据，无数据集split、无模型权重、无GPU、无正式指标；代码尚未commit。
- 下一步由主任务在授权服务器环境执行该测试，随后补记真实结果。记忆页与进度索引由主任务统一更新以避免并发覆盖。
