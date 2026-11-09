# 2B–4B 跨页表格恢复候选补查

日期：2026-11-06，Asia/Shanghai。状态：官方资料只读核验完成；无下载、服务器访问、推理、训练或新增分数。沿用 academic-research-workflow 的证据分层。

## 已提供：官方来源

| 候选 | 公开规模与定位 | 官方来源 | 跨页能力边界 |
| --- | --- | --- | --- |
| Qwen3-VL-2B-Instruct / 4B-Instruct | 2B/4B 档通用VLM，模型卡Apache-2.0 | https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct 、https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct | OCR、文档理解及多图输入；作为多页联合恢复候选，不等于已有严格跨页恢复结果 |
| DeepSeek-OCR-2 | 模型页约3B，Apache-2.0，文档OCR | https://huggingface.co/deepseek-ai/DeepSeek-OCR-2 | 优先作为页级解析上游；未据此确认原生跨页合并 |
| MonkeyOCR-pro-3B | 3B识别核心；完整管线另有版面等组件 | https://huggingface.co/echo840/MonkeyOCR-pro-3B 、https://github.com/Yuliang-Liu/MonkeyOCR | v1.5论文描述 Type-Guided Table Merging，公开权重与v1.5跨页模块的对应及可执行发布状态待核验 |
| InternVL3_5-4B | 4B档通用VLM，模型卡Apache-2.0 | https://huggingface.co/OpenGVLab/InternVL3_5-4B | 官方有多图推理示例，适合多页联合基线；严格跨页恢复效果待实验 |

MonkeyOCR v1.5 一手论文：https://arxiv.org/abs/2511.10390 。论文明确提出跨页/跨栏表格重建，但不能把旧pro-3B权重自动等同于已发布完整v1.5模块。官方仓库本次README未检出merge接口描述，未做源码级完整审计，不能据此断言模块不存在。各规模为官方命名/模型卡口径，非统一重新统计总参数；MoE总参数、激活参数及完整系统规模须在正式选型时单独记录。

## 推断：本项目接入价值

优先小范围核验MonkeyOCR跨页模块可复现性；Qwen3-VL-4B适合补充通用多图VLM对照；DeepSeek-OCR-2适合补充专用页解析器上游；2B与InternVL作为预算允许时的规模/模型家族对照。优先级是研究建议，未改变既有OCRFlux→Popo执行安排，未证明任何候选优于当前Paddle。

整文档输入应覆盖全部页面且不使用GT框/续接筛选。候选页发现与滑窗协议必须不依赖GT，明确窗口边界和跨窗口合并；已知同表裁剪只能单列oracle诊断。两条赛道独立；在train核验提示、输出HTML/span/来源链与正负例后冻结协议，再做val，test不参与开发。接入前固定源码/权重revision、许可证、依赖和完整管线组件，并做GPU资源门禁与显存实测。
