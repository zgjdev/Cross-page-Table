# PaddleOCR-VL-1.5 全量推理启动门禁与断点方案

日期：2026-10-23（Asia/Shanghai）。状态：实现/验收中，尚未启动完整validation。用户授权持续推进到可启动。

## 冻结协议与启动门槛

- PubTables-v2 Full Documents revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，validation完整935文档/13,871页；既有固定清单 `artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl`，SHA `2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd`。
- 不读GT决定输入，所有无表页保留；页面按整文档派生image-only PDF，无文字层、嵌入原JPEG字节，图像来源在split根目录受检。
- 同原smoke：PaddleOCR3.4.0/PaddleX3.4.1/PaddleGPU3.2.1/cu118/NumPy1.26.4、seed0、三个batch=1、关闭方向/去畸变及队列，生成参数官方默认；固定主模型/版面模型SHA。启动前重新核验两个模型仓库所有下载文件当前大小/SHA、运行依赖与共享磁盘至少100GiB空余。
- GPU0需空余至少20,000MiB；native worker逐页检查低于8,192MiB保护退出。已有进程不终止、不更改设备或系统环境；空余显存不是独占承诺。
- 保留no_merge/native_merge_official原样输出，content-compatible修正版仅离线派生；不能将其混称官方性能。评分和GT不进入推理进程。

## 断点入口实现

文件：`src/cptla/evaluation/document_run.py`、`scripts/run_paddle_document_full.py`；底层仍使用已实际GPU验证的 `scripts/run_paddle_v15_smoke.py`，仅新增显式split与匹配run ID校验，防止train结果写成val。

按文档顺序：只在处理前打包当前整文档 → 调用固定native worker → 检查原始页面覆盖及官方输出文件齐全 → 保存完整产物SHA及protocol → 独占创建该文档checkpoint。每文档单独进程，增加模型重新加载开销，但复用已验证入口、释放完成文档显存，不在断点恢复时反复丢弃整批。

全量产物根 `artifacts/paddle-document-runs/<RUN_ID>/`。每个native worker的新run ID带文档ID，仍存标准 `outputs/baselines/paddleocr-vl-1.5/`、`logs/baselines/paddleocr-vl-1.5/`；原始PDF及pack来源SHA在本次run的inputs/下。主进程checkpoint只引用项目内路径，不移动、覆盖或删除原数据。

恢复时必须新RUN_ID并显式 `--resume-from <旧run根> [...]`，核对protocol与全部引用产物当前SHA，才跳过已完成文档。protocol冻结清单/模型manifest/运行依赖/seed/GPU及worker/packer/orchestrator/checkpoint源码SHA；代码行为变化时拒绝自动混用。未完成文档只重跑该文档，旧半截输出原样保留；OOM/低显存/推理异常后停止，不无限重试、不终止其他进程。

全部完成后生成全新 `exported-inputs/`、`exported-predictions/`，按固定清单顺序汇总，兼容本轮三组离线adapter；原per-doc结果不动。export前再次核验checkpoint产物SHA。每组评分独立生成目录，之后才读取val GT。

## 验收清单

- [x] 原smoke两train正例6页官方原版/兼容版配对评分与来源页检查完成，服务器62项相关回归通过。
- [x] 额外真实train负例PMC11626747全4页完成；三组均6个页面表、0个多页合并组，未误连已核验负对[1,2]。仅一个选定负例，不外推误连率。原始预测SHA及细节在三组评分实验记录。
- [x] 新增断点单元测试：中断后跳过完成文档、校验SHA/protocol、缺页/重复/文件缺失拒绝、原目录不覆盖；split误标拒绝；worker产物/最终导出格式与模型文件变更检查。
- [ ] 固定完整val清单只读预检通过（935/13,871，图片存在和JPEG头、模型/环境/资源）。
- [ ] 在train负例做新入口完整GPU pilot，确认checkpoint、导出及三组适配；恢复pilot确认零新增GPU工作、SHA不变。
- [ ] 服务器最终回归、代码审查与远程分支同步；记忆页/进度状态记录为ready，不误写全量运行中。

## 预检与未来执行命令

均在服务器项目根目录执行。预检只读，不下载、不改原数据、不进行GPU推理；读取模型文件校验哈希可能耗时。正式命令会使用GPU0、逐文档生成新PDF/预测/checkpoint，原始输入只读。

```bash
cd /data01/public/zhengguojie/paper
PYTHONPATH=src .venvs/eval312/bin/python scripts/run_paddle_document_full.py \
  --run-id 20261023T103000Z-paddle-val-full --gpu 0 --preflight
```

实际启动时选全新UTC时间戳RUN_ID，去掉 `--preflight`；后台启动要将stdout/stderr写入新时间戳launcher日志，保留systemd unit/PID。此文档命令不是启动证据；完成门禁前不执行全量。恢复命令添加 `--resume-from artifacts/paddle-document-runs/<旧RUN_ID>`（如多段则全部传入，无重叠checkpoint）。

## 入口验收中间检查点

代码初版 `d3c32b5` 服务器72回归测试通过。初次完整val只读预检发现原固定清单按文件名字典序排列（例如page_10先于page_2），在PMC10157785拒绝非数字页序；没有启动任何val推理。现保留原清单及其SHA，新增按document_id/page_number排序的派生清单，并单列ordered SHA；不改变成员、不读GT，同时核验val图片目录完整成员相等。

初版完整入口train pilot `20261023T102500Z-paddle-train-pilot` 已完成，用户unit `paper-paddle-full-entry-pilot-20261023T102500Z.service` 初始PID1250488、exit0、inactive；输入清单 `artifacts/input-manifests/20261023T102500Z-paddle-train-pilot.jsonl`（PMC11626747全4页，SHA550a2f04f87e47a5a91571b9e24fd4e57e4ab9f23a36c99a216ee3f9dcfc1688）。输出 `artifacts/paddle-document-runs/20261023T102500Z-paddle-train-pilot/` 已生成checkpoint和导出；launcher `logs/paddle-launchers/20261023T102500Z/pilot.log`。这一额外GPU重跑用于新编排入口验收，不当作独立性能重复实验。

代码审查又核验出checkpoint写入中断与导出清单变化两项保护缺口，均通过RED/GREEN回归后修复：先写独占UUID `.pending` 文件，flush/fsync，再用同目录硬链接原子发布最终JSON，不覆盖/删除临时或旧产物；恢复只扫描最终*.json。导出对同一份bytes重新核对原始SHA，再排序/写出并核验全部文档页序。代码复审确认无Critical/Important；最终版需重新pilot及恢复验证（源码SHA改变后不得冒用初版protocol）。所有初版产物保留。
