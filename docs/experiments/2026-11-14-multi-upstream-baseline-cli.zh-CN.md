# 2026-11-14 多上游缓存联合评分

状态：本地实现及测试完成，未访问服务器、未运行200表评分、未提交。

scripts/score_reconstruction_baseline.py新增可重复参数--additional-upstream-run。保留--upstream-run单run行为；多个run各自须prepared且summary completed，expected/completed等于记录数，复用source/crop/原图/预测身份和SHA检查。跨run出现任何相同group_id或重复run路径即失败，不去重、不合并或复制原数据。run-manifest参数保存完整upstream_runs。

分母来自全部输入prepared的group并集，targets只提供对应目标；缺失预测仍计入失败，额外/缺失预测路径联合输出。所有读文件末尾SHA复验，各run预测文件清单末尾复查。该功能仍为pilot diagnostic，不改变评分协议。

TDD先观察新增参数未支持导致5项失败，再实现；中途合成fixture替换误改group_id字段名，修正fixture后通过。新增6项测试覆盖联合分母与哈希、重复run/group、未完成run、缺失预测和第二run评分中途变更。连旧CLI共17 passed，Ruff通过。验证命令：.venv/Scripts/python.exe -m pytest tests/reconstruction/test_baseline_multi_run.py tests/reconstruction/test_baseline_cli.py -q -o addopts= --basetemp artifacts/multirun-test-04。

200表用途：既有20表run作--upstream-run，新180表run完成后作--additional-upstream-run；统一targets与新run_id，分别生成B0及冻结强基线。尚无真实200表指标，不能将工具测试成功写成实验完成。
