# dots.ocr Full Documents/val 断点补跑与计时修复

## 当前状态

2026-10-10 02:52 UTC：**断点补跑运行中**，已验证首两条新记录，尚未完成全页覆盖。本次仅在原 13,871 页 validation 固定清单上补足缺失的 7,720 页；不是新的测试集实验，也不是跨页合并评分。

## 输入和修复依据

- PubTables-v2 Full Documents/val revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，全部 935 篇、13,871 页；固定输入清单 `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl`，SHA-256 `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`，不以真值选页。
- `image-only`，本地 `checkpoints/dots-ocr` 模型 revision `c0111ce6bc07803dbc267932ffef0ae3a51dc951`；`max_new_tokens=24000`、`do_sample=False`，无采样随机种子；无数据、模型下载或原始数据修改。
- 原运行 `20261006T172527Z-dots-full-val` 于 2026-10-09 06:54:01 UTC 因负耗时校验失败中断；旧预测 `outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl` SHA-256 `76d318a1b51406c3d6fae65f15b875ca7ca70092bb8bbdbf3eb4e9e793e1d57e`，保存 6,151 条唯一且等于输入前缀的记录（6,149 `ok`、2 `error`）。本次以 `--resume-from` 将其作为只读历史输入，不覆盖旧文件；下一页 `PMC11157072_page_0.jpg`。
- 修复只涉及 `elapsed_sec`：原 `time.time()` 易受墙上时钟调整影响，改用 `time.monotonic()`；即使异常分支出现时钟计时异常也钳制为非负。提示词、模型权重、输入和生成参数不变。旧输出和错误状态仍作为原始证据保留，不回填/修改。
- 代码 HEAD `007b8fd9a02ae5bf2e8361e1a1a1c074da9bb32d`，计时修复尚未提交；`scripts/evaluate_dotsocr_pubtables_v2.py` SHA-256 `5d5685aebaa8624599101d1aab6b781f93a3b912b0e1d33273e0b33192f4af87`，`scripts/run_dotsocr_full_val_background.sh` SHA-256 `4b2d8f4555237cd6c1a11ed7a42e154ae4506205e51e1529d46eb4fab84eaeb6`。项目 `.venvs/eval312`：Python 3.12.7、PyTorch 2.6.0+cu124、transformers 4.51.0、CUDA runtime 12.4；复用物理共享 GPU0，正式启动前再次检查显存/进程。
- 回归：`PYTHONPATH=src:third_party/grits-main .venvs/eval312/bin/python -m pytest -p no:cacheprovider --basetemp=artifacts/test-runs/20261010-resume-full-01 -q` 得到 **151 passed**；Ruff check/format、`bash -n`、`git diff --check` 通过。只读预检确认原历史文件 SHA、6151 行与 13,871 页清单，并检查 GPU0 至少 30,000 MiB 空余；模型加载后仍需验证首条新页和显存。

## 拟启动与运行保护

运行 ID `20261010T024700Z-dots-full-val`，用户级 unit `paper-dots-full-val-20261010T024700Z.service`。拟执行命令：

```bash
mkdir -p logs/baselines/dots-ocr/20261010T024700Z-dots-full-val
systemd-run --user --unit=paper-dots-full-val-20261010T024700Z \
  --working-directory="$PWD" \
  --property="StandardOutput=append:$PWD/logs/baselines/dots-ocr/20261010T024700Z-dots-full-val/launcher.log" \
  --property="StandardError=append:$PWD/logs/baselines/dots-ocr/20261010T024700Z-dots-full-val/launcher.log" \
  /usr/bin/bash scripts/run_dotsocr_full_val_background.sh 20261010T024700Z-dots-full-val \
    --resume-from outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl
```

新预测只写到 `outputs/baselines/dots-ocr/20261010T024700Z-dots-full-val/predictions.jsonl`。日志和监控仅写新目录 `logs/baselines/dots-ocr/20261010T024700Z-dots-full-val/`，缓存限于项目内新时间戳目录。后台入口按分钟写 `progress.csv`（**历史 6,151 + 新分片行数**），每 10 秒采样 GPU0；剩余显存 <8 GiB、CUDA OOM、连续 3 页错误或 90 分钟无新增页时仅终止自己的推理进程，保留历史与新分片。`Linger=no` 仍是潜在会话持久性风险；无自动重启保证。

## 验收与限制

启动后须核验 unit/runner PID、首条预测属于 `PMC11157072_page_0.jpg`、无重复、进度与显存监控持续更新。完成后联合两个分片检查 13,871 页每页恰有一条终态，missing/extra/duplicate 均为 0，分别报告 `ok`、`error`、warning、文件 SHA-256，再离线做跨页合并与评分。此阶段无正式模型分数。运行状态/PID/产物待启动后实填，不用计划替代证据。

