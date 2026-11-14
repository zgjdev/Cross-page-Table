# 2026-11-14 B3 多图 SFT 数据接口（仅CPU）

依据：11月9日研究方案 B3 同骨干直接多图整表HTML生成对照。新增 `src/cptla/reconstruction/sft_data.py`，没有实现训练器、LoRA、真实Qwen processor适配或GPU执行。接口通过mock测试，不能据此宣称训练就绪或G1/G2通过。

输入契约是新显式投影，不直接接受完整manifest：`group_id, split, track, fragments`；split仅 `train_fit`，track仅 `image-only`。片段顺序即输入顺序，每片段仅 `image_path,prediction_html`。相对图路径不得逃逸/绝对/含驱动器或URL；接口不读图。上游预测可以是坏HTML原文，不用目标修补。标签独立参数，仅 `group_id,grid_version,html`；身份必须相同，版本必须为当前GRID_VERSION，HTML验证但保持原文。未知输入字段直接拒绝，目标仅进入assistant消息。此白名单不能证明调用方没有把GT冒充prediction；正式构建器仍必须从冻结上游产物读取并做来源hash核验及文档划分验收。

注入processor适配器协议：调用 `(messages, add_generation_prompt=..., truncation=False)`，返回单例未padding的list[int] input_ids、全1 attention_mask，以及视觉字段。先编码仅user且有assistant生成前缀的prompt，再编码含完整assistant标签的full；强制full严格以前者为前缀且有非空后缀。prompt/image tokens labels=-100，assistant后缀（含终止标记）监督。视觉字段保留。超预算整例显式拒绝并计数，不截断、不静默过滤。返回逐例encoding列表，尚不是HF Trainer可直接使用的tensor batch；padding、视觉张量拼接和位置编码必须由未来适配器实现并验证。适配器必须履行完整编码契约；mock测试不能证明真实模型模板无隐式截断。正式接入需独立验证标签token覆盖、结束标记、图像token展开后长度及多图位置编码。

测试：先因缺少模块而收集失败，实施后9项通过，Ruff通过。覆盖train_dev/train_confirm/test/validation拒绝、输入目标字段泄漏拒绝、标签身份、assistant mask、预算拒绝计数、图序/原文保持及非前缀tokenization拒绝。命令：`.venv/Scripts/python.exe -m pytest tests/reconstruction/test_sft_data.py -q -o cache_dir=.test-runs/sft-final-cache`。本地CPU、无下载、无服务器、无训练数据生成；不存在正式样本数/指标/模型运行结果。下一步先用冻结模型processor做CPU真实模板兼容性验收，再讨论训练接口，不能绕过划分/人工审计关口。
