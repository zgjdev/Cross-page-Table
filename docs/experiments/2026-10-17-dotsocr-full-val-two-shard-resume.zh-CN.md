# dots.ocr Full Documents/val 双分片断点补跑

## 状态与研究问题

2026-10-20 01:52 UTC 核验：**本轮 GPU0 双分片断点补跑已于 2026-10-19 17:20:05 UTC 触发显存保护中断**，页级输出尚未覆盖全量。目标是在 PubTables-v2 Full Documents/val 上补足完整文档的 dots.ocr `image-only` 页级输出，然后单独开展文档级跨页恢复与评分；本阶段不是正式跨页模型分数。

## 固定输入与协议

- 数据集 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`；validation 935 篇、13,871 页，全部输入、不按真值筛页。清单 `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl`，SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`；图片位于 `data/pubtables-v2/extracted/Full Documents/val/images`，只读。
- dots.ocr 本地权重 `checkpoints/dots-ocr`，revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`；`max_new_tokens=24000`、`do_sample=False`、无采样随机种子；不下载数据/模型、不修改原始输入。代码 HEAD `007b8fd9a02ae5bf2e8361e1a1a1c074da9bb32d` 加工作区未提交计时修复及入口修复；推理脚本 SHA-256 `5d5685aebaa8624599101d1aab6b781f93a3b912b0e1d33273e0b33192f4af87`；入口 SHA-256 `1cc652de2656fcf2fc61ab975a50feb604bf86c2d57a144366f74915c554638d`。环境 `.venvs/eval312`，Python 3.12.7、PyTorch 2.6.0+cu124、transformers 4.51.0、CUDA runtime 12.4；GPU0 A100 80GB 共享使用，启动前须复核显存和既有进程。
- 两段只读历史输入：`outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl`（6,151 页、SHA-256 `76d318a1b51406c3d6fae65f15b875ca7ca70092bb8bbdbf3eb4e9e793e1d57e`）和 `outputs/baselines/dots-ocr/20261010T024700Z-dots-full-val/predictions.jsonl`（636 页、SHA-256 `1765dc4c23dec7bafe3b5a673458ad004a8f5185b89427281e865510dccd0e79`）。联合 6,787 页前缀、无重复，`ok=6,785`、`error=2`；下一个待推理 `PMC11233398_page_5.jpg`，剩 7,084 页。原产物不覆写；历史错误记录保留其原状态。

## 预检与保护

- 后台脚本 `scripts/run_dotsocr_full_val_background.sh` 现在要求顺序正确的最多两段固定历史文件，逐段校验 SHA-256/行数，并用 JSON 解析核对联合 ID 与 manifest 前缀；传递全部 `--resume-from` 给已支持多分片的 runner。监控日志匹配改为系统 `grep`，保留 GPU0 空余 <8 GiB、OOM、连续三页错误、90 分钟无新增页及 `nvidia-smi` 连续失败保护；仅终止自己的 runner。
- 2026-10-17 08:17:42 UTC，双分片 `--preflight` 确认 `validated recovery prefix: 6787/13871 pages`、GPU0 空余 40,579 MiB；颠倒历史分片时按预期 exit 2。`bash -n` 与 `git diff --check` 通过；全量回归命令 `PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python -m pytest -p no:cacheprovider --basetemp=artifacts/test-runs/20261017-resume-full-01 -q`，结果 **151 passed**。
- 2026-10-17 08:16:40 UTC GPU0 既有 4 个计算进程，空余 40,579 MiB；该值仅瞬时快照。`Linger=no`，所有会话结束时用户级 unit 可能停止；不能保证无人值守持续运行。启动前再核对 GPU0、固定分片、日志和新目录不存在；如既有进程显存上涨，将依保护停掉自身任务，不终止他人进程。

## 启动及验收待填

全新 `RUN_ID`、unit、PID、实际启动 UTC、完整 `systemd-run` 命令、日志及输出目录在启动后追加。入口命令格式：

```bash
bash scripts/run_dotsocr_full_val_background.sh "$RUN_ID" \
  --resume-from \
  outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl \
  outputs/baselines/dots-ocr/20261010T024700Z-dots-full-val/predictions.jsonl