## 实际启动

- 2026-10-10 02:49:53 UTC 启动前复核 GPU0：已占 32,302 MiB、剩余 48,737 MiB、瞬时利用率 0%，已有 4 个计算进程；只使用共享 GPU0，不终止现有进程。
- 02:50:03 UTC 通过上述 `systemd-run --user` 命令启动；unit `paper-dots-full-val-20261010T024700Z.service` active/running，wrapper PID `3225365`、runner PID `3225408`。`events.log` 记录原预测 SHA `76d318a1b51406c3d6fae65f15b875ca7ca70092bb8bbdbf3eb4e9e793e1d57e` 和历史页数 6,151；02:50:04 UTC 首个 GPU 采样已写入。首条新预测尚待核验，不宣称补跑已经产生完整数据。
- 02:52:57 UTC 检查点：新分片已刷盘 2 条，`PMC11157072_page_0.jpg` (`ok`, `elapsed_sec=61.773`) 与 `PMC11157072_page_1.jpg` (`ok`, `elapsed_sec=35.264`)；JSON 解析与固定 manifest 第 6,152、6,153 页逐条相符，新记录内部无重复。`progress.csv` 02:52:55 UTC 更新为历史加新页共 **6,153/13,871**，尚缺 7,718 页。旧分片 SHA-256 重算未变；unit 仍 active/running、wrapper PID `3225365`，GPU0 在 02:52:45 UTC 采样已用/空余 48,446/32,593 MiB。尚未做完整联合去重/评分，运行结束和完整覆盖待核验。

## 2026-10-11 05:16 UTC 中断核验

- **已提供：**`events.log` 记录 2026-10-10 08:59:38 UTC GPU0 空余仅 47 MiB，显存保护终止自身 runner；`finished` 记录退出码 143。2026-10-11 05:16 UTC `systemctl --user show` 确认 unit `failed/failed`、`MainPID=0`，原 wrapper/runner PID 均已退出。最近一次 `nvidia-smi` 快照 GPU0 空余 32,289 MiB；这只是瞬时值，不能据此认定可立即重启。
- **已提供：**旧分片 6,151 行（6,149 `ok`、2 `error`），新分片 636 行（全部 `ok`）；两段 JSON 均可解析，ID 拼接严格等于固定 manifest 前 6,787 页，重复 0、清单外 0，尚缺 **7,084 页**。最后已保存页 `PMC11233398_page_4.jpg`，下一页 `PMC11233398_page_5.jpg`。旧预测 SHA-256 仍为 `76d318a1b51406c3d6fae65f15b875ca7ca70092bb8bbdbf3eb4e9e793e1d57e`，新预测 SHA-256 为 `1765dc4c23dec7bafe3b5a673458ad004a8f5185b89427281e865510dccd0e79`；原文件均不修改。
- **已提供/限制：**`launcher.log` 多次显示 `rg: command not found`；后台 service 的 `PATH` 未覆盖 `rg`，导致脚本中 CUDA OOM 文本和连续三页错误的日志告警检查不能按预期工作。本次显存余量保护仍明确触发，但下次启动前必须修复监控依赖并验证。显存突降来自哪个进程尚待核验，不归因于其他用户，也不终止其他进程。
- **下一步：**先修正并测试监控依赖/资源门禁，重新检查 GPU 上正在运行的进程与显存，再以全新时间戳目录、两个旧分片只读断点输入补剩余页；不得覆写任一分片，也不得将当前部分覆盖报告为全量评分。

## 2026-10-11 远端 GPU 候选核验

