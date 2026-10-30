# OCRFlux Full Documents 全量验收与运行说明

日期：2026-10-30（Asia/Shanghai，日志为UTC）。验收在02:14:46 UTC完成；用户授权后已于03:24:57 UTC启动全量，首条真实GPU预测通过，运行中。RUN_ID `20261030T032500Z-ocrflux-val-full`，当前状态与日志见 [全量实验](experiments/2026-10-30-ocrflux-full-val-inference.zh-CN.md)。下文保留可用于新run的启动/恢复模板，当前仅对应OCRFlux-3B，不代表MinerU-Popo就绪。

## 已验收的完整流程

复用官方页面识别、续接检测、表重建提示与函数，不执行含eval的原始parse。整篇图像PDF全部页面输入→逐页预测→同批页面生成no_merge/merged→来源链→统一CPU评分。命名 `OCRFlux-official-API-instrumented`；不宣称原CLI字节级复现。

3篇train共10页（包括4个无表页）已全部完成且页面错误0，两组评分覆盖missing/extra/duplicate=0；均有1项非法HTML，保留原输出和评分诊断。首个正例来源[1,2]合并，第二个正例存在模型漏识别，负例未形成多页表。小样本用于接口验收，不能宣称正式性能。

正式全量入口另执行4页train pilot完成，并在新run恢复：resumed_documents=1，没有创建documents目录、没有新GPU调用；两组document-tables的SHA与首run相同。31份检查点相关文件全部重算SHA通过。

最终v3服务器22项新增测试加7项恢复回归和3项打包回归，共32项通过；本地29项相关测试及ruff通过。v3完整val预检通过935篇/13,871页：完整输入成员/JPEG头、模型15文件大小/SHA、安装的官方源码与固定revision源文件、环境freeze及代码SHA全部核验。独立复核的GPU异常传播与长文档词法页序两项P1均已修复并通过对应回归。

## 协议与证据

- 本地代码commit：`6856155`，身份zgjdev；服务器使用下述已核验隔离源码，原分支未切换。本轮尚未推送GitHub。
- 数据：PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`；image-only，train开发、val正式比较，test未使用。GT只进入离线评分，不提供给模型或adapter。
- 模型：OCRFlux-3B revision `e68592278bbc8ab32edf7b65e6e411f1d878ef72`；官方代码 `c1b315aa4c8309f8dc436a5d90fc4977bcf0d865`。
- 固定环境：`.venvs/20261029T162200Z-ocrflux/`，Python3.11、torch2.5.1+cu124、vllm0.7.3、transformers4.50.0、Poppler26.10.0；freeze SHA `842cb1c8896026a0652a4be982523a4a2c3c40548bfd7f9e7cae2aff4971786e`。
- GPU0单卡，TP1/bfloat16/显存预算0.20/max_model_len16384/max_num_seqs1/enforce_eager、image1/video0；seed0/temp0/max_tokens8192/max_page_retries0，官方最长边1024。
- 验收归档根：`artifacts/ocrflux-prep/20261030T015400Z/`；`train-scores-v3/summary.json`含最终适配评分命令与SHA，`acceptance/final-full-preflight-v3.json`及`final-audit-v3.json`含最终协议和恢复核验。旧版验收证据仍保留。
- 原预测：`outputs/baselines/ocrflux-3b/20261030T015400Z-ocrflux-train-smoke/`。
- 最终实际pilot/恢复：`artifacts/ocrflux-document-runs/20261030T015400Z-ocrflux-full-entry-{pilot,resume}-v3/`。
- 服务器已冻结可执行源码：`artifacts/ocrflux-prep/20261030T015400Z/full-source-v3/`，不覆盖服务器原分支src/scripts。完整经过与失败现场见 [实验记录](experiments/2026-10-30-ocrflux-runtime-and-smoke-readiness.zh-CN.md)。

## 全量启动与恢复模板

阶段是validation推理，目的是取得935篇完整文档两组可复现预测。输入为已有val原始JPEG和冻结清单；输出为新的按文档检查点、原始响应、两组评分输入与日志。不下载数据、不修改原始数据，使用GPU0。推理结束后另做两次CPU正式评分；自动导出不等于已评分。

启动前重新查询GPU和已有进程；启动空余显存需至少30,000MiB，请求前低于8192MiB停止。共享GPU不是独占。后台任务依赖本用户Linger状态，启动前须核验，不因技术ready而自行改变系统设置。没有自动定期监控。

以下命令在服务器项目根目录执行，`RUN_ID`每次必须新建，不复用已有目录：

```bash
cd /data01/public/zhengguojie/paper
nvidia-smi --query-gpu=index,memory.free,utilization.gpu --format=csv
nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv
loginctl show-user zhengguojie -p Linger
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-ocrflux-val-full"
mkdir -p logs/ocrflux-launchers
mkdir "logs/ocrflux-launchers/$RUN_ID"
STAGE=/data01/public/zhengguojie/paper/artifacts/ocrflux-prep/20261030T015400Z/full-source-v3
systemd-run --user --unit="paper-$RUN_ID" \
  --property=Type=exec --property=Restart=no \
  --property=WorkingDirectory=/data01/public/zhengguojie/paper \
  --property="StandardOutput=append:/data01/public/zhengguojie/paper/logs/ocrflux-launchers/$RUN_ID/full.log" \
  --property=StandardError=inherit \
  --setenv="PYTHONPATH=$STAGE/src" \
  /data01/public/zhengguojie/paper/.venvs/eval312/bin/python -u \
  "$STAGE/scripts/run_ocrflux_document_full.py" \
  --project /data01/public/zhengguojie/paper \
  --images '/data01/public/zhengguojie/paper/data/pubtables-v2/extracted/Full Documents/val/images' \
  --manifest /data01/public/zhengguojie/paper/artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl \
  --manifest-sha 2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd \
  --expected-pages 13871 --expected-documents 935 --split val --run-id "$RUN_ID"
```

先只验证输入/协议时，在脚本参数末尾加`--preflight`，不调用GPU、不创建结果目录。实际启动须保存RUN_ID、PID、unit、起止和输入协议，更新三层记录；不能以unit启动即认为推理成功。

中断后使用新RUN_ID，在同一命令末尾增加 `--resume /data01/public/zhengguojie/paper/artifacts/ocrflux-document-runs/旧RUN_ID`。已完成文档经SHA核验后跳过，不完整文档在新目录重跑；协议不同拒绝恢复。原run所有文件保留。

## 限制

仅对表格分支保存最终评分对象，不把段落续接字符串当表格合并；重建失败保留原表片段并记录错误，与原CLI普通字符串连接的失败行为不同。逐页顺序生成而非整文档批量请求；没有改提示或用val GT调参。官方最坏情况context警告仍可能出现，实际train请求通过但不能保证任意长页均生成成功；截断和解析失败按错误记录。

当前train 10页用时约7分钟量级。全量13,871页、共享GPU负载和长表差异明显，且每篇独立加载模型；只能粗估约一周量级，正式启动后的完整文档吞吐更适合更新预计时间。技术ready不表示模型效果已达标。
