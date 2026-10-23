# PaddleOCR-VL-1.5 Full Documents validation 全量推理

日期：2026-10-23（Asia/Shanghai；运行时刻记UTC）。状态：**后台GPU推理运行中，首3页预测已核验**。用户明确确认“启动全量，并授权配置后台保活”。本轮不下载数据或权重，不修改原始输入，不启动训练，不读取GT调参。

## 研究问题、输入和冻结协议

目标：获得完整文档image-only页面解析及跨页恢复基线。数据为PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`、validation **935文档/13,871页**，包括所有无表页；不提供真值框、文字、续表标签或已知同表片段。赛道image-only。

输入原图目录 `data/pubtables-v2/extracted/Full Documents/val/images/`；完整输入清单 `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl`，源SHA `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`，按数字页码排序的派生SHA `1d39ca16b7fcfedf3dabb174c80ef4ae914d90a76a2839617a469c0ba75e90c5`。不改成员，只改管线所需页序；逐文档生成无文字层PDF，原JPEG嵌入字节一致并保存来源SHA。

PaddleOCR-VL-1.5模型 revision `2a4195faa5e7914c12f2fc601d72c81caf8d2da5`，路径 `models/20261023T064109Z-public-models/paddleocr-vl-1.5/`；版面组件PP-DocLayoutV3 revision `241f8bdfc77a7c7bee915a5057aaee58c235a8d3`，路径 `models/20261023T081029Z-paddle-layout/pp-doclayoutv3/`。PaddleOCR3.4.0、PaddleX3.4.1、PaddleGPU3.2.1/cu118、NumPy1.26.4、Python3.12；父进程eval312，native worker环境 `.venvs/paddle-v15-20261023T081029Z-paddle-v15/`。GPU0为共享A100 80GB；驱动550.127.08（既有环境核验），启动快照空余39,607MiB、已有4个计算进程；没有终止其他进程。

代码启动commit `b20324898cd8acfbb3b06e2eee0b100890988ee4`，分支 `codex/paddle-merge-compat`，冻结逻辑实现commit b390273。seed0、page/layout/VLM batch=1、use_queues=False、方向与去畸变关闭；生成参数使用官方默认。保留no_merge和官方native_merge，content-compatible后处理之后CPU单列，不改官方包，不混称原版成绩。完整参数、真实train正负例、76测试、断点及代码审查证据见 [启动门禁](../2026-10-23-paddle-full-validation-readiness.zh-CN.md)。

## 后台保活授权与实际启动证据

服务器用户 `zhengguojie`；按本轮明确授权执行 `loginctl enable-linger "$(id -un)"`，返回0，`loginctl show-user ... -p Linger` 从no变为 **yes**。仅为该用户启用用户服务保活，未读取/修改其他用户文件或系统目录内容。该授权是项目根目录外系统设置的特定例外，不扩大其他访问权限。Linger使用户服务不依赖登录会话存续，不保证断电、重启、OOM或资源变化后自动恢复；本任务Restart=no，中止后依checkpoint用新RUN_ID恢复。

任务 `20261023T152753Z-paddle-val-full`；实际服务启动 **2026-10-23 15:28:13 UTC（北京时间23:28:13）**。用户unit `paper-paddle-full-20261023T152753Z.service`，初始父PID **3358795**，启动核验active/running；尚未据父进程active冒称已写出GPU预测。

已执行启动命令：

```bash
cd /data01/public/zhengguojie/paper
systemd-run --user --unit=paper-paddle-full-20261023T152753Z \
  --property=Type=exec --property=Restart=no \
  --property=WorkingDirectory=/data01/public/zhengguojie/paper \
  --property=StandardOutput=append:/data01/public/zhengguojie/paper/logs/paddle-launchers/20261023T152753Z/full.log \
  --property=StandardError=inherit --setenv=PYTHONPATH=src \
  /data01/public/zhengguojie/paper/.venvs/eval312/bin/python -u \
  scripts/run_paddle_document_full.py --run-id 20261023T152753Z-paddle-val-full --gpu 0
```

## 产物、完成条件与恢复

- 总入口日志 `logs/paddle-launchers/20261023T152753Z/full.log`；后台启动前确认新日志目录和run根不存在，无覆盖。
- run根 `artifacts/paddle-document-runs/20261023T152753Z-paddle-val-full/`；其中run-manifest记录冻结protocol、checkpoints每文档原子发布并记录完整产物SHA、inputs存逐文档派生PDF/来源manifest、`<document_id>.log`存native worker输出。
- 原始预测/原版重组 `outputs/baselines/paddleocr-vl-1.5/20261023T152753Z-paddle-val-full-<document_id>/`；worker manifest/config/GPU采样在对应 `logs/baselines/paddleocr-vl-1.5/`。
- GPU启动门槛空余20,000MiB，worker逐页低于8,192MiB保护退出；不自动杀其他用户进程或无限重试。
- 完成须summary.status=completed、935文档/13,871页及最终export-complete、源/排序后清单SHA正确。再核对missing/extra/duplicate、每页终态、非法HTML及来源页；当前没有全量正式分数。
- 中断保留已发布checkpoint和所有部分结果。恢复需新的UTC run ID，追加 `--resume-from artifacts/paddle-document-runs/20261023T152753Z-paddle-val-full`；若有更多续跑段，全部传入不重叠历史段，核验protocol和产物SHA后跳过完整文档，不覆盖旧run。

时间预期仅为数天量级，不以少量train速度承诺完成时刻；首批val实际耗时可再估。按用户既有偏好，本轮不创建定期监控/自动通知；任务在服务器独立执行，后续由用户请求检查进度。首条GPU产物与运行检查点将在本轮结束前追加。

## 15:30 UTC（北京时间23:30）GPU启动核验

总日志已打印完整val935/13,871预检ready，与冻结protocol各项SHA一致。首篇PMC10154845全8页已打包，`pdf_text_audit=empty`、`embedded_image_audit=byte-identical`。native worker的run-manifest明确 `split=val`、`input_track=image-only`、seed0、commit b203248；保存到对应logs目录。

`outputs/baselines/paddleocr-vl-1.5/20261023T152753Z-paddle-val-full-PMC10154845/pages.jsonl` 首3条完整JSON可解析，page_index=[0,1,2]、page_count均8、无尾部残片。日志首次 `page_complete` 在15:29:04.879 UTC，page1在15:29:43.574 UTC。当前已完成文档checkpoint=0，正在处理首篇，不能声称3页已成为可跳过的完整文档；恢复粒度为整文档。

运行状态仍active/running、父PID3358795。最近GPU0空余34,353MiB、整卡占用46,686MiB、利用率27%；共享卡采样不是本任务严格峰值。原4个计算进程未终止。已核验真实页面产物，而非仅依赖服务active作推理已开始的判断。run根 `run-manifest.json` SHA-256 `32051311a3782e999230ad746447ae72ee5527a82595fb4e5b80dc6802d10c0d`。

目前约3/13,871页的启动快照，无正式全量指标；不得按首篇少量页面给精确完成时刻。开启Linger已授权且核验yes，关闭客户端不要求此对话持续运行；机器重启/断电/资源保护等仍可能中止任务。后续每次检查先核验unit、checkpoint及日志，再记录覆盖和异常，不因未更新对话而重跑已有完成文档。