- 用户提出使用 `172.17.62.73`；仅尝试只读 SSH GPU/身份查询，`ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=yes 172.17.62.73 'id -un; hostname; nvidia-smi ...; date -u +%FT%TZ'` 在主机密钥校验阶段被拒：`No ED25519 host key is known for 172.17.62.73`，退出码 255。此时尚未验证远端账号认证、GPU、数据或模型是否存在，**未访问远端文件、未上传、未启动任务**。
- 本机 SSH 配置检查未见指向该 IP 的可用 `73`/`server73`/`gpu73` 别名；当前 SSH 客户端与用户 VS Code 的配置不一定共享。下一步需通过可信渠道核对远端主机密钥指纹与可用账号/连接配置，不禁用主机密钥校验；连接后才可只读审计远端 GPU、权限、可用存储，以及是否具备相同权重和数据，再设计无覆写的数据迁移与断点补跑。
- 后续用户通过已连接的 VS Code 73 终端提供 ED25519 指纹；本机 `ssh-keyscan` 返回的公钥指纹与其一致，匹配值保存在项目内 `artifacts/ssh-known-hosts/20261011-server73-ed25519`（**仅公钥，无私密凭据**）。用该信任文件、严格主机密钥校验和 `BatchMode=yes` 重试 `zhengguojie@172.17.62.73`，返回 `Permission denied (publickey,password)`，说明主机校验已通过、当前机器没有免交互认证能力。仍未取得远端 GPU/文件状态，未使用、保存或重发用户提供的密码；建议经已登录的 VS Code 远端终端只读查询 GPU，或安全配置 SSH 密钥登录。
- 2026-10-11 用户提供的 73 服务器终端 `nvidia-smi` 输出为 `Unable to determine the device handle for GPU0000:01:00.0: Unknown Error`。**已提供：**该命令未返回 GPU 资源清单；**待核验：**错误根因及该机是否还有可用 GPU。不能据此宣称该机可运行或已确认硬件故障；下一步由用户在已登录远端终端只读执行 `nvidia-smi -L` 与 `lspci -nn` 的 NVIDIA 设备过滤，必要时再经授权查看相关系统日志。未在远端启动测试或迁移数据。
- 2026-10-11 05:37 UTC 用户追加提供 73 终端 `nvidia-smi -L` 与 `lspci -nn | grep -i nvidia` 输出：PCI 共枚举 5 张 RTX 3090；GPU 0（`01:00.0`）和 GPU 2（`3e:00.0`）报告 `Unable to determine the device handle`，两者 PCI revision 显示 `ff`；GPU 1、3、4 均列出 UUID，PCI revision 显示 `a1`。**推断：**候选仅 GPU 1/3/4，GPU 0/2 暂不可用于推理；**待核验：**三张候选卡的显存、现有任务、驱动实际可计算性及故障原因。本机仍无法免交互远程登录；尚未上传数据或模型、未在远端启动实验。
- 2026-10-11 05:39 UTC 用户提供 73 终端 `nvidia-smi -i 1,3,4 --query-gpu=...` 和 `--query-compute-apps=...` 快照：GPU1/4 各剩 24,240 MiB、已用 13 MiB、利用率 0%，未列计算进程；GPU3 剩 21,765 MiB、已用 2,488 MiB，列出 1 个约 2,472 MiB 的计算进程，利用率 0%。这是**用户提供的瞬时快照**，不是独占授权或稳定显存保证。旧 A100 三页 smoke 的整卡采样增量为 16,644 MiB（见 `docs/experiments/2026-10-06-dotsocr-full-documents-gpu0-smoke.zh-CN.md`），仅作粗略容量推断：若 RTX 3090 用量相近，GPU1/4 余量约 7,596 MiB，低于现有脚本 8,192 MiB 停机阈值；模型峰值可能因设备和输入变化，**不得直接沿用 A100 数据断言 3090 能跑全量**。迁移前须核验远端权重/输入/依赖与可访问性、修复两个旧分片续跑及后台 `rg` 监控，在 GPU1 或 GPU4 上先做显存受控短试跑，评估真实峰值与保护门限后再决定全量。不触碰 GPU0/2 故障卡或 GPU3 现有进程。

## 2026-10-12 11:29 UTC 本机只读资源检查

- `nvidia-smi --query-gpu=...`：本机 GPU0/1/2/3 均为 A100-SXM4-80GB，已用显存分别 47,046/80,615/60,470/58,494 MiB，空余 33,993/423/20,569/22,545 MiB，瞬时利用率 60/0/33/59%；计算进程数分别 5/1/10/10。快照只代表检查时刻，不能推定稳定独占资源。
- `systemctl --user show paper-dots-full-val-20261010T024700Z.service` 仍为 `failed/failed`、`MainPID=0`；两分片分别 6,151/636 行，累计 6,787/13,871 页，较上次无新预测。本轮只读检查，未重启、未下载或修改原始数据；需先修复恢复入口与监控，再审查共享 GPU 窗口。

## 2026-10-17 08:14 UTC 本机只读资源检查

- `nvidia-smi --query-gpu=...` 显示本机四张 A100-SXM4-80GB GPU0/1/2/3 已用 40,460/80,615/55,696/58,278 MiB，空余 40,579/423/25,343/22,761 MiB；四卡瞬时利用率均为 0%，但分别列有 4/1/10/10 个计算进程。GPU0 当前显存余量高于上次快照，不等于独占空闲或稳定窗口。
- `paper-dots-full-val-20261010T024700Z.service` 仍为 `failed/failed`、`MainPID=0`；原两分片分别 6,151/636 行，共 6,787/13,871 页，**无新结果**。本轮仅核对状态，未运行模型、下载或修改原始数据；重启前仍须修复双分片恢复和后台监控，并重新评估共享资源。