```

预期新分片首条为 `PMC11233398_page_5.jpg`。启动后检查 unit/runner、监控采样、首条记录和旧分片 SHA 不变；结束后联合三分片核验完整 13,871 页、ID 无重复/缺失/额外、分别报告 `ok`/`error`、warning、产物 SHA 与失败案例，再进行离线跨页合并/评分。未覆盖全页前不得声称完成评估。

## 实际启动

- 2026-10-17 08:18:59 UTC 复核 GPU0 已用/空余 40,460/40,579 MiB，4 个已有计算进程；两段历史分片 SHA-256 均未变化，旧 service 为 failed、未运行。
- 08:19:12 UTC 启动新 `RUN_ID=20261017T081912Z-dots-full-val`，unit `paper-dots-full-val-20261017T081912Z.service`，`systemd-run --user` 在项目工作目录执行：

```bash
systemd-run --user --unit=paper-dots-full-val-20261017T081912Z.service \
  --working-directory="$PWD" \
  --property="StandardOutput=append:$PWD/logs/baselines/dots-ocr/20261017T081912Z-dots-full-val/launcher.log" \
  --property="StandardError=append:$PWD/logs/baselines/dots-ocr/20261017T081912Z-dots-full-val/launcher.log" \
  /usr/bin/bash scripts/run_dotsocr_full_val_background.sh 20261017T081912Z-dots-full-val \
    --resume-from \
    outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl \
    outputs/baselines/dots-ocr/20261010T024700Z-dots-full-val/predictions.jsonl
