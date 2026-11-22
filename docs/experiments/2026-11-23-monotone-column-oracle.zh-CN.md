# 30 张列数冲突表的保序补列上界

2026-11-23，北京时间。CPU 诊断已完成。冻结前述 200 张 train_fit 表的预测和真值，专门查看其中 B0 因页间预测列数不同而失败的 30 张。原内容对齐启发式在这 30 张也全部失败。数据版本、赛道及历史实验见前项。[边界编辑审计](2026-11-23-boundary-edit-oracle.zh-CN.md)

## 结果

| 条件 | 总行列数正确 | 结构完全匹配 | 内容完全匹配 | 结构与内容联合全等 |
| --- | ---: | ---: | ---: | ---: |
| 保序补空列，保留所有行 | 5/30 | 0/30 | 0/30 | 0/30 |
| 保序补空列，允许删精确重复前缀 | 6/30 | 0/30 | 0/30 | 0/30 |

给定真值宽度后，为每片段枚举保序列映射，插入空列，拒绝把已有横跨单元格切开。保留预测文字及原有单元格跨度。去重条件另外允许删与首片段精确相同且跨度安全的开头 1–3 行。正文不生成新行，预测中过宽的列也不删除。每张表独立搜索结构、内容和两者同时完全匹配的路径。每片段最多检查 4,096 种映射，单目录每表最多 100 万状态转换，实际无组超预算。

真值宽度等于预测最宽片段的有 15/30 张，等于唯一众数的有 13/30 张，纳入并列众数为 22/30 张。13 张至少有一个预测片段比真值宽，单纯补空列不能到达真值。另有 5 张原预测总行数已少于真值，2 张需要删去的总行数超出所设边界前缀范围。剩余 10 张实枚举。6 张找到了行列数正确的某个路径，其中 5 张仅尺寸就有多个候选。逐张抽看报告保存的第一个尺寸匹配路径，结构不匹配行分别为 1、4、2、4、17、2 行。3 张首行就错，说明边界之外也存在单元格跨度或位置错误。

即使离线提供真值宽度，单纯放宽列标签匹配并补空列在这组仍未恢复一张整表。可将宽度估计保留为独立诊断，优先确认局部结构和文字错误能否由页内预测获得足够证据。此结果只限定当前候选族，不排除视觉重新识别、拆/并局部单元格或更细粒度列映射的价值。

## 证据与复现

- 有效报告为 `artifacts/reconstruction-diagnostics/20261122T170213Z-monotone-column-oracle-30/report.json`，SHA256 `8f7882c77eed95f12f92bed482915e675d3ddc72481617fd95a93e697911a14c`。完整输入哈希、分组宽度、局部映射路径及各指标在报告中。脚本同目录保存，SHA256 `c5a88e2376c78c996bdc94de4371a2756226513916a3a74124ed649671ba9f2d`。
- 首次探针 `20261122T170141Z-monotone-column-oracle-30` 把元组直接传给已有空列插入函数。该辅助函数与列表切片比较，误把所有合法跨度判为不连续。首次报告保留作失败记录。改传列表后两个合成断言及 Ruff 均通过，重新写入有效报告。断言分别核对尺寸、结构、内容分离的路径数以及禁止切断 colspan。
- 现有 Python 3.12.7 环境，CPU、无权重加载或下载。真值仅作离线条件及评价，不能用作实际推理宽度。无随机步骤。实际命令如下。重复运行应使用新的输出目录。

```bash
cd /data01/public/zhengguojie/paper
run=artifacts/reconstruction-diagnostics/20261122T170213Z-monotone-column-oracle-30
prior=artifacts/reconstruction-diagnostics/20261122T165111Z-boundary-oracle-200
PYTHONPATH=src:$prior CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 \
  .venvs/20261114T095359Z-qwen-env/bin/python "$run/audit_reconstruction_column_oracle.py" \
  --root /data01/public/zhengguojie/paper \
  --boundary-report "$prior/report.json" \
  --b0 artifacts/reconstruction-baselines/20261114T153243Z-200table-b0/predictions.json \
  --output "$run/report.json"
```
