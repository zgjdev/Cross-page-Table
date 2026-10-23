# dots.ocr PubTables-v2 Full Documents/val 全页后台推理

## 当前状态

2026-10-06 17:26 UTC：**新 ID 的用户级 systemd 后台任务正在运行；尚未完成全页推理/正式评测**。用户明确要求在后台开始全量测试，次日自行检查是否中断。

## 固定协议与版本

- 研究问题：为后续文档级跨页表恢复提供完整页级 `image-only` 预测；本任务只做页级推理，完成后另做跨页合并及离线评测。
- 数据：`kensho/PubTables-v2`，revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，`Full Documents/val`；**全部 935 篇、13,871 页**均进入推理，不用真值筛页；test 不参与。
- 固定输入：`artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl`，SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`；只读原始图片 `data/pubtables-v2/extracted/Full Documents/val/images/`。
- 模型 `rednote-hilab/dots.ocr`，revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`，本地 `checkpoints/dots-ocr/`；生成 `do_sample=False`，`max_new_tokens=24000`；不设随机种子（确定性解码）。
- 代码 HEAD `007b8fd9a02ae5bf2e8361e1a1a1c074da9bb32d`；启动脚本 `scripts/run_dotsocr_full_val_background.sh` SHA-256 `5357c81b25b1749c7d0a31eb02179a635d8bb66901a55ce9ca4796c74cce3a27`；推理脚本 `scripts/evaluate_dotsocr_pubtables_v2.py` SHA-256 `e300e0b171d1ac1d45791aeb331b8bd489c99d5d90ba3c23dee1fd3519b8ee51`，新增启动脚本及本文档尚未提交。
- 环境：`.venvs/eval312`，Python 3.12.7，PyTorch 2.6.0+cu124，transformers 4.51.0，CUDA runtime 12.4；物理 GPU0 A100-SXM4-80GB，**共享**，2026-10-06 17:18:58 UTC 检查时已占 32,302 MiB，余 48,737 MiB，有 4 个已有计算进程。17:11:59--17:15:13 UTC 同文档 3 页 smoke 的整卡采样增量 16,644 MiB；不能据此保证更复杂页面不会超标。
- 不下载新数据/模型，不覆盖已有文件；所有缓存、临时文件、预测、监控均位于项目内本次新目录。若显存不足、GPU 查询连续失败、连续三页错误、CUDA OOM 或 90 分钟无新增页，脚本只终止自己的推理进程并记录原因，不终止他人进程、不自动重跑。CPU/GPU 占用随共享任务变化，资源门槛仍可能无法避免所有冲突。

## 启动与检查

正式运行 ID：`20261006T172527Z-dots-full-val`；用户级 unit `paper-dots-full-val-20261006T172527Z.service`。拟执行命令（以 unit 状态、`launcher.log` 和 `events.log` 核验是否执行）：

```bash
mkdir -p logs/baselines/dots-ocr/20261006T172527Z-dots-full-val
systemd-run --user --unit=paper-dots-full-val-20261006T172527Z \
  --working-directory="$PWD" \
  --property="StandardOutput=append:$PWD/logs/baselines/dots-ocr/20261006T172527Z-dots-full-val/launcher.log" \
  --property="StandardError=append:$PWD/logs/baselines/dots-ocr/20261006T172527Z-dots-full-val/launcher.log" \
  /usr/bin/bash scripts/run_dotsocr_full_val_background.sh 20261006T172527Z-dots-full-val
```

- 推理脚本实际运行：`CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 PYTHONPATH=src .venvs/eval312/bin/python scripts/evaluate_dotsocr_pubtables_v2.py --model checkpoints/dots-ocr --images 'data/pubtables-v2/extracted/Full Documents/val/images' --manifest artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl --output outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl --max-new-tokens 24000`；HF、XDG、TORCH、TMP 缓存重定向到新项目内目录，shell 脚本是确切可执行环境来源。
- 运行时证据：`logs/baselines/dots-ocr/20261006T172527Z-dots-full-val/{launcher.log,events.log,inference.log,gpu-memory.csv,progress.csv,gpu-processes-start.csv}`；预测逐页追加到 `outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl`。`events.log` 记录 wrapper/runner PID 和最终退出码；`progress.csv` 约 60 秒追加一次计数，`gpu-memory.csv` 约 10 秒采样。只有进程实际启动后才把状态更新为“运行中”。
- 明天检查：核对 `events.log` 最近事件与 `progress.csv` 末行、`inference.log` 末行和 `ps -p <runner_pid>`；预测文件每页刷盘。若中断，不清空或覆盖本次预测，使用 `--resume-from` 指向已有预测，并将补跑输出写入全新的文件/目录，重新核查覆盖与重复。
- 完成条件：全 13,871 页各有一次终态记录，missing/extra/duplicate=0，错误及警告单列；保存完整输入/预测校验和、模型输出及环境信息。退出码 0 不等于预测均正确。离线适配、续接合并和结构/内容评分另开记录；当前无正式模型指标。

