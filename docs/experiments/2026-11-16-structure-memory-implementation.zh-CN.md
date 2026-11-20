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

## 2026-11-20 恢复核验与实现续进（北京时间）

11月16日服务器真实Torch测试已执行：`CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venvs/20261114T095359Z-qwen-env/bin/python -m pytest tests/reconstruction tests/test_structure_memory.py -q -o addopts= --basetemp artifacts/reconstruction-test-tmp/20261116-core-grid --tb=short`，230 passed。修正上文“真实torch待核验”为已完成独立模块验证，不能代替Qwen集成。

11月20日重新读取已完成的直接grid单步产物：`artifacts/reconstruction-qwen-smoke/20261116T030726Z-direct-grid-first-step/`。summary为completed_smoke，结束UTC 2026-11-16T03:08:12.797183；代码109d57f，seed20261109，Qwen3-VL-2B-Instruct固定revision89644892e4d85e24eaac8bacfd4f463576704203，PubTables-v2固定revision aa575e798cb00a296925e2086addb3e3fd9a1903。输入train_fit/image-only单组PMC10488684-table-0，2片段，既有20组上游预测；非正式Acc-Con评估。完整命令/模型与输入SHA/环境见该目录run-manifest.json、model-hashes.json、input-hashes.json、versions.json。step-001：2828输入tokens、1859监督tokens、loss0.07117146、gradient_norm_sum2.232929、峰值分配5677635072 bytes；optimization记录参数实际更新、reload_equal=true。此结果仅证明grid目标训练链路可执行，不证明泛化或方法收益。

新增prefix_injection适配器：在完整input_ids对应的embedding调用替换80个前缀，保留原生图像占位符与位置计算；缓存单token跳过、异常自动撤销hook。未完成真实Qwen缓存验证，暂不声称方法已接通。

独立审查发现超过4300位JSON整数可使生成批次中断；已补回归并将解析ValueError统一为GridError。新回归证明raw保留、失败留在结果列表、后续样本继续。11月20日本地16项grid/生成测试通过；prefix合约本地缺Torch仍跳过，须服务器验证。默认临时目录权限失败后改用项目内新目录测试，没有删除旧目录。

下一步：真实预测HTML和视觉特征构造共同结构前缀，核验整表主损失梯度与参数更新、native mRoPE/cache一致性，再做同预算配对实验。人工审计仍pending，不阻塞此技术验证，不自动放行全量训练。
