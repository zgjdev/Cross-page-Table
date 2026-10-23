# 公开模型优先评测安排与准备状态

日期：2026-10-23（Asia/Shanghai）。状态：用户已指定优先 PaddleOCR-VL-1.5、OCRFlux-3B、MinerU-Popo；本轮完成官方来源和服务器只读预检，尚未下载权重、安装新环境或执行这三个模型的推理。本文调整 [五方案计划](2026-10-20-cross-page-five-method-evaluation-plan.zh-CN.md) 的优先顺序；旧结果及计划历史保留。

目标：在 PubTables-v2 Full Documents 固定 revision `aa575e798cb00a296925e2086addb3e3fd9a1903` 上优先取得可复现的公开模型基线，最终与文档级跨页表格关系重建方法比较。validation 为 935 篇、13,871 页；全页输入与 983 张跨页子集的既有定义不变，test 不参与开发。此处延续完整文档 image-only 主实验；已知同表裁剪图片列表仍是单独诊断任务，未启动。

## 1. 新执行顺序

| 优先级 | 方案 | 配对比较与验收 |
| --- | --- | --- |
| 1 | PaddleOCR-VL-1.5 | 使用完整官方页面管线，显式 `pipeline_version="v1.5"`；保存同一批页面结果，分别调用 `restructure_pages(..., merge_tables=False/True)`。先做 train 整文档 smoke，通过来源页、完整表 HTML、失败终态和显存核验后再 val 全量。不能以 transformers 的元素识别示例冒充全页管线。 |
| 2 | OCRFlux-3B | 使用官方逐页解析及跨页管线，比较 `--skip_cross_page_merge` 开关；输入为原始 JPEG 页按整文档封装的无文字层派生 PDF。核验表格 HTML/网格与来源页可审计转换，再启动 val 全量。 |
| 3 | MinerU-Popo | 是后处理器，需要固定页面解析输出。先核验官方对 PaddleOCR-VL-1.5 的原生转换；新增固定 Paddle 上游的 `no_merge / native_merge / Popo` 配对条件，明确它与既有固定 dots 上游计划不同。固定 dots + Popo 对照仍可保留，但不能跨上游归因合并增量。仅做本地表格相关处理，不启用云端 enrichment。 |
| 后续 | POTATR | 暂不以它的可用性或自行实现为这三项工作的前置条件；制品可用性/自行复现另立分支，未经核验不绝对断言从未发布。 |

上述接口已在官方文档核验，但**输出能否无损对接当前跨页评分器仍未验证**。所有方案分别报告全表和跨页子集的 GriTS、内容 exact，并注明尚未实现的来源页严格校验/误连指标。现有 HTML 兼容审计结论保留，不能把不同解析策略造成的分差都归因于模型。不能把 0.9 以上的官方层级 TEDS 直接当作本项目跨页 Acc-Con。

## 2. 官方来源与固定权重候选

以下 resolved SHA 和文件大小来自本机对官方 Hugging Face `/api/models/<repo>?blobs=true` 的只读查询，不是服务器已有权重。元信息查询没有下载权重。

