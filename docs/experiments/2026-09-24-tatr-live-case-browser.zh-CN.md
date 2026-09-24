# TATR 实时案例浏览服务记录

## 状态

- 日期与时区：2026-09-24，Asia/Shanghai
- 状态：实时服务已实现并通过本地测试；待服务器启动核验
- 代码分支：`codex/table-case-analysis-report`
- 实现提交：`8c51548`
- 输入：PubTables-v2 `Cropped Tables/val` 13,384 例，revision `aa575e798cb00a296925e2086addb3e3fd9a1903`
- track：`PDF-text-assisted`
- GPU：不使用

## 需求变更与旧任务

原静态报告工具需要先对 13,384 例全部计算后才生成 HTML，不符合“服务启动后按顺序、点击下一页时实时加载”的实际需求。用户确认后，后台静态任务 PID `521962` 于处理到约 700/13,384 时正常终止；日志保留于：

`logs/analysis/table-case-reports/20260924T040248Z-tatr-case-report/`

新增 `stopped-at.txt` 和 `status.txt`，没有删除日志，没有生成或删除静态报告目录。

## 实时服务行为

- 启动时只读取 manifest 并建立 predictions JSONL 字节偏移索引，不做全量 GriTS；
- 浏览器请求某一案例时才读取对应 truth、prediction 和原图，并计算该例指标；
- 已浏览案例使用 LRU 内存缓存，默认 128 例；
- 支持上一个、下一个、序号/`unit_id` 跳转和左右方向键；
- 浏览器 `localStorage` 记录上次位置；
- 同屏显示原图、GT、预测、GriTS、结构画像和错误线索；
- 每次查看追加到新会话的 `viewed-cases.jsonl`，保留人工审计轨迹；
- 服务强制只绑定 loopback，不允许 `0.0.0.0`，通过 SSH 隧道访问；
- 原图、真值和预测只读，不复制或修改完整数据。

## 启动方式

服务器：

```bash
cd /data01/public/zhengguojie/paper
git switch codex/table-case-analysis-report

browser_run="$(date -u +%Y%m%dT%H%M%SZ)-tatr-live-browser"
browser_log="logs/analysis/table-case-browser/$browser_run"
mkdir -p "$browser_log"

nohup env CUDA_VISIBLE_DEVICES="" \
  .venvs/eval312/bin/python scripts/serve_table_case_browser.py \
  --config configs/evaluation/tatr-cropped-val-case-report.yaml \
  --host 127.0.0.1 \
  --port 8765 \
  > "$browser_log/server.log" 2>&1 &

echo $! | tee "$browser_log/runner.pid"
```

本机建立隧道：

```bash
ssh -N -L 8765:127.0.0.1:8765 172.17.60.82
```

浏览器打开 `http://127.0.0.1:8765`。服务启动日志会立即打印 `status=ready`、样本总数和会话目录；不需要等待全量评分。

## 验证与边界

新增测试覆盖懒加载、单例评分、LRU 缓存、序号/ID 定位、访问留痕、HTTP JSON、图片流和非 loopback 拒绝。自动结构差异仍只是诊断线索；Cropped Tables 页面不能解释为跨页恢复结果。