## 启动前核验

- `bash -n`、只读 `--preflight` 通过，验证固定清单 13,871 页和 GPU0 >= 30,000 MiB 余量。
- 项目全量回归 149 项通过（`PYTHONPATH=src:third_party/grits-main`，`artifacts/test-runs/20261006-full-val-launch-02/`）。首次测试漏设 vendored GriTS 的路径导致收集错误，失败临时目录 `artifacts/test-runs/20261006-full-val-launch-01/` 保留；补齐环境后通过，非代码逻辑失败。

## 实际运行记录

- 2026-10-06 17:24 UTC：首次尝试 `nohup bash ... 20261006T172221Z-dots-full-val`（命令 shell 返回 wrapper PID `3930310`），后续 `ps` 无此进程，目录 `logs/baselines/dots-ocr/20261006T172221Z-dots-full-val/` 仅有 0 字节 `launcher.log`；无 `events.log`、无预测目录、无 GPU 模型进程。本次**没有进入推理**，保留原目录不覆盖。推测是命令执行会话退出时回收了该子进程；改用服务器已有的 `systemd --user` 承载并在新 ID 下重试。
- 2026-10-06 17:26:41 UTC：正式 unit 已启动，`systemctl --user show paper-dots-full-val-20261006T172527Z.service` 返回 `ActiveState=active`、`SubState=running`、`MainPID=3946380`；`events.log` 中 wrapper PID `3946380`、runner PID `3946441`，GPU0 启动前剩余 48,737 MiB。`Result=success` / `ExecMainStatus=0` 此时仅是尚未终止的 unit 属性，**不表示任务完成**。
- 2026-10-06 17:27:46 UTC 核验首条 `PMC10154845_page_0.jpg` 预测 `status=ok`；17:28:24 UTC 文件已有 1 条且唯一，0 错误；unit/runner 仍在运行。GPU0 采样占用 49,998 MiB、剩余 31,041 MiB；尚无跨页评分或全量结论。`progress.csv` 首个定时检查点 17:27:32 UTC 为 0 页，是预测写入前的旧值，下一次会更新。最终覆盖/错误和哈希待完成。
- 2026-10-06 17:29:22 UTC 检查：unit 仍 active，预测文件已有 2 行（page 0、page 1），均 `ok`；17:28:32 UTC `progress.csv` 第二次采样为 1/13,871 页，已验证周期追加正常。当前是运行中检查点，不将部分页的结果当成最终覆盖或论文指标。
- 2026-10-06 17:30:21 UTC 交接检查点：unit active、runner PID `3946441` 存活；预测 4 行/4 个不同页，均 `ok`、无警告；17:29:33 UTC 最近定时进度为 2/13,871 页（定时采样滞后于实时文件），GPU0 已占 49,998 MiB、剩余 31,041 MiB。进程仍在后台运行，尚无完整覆盖/评分/预测文件最终 SHA-256。
- **会话持久性风险（待明天验证）：**`loginctl show-user` 于 17:28 UTC 显示 `Linger=no`、7 个活跃登录会话。用户级 service 目前独立于命令会话，但若所有登录会话关闭，用户级 manager 可能停止；本轮无权更改账号级 linger 设置，也没有承诺自动重启。即使中断，逐页 `predictions.jsonl`、监控和事件日志必须保留，重新检查 GPU 并在新的唯一输出目录用 `--resume-from` 补缺页；不能覆写原文件。后台运行期间 `progress.csv` 是自动检查点，Agent 离线后不会自动修改本研究文档，恢复会话应对照产物补记阶段事实。

## 2026-10-07 04:12 UTC 运行中检查点

