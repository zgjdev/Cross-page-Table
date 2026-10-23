# dots.ocr Full Documents/val 最后 240 页断点补跑

## 状态与输入

2026-10-20 12:26 UTC 核验：**最后 240 页后台推理已完成，全 13,871 页终态覆盖已验收；跨页合并和评分未执行**。本轮只补 PubTables-v2 Full Documents/val 最后 240 页的 dots.ocr `image-only` 页级推理，不进行模型训练、数据下载或跨页评分。固定数据 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，全部 935 篇、13,871 页，不用真值筛页；manifest `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl` SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`。本地原图 `data/pubtables-v2/extracted/Full Documents/val/images` 与 dots.ocr 权重 `checkpoints/dots-ocr` 均只读；权重 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`。`max_new_tokens=24000`、`do_sample=False`、无采样随机种子。

历史预测三段（只读，顺序固定）：

1. `outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl`：6,151 条，SHA-256 `76d318a1b51406c3d6fae65f15b875ca7ca70092bb8bbdbf3eb4e9e793e1d57e`。
2. `outputs/baselines/dots-ocr/20261010T024700Z-dots-full-val/predictions.jsonl`：636 条，SHA-256 `1765dc4c23dec7bafe3b5a673458ad004a8f5185b89427281e865510dccd0e79`。
3. `outputs/baselines/dots-ocr/20261017T081912Z-dots-full-val/predictions.jsonl`：6,844 条，SHA-256 `90209757ffa3bf1b6ac6e3682b89a4acce46a67243227d5b67660732af43bbfa`。

三段联合 13,631 页，按 manifest 顺序无重复/缺失前缀，历史 `ok=13,629`、`error=2`；下一页 `PMC12305305_page_0.jpg`。旧错误终态保留，不修改或重试旧输出。

## 代码、环境与启动门槛

代码 HEAD `007b8fd9a02ae5bf2e8361e1a1a1c074da9bb32d` 加工作区尚未提交的断点及计时修复；推理脚本 SHA-256 `5d5685aebaa8624599101d1aab6b781f93a3b912b0e1d33273e0b33192f4af87`，后台入口 SHA-256 `c94c4f128f0216ef674741d5ebfd813efaca17198ba7d8dcc81bdce68a8de440`。本地 `.venvs/eval312` Python 3.12.7、PyTorch 2.6.0+cu124、transformers 4.51.0、CUDA runtime 12.4。只使用共享 GPU0 A100 80GB；不终止其他用户进程。

- 后台入口新增第三个固定分片的路径、SHA 和行数；原逐条 JSON manifest 前缀验证保留，反序分片 preflight 拒绝。`bash -n`、`git diff --check` 通过。命令 `bash scripts/run_dotsocr_full_val_background.sh 20261020T020000Z-dots-full-val --resume-from <上述三段依次传入> --preflight` 于 01:54:42 UTC 输出 `validated recovery prefix: 13631/13871 pages`；此 ID 仅用于预检，不创建输出。回归 `PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python -m pytest -p no:cacheprovider --basetemp=artifacts/test-runs/20261020-resume-240-01 -q` 得 **151 passed**。
- 01:55:01 UTC 再次只读核对 GPU0 已用/空余 41,480/39,559 MiB，已有 4 个计算进程，瞬时利用率 0%；这不是独占许可或稳定余量。入口启动门槛 30,000 MiB，后台每 10 秒采样，余量 <8,192 MiB 等保护规则与原实验相同；如波动则只停止本任务并保存新旧分片。`Linger=no`，最后会话退出可能中断用户级 service。

## 启动与完成条件

正式启动时在 `logs/baselines/dots-ocr/<RUN_ID>/` 写 `launcher.log`、`events.log`、`inference.log`、`progress.csv`、`gpu-memory.csv`，仅新建 `outputs/baselines/dots-ocr/<RUN_ID>/predictions.jsonl` 和项目内独立缓存。`systemd-run --user` 的准确 ID、命令、PID、启动时间及首次新页在启动后追加；不可覆盖任何旧产物。完成条件为 unit 正常退出、四分片合计 13,871 条终态、每个 manifest ID 恰有一条且 missing/extra/duplicate 均为 0，并单列 `ok`/`error`/warnings、输出 SHA 和限制。只有之后才进入文档级跨页合并与离线评分；本轮不把页级覆盖当成跨页分数。

## 实际启动

