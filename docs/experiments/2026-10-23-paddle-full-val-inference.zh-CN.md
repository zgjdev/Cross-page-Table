# PaddleOCR-VL-1.5 Full Documents validation 全量推理

日期：2026-10-23（Asia/Shanghai；运行时刻记UTC）。状态：**全量GPU推理及原始导出已完成；三组离线评分亦完成，2026-10-30核验通过，详见[评分记录](2026-10-29-paddle-full-val-three-condition-scores.zh-CN.md)**。用户明确确认“启动全量，并授权配置后台保活”。本轮不下载数据或权重，不修改原始输入，不启动训练，不读取GT调参。

## 研究问题、输入和冻结协议

2026-10-29流程说明：`scripts/run_paddle_v15_smoke.py::run_documents` 对整篇图像PDF调用predict_iter，再分别调用restructure_pages(merge_tables=False/True)，已保存官方no_merge与native_merge。输入是完整文档全页图像重打包的无文字层PDF，不是原生带文字层PDF，不给GT筛页/表框/续接关系。流程级属于文档到恢复结果的端到端评测，但技术实现为版面检测、逐页VLM识别和规则式跨页合并的分阶段管线，不是单个联合训练的跨页模型。`scripts/adapt_paddle_document_predictions.py` 将复用保存结果生成三组评分输入，兼容版仅桥接已在train核验的文字字段，不读取GT决策或重跑GPU；三组必须分列。此段仅解释现有设计和下一步，没有启动后处理/评分或产生新指标。

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

## 2026-10-24 07:05 UTC（北京时间15:05）用户触发进度检查

只读核验同一run，未重新启动、修改代码/参数、终止进程或创建定期监控。服务仍 `active/running`、MainPID3358795；运行中 `ExecMainStatus=0` 不是最终成功退出证据。

读取run-manifest及全部已发布 `checkpoints/*.json`：**108/935文档**完成，checkpoint累计 **1,631/13,871页（11.76%）**；文档重复0、额外文档0、checkpoint页数与冻结manifest不一致0。本次核验计数和身份一致性，没有重算全部已完成文件SHA；最终验收仍需完整哈希和全量覆盖检查。

当前文档 `PMC10436224` 共9页，raw `outputs/baselines/paddleocr-vl-1.5/20261023T152753Z-paddle-val-full-PMC10436224/pages.jsonl` 快照有8条完整JSONL、page_index=[0,1,2,3,4,5,6,7]，解析错误0、尾残片0。该文档尚未发布checkpoint，不能计入已可恢复的完整文档数。run根对应 `PMC10436224.log` 最新 `page_complete` 为07:05:33 UTC，较07:03:34时的page4继续增长到page7，提供实际仍在推进的证据。父summary尚未发布，最终导出与正式全量评分尚未完成。

GPU0整卡快照空余17,343MiB、占用63,695MiB、利用率55%；高于运行中逐页8,192MiB保护线，不能据此归因其他进程或承诺之后资源不变。没有修改资源保护门槛。文件mtime与日志UTC不一致，本次进度时刻依据服务器UTC查询及事件内UTC，不据文件mtime判断停滞。

从15:28:13 UTC启动至本次检查约15.6小时，按已完成checkpoint页数计算约104页/小时；若后续耗时分布和共享资源近似不变，剩余12,240页粗估约117小时，即**约5天**。这是含逐文档加载开销的全程均值外推，不是完成承诺，也不含后续CPU后处理/正式评分。下一步保持当前任务运行；后续检查先核验服务、checkpoint、当前文档页面及资源，再进行全量导出/覆盖验收和三组配对离线评分。OCRFlux和MinerU-Popo不是此run的已完成测试。

## 2026-10-25 14:31 UTC（北京时间22:31）用户触发进度检查

同一run `20261023T152753Z-paddle-val-full` 和用户service只读核验：仍active/running、MainPID3358795，ExecMainExitTimestamp=n/a。全部已发布checkpoint共357个唯一文档，冻结manifest对应935文档/13,871页；已完成 **357/935文档、4,995/13,871页（36.01%）**，较10月24日检查增加249文档/3,364页。checkpoint解析错误0、文档重复0、额外文档0、页数不一致0；仅复核身份/计数，未全量重算产物SHA或审计每页内容质量。

当前PMC11008875共15页，raw `outputs/baselines/paddleocr-vl-1.5/20261023T152753Z-paddle-val-full-PMC11008875/pages.jsonl` 已有5条完整记录、page_index=[0,1,2,3,4]，解析错误0、尾残片0；对应文档日志page_complete从14:29:28 UTC到14:31:14 UTC持续产出。当前文档尚未发布checkpoint，不计入4,995页。父 `summary.json` 尚未发布，最终导出/全量正式评分仍未完成。

