# 2026-11-14 Qwen3-VL-2B-Instruct 固定下载清单预检

状态：仅清单准备与 dry-run 已完成；未下载权重、未运行模型、未访问服务器、未读取凭证。此步骤不表示训练关口已通过。

已核验：通过无认证 urllib 请求官方 Hugging Face API，main 返回 SHA 后再次请求固定 revision 元数据并断言一致。固定 revision 为 `89644892e4d85e24eaac8bacfd4f463576704203`。来源：`https://huggingface.co/api/models/Qwen/Qwen3-VL-2B-Instruct/revision/89644892e4d85e24eaac8bacfd4f463576704203?blobs=true`。精确请求时间 UTC 与原始响应 SHA256 写入清单，日期按 Asia/Shanghai 记本条。

清单：`configs/models/qwen3-vl-2b-instruct-2026-11-14.json`；包含 API 列出的全部12个根目录文件（含README/.gitattributes、处理器、tokenizer、配置及单文件权重），总计4,266,648,961字节。权重 model.safetensors 4,255,140,312字节，LFS SHA256 `7de1838c87a5349b016c26a1c3f7d2bc400a3d485f95ef39a7059ffd734977a0`；所有文件均保留 git_blob_id，普通文件 sha256 为 null，供现有下载器按 Git blob 校验。LFS 的 git_blob_id 是指针blob，实际权重校验优先使用LFS SHA256。

复用 `scripts/download_public_models.py` 原格式 schema_version=1，未修改脚本。已读取其验证实现：仅允许固定40位SHA、根目录文件名，以及 SHA256/Git blob 校验；dry-run 在创建模型和日志目录前返回。命令：

```powershell
.venv/Scripts/python.exe scripts/download_public_models.py --manifest configs/models/qwen3-vl-2b-instruct-2026-11-14.json --run-id qwen3-vl-2b-manifest-preflight-20261114 --dry-run
```

输出 `{"qwen3-vl-2b-instruct": 4266648961}`，exit 0。本地无需GPU，未下载数据，也未修改原始数据。实际下载仍待主任务按批准范围在服务器另取唯一 run-id；现有脚本下载端点硬编码 hf-mirror.com，清单证据来自官方API，最终以固定revision和文件hash核验。镜像可达性、模型加载兼容性、显存和训练环境均待核验，不由 dry-run 推断。
