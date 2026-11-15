# 2026-11-15 全train_fit裁剪准备与联合核验

状态：CPU裁剪与完整性核验已完成；全量上游预测未完成；不放行正式训练。

固定PubTables-v2 revision `aa575e798cb00a296925e2086addb3e3fd9a1903`，R0已知GT片段/分组，image-only，暂定train_fit5322表。复用已完成200表/658片段，剩5122表/11642片段在服务器生成裁剪；不下载、不改原始图像，不使用GPU、不生成新预测。

启动2026-11-15 07:53:49 UTC（15:53北京时间），代码0bde16b，PID1723289，独立环境 `.venvs/20261114T095359Z-qwen-env/bin/python`，CUDA_VISIBLE_DEVICES为空，seed0（确定性裁剪无随机采样）。launcher `artifacts/reconstruction-launchers/20261115T075349Z-fit-remaining5122-prepare` 保存完整显式5122组argv、输入SHA、PID、stdout与exit0收据。命令入口 `scripts/run_reconstruction_upstream.py --prepare-only --project-root /data01/public/zhengguojie/paper --inputs artifacts/reconstruction/20261109T153945Z-reconstruction-train-full/inputs.jsonl --run 20261115T075349Z-fit-remaining5122-prepare`，所有`--group-id`以command.json的argv为准，不在正文省略后冒称可直接复现。

输出 `artifacts/reconstruction-upstream/20261115T075349Z-fit-remaining5122-prepare`，prepared状态，5122表11642片段。12:26 UTC检查时已完成；exit收据未记录结束UTC，文件mtime与run日期不一致，不能据其补造结束时间。未读取/修改项目外系统设置。

12:29:29 UTC联合审计完成：`artifacts/reconstruction-readiness/20261115T122718Z-full-fit-crops/{inventory.jsonl,source-hashes.json,summary.json}`。联合旧20表66片段、旧180表592片段与新5122表11642片段，**5322表/12300片段，missing/extra/duplicate=0**。逐条回查原inputs字段、source.json、原图SHA与crop SHA，37352文件校验通过，并确认核验期间文件stat未变。inventory SHA `938e2a9339eaa75b982486fb4819bac39af4cf51802d5a80e857fb86343c1d4e`，source-hashes SHA `5b2785ae88320c5c4273e8e3e75632d62d94e1b7b2a713b0aeffbb880008c9e9`。

当前可用局部模型预测仍为658片段，**11642片段尚未推理**；不能把裁剪完成描述成全量预测或训练输入已全部就绪。已知隔离文档PMC10748512不属于fit，本次fit集合未包含该文档；整体文档簇划分仍暂定，近重复/人工关口未关闭。下一步先完善新目录分片复用入口，再按研究门槛决定是否扩大GPU；不重跑200表既有预测，不覆盖旧裁剪/记录。
