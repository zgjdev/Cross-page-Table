# OCRFlux-pubtabnet-cross 数据准备记录

## 状态

**已完成下载，数据审计通过；来源独立核验仍有限。**

## 目的与范围

- 目的：为后续 OCRFlux-3B 的 HTML 片段纯拼接诊断准备公开数据。
- 数据集：`ChatDOC/OCRFlux-pubtabnet-cross`。
- 数据性质：HTML 片段对及完整 HTML，不是自然跨页 PDF 页面；不得与 PubTables-v2 的 image-only 主指标合并。
- 不使用 GPU；不修改或覆盖 PubTables-v2、已有模型和实验产物。

## 来源核验

- 官方仓库：`https://huggingface.co/datasets/ChatDOC/OCRFlux-pubtabnet-cross`
- 下载 endpoint：`https://hf-mirror.com`（官方 endpoint 在 2026-09-29 查询超时，镜像仅作为公开数据传输通道）。
- 镜像返回 revision：`10f47124646489a33c9c9c049707d7e710b00a31`
- 文件清单：`.gitattributes` 2,508 B；`README.md` 2,033 B；`data.jsonl` 30,147,757 B；`images.tar.gz` 187,343,520 B。
- 预计总大小：约 217 MB；实际样本数和字段须下载后从文件审计，不以文档中的约数代替。

## 实际结果

- 下载时间：2026-09-29 10:40:58--10:41:10 UTC。
- 下载日志：`logs/datasets/20260929T103902Z-ocrflux-pubtabnet-cross-download.log`。
- 保存目录：`data/external/ocrflux-pubtabnet-cross-10f47124646489a33c9c9c049707d7e710b00a31/`。
- 文件 SHA-256：`artifacts/model-manifests/20260929T103902Z-ocrflux-pubtabnet-cross.sha256`。
- `data.jsonl`：9,064/9,064 行可解析；字段为 `image_name`、`type`、`gt_table`、`table_fragment_1`、`table_fragment_2`；HTML 字段无空值。
- `image_name`、三个 HTML 字段均各自 9,064 个唯一值；`type` 为 `simple` 4,623 条、`complex` 4,441 条。
- `images.tar.gz`：归档条目 9,065 个，包含目录项 `images/` 和 9,064 张图片；暂未解压。
- 未使用 GPU；未修改已有 PubTables-v2 数据和已有实验产物。

## SHA-256

详见清单文件；关键值如下：

```text
53bb648161859965d35106fe554feeddd097737ad5a9ade550ce4f672284036b  data.jsonl
e38b79fa26535107858b89fa75b75f44a92f659559091a61e3dd45991c8698a3  images.tar.gz
```

## 结论边界

数据已可用于后续 OCRFlux HTML-only 诊断，但不能称为自然跨页 PDF benchmark。归档图片是原始完整表格图，不能直接当作两个跨页页面输入；若用它做 OCR 推理会改变任务定义。该集结果只能单独报告 HTML 合并指标，不能与 PubTables-v2 的文档级 image-only 跨页恢复指标直接合并或作一一对应比较。镜像返回的 revision 已固定，官方 endpoint 本轮超时，需在正式论文引用或跨环境复现时补充官方页面/独立来源核验。

## 计划命令

```bash
HF_ENDPOINT=https://hf-mirror.com \
HF_HUB_DISABLE_IMPLICIT_TOKEN=1 HF_TOKEN= HUGGING_FACE_HUB_TOKEN= \
.venvs/eval312/bin/hf download ChatDOC/OCRFlux-pubtabnet-cross \
  --repo-type dataset \
  --revision 10f47124646489a33c9c9c049707d7e710b00a31 \
  --local-dir data/external/ocrflux-pubtabnet-cross-10f47124646489a33c9c9c049707d7e710b00a31
```

## 下载后必须完成

1. 保存命令日志和 endpoint、revision、结束状态。
2. 对所有下载文件执行 `sha256sum` 并保存清单。
3. 解析 `data.jsonl` 的行数、字段、HTML 空值/损坏数和图片引用；检查是否有重复源表或重复样本。
4. 解压图片前先记录归档 SHA-256；解压到该数据集自己的子目录，不覆盖原始归档。
5. 若镜像内容无法与公开 revision 独立核验，状态保持“待核验”，不能写成正式 benchmark 结果。