GPU0整卡空余18,581MiB、占用62,457MiB、利用率52%，高于运行中8,192MiB保护线；不是本模型独占显存或峰值测量。从启动到检查约47.05小时，按4,995页全程均速约106页/小时，剩余8,876页粗估83.6小时（约3–4天），不含后续离线后处理/评分，且受文档分布/共享资源影响，不保证完成时刻。

本次没有下载、改动服务器文件/代码/配置、重启或终止任务、创建监控；仅更新本地三层进度记录。下一步仍为继续运行并在用户下次询问时核验进度，待全量结束后做哈希/覆盖验收及三组配对评分；OCRFlux和MinerU-Popo不属于本run。

## 2026-10-27 15:45 UTC（北京时间23:45）用户触发进度检查

只读核验原run及同一service：active/running、MainPID3358795、ExecMainExitTimestamp=n/a。按run-manifest与全部已发布checkpoint统计，**719/935文档、10,450/13,871页（75.34%）**，较10月25日增加362文档/5,455页。checkpoint解析错误/重复文档/额外文档/页数不一致均0；本次未全量重算文件SHA或审计预测内容质量。

当前文档PMC11764768共20页，`outputs/baselines/paddleocr-vl-1.5/20261023T152753Z-paddle-val-full-PMC11764768/pages.jsonl` 有18条完整记录，page_index=[0..17]、解析错误0、尾残片0，尚未发布完整checkpoint，不计入10,450页。对应文档日志15:37:24至15:44:32 UTC连续产出页面，父日志最新完整文档PMC11764690；父summary尚未发布，无正式全量指标。GPU0整卡空余34,121MiB、占用46,918MiB、利用率22%，不代表本任务独占占用/峰值。

启动至本次约96.28小时，全程平均约108.5页/小时；剩余3,421页按均速粗估31.5小时（约1–2天），不含后续离线后处理/评分，受共享资源和页面复杂度影响，非完成承诺。本次未修改服务器文件/代码/参数、未重启或停止任务、未创建监控，仅追加本地三层记录。下一步继续当前推理，结束后先做全量覆盖/哈希验收，再做三组配对离线评分。

## 2026-10-29 03:39 UTC（北京时间11:39）全量推理完成核验

用户询问进度后只读检查原run `20261023T152753Z-paddle-val-full`。`summary.json` 明确status=completed、resumed_documents=0、completed_documents=935、pages=13,871，与冻结935/13,871一致。935个checkpoint全部可解析，文档重复/额外/页数不一致均0、缺失文档0。935份worker summary均status=completed，无error字段；这证明执行完成，不代表预测内容准确或没有一般依赖警告。

最后文档PMC7617896共38页，其日志document_complete及summary.ended_utc均为2026-10-29 00:11:16 UTC（北京时间08:11:16）；从10月23日15:28:13 UTC启动到最后文档结束约128.72小时（5.36天）。最终导出具体结束时刻未额外核验，不以文件mtime推断。服务当前inactive/dead、MainPID0；查询返回ExecMainStatus0，但ExecMainExitTimestamp仍n/a，不单靠该字段证明成功，以上述实际summary与导出证据为依据。

`export-complete.json` 明确pages=13,871、manifest_sha256=`1d39ca16b7fcfedf3dabb174c80ef4ae914d90a76a2839617a469c0ba75e90c5`。本次重算 `exported-inputs/input-manifest.jsonl` SHA与其一致，输入13,871行且身份无重复；流式解析 `exported-predictions/pages.jsonl`（168,764,285字节），共13,871条/13,871个唯一页面，全部JSON可解析、末行换行完整。以输入(document_id,page_number)对预测(document_id,res.page_index)核验 **missing=extra=duplicate=0**。导出路径均位于原run根。

本次没有重算所有checkpoint引用文件SHA，完整产物哈希复核仍属评分前验收；没有产生正式全量指标或启动新后台评分。GPU0整卡快照空余37,943MiB、占用43,096MiB、利用率28%，不归因本任务，也不据此启动其他模型。下一步为产物哈希验收、无合并/官方原版合并/content-compatible三组CPU适配及配对离线评分，再分析跨页恢复效果；OCRFlux和MinerU-Popo尚不能据本run声称已测。本次仅更新本地三层记录，未修改服务器数据/代码、未重启或终止任何任务。