| 模型 | 官方仓库及 revision | 权重文件合计 |
| --- | --- | ---: |
| PaddleOCR-VL-1.5 | [PaddlePaddle/PaddleOCR-VL-1.5](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.5/tree/2a4195faa5e7914c12f2fc601d72c81caf8d2da5)，`2a4195faa5e7914c12f2fc601d72c81caf8d2da5` | 1,917,255,968 bytes |
| OCRFlux-3B | [ChatDOC/OCRFlux-3B](https://huggingface.co/ChatDOC/OCRFlux-3B/tree/e68592278bbc8ab32edf7b65e6e411f1d878ef72)，`e68592278bbc8ab32edf7b65e6e411f1d878ef72` | 8,129,570,856 bytes |
| MinerU-Popo | [DreamEternal/MinerU-Popo](https://huggingface.co/DreamEternal/MinerU-Popo/tree/af75342abdc5cbd461264521c9ef46719ff74190)，`af75342abdc5cbd461264521c9ef46719ff74190` | 17,751,350,264 bytes |

Paddle 模型卡为 Apache-2.0，Popo 模型卡为 MIT。OCRFlux 工具仓库明确 Apache-2.0，权重仓库有 LICENSE 文件但模型卡 metadata 的 license 为空；实际安装/运行前须读取固定 revision 的 LICENSE，不将工具许可自动代替权重许可。权重大小不含 tokenizer、依赖、缓存、Paddle 版面组件和输出。

官方接口证据：

- [PaddleOCR-VL 官方用法](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html)：支持多页重组及 `merge_tables`；当前默认版本可能为 v1.6，所以必须显式固定 v1.5，并固定包含该接口的 PaddleOCR/PaddleX 版本。
- [PaddleOCR-VL-1.5 模型卡](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.5)：完整页面管线与元素级 transformers 用法不同；后者不能替代页面检测。
- [OCRFlux 官方代码](https://github.com/chatdoc-com/OCRFlux)：逐页解析、续接识别、表格片段合并和跳过合并开关；安装需要独立环境，不能在 eval312 混装。
- [MinerU-Popo 官方代码](https://github.com/opendatalab/MinerU-Popo)：默认分支 master；明确支持 PaddleOCR-VL-1.5 页结果转换、label normalization、推理和文档树构建。

## 3. 服务器只读预检

启动前代码为 `fc736c0`，服务器和本地 main 均干净。项目内只有旧 TATR/dots 检查点与 eval312/dots 环境，没有三个新模型的权重/独立环境。共享文件系统 `df -h .` 显示约 34 TiB 可用，不等于用户独占配额。

GPU 0/1/2/3 空余显存分别为 39,607/423/25,343/22,761 MiB，全部有既有计算进程。该快照不能作为后续运行许可或独占保证；新 GPU smoke 前重新检查，单卡、单任务、小 batch，记录峰值。

网络核查：

- 服务器访问 `huggingface.co` 官方 API 报 `[Errno 101] Network is unreachable`。
- `hf-mirror.com/api/models/...` 部分返回 403；所以依赖仓库枚举 API 的整仓下载可能失败。
- 使用**本机官方核验的固定 SHA**访问镜像 `/resolve/<SHA>/config.json`，三个模型均返回 200，模型类型分别为 `paddleocr_vl`、`qwen2_5_vl`、`qwen3_vl`。这只证明小文件通路，不证明大权重下载完成。
- ModelScope 的 Paddle 模型 API 和 GitHub raw README 可访问，尚未核验其完整权重文件/版本对应。
- 所有检查仅取公开元信息/小文件到内存，没有 token、没有数据上传或本地数据下载。

## 4. 下一阶段具体交付与检查点

- [ ] 从本机官方 API 固定完整文件清单、大小和 LFS SHA；读取权重及工具 LICENSE，固定官方代码 commit。模型直接下载到服务器 `models/<模型>-<SHA>/` 的新目录；API 不可用时逐文件使用已核验的公开固定链接，不发送凭证。每项下载后核验大小和 SHA，保留不完整下载，不声称 ready。
- [ ] 首先建立 Paddle 独立环境，固定 v1.5 所需版面模型与缓存目录。先审计源码的默认下载/缓存路径，仅允许项目根目录内写入；不更改 eval312/dots 环境。第三方安装状态、冻结依赖和每个权重路径均写实验记录。
- [ ] 实现整文档派生输入与输出 adapter 时先写合成契约测试：页面数不变、没有文字层、不能读取 GT、每表来源页明确、重复与缺页被拒绝、同一页结果可分别执行两组后处理；缺失字段明确报错，不能猜测或从 GT 补齐。
- [ ] 先固定 train 整文档 smoke；模型下载/CPU 转换均通过后，重新检查 GPU，执行一张卡的小规模真实推理，记录完整命令、环境、峰值、每页终态、HTML 可解析率与来源页。根据实测速度估算全量时间。
- [ ] smoke 通过后沿文档边界建立可恢复 validation 分片和独立时间戳目录；保存原始输出后离线进行开关合并配对评分。全量任务启动及完成时更新记忆页、进度索引及对应实验记录。

本轮完成项是优先顺序调整、公开制品确认和服务器预检；上述下载、adapter、smoke 与新模型全量分数均尚未完成。dots HTML 规范化复评可独立推进，不再阻塞这三项模型的准备。