- **状态：运行中，尚未完成。** `systemctl --user show` 返回 `ActiveState=active`、`SubState=running`、主 PID `3946380`；runner PID `3946441` 仍存活。任务自 2026-10-06 17:26:41 UTC 起持续运行约 10 小时 45 分钟；`events.log` 仍只有启动事件，没有 guard/finished。最近的逐分钟检查点为 04:11:14 UTC 的 954/13,871 页，04:12:02 UTC 直接检查预测文件为 955 条完整记录，说明任务仍在增长；定时进度允许滞后于刷盘记录。
- 对 955 条完整 JSONL 的只读核验：954 `ok`、1 `error`；无重复 ID、无清单外 ID，现有页面顺序严格等于固定 manifest 前缀；尚余 12,916 页未产生终态。错误页为 `PMC10293395_page_18.jpg`，记录 `ValueError: layout list contains a non-object element`（该页耗时 582.34 秒）。另有 78 页累计 92 条 `invalid_table_html` 警告；目前页级表格计数 167，仅用于运行诊断，不代表跨页恢复分数。失败页按终态计覆盖，后续评分须单列。
- GPU0 即时显存占用 57,616 MiB、余 23,423 MiB、利用率 40%；`gpu-memory.csv` 截至检查有 3,836 个采样，峰值占用 57,616 MiB、最低余量 23,423 MiB。尚未触发 8 GiB 保护阈值；不要将整卡显存峰值归因于本模型的独占显存。
- 现阶段平均推进约 89 页/小时（955 页 / 约 10.75 小时）。若速度不变，剩余页需要约 145 小时；这是容量粗估而非完成时间承诺，不能因为明天未完成就误判中断。下次按 unit、`events.log`、实时预测条数及近期 `progress.csv` 增量核验；中断按原记录只在新目录补跑。
- 仍未完成全量覆盖、预测最终 SHA-256、文档级跨页合并与评分；本次不生成中途模型成绩。

## 2026-10-10 02:41 UTC 中断核验

- **状态：失败/中断，不是全量完成。** `events.log` 明确记录 2026-10-09 06:54:01 UTC 结束、`exit_code=1`、`pages_written=6151`、`expected=13871`；2026-10-10 02:41 UTC 核验用户级 unit 为 `ActiveState=failed`、`Result=exit-code`、`ExecMainStatus=1`，原 wrapper/runner PID 均不存在。GPU0 即时显存占用 32,302 MiB、剩余 48,737 MiB；不再占用本轮推理显存。
- 保存的 `predictions.jsonl` 共 6,151 条/6,151 个唯一 ID，全部是可解析 JSONL 且以换行结束；严格等于原 13,871 页清单前缀，没有重复或清单外 ID。状态 `ok=6149`、`error=2`，累计 warning 条目 522；**剩余 7,720 页没有终态记录**。最后完成页 `PMC11156423_page_9.jpg`；下一个待推理页 `PMC11157072_page_0.jpg`。失败页也保留为终态，后续不得默默改为成功。
- 停止原因的直接证据：`inference.log` 最后记录 `PredictionRecord.elapsed_sec` 校验失败，得到负耗时 `-27.142` 秒。推理脚本当前用 `time.time()` 计算耗时，`PredictionRecord` 要求耗时非负；构造 `ok` 记录失败后在 `except` 路径再次构造 `error` 记录仍使用同样的负耗时，异常传播并终止进程。**推断**：系统墙上时间在该页推理期间发生回退；时间回退的外部原因/精确事件尚未独立核验，不应归因于 GPU、显存或模型输出内容。该待推理页没有写入预测文件。本轮 GPU 采样 21,938 次，整卡峰值已占 57,616 MiB、最低剩余 23,423 MiB；事件日志没有 GPU 保护中止记录。
- 证据路径：`logs/baselines/dots-ocr/20261006T172527Z-dots-full-val/{events.log,inference.log,gpu-memory.csv,progress.csv}`；预测文件 `outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl`。预测 SHA-256 `76d318a1b51406c3d6fae65f15b875ca7ca70092bb8bbdbf3eb4e9e793e1d57e`；事件日志 SHA-256 `0550ce5a6b7bd0499f95a6759f62d5fbac3555a109b9c56c17aee56a4c8f5878`。原始文件保持不变。
- **下一步（尚未执行）：**先用可重复的单元测试修复耗时计算（考虑单调时钟）并确认异常分支也不会引起次生校验错误；重新核查 GPU 和输入/输出哈希，然后在**新运行 ID/新输出目录**使用 `--resume-from` 指向此预测文件，只补剩余 7,720 页。合并后核对 13,871 页唯一覆盖、错误和警告，再开展离线跨页恢复与评分；不能把本次 6,151 页写成正式完整成绩。
