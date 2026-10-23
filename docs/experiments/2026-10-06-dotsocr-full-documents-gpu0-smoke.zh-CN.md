# dots.ocr Full Documents GPU0 短试跑

## 状态与目标

- 2026-10-06 17:11:59--17:15:13 UTC：**已完成，退出码 0**。用户要求测试共享 GPU 条件下是否能够进行之前约定的推理；启动前 17:11:34 UTC 再次核验 GPU0 剩余 48,737 MiB，4 个原有进程。
- 本轮仅复跑已有 3 页完整 validation 文档 `PMC11977379`，核验资源、输出覆盖和可恢复性；不代表全 validation 成绩，也不根据此样本调整规则。
- 输入：`kensho/PubTables-v2` Full Documents/val，revision `aa575e798cb00a296925e2086addb3e3fd9a1903`；不按真值删页。清单 `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-smoke.jsonl`，SHA-256 `c4d22178526b59384a487bf0274e64c86b6d04312bb0c9fc4476dad7d6afb006`；3 页、1 篇文档。
- 模型：本地 `checkpoints/dots-ocr`，历史模型 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`；赛道 `image-only`。代码 commit `007b8fd9a02ae5bf2e8361e1a1a1c074da9bb32d`；PyTorch `2.6.0+cu124`，transformers `4.51.0`，CUDA runtime `12.4`；项目 `.venvs/eval312`；确定性生成 `do_sample=False`，种子不适用（不设随机种子）。
- GPU：A100-SXM4-80GB，物理 GPU 0，**共享**，启动前 4 个已有进程，剩余 48,737 MiB，瞬时利用率 0%。旧三页 smoke 测得整卡峰值增量约 16,644 MiB；本轮重新监控整卡与本进程用量。绝不终止他人进程。
- 运行标识：`20261006T171019Z-dots-full-documents-gpu0-smoke`。输出：`outputs/baselines/dots-ocr/20261006T171019Z-dots-full-documents-gpu0-smoke/predictions.jsonl`；日志：`logs/baselines/dots-ocr/20261006T171019Z-dots-full-documents-gpu0-smoke/{inference,gpu-memory}.log`；缓存和临时目录限于新的项目内目录 `artifacts/cache/`、`artifacts/tmp-20261006T171019Z-dots-full-documents-gpu0-smoke/`。不下载、不修改原始数据或旧产物。

## 拟执行命令

```bash
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  HF_HOME="$PWD/artifacts/cache/hf-20261006T171019Z-dots-full-documents-gpu0-smoke" \
  XDG_CACHE_HOME="$PWD/artifacts/cache/xdg-20261006T171019Z-dots-full-documents-gpu0-smoke" \
  TMPDIR="$PWD/artifacts/tmp-20261006T171019Z-dots-full-documents-gpu0-smoke" \
  PYTHONPATH=src .venvs/eval312/bin/python scripts/evaluate_dotsocr_pubtables_v2.py \
  --model checkpoints/dots-ocr \
  --images 'data/pubtables-v2/extracted/Full Documents/val/images' \
  --manifest artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-smoke.jsonl \
  --output outputs/baselines/dots-ocr/20261006T171019Z-dots-full-documents-gpu0-smoke/predictions.jsonl \
  --max-new-tokens 24000
```

预期完成条件：进程正常结束、预测 3/3 页各一次、失败与警告单列、保存显存峰值和输出 SHA-256。若可用显存跌至 8 GiB 以下、出现 OOM 或影响其他任务，仅停止本轮自身推理，保留所有已产生的记录；不自动启动全量 13,871 页。

## 运行结果

- 启动时间：2026-10-06 17:11:59 UTC；推理 PID `3837378`；`logs/baselines/dots-ocr/20261006T171019Z-dots-full-documents-gpu0-smoke/run.log` 保存启停信息，`inference.log` 保存模型输出，`gpu-memory.log` 每约 2 秒采样 GPU0 已用/剩余 MiB 和利用率。命令与上方相同，另设置项目内 `TORCH_HOME`；监控进程仅在 GPU0 剩余显存低于 8 GiB 时终止本次推理 PID。
- 结束时间：2026-10-06 17:15:13 UTC，退出码 0；监控进程已停止，显存保护阈值未触发。93 次整卡采样显示峰值占用 48,946 MiB、最低剩余 32,093 MiB；相对启动前 32,302 MiB，**整卡采样增量** 16,644 MiB（不是独占精确峰值）。结束后 GPU0 已用 32,302 MiB，回到启动前水平；不声称其他进程未来不会变化。
- 输出 `predictions.jsonl` 中 manifest 3/3 页各出现一次，missing/extra/duplicate 均为 0；status `ok` 3、error 0、解析警告 0、页级表 1；逐页耗时 52.176、55.395、38.107 秒。逐页 `raw_output` 及 `tables_html` 与 2026-09-21 保存的同一文档 smoke 逐项相等（耗时字段不同）。日志包含已知的 flash-attention 不可用转 eager、`pad_token_id` 和 transformers FutureWarning；不是本轮错误。
- SHA-256：`predictions.jsonl` `051dca2e25f9ef22a45772e5655428d618092173b3f2c2e7135eb7ffae87fc94`；`inference.log` `ec50d91bf4389bf5dd957e7e2877e1a67c2bedad6a4caf534f64d51572eaca9a`；`gpu-memory.log` `6608a0f32449c1d2d24c215cf811d3bda552d5d5fe7576ff346cad116e9025fe`；`run.log` `470802813f15743bd5024fa9cd8e105dedeb43969c6e56c971f8aadca5bbfc91`。
- **结论边界：**仅复测同一篇 3 页文档的资源稳定性和输出可复现性，未评长文档极端显存、未运行跨页合并/正式评分，也未启动全 validation 13,871 页。该文档的真值表跨 `[1,2]` 页，模型本轮仍只识别出第 1 页表格；不能把 3/3 页推理成功解释为跨页恢复成功。下一步应另选完整较长文档做资源 smoke，评估单页长输出和现有任务影响；全量任务需重新核查显存和共享运行窗口，且只在确认稳定后开始，输出新目录并持续记录。