```

- 08:19:13 UTC `events.log` 记录固定清单 SHA、两段历史 SHA 和 `historical_pages=6787`，启动 GPU0 空余 40,579 MiB；unit active/running，wrapper PID `2239841`、runner PID `2239881`。新预测只写 `outputs/baselines/dots-ocr/20261017T081912Z-dots-full-val/predictions.jsonl`；监控日志 `logs/baselines/dots-ocr/20261017T081912Z-dots-full-val/`，缓存/临时文件均在项目内以新 ID 命名。首条新预测及结束状态待核验；用户级 service `Linger=no`，不保证会话消失后持续运行。
- 08:21:18 UTC 首条新预测 `PMC11233398_page_5.jpg` 落盘，`status=ok`、`elapsed_sec=46.657`、无 warning。JSON 解析三分片时联合 6,788 页，ID 唯一 6,788、完全匹配固定 manifest 前缀，剩余 7,083 页；两个旧分片 SHA-256 重算均保持不变。08:22:04 UTC `progress.csv` 已更新为 6,788/13,871，与落盘量一致；08:22:25 UTC GPU0 已用/空余 57,628/23,411 MiB，unit 仍 active/running。当前仅验证恢复点和监控，不代表全页已完成；后续如中断保留第三分片以便再恢复。
- 08:26:38 UTC 检查点：第三分片已刷盘 7 条、均 `ok`，新 ID 无重复且逐条匹配 manifest 从第 6,788 页起的前缀；联合 **6,794/13,871**，剩余 7,077 页，最新 `PMC11235342_page_1.jpg`。`progress.csv` 08:26:07 UTC 的 6,793 页略早于第 7 条刷盘，正常采样滞后。unit 仍 active/running，GPU0 最近空余 23,411 MiB；新 `launcher.log` 未见 `command not found`，两旧分片 SHA 均未变，尚无 guard 事件。保持后台运行，后续检查本文件所列 unit、日志与预测，并在完成/失败时补记最终状态和联合审计。
- 08:53:30 UTC 用户询问 VS Code 是否可关闭；只读检查 unit 仍 active/running（wrapper PID `2239841`），新分片 65 行、三段累计 6,852/13,871 页（仅行数检查，未做本轮联合内容审计）。`loginctl show-user` 显示 `Linger=no`、当时存在 7 个会话；关闭一个 VS Code 连接不保证停止，但若所有用户会话结束，用户级 service 可能被停止。没有更改 linger/系统服务设置，也未停止或重启任务；若需无人值守运行，须先通过授权且符合项目目录约束的方式处理会话持久性。
- 11:09:25 UTC 只读检查：unit `active/running`、wrapper PID `2239841`；新分片已刷盘 364 条、全部 `ok`，三个分片合计 **7,151/13,871** 页（其中历史 6,787 页），剩余 6,720 页。全部 JSON 可解析，联合 ID 唯一且严格等于固定清单前缀；最近一页 `PMC11280285_page_6.jpg`、下页 `PMC11280285_page_7.jpg`。`progress.csv` 的 11:08:30 UTC 采样为 7,150 页（采样滞后于落盘），GPU0 11:09:20 UTC 已用/空余 64,812/16,227 MiB；`events.log` 暂无保护停机事件。仍在推理，无跨页合并和正式评分；继续关注 8 GiB 显存保护阈值。
- 2026-10-18 13:27:41 UTC 检查点：unit 仍 `active/running`、wrapper PID `2239841`。三分片 JSON 均可解析，分别 6,151（6,149 `ok`、2 `error`）、636（全部 `ok`）、3,505（全部 `ok`）页，合计 **10,292/13,871**，约 74.2%，剩余 3,579 页；联合 ID 无重复并严格对应固定 manifest 前缀。新分片末页 `PMC11753089_page_10.jpg`，清单下一项 `PMC11753089_page_2.jpg`（保持输入清单既定顺序，不按页号排序）。`progress.csv` 13:26:51 UTC 采样为 10,291 页，早于本次落盘核验。GPU0 13:27 UTC 已用/空余 64,812/16,227 MiB，`events.log` 未见停机事件。本轮只读核验，未改变任务或原始文件；尚无全量覆盖或跨页评分。
- 2026-10-19 09:18:34 UTC 检查点：unit 仍 `active/running`、wrapper PID `2239841`；新分片 5,813 条全部 `ok`，旧分片分别 6,151（6,149 `ok`、2 `error`）和 636（均 `ok`）。三分片合计 **12,600/13,871** 页（90.84%），仍缺 1,271 页；全部 JSON 可解析、联合 ID 无重复且严格等于固定 manifest 前缀。新分片最后 `PMC12149120_page_16.jpg`，下一个清单 ID `PMC12149120_page_17.jpg`。09:18:00 UTC 进度监控已记录 12,600 页，GPU0 已用/空余 65,914/15,125 MiB；暂无 guard/finished 事件。本轮只读检查，未更改推理/原始产物；尚未完成全页覆盖或跨页评分。
- 2026-10-19 15:19:55 UTC 检查点：unit 仍 `active/running`，wrapper PID `2239841`，未见 `finished` 或 `guard`；三段预测经 JSON 解析合计 **13,375/13,871** 页（96.42%），新分片 6,588 条全部 `ok`，历史 6,151（6,149 `ok`、2 `error`）及 636（均 `ok`）。联合 ID 无重复，严格匹配固定 manifest 前缀，剩余 **496** 页，末页 `PMC12277345_page_14.jpg`，下一页 `PMC12277345_page_15.jpg`。`progress.csv` 15:18:56 UTC 为 13,373，较实时落盘略滞后；GPU0 最新采样空余 15,125 MiB。只读核验，没有停止、重启或修改模型/原始输入；**尚未完成全量，也没有跨页合并评分**。

## 2026-10-20 01:52 UTC 中断核验

- **已提供：**`events.log` 在 2026-10-19 17:20:05 UTC 记录 `gpu0 free=7589 MiB, stopping own runner`，`finished` 为 `exit_code=143;new_pages=6844;historical_pages=6787;combined_pages=13631;expected=13871`；`systemctl --user show` 显示该 unit `failed/failed`、`MainPID=0`、结束时间同上。保护只停止自己的推理进程，未终止其他任务。该时刻 `gpu-memory.csv` 从 15,125 MiB 空余跌至 7,589 MiB；额外用显存来自哪个进程**待核验**，不能推断归属。
- **已提供：**固定 manifest 13,871 页；三段预测均可解析，分别 6,151（6,149 `ok`、2 `error`）、636（均 `ok`）、6,844（均 `ok`）。合计 **13,631/13,871 页（98.27%）**，尚缺 240 页；ID 无重复、严格等于固定 manifest 前缀，无清单外页。最后 `PMC12299400_page_7.jpg`，下一页 `PMC12305305_page_0.jpg`。已保存记录共 1,156 页带 warnings、1,311 条 warning（仅计数，类型分布待审计）。两条历史 `error` 都是 `ValueError: layout list contains a non-object element`，ID 分别 `PMC10293395_page_18.jpg` 和 `PMC10423702_page_13.jpg`；仍作为历史终态保留，不声称全部页成功。
- **产物校验：**旧分片 SHA-256 依次保持 `76d318a1b51406c3d6fae65f15b875ca7ca70092bb8bbdbf3eb4e9e793e1d57e`、`1765dc4c23dec7bafe3b5a673458ad004a8f5185b89427281e865510dccd0e79`；第三分片 `outputs/baselines/dots-ocr/20261017T081912Z-dots-full-val/predictions.jsonl` SHA-256 `90209757ffa3bf1b6ac6e3682b89a4acce46a67243227d5b67660732af43bbfa`，与后台保存的 `logs/baselines/dots-ocr/20261017T081912Z-dots-full-val/predictions.sha256` 一致。10 月 20 日 01:52 UTC GPU0 瞬时空余 39,559 MiB；不代表稳定运行窗口。本次只读审计，未重新启动、未修改任何预测/日志或原始数据。
- **下一步：**若继续补齐最后 240 页，需先核验 GPU 资源及共享进程，在**全新时间戳目录**只读复用三段已有预测，修订/检验现有后台入口目前最多只接受两个固定历史分片的限制；不得覆写原分片。完成后联合审计 13,871 页完整覆盖，单列 2 页历史错误与 warnings，再做离线跨页合并及评分；当前无正式跨页结果。
