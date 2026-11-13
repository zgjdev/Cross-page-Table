# 重建评分契约首轮核验

2026-11-13，北京时间10:46–10:47。状态：首轮合成检查完成，评分协议尚未冻结。执行依据为联合重建方案第7节与G0；本轮不使用数据集样本、模型、权重或GPU，随机种子不适用，不产生模型分数。

代码 `03be385f50f42732661dc46c35e799c0666740c8`。本地Python环境缺少pylcs，pytest在收集阶段失败，未修改环境。改用服务器项目内 `.venvs/eval312/bin/python`（Python3.12.7），`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:third_party/grits-main`，执行：

```bash
python -m pytest tests/evaluation/test_cross_page.py tests/evaluation/test_html_audit.py --basetemp artifacts/reconstruction-contract-audits/20261113T024637Z/pytest -q -o addopts= --tb=short
```

21 passed，3.30秒。服务器根为 `/data01/public/zhengguojie/paper`，以下路径均相对此根。测试输出保存于 `artifacts/reconstruction-contract-audits/20261113T024637Z/pytest.txt`。随后合成探针首次在保存TableCell对象时发生JSON序列化失败，旧不完整audit.json保留；改为cells_repr并先序列化再独占写入，在新目录 `artifacts/reconstruction-contract-audits/20261113T024713Z/audit.json` 成功保存，命令退出0。

探针通过 `runpy.run_path('tests/evaluation/test_cross_page.py')` 复用fixture、pred、score：GT跨页表为A、B两行，来源页[1,3]；其他真值和完整页覆盖同该fixture。四种预测分别为同内容且来源[1,3]、同内容且来源[0,2]、正确预测加一张内容unrelated且来源[0,2]的表、空预测列表。

| 合成条件 | 跨页内容grid exact | 其他证据 |
| --- | ---: | --- |
| 正确内容及来源 | 1 | 无来源异常 |
| 正确内容、错误来源 | 1 | missing/extra source各1张 |
| 正确预测另加无关表 | 1 | unmatched预测1张 |
| 没有预测 | 0 | 分母未删除 |

这些结果符合旧评分器“先全表匹配、再统计GT跨页子集”的定义，不据此宣称旧公式错误。**它不能单独充当新任务的严格完整恢复成功率**：来源正确性和多余输出需要另设指标与失败条件。

解析探针直接调用vendored `grits.html_to_cell_list`：

| 输入 | 观察 |
| --- | --- |
| `<table><tr><td>A &amp; B</td></tr></table>` | 一个cell，文本A & B |
| 上例tr外包tbody | 同文本及拓扑 |
| 上例改为thead/tr/th | 同文本及拓扑，header角色为True |
| `<table><tr><td>A&nbsp;B</td></tr></table>` | TypeError |
| `<table><tr><td>A<td>B</tr></table>` | TypeError |

只验证以上合成输入，不推断所有HTML行为；后两种兼容边界不能用来估计真实分数损失。历史评分及预测未修改、未重算。本轮没有触碰原始数据，也没有后台任务。

下一项具体实现：建立独立、版本化的规范网格层和契约测试；对显式/省略标签、实体、span、空cell、截断和语义往返分别规定接受或拒绝，不静默吞内容。R0按已知group_id一一评分并保留失败分母；D0另报来源一致性及额外预测处罚，不能把子集Con直接命名为严格恢复成功率。实现后先过合成与train小样本检查，再用同一协议对各基线比较。G0尚未通过，泄漏校准与方向处理也仍待完成。