- 2026-10-20 01:55:43 UTC，运行 ID `20261020T015543Z-dots-full-val`，用户级 unit `paper-dots-full-val-20261020T015543Z-dots-full-val.service`；01:55:44 UTC 入口再次核对三段 SHA、13,631 页前缀与 GPU0 剩余 39,559 MiB，unit active/running，wrapper PID `946957`、runner PID `947020`。没有终止任何原有进程。完整启动命令：

```bash
systemd-run --user --unit=paper-dots-full-val-20261020T015543Z-dots-full-val \
  --working-directory="$PWD" \
  --property="StandardOutput=append:$PWD/logs/baselines/dots-ocr/20261020T015543Z-dots-full-val/launcher.log" \
  --property="StandardError=append:$PWD/logs/baselines/dots-ocr/20261020T015543Z-dots-full-val/launcher.log" \
  /usr/bin/bash scripts/run_dotsocr_full_val_background.sh 20261020T015543Z-dots-full-val \
    --resume-from \
    outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl \
    outputs/baselines/dots-ocr/20261010T024700Z-dots-full-val/predictions.jsonl \
    outputs/baselines/dots-ocr/20261017T081912Z-dots-full-val/predictions.jsonl
```

- 新输出 `outputs/baselines/dots-ocr/20261020T015543Z-dots-full-val/predictions.jsonl`，新监控 `logs/baselines/dots-ocr/20261020T015543Z-dots-full-val/`；`events.log` 01:55:44 UTC 记录 PID、全部历史 SHA 和输入 SHA；首个 `gpu-memory.csv` 采样已写出。首条预测及运行结束状态尚待核验，当前不可宣称全量完成。
- 01:57 UTC 检查点：新分片已写 3 页，均 `ok`；首条 `PMC12305305_page_0.jpg` 正好接上旧清单，第 3 条 `PMC12305305_page_10.jpg`（清单顺序按输入保存），四分片合计 **13,634/13,871**，缺 237 页，JSON 可解析、无重复并严格对应固定 manifest 前缀。service 仍 active/running；GPU0 01:56:55 UTC 采样空余 21,313 MiB；`progress.csv` 01:56:34 UTC 报 13,633，属分钟采样滞后。无 guard/finished 事件；尚未完成全量或跨页评分。

## 2026-10-20 12:26 UTC 完成核验

- **已提供：**`events.log` 于 2026-10-20 04:14:23 UTC 记录 `finished`，`exit_code=0;new_pages=240;historical_pages=13631;combined_pages=13871;expected=13871`；`progress.csv` 终项为 13,871/13,871。12:26 UTC 检查 unit 为 `inactive/dead`、`MainPID=0`、`ExecMainStatus=0`。本轮后台推理正常结束，不再运行。
- **覆盖审计：**用 `PredictionRecord.model_validate_json` 逐条验证四分片，各 6,151/636/6,844/240 条；按顺序拼接后与固定 13,871 页 manifest **逐条完全一致**，唯一 ID 13,871，重复/缺失/额外各 0。总计 `ok=13,869`、`error=2`；最后 240 页全部 `ok`。历史两条失败为 `PMC10293395_page_18.jpg`、`PMC10423702_page_13.jpg`，均 `ValueError: layout list contains a non-object element`；没有改写失败记录。共 1,168 页带 warning、1,324 条 warning，均为 `invalid_table_html:<layout_index>` 类型；这些不是端到端评分结果。
- **校验和：**本轮 `outputs/baselines/dots-ocr/20261020T015543Z-dots-full-val/predictions.jsonl` SHA-256 `0a0a878f636786a3ff7d72dec423f7943668d389b6bffb1f192e036e760a3349`，与原 `logs/baselines/dots-ocr/20261020T015543Z-dots-full-val/predictions.sha256` 一致；三段历史 SHA 保持本文件所列数值，固定 manifest SHA 保持不变。审计只读，未修改数据、预测或既有日志。
- **结论边界及下一步：**这证明 dots.ocr `image-only` 固定 validation **页级终态全覆盖**，不代表所有页面解析成功，也不代表跨页逻辑整表已恢复。下一步先只读检查四分片适配器/合并基线对完整覆盖和 2 条 error 的处理，然后在**独立的新产物目录**进行文档级无合并与固定简单合并的配对离线评分，区分跨页子集与全表指标；不得用 validation 调整合并规则，PDF-text-assisted 结果不得与 image-only 混算。
