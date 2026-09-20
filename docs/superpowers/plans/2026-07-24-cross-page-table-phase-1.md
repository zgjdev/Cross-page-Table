# 跨页表格研究第一阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 7 周内建立可复现的文献调研、PubTables-v2 数据审计、细粒度标签派生、数据划分、评价和跨页拼接基线，为后续分层关系图模型提供稳定输入与可信对照。

**Architecture:** 第一阶段不实现最终联合模型，而是建立四个稳定边界：研究证据库、规范化数据模型、可审计的标签/划分流水线、统一基线与评价接口。所有算法先在合成 fixture 上测试，再在 PubTables-v2 小样本上验证；大型数据和训练只通过 manifest/config 引用，不进入 Git。

**Tech Stack:** Python 3.11、PyTorch 2.x、torchvision、PyMuPDF、Pydantic 2、NumPy、SciPy、scikit-learn、RapidFuzz、PyYAML、Hugging Face Hub、pytest、Ruff。

## Global Constraints

- 研究对象固定为英文原生 PDF 学术论文；扫描件、OCR、多语言不进入第一阶段主线。
- 主数据固定为 PubTables-v2；PubTables-1M 只作为后续页内预训练数据。
- 所有数据划分以文档为最小单位，不允许页面级泄漏。
- continuation F1 是诊断指标；阶段最终报告必须包含结构拼接指标和错误类型。
- 原始 PDF、页面图像、缓存、检查点和完整数据集不得进入 Git。
- 每个数据产物必须记录源数据版本、SHA-256、生成配置、随机种子和代码提交号。
- Windows 本地环境只做 CPU 小样本验证；正式 ViT 训练在实验室 H100 集群运行。
- 随机种子默认使用 `20260724`。
- 代码、标识符和机器可读输出使用英文；`docs/literature/` 与 `docs/reports/` 下的叙述性 Markdown 必须同时提供 `.en.md` 与 `.zh-CN.md` 两个内容等价版本。

---

## File Structure

```text
paper/
  .gitignore                         # 数据、缓存、权重和本地环境排除规则
  pyproject.toml                     # Python 包、依赖和工具配置
  configs/
    data/pubtables_v2.yaml           # 数据仓库、collection 和本地路径配置
    experiments/continuation_vit.yaml# ViT continuation 基线配置
  docs/
    literature/search-protocol.en.md # 英文检索式、纳排标准和筛选日志规范
    literature/search-protocol.zh-CN.md # 中文对照版
    literature/papers.csv            # 结构化论文矩阵
    literature/search-log.csv        # 每轮检索来源、查询、日期和结果数
    literature/synthesis.en.md       # 英文分类综述、方法对比和研究空白
    literature/synthesis.zh-CN.md    # 中文对照版
    reports/novelty-gate.en.md       # 英文选题审查
    reports/novelty-gate.zh-CN.md    # 中文对照版
    reports/pubtables-v2-inventory.en.md # 英文数据集清单报告
    reports/pubtables-v2-inventory.zh-CN.md # 中文对照版
    reports/phase-1-exit.en.md        # 英文第一阶段验收报告
    reports/phase-1-exit.zh-CN.md     # 中文对照版
  src/cptla/
    __init__.py                      # 包版本
    cli.py                           # 统一命令行入口
    research/literature.py           # 文献矩阵校验
    data/models.py                   # 内部规范化数据类型
    data/inventory.py                # HF 仓库元数据审计
    data/labels.py                   # 跨页细粒度标签派生
    data/splits.py                   # 官方及模板隔离划分
    metrics/relations.py             # 关系、链和对齐指标
    baselines/rules.py               # 规则 continuation 与结构拼接
    baselines/vision.py              # ViT-B/16 continuation 基线
    experiments/registry.py          # 实验记录和可复现元数据
  scripts/
    audit_pubtables_v2.py            # 生成数据审计报告
    derive_cross_page_labels.py      # 生成细粒度标签
    build_splits.py                  # 生成划分 manifest
    train_continuation.py            # H100 训练入口
    evaluate_baselines.py            # 统一基线评测入口
  tests/
    fixtures/                        # 小型合成文档与标注
    research/test_literature.py
    data/test_models.py
    data/test_inventory.py
    data/test_labels.py
    data/test_splits.py
    metrics/test_relations.py
    baselines/test_rules.py
    baselines/test_vision.py
    experiments/test_registry.py
```

---

### Task 1: 建立可复现 Python 项目骨架

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/cptla/__init__.py`
- Create: `src/cptla/cli.py`
- Create: `tests/test_import.py`

**Interfaces:**
- Produces: `cptla.__version__: str`
- Produces: CLI `python -m cptla.cli --version`

- [ ] **Step 1: 初始化版本库并写导入失败测试**

Run:

```powershell
git init
New-Item -ItemType Directory -Force tests | Out-Null
```

Create `tests/test_import.py`:

```python
def test_package_version() -> None:
    import cptla

    assert cptla.__version__ == "0.1.0"
```

- [ ] **Step 2: 创建项目配置与依赖定义**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cptla"
version = "0.1.0"
description = "Cross-page table recovery integrated with document layout analysis"
requires-python = ">=3.11,<3.13"
dependencies = [
  "huggingface-hub>=0.27,<2",
  "jmespath>=1.0,<2",
  "numpy>=1.26,<3",
  "pydantic>=2.10,<3",
  "PyMuPDF>=1.25,<2",
  "PyYAML>=6.0,<7",
  "rapidfuzz>=3.10,<4",
  "scikit-learn>=1.5,<2",
  "scipy>=1.14,<2",
]

[project.optional-dependencies]
train = ["torch>=2.5,<3", "torchvision>=0.20,<1"]
dev = ["pytest>=8.3,<9", "ruff>=0.9,<1"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
*.egg-info/
data/
artifacts/
checkpoints/
outputs/
*.pdf
*.pt
*.pth
*.safetensors
```

- [ ] **Step 3: 安装开发环境并验证测试先失败**

Run:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest tests\test_import.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cptla'` or missing `__version__`.

- [ ] **Step 4: 实现最小包与 CLI**

Create `src/cptla/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/cptla/cli.py`:

```python
from __future__ import annotations

import argparse

from cptla import __version__


def main() -> int:
    parser = argparse.ArgumentParser(prog="cptla")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    if args.version:
        print(__version__)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 验证项目骨架**

Run:

```powershell
.venv\Scripts\python -m pytest tests\test_import.py -q
.venv\Scripts\python -m cptla.cli --version
.venv\Scripts\python -m ruff check src tests
```

Expected: `1 passed`, version `0.1.0`, Ruff exits 0.

- [ ] **Step 6: Commit**

```powershell
git add .gitignore pyproject.toml src tests/test_import.py
git commit -m "chore: initialize cross-page table research project"
```

---

### Task 2: 建立可审计的文献调研协议与论文矩阵

**Files:**
- Create: `docs/literature/search-protocol.en.md`
- Create: `docs/literature/search-protocol.zh-CN.md`
- Create: `docs/literature/papers.csv`
- Create: `src/cptla/research/literature.py`
- Create: `tests/research/test_literature.py`

**Interfaces:**
- Consumes: CSV with the exact columns defined below
- Produces: `validate_literature_csv(path: Path) -> list[str]`

- [ ] **Step 1: 写文献矩阵校验失败测试**

Create `tests/research/test_literature.py`:

```python
from pathlib import Path

from cptla.research.literature import validate_literature_csv


def test_rejects_missing_evidence_fields(tmp_path: Path) -> None:
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text("paper_id,title,year\np1,Example,2026\n", encoding="utf-8")

    errors = validate_literature_csv(csv_path)

    assert "missing columns" in errors[0]


def test_accepts_complete_seed_row(tmp_path: Path) -> None:
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "paper_id,title,year,venue,url,task,data,context,modality,method,metrics,code,status,notes\n"
        "smock2026pubtablesv2,PubTables-v2,2026,arXiv,https://arxiv.org/abs/2512.10888,"
        "table extraction,PubTables-v2,document,vision+text,VLM and classifiers,GriTS+TEDS,"
        "https://huggingface.co/datasets/kensho/PubTables-v2,read,primary dataset\n",
        encoding="utf-8",
    )

    assert validate_literature_csv(csv_path) == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\research\test_literature.py -q`

Expected: FAIL because `cptla.research.literature` does not exist.

- [ ] **Step 3: 实现严格 CSV 校验器**

Create `src/cptla/research/literature.py`:

```python
from __future__ import annotations

import csv
from pathlib import Path

REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "year",
    "venue",
    "url",
    "task",
    "data",
    "context",
    "modality",
    "method",
    "metrics",
    "code",
    "status",
    "notes",
)


def validate_literature_csv(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            return [f"missing columns: {', '.join(missing)}"]
        seen: set[str] = set()
        for line_no, row in enumerate(reader, start=2):
            paper_id = row["paper_id"].strip()
            if not paper_id:
                errors.append(f"line {line_no}: empty paper_id")
            elif paper_id in seen:
                errors.append(f"line {line_no}: duplicate paper_id {paper_id}")
            seen.add(paper_id)
            if row["status"] not in {"candidate", "screened", "read", "excluded"}:
                errors.append(f"line {line_no}: invalid status {row['status']}")
            if not row["url"].startswith(("https://", "http://")):
                errors.append(f"line {line_no}: invalid url")
    return errors
```

- [ ] **Step 4: 写检索协议**

Create `docs/literature/search-protocol.en.md` with these exact sections and decisions, then create
`docs/literature/search-protocol.zh-CN.md` as a reviewed, structurally equivalent academic-Chinese version:

```markdown
# Literature Search Protocol

## Scope

English-language research on table extraction, multi-page tables, hierarchical document
parsing, document graphs, structured table generation, and template/domain generalization.
The primary publication window is 2015-07-24 through 2026-07-24; earlier seminal work may
be included through backward citation search.

## Sources

Search arXiv, DBLP, Semantic Scholar, IEEE Xplore, ACM Digital Library, SpringerLink, and
CVF Open Access. Record the canonical paper URL and an official code/data URL when present.

## Queries

- "multi-page table" AND (recognition OR extraction OR detection)
- "cross-page table" AND (continuation OR merging OR structure)
- "table extraction" AND (full document OR page context)
- "hierarchical document parsing" AND (graph OR relation)
- "table structure recognition" AND (long table OR document)
- "document layout analysis" AND (relationship OR reading order)
- "template generalization" AND document AI

## Inclusion Criteria

- Defines a relevant task, dataset, model, metric, or evaluation protocol.
- Contains enough methodological detail to reproduce or compare the result.
- Uses document images, PDF text/layout, or both.

## Exclusion Criteria

- Web/relational tables without document layout.
- Spreadsheet-only processing.
- OCR-only papers without layout or table structure contribution.
- Non-research product pages without technical evidence.

## Screening

Deduplicate by DOI/arXiv ID, screen title and abstract, then read the full text for included
papers. For each included paper, record task, context level, modality, data, method, metrics,
code availability, strongest evidence, and a limitation relevant to this project.

## Stopping Rule

Stop the first pass after at least 40 screened papers, at least 25 fully read papers, and two
consecutive backward/forward citation rounds add no new method or dataset category.
```

- [ ] **Step 5: 创建种子论文矩阵**

Create `docs/literature/papers.csv` using the required header and at least these verified seeds:

```csv
paper_id,title,year,venue,url,task,data,context,modality,method,metrics,code,status,notes
smock2026pubtablesv2,PubTables-v2: A new large-scale dataset for full-page and multi-page table extraction,2026,arXiv,https://arxiv.org/abs/2512.10888,table extraction,PubTables-v2,document,vision+text,dataset and baselines,GriTS+TEDS,https://huggingface.co/datasets/kensho/PubTables-v2,read,Primary multi-page benchmark
smock2022pubtables1m,PubTables-1M: Towards comprehensive table extraction from unstructured documents,2022,CVPR,https://arxiv.org/abs/2110.00061,table extraction,PubTables-1M,page+crop,vision+text,DETR table transformer,GriTS,https://github.com/microsoft/table-transformer,read,Page-level pretraining source
zhong2020pubtabnet,Image-based table recognition: data model and evaluation,2020,ECCV,https://arxiv.org/abs/1911.10683,table structure recognition,PubTabNet,crop,vision,image-to-HTML,TEDS,https://github.com/ibm-aur-nlp/PubTabNet,screened,Cropped-table benchmark
pfitzmann2022doclaynet,DocLayNet: A large human-annotated dataset for document-layout analysis,2022,KDD,https://arxiv.org/abs/2206.01062,layout analysis,DocLayNet,page,vision,layout detection,mAP,https://github.com/DS4SD/DocLayNet,screened,Auxiliary layout dataset
```

- [ ] **Step 6: 验证协议产物**

Run:

```powershell
.venv\Scripts\python -m pytest tests\research\test_literature.py -q
.venv\Scripts\python -c "from pathlib import Path; from cptla.research.literature import validate_literature_csv; e=validate_literature_csv(Path('docs/literature/papers.csv')); print(e); raise SystemExit(bool(e))"
```

Expected: `2 passed` and `[]`.

- [ ] **Step 7: Commit**

```powershell
git add docs/literature src/cptla/research tests/research
git commit -m "docs: establish table research review protocol"
```

---

### Task 3: 完成系统性文献调研并通过创新性关口

**Files:**
- Modify: `docs/literature/papers.csv`
- Create: `docs/literature/search-log.csv`
- Create: `docs/literature/synthesis.en.md`
- Create: `docs/literature/synthesis.zh-CN.md`
- Create: `docs/reports/novelty-gate.en.md`
- Create: `docs/reports/novelty-gate.zh-CN.md`

**Interfaces:**
- Consumes: Task 2 的检索协议和论文矩阵
- Produces: 至少 40 篇已筛选、25 篇已精读的证据库
- Produces: 对核心研究命题的 `proceed`、`revise` 或 `stop` 决策

本任务是进入数据下载和代码实现前的硬门槛。Task 4 及之后的任务不得在
`docs/reports/novelty-gate.en.md` 与 `docs/reports/novelty-gate.zh-CN.md` 得出一致的 `proceed` 或明确修订后的 `revise` 结论前开始。

- [ ] **Step 1: 建立可重复的检索日志**

Create `docs/literature/search-log.csv` with this exact header:

```csv
search_id,date,source,query,result_count,pages_screened,new_candidates,notes
```

对 Task 2 中的 7 个检索式分别在 arXiv、DBLP、Semantic Scholar、IEEE Xplore、ACM DL、
SpringerLink 和 CVF Open Access 执行适用查询。每次查询记录当前日期、原始查询字符串、
结果数、实际筛选页数和新增候选数；不得用搜索引擎摘要代替原论文证据。

- [ ] **Step 2: 完成标题与摘要筛选**

将 `docs/literature/papers.csv` 扩展到至少 40 篇 `screened`、`read` 或 `excluded` 记录。
每条排除记录在 `notes` 中使用一个明确原因：`non-document-table`、`ocr-only`、
`spreadsheet-only`、`no-method-detail` 或 `duplicate`。先按 DOI/arXiv ID 去重，再按标题去重。

Run:

```powershell
.venv\Scripts\python -c "import csv; from pathlib import Path; rows=list(csv.DictReader(Path('docs/literature/papers.csv').open(encoding='utf-8'))); screened=[r for r in rows if r['status'] in {'screened','read','excluded'}]; print(len(screened)); raise SystemExit(len(screened)<40)"
```

Expected: prints at least `40` and exits 0.

- [ ] **Step 3: 精读最接近的 25 篇以上论文**

至少精读以下六类工作，并在每类保留不少于 3 篇有效论文：

1. multi-page/cross-page table extraction；
2. page-level table extraction and TSR；
3. hierarchical document parsing and relation prediction；
4. graph-based document understanding；
5. multi-page VLM/document parsing；
6. template/domain generalization and shortcut analysis。

每条 `read` 记录必须填写 `task`、`data`、`context`、`modality`、`method`、`metrics`、
`code` 和 `notes`。`notes` 必须同时包含 strongest evidence 和 limitation，不接受只有摘要复述的记录。

Run:

```powershell
.venv\Scripts\python -c "import csv; from pathlib import Path; rows=list(csv.DictReader(Path('docs/literature/papers.csv').open(encoding='utf-8'))); read=[r for r in rows if r['status']=='read']; complete=[r for r in read if all(r[k].strip() for k in ('task','data','context','modality','method','metrics','code','notes'))]; print(len(read),len(complete)); raise SystemExit(len(read)<25 or len(read)!=len(complete))"
```

Expected: both values are at least `25`, equal, and the command exits 0.

- [ ] **Step 4: 完成前向与后向引文追踪**

以 PubTables-v2、PubTables-1M、POTATR、GriTS、DocParser 和最接近的跨页拼接工作为种子，
执行至少两轮 backward/forward citation search。只有连续两轮没有产生新的方法类别或数据集类别时
才满足停止规则；每轮结果单独记录在 `search-log.csv`。

- [ ] **Step 5: 写分类综述与竞争工作对比**

Create `docs/literature/synthesis.en.md` with these completed sections, then create
`docs/literature/synthesis.zh-CN.md` with identical section order, tables, evidence, and conclusions:

```markdown
# Cross-Page Table Literature Synthesis

## Task Taxonomy
## Dataset and Annotation Comparison
## Page-Level Extraction Methods
## Cross-Page Association and Merging Methods
## Hierarchical and Graph-Based Document Parsing
## Multi-Page Vision-Language Models
## Metrics and Evaluation Protocols
## Template Generalization and Shortcut Risks
## Closest-Work Comparison
## Supported Research Gap
```

`Dataset and Annotation Comparison` 必须列出文档类型、上下文范围、跨页实例数、结构标注、
版式关系标注、许可和公开状态。`Closest-Work Comparison` 必须逐项比较输入、输出、模型耦合方式、
跨页结构对齐、评价指标和已知局限，至少包含 PubTables-v2 的 ViT merging 基线。

- [ ] **Step 6: 做创新性审查**

Create `docs/reports/novelty-gate.en.md` and `docs/reports/novelty-gate.zh-CN.md`, and逐条回答：

- 是否已有工作联合预测版式关系、跨页归属和列/行对应？
- PubTables-v2 之后是否出现新的直接竞争论文或代码？
- continuation 分类是否已经饱和，剩余错误具体来自哪里？
- template-disjoint 评测是否已有公开协议？
- 当前方案相对最接近工作新增了什么可验证能力，而不只是换模型？
- 3-6 个月内哪些贡献是最小可行、哪些属于增强项？

文档结尾只能给出一个决策：

- `proceed`：研究空白有直接文献证据，保持当前任务定义；
- `revise`：保留方向但明确改写任务、贡献或评测，并同步修改研究设计；
- `stop`：已有工作实质覆盖核心贡献，需要重新选题。

- [ ] **Step 7: 复核证据库并提交**

Run:

```powershell
.venv\Scripts\python -m pytest tests\research\test_literature.py -q
.venv\Scripts\python -c "from pathlib import Path; from cptla.research.literature import validate_literature_csv; e=validate_literature_csv(Path('docs/literature/papers.csv')); print(e); raise SystemExit(bool(e))"
```

Expected: tests pass and the validator prints `[]`.

```powershell
git add docs/literature docs/reports/novelty-gate.en.md docs/reports/novelty-gate.zh-CN.md
git commit -m "docs: complete cross-page table literature review"
```

---

### Task 4: 定义稳定的规范化数据模型

**Files:**
- Create: `src/cptla/data/models.py`
- Create: `tests/data/test_models.py`

**Interfaces:**
- Produces: `BBox`, `Word`, `Cell`, `TableFragment`, `LogicalTable`, `DocumentRecord`
- All later data, label, split, metric, and baseline tasks consume these Pydantic models.

- [ ] **Step 1: 写模型 round-trip 和约束测试**

Create `tests/data/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from cptla.data.models import BBox, Cell, DocumentRecord, LogicalTable, TableFragment, Word


def test_document_round_trip() -> None:
    record = DocumentRecord(
        document_id="doc-1",
        source_split="train",
        journal_id="journal-a",
        page_count=2,
        words=[Word(page=0, text="Age", bbox=BBox(x0=0.1, y0=0.1, x1=0.2, y1=0.2))],
        tables=[
            LogicalTable(
                table_id="table-1",
                cells=[Cell(cell_id="c1", row=0, column=0, text="Age")],
                fragments=[
                    TableFragment(
                        fragment_id="f1",
                        table_id="table-1",
                        page=0,
                        bbox=BBox(x0=0.05, y0=0.1, x1=0.95, y1=0.95),
                    )
                ],
            )
        ],
    )

    assert DocumentRecord.model_validate_json(record.model_dump_json()) == record


def test_bbox_rejects_inverted_coordinates() -> None:
    with pytest.raises(ValidationError):
        BBox(x0=0.8, y0=0.1, x1=0.2, y1=0.5)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\data\test_models.py -q`

Expected: FAIL because `cptla.data.models` does not exist.

- [ ] **Step 3: 实现规范化模型**

Create `src/cptla/data/models.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BBox(StrictModel):
    x0: float = Field(ge=0.0, le=1.0)
    y0: float = Field(ge=0.0, le=1.0)
    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_order(self) -> "BBox":
        if self.x0 >= self.x1 or self.y0 >= self.y1:
            raise ValueError("bbox coordinates must be ordered")
        return self


class Word(StrictModel):
    page: int = Field(ge=0)
    text: str = Field(min_length=1)
    bbox: BBox


class Cell(StrictModel):
    cell_id: str = Field(min_length=1)
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    row_span: int = Field(default=1, ge=1)
    column_span: int = Field(default=1, ge=1)
    text: str
    is_header: bool = False
    word_indices: tuple[int, ...] = ()


class TableFragment(StrictModel):
    fragment_id: str = Field(min_length=1)
    table_id: str = Field(min_length=1)
    page: int = Field(ge=0)
    bbox: BBox


class LogicalTable(StrictModel):
    table_id: str = Field(min_length=1)
    cells: list[Cell]
    fragments: list[TableFragment]


class DocumentRecord(StrictModel):
    document_id: str = Field(min_length=1)
    source_split: Literal["train", "validation", "test", "hidden_test"]
    journal_id: str | None = None
    page_count: int = Field(ge=1)
    words: list[Word]
    tables: list[LogicalTable]
```

- [ ] **Step 4: 验证模型**

Run:

```powershell
.venv\Scripts\python -m pytest tests\data\test_models.py -q
.venv\Scripts\python -m ruff check src/cptla/data tests/data
```

Expected: `2 passed`, Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add src/cptla/data tests/data tests/fixtures
git commit -m "feat: define normalized document table schema"
```

---

### Task 5: 审计 PubTables-v2 仓库而不下载大型数据

**Files:**
- Create: `configs/data/pubtables_v2.yaml`
- Create: `src/cptla/data/inventory.py`
- Create: `scripts/audit_pubtables_v2.py`
- Create: `tests/data/test_inventory.py`
- Create: `docs/reports/pubtables-v2-inventory.en.md` (generated, then reviewed)
- Create: `docs/reports/pubtables-v2-inventory.zh-CN.md` (translated, then reviewed for parity)
- Create: `artifacts/manifests/pubtables-v2-repo.json` (generated, Git-ignored)

**Interfaces:**
- Produces: `RepoInventory(repo_id, revision, files, total_bytes)`
- Produces: Markdown report containing repository revision, file counts, sizes, extensions, and collection candidates.

- [ ] **Step 1: 写纯函数审计测试**

Create `tests/data/test_inventory.py`:

```python
from cptla.data.inventory import summarize_files


def test_summarize_files_groups_extensions_and_sizes() -> None:
    summary = summarize_files(
        [("README.md", 100), ("full_documents/train/a.json", 300), ("images/a.png", 600)]
    )

    assert summary["file_count"] == 3
    assert summary["total_bytes"] == 1000
    assert summary["extensions"] == {".json": 1, ".md": 1, ".png": 1}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\data\test_inventory.py -q`

Expected: FAIL because `cptla.data.inventory` does not exist.

- [ ] **Step 3: 实现仓库清单与摘要**

Create `src/cptla/data/inventory.py`:

```python
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

from huggingface_hub import HfApi


def summarize_files(files: Iterable[tuple[str, int]]) -> dict[str, object]:
    rows = list(files)
    extensions = Counter(Path(path).suffix.lower() or "<none>" for path, _ in rows)
    return {
        "file_count": len(rows),
        "total_bytes": sum(size for _, size in rows),
        "extensions": dict(sorted(extensions.items())),
    }


def fetch_inventory(repo_id: str, revision: str = "main") -> dict[str, object]:
    info = HfApi().dataset_info(repo_id=repo_id, revision=revision, files_metadata=True)
    files = sorted((item.rfilename, int(item.size or 0)) for item in info.siblings)
    return {
        "repo_id": repo_id,
        "requested_revision": revision,
        "resolved_sha": info.sha,
        "files": [{"path": path, "size": size} for path, size in files],
        "summary": summarize_files(files),
    }
```

Create `configs/data/pubtables_v2.yaml`:

```yaml
repo_id: kensho/PubTables-v2
revision: main
local_root: data/pubtables-v2
manifest_path: artifacts/manifests/pubtables-v2-repo.json
seed: 20260724
```

- [ ] **Step 4: 实现审计脚本**

Create `scripts/audit_pubtables_v2.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from cptla.data.inventory import fetch_inventory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    inventory = fetch_inventory(config["repo_id"], config["revision"])
    manifest = Path(config["manifest_path"])
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    summary = inventory["summary"]
    lines = [
        "# PubTables-v2 Repository Inventory",
        "",
        f"- Repository: `{inventory['repo_id']}`",
        f"- Resolved revision: `{inventory['resolved_sha']}`",
        f"- Files: {summary['file_count']}",
        f"- Bytes: {summary['total_bytes']}",
        f"- Extensions: `{json.dumps(summary['extensions'], sort_keys=True)}`",
        "",
        "The JSON manifest is stored outside Git under `artifacts/manifests/`.",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 验证纯函数并生成真实仓库审计**

Run:

```powershell
.venv\Scripts\python -m pytest tests\data\test_inventory.py -q
.venv\Scripts\python scripts\audit_pubtables_v2.py --config configs\data\pubtables_v2.yaml --report docs\reports\pubtables-v2-inventory.en.md
```

Expected: test passes; report contains a non-empty resolved SHA and positive file count. If Hugging Face is temporarily unreachable, preserve the test result and rerun only the second command when connectivity returns; do not invent inventory values.

- [ ] **Step 6: 人工检查数据卡和文件格式**

Record in `docs/reports/pubtables-v2-inventory.en.md`, then mirror and review the same facts in
`docs/reports/pubtables-v2-inventory.zh-CN.md`:

- exact dataset license, verified against the paper appendix as CDLA-Permissive-2.0 rather
  than the paper's CC BY 4.0 license;
- collection directory/file names;
- annotation serialization format;
- image and PDF-text artifact formats;
- official split identifiers;
- whether journal/PMCID/DOI metadata is available;
- byte estimate for metadata-only, sample, and full download.

The task is complete only when every item is supported by the repository manifest or dataset card,
and both language versions have matching headings, tables, identifiers, numeric literals, license
distinctions, and audit conclusions.

- [ ] **Step 7: Commit**

```powershell
git add configs/data/pubtables_v2.yaml src/cptla/data/inventory.py scripts/audit_pubtables_v2.py tests/data/test_inventory.py docs/reports/pubtables-v2-inventory.en.md docs/reports/pubtables-v2-inventory.zh-CN.md
git commit -m "feat: add PubTables-v2 repository audit"
```

---

### Task 6: 实现 PubTables-v2 到内部模型的适配层

**Files:**
- Create: `configs/data/pubtables_v2_mapping.yaml`
- Create: `src/cptla/data/pubtables_v2.py`
- Create: `scripts/normalize_pubtables_v2.py`
- Create: `tests/data/test_pubtables_v2.py`
- Create: `tests/fixtures/pubtables_v2_raw_sample.json`

**Interfaces:**
- Consumes: Task 5 审计确认的 Full Documents JSON 和一个基于 JMESPath 的字段映射
- Produces: one UTF-8 `DocumentRecord` JSON object per JSONL line
- Produces: rejection JSONL containing source path, record ID, validation error, and source revision

Task 5 is a hard checkpoint for this task. Copy one license-compatible raw annotation into
`tests/fixtures/pubtables_v2_raw_sample.json`, preserving its original field names and replacing
only document/cell text with synthetic English text. Do not invent raw field names before the
repository schema has been inspected.

- [ ] **Step 1: 根据真实 fixture 写适配失败测试**

Create `tests/data/test_pubtables_v2.py`:

```python
import json
from pathlib import Path

import yaml

from cptla.data.models import DocumentRecord
from cptla.data.pubtables_v2 import normalize_record


def test_normalizes_repository_sample() -> None:
    raw = json.loads(Path("tests/fixtures/pubtables_v2_raw_sample.json").read_text(encoding="utf-8"))
    mapping = yaml.safe_load(
        Path("configs/data/pubtables_v2_mapping.yaml").read_text(encoding="utf-8")
    )

    record = DocumentRecord.model_validate(normalize_record(raw, mapping))

    assert record.document_id
    assert record.page_count >= 2
    assert any(len(table.fragments) >= 2 for table in record.tables)
    assert all(fragment.table_id == table.table_id for table in record.tables for fragment in table.fragments)
```

- [ ] **Step 2: 写经过审计的字段映射**

Create `configs/data/pubtables_v2_mapping.yaml` from the actual raw fixture and Task 5 schema
report. It must contain the target keys `document_id`, `source_split`, `journal_id`, `page_count`,
`words`, and `tables`; every value is a JMESPath expression verified against the copied raw
fixture. Add `source_revision` with the exact resolved Hugging Face SHA. Review every mapping
value against the fixture and require that no placeholder token or angle bracket remains before
continuing. This checkpoint is evidence-dependent because the public dataset README, not the
paper, defines the raw JSON field names.

- [ ] **Step 3: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\data\test_pubtables_v2.py -q`

Expected: FAIL because `cptla.data.pubtables_v2` does not exist.

- [ ] **Step 4: 实现适配器和严格错误报告**

Create `src/cptla/data/pubtables_v2.py`:

```python
from __future__ import annotations

from typing import Any

import jmespath


REQUIRED_TARGETS = {
    "document_id",
    "source_split",
    "journal_id",
    "page_count",
    "words",
    "tables",
}


def normalize_record(raw: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    missing = REQUIRED_TARGETS - mapping.keys()
    if missing:
        raise ValueError(f"missing mapping targets: {sorted(missing)}")
    normalized = {target: jmespath.search(mapping[target], raw) for target in REQUIRED_TARGETS}
    if normalized["document_id"] is None or normalized["tables"] is None:
        raise ValueError("mapping did not produce document_id and tables")
    return normalized
```

Implement `scripts/normalize_pubtables_v2.py` as a streaming JSON/JSONL converter. For every
source record, call `normalize_record`, validate with `DocumentRecord.model_validate`, write valid
records to the output JSONL, and write invalid records to the rejection JSONL. Exit non-zero when
the rejection rate exceeds `--max-rejection-rate`, whose default is `0.001`.

- [ ] **Step 5: 验证 fixture 与真实 100 篇文档**

Run:

```powershell
.venv\Scripts\python -m pytest tests\data\test_pubtables_v2.py -q
.venv\Scripts\python scripts\normalize_pubtables_v2.py --mapping configs\data\pubtables_v2_mapping.yaml --input data\pubtables-v2\full_documents --output artifacts\normalized\documents.jsonl --rejects artifacts\normalized\rejects.jsonl --limit 100 --max-rejection-rate 0.001
```

Expected: test passes; 100 valid records are emitted; rejection rate is at most 0.1%; every
logical table's fragment references are valid. Record any schema anomaly in the Task 5 report.

- [ ] **Step 6: Commit**

```powershell
git add configs/data/pubtables_v2_mapping.yaml src/cptla/data/pubtables_v2.py scripts/normalize_pubtables_v2.py tests/data/test_pubtables_v2.py tests/fixtures/pubtables_v2_raw_sample.json
git commit -m "feat: normalize PubTables-v2 document annotations"
```

---

### Task 7: 派生 continuation、列对应、重复表头和断裂行标签

**Files:**
- Create: `src/cptla/data/labels.py`
- Create: `scripts/derive_cross_page_labels.py`
- Create: `tests/data/test_labels.py`
- Create: `tests/fixtures/documents.jsonl`

**Interfaces:**
- Consumes: `DocumentRecord`
- Produces: `CrossPagePair` with fragment IDs, continuation label, monotonic column pairs, repeated header rows, split row pairs, and confidence.

- [ ] **Step 1: 写标签派生行为测试**

Create `tests/data/test_labels.py`:

```python
from cptla.data.labels import normalize_text, monotonic_column_pairs, repeated_header_rows


def test_normalize_text_removes_layout_noise() -> None:
    assert normalize_text("  Mean\u00ad value\n") == "meanvalue"


def test_monotonic_column_pairs_uses_global_indices() -> None:
    assert monotonic_column_pairs([0, 1, 3], [0, 2, 3]) == [(0, 0), (3, 3)]


def test_repeated_header_rows_matches_normalized_text() -> None:
    previous = {0: ["Age", "Mean Value"], 1: ["10", "2.0"]}
    following = {0: ["Age", "Mean value"], 2: ["11", "2.1"]}

    assert repeated_header_rows(previous, following, header_rows={0}) == {0}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\data\test_labels.py -q`

Expected: FAIL because `cptla.data.labels` does not exist.

- [ ] **Step 3: 实现可独立验证的标签函数**

Create `src/cptla/data/labels.py`:

```python
from __future__ import annotations

import re
import unicodedata
from typing import Iterable


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    return re.sub(r"\W+", "", normalized, flags=re.UNICODE).casefold()


def monotonic_column_pairs(
    previous_columns: Iterable[int], following_columns: Iterable[int]
) -> list[tuple[int, int]]:
    following = set(following_columns)
    return [(column, column) for column in sorted(set(previous_columns)) if column in following]


def repeated_header_rows(
    previous_rows: dict[int, list[str]],
    following_rows: dict[int, list[str]],
    header_rows: set[int],
) -> set[int]:
    previous_signatures = {
        tuple(normalize_text(value) for value in values)
        for row, values in previous_rows.items()
        if row in header_rows
    }
    return {
        row
        for row, values in following_rows.items()
        if tuple(normalize_text(value) for value in values) in previous_signatures
    }


def split_row_pairs(cell_pages: dict[str, set[int]], cell_rows: dict[str, int]) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    for cell_id, pages in cell_pages.items():
        ordered = sorted(pages)
        if len(ordered) > 1:
            row = cell_rows[cell_id]
            pairs.update((row, page) for page in ordered[1:])
    return pairs
```

- [ ] **Step 4: 创建跨两页的规范化 fixture**

Create `tests/fixtures/documents.jsonl` as one UTF-8 JSON line:

```json
{"document_id":"doc-1","source_split":"train","journal_id":"journal-a","page_count":2,"words":[{"page":0,"text":"Age","bbox":{"x0":0.10,"y0":0.10,"x1":0.20,"y1":0.15}},{"page":0,"text":"10","bbox":{"x0":0.10,"y0":0.20,"x1":0.20,"y1":0.25}},{"page":1,"text":"Age","bbox":{"x0":0.10,"y0":0.10,"x1":0.20,"y1":0.15}},{"page":1,"text":"11","bbox":{"x0":0.10,"y0":0.20,"x1":0.20,"y1":0.25}}],"tables":[{"table_id":"table-1","cells":[{"cell_id":"header","row":0,"column":0,"row_span":1,"column_span":1,"text":"Age","is_header":true,"word_indices":[0,2]},{"cell_id":"row-1","row":1,"column":0,"row_span":1,"column_span":1,"text":"10","is_header":false,"word_indices":[1]},{"cell_id":"row-2","row":2,"column":0,"row_span":1,"column_span":1,"text":"11","is_header":false,"word_indices":[3]}],"fragments":[{"fragment_id":"fragment-1","table_id":"table-1","page":0,"bbox":{"x0":0.05,"y0":0.10,"x1":0.95,"y1":0.95}},{"fragment_id":"fragment-2","table_id":"table-1","page":1,"bbox":{"x0":0.05,"y0":0.05,"x1":0.95,"y1":0.50}}]}]}
```

- [ ] **Step 5: 添加真实适配层和 JSONL 输出脚本**

Implement `scripts/derive_cross_page_labels.py` so it:

1. reads normalized `DocumentRecord` JSONL;
2. orders fragments by page;
3. emits one record for every adjacent fragment pair from the same logical table;
4. emits same-document adjacent-page negative pairs containing tables;
5. calls the tested functions above for columns, repeated headers, and split rows;
6. writes JSONL with `source_document_id`, `source_revision`, and `derivation_version="v1"`;
7. writes a summary JSON with positive/negative counts and confidence histogram.

The emitted record must have exactly these keys:

```json
{
  "document_id": "doc-1",
  "previous_fragment_id": "f1",
  "following_fragment_id": "f2",
  "continuation": true,
  "column_pairs": [[0, 0], [1, 1]],
  "repeated_header_rows": [0],
  "split_row_pairs": [],
  "confidence": 1.0,
  "source_revision": "resolved-hf-sha",
  "derivation_version": "v1"
}
```

- [ ] **Step 6: 验证合成 fixture 与 100 篇真实文档 dry run**

Run:

```powershell
.venv\Scripts\python -m pytest tests\data\test_labels.py -q
.venv\Scripts\python scripts\derive_cross_page_labels.py --input tests\fixtures\documents.jsonl --output artifacts\labels\fixture.jsonl --summary artifacts\labels\fixture-summary.json
.venv\Scripts\python scripts\derive_cross_page_labels.py --input data\pubtables-v2\sample\documents.jsonl --output artifacts\labels\sample-v1.jsonl --summary artifacts\labels\sample-v1-summary.json --limit 100
```

Expected: all tests pass; fixture produces the exact expected labels; the real dry run emits no invalid references and reports both positive and negative pairs. The real command is run only after Task 5 audits and Task 6 normalizes the actual dataset format.

- [ ] **Step 7: 建立人工审计表**

Create `artifacts/audit/cross-page-label-audit.csv` with columns:

```csv
document_id,previous_fragment_id,following_fragment_id,continuation_ok,column_pairs_ok,repeated_header_ok,split_row_ok,error_type,reviewer,notes
```

Sample 200-300 records stratified by page span and difficulty. Report label precision and error categories in `docs/reports/phase-1-exit.en.md` and `docs/reports/phase-1-exit.zh-CN.md`; do not use audited test records for training.

- [ ] **Step 8: Commit**

```powershell
git add src/cptla/data/labels.py scripts/derive_cross_page_labels.py tests/data/test_labels.py tests/fixtures
git commit -m "feat: derive cross-page table relation labels"
```

---

### Task 8: 构建无文档泄漏的官方和模板隔离划分

**Files:**
- Create: `src/cptla/data/splits.py`
- Create: `scripts/build_splits.py`
- Create: `tests/data/test_splits.py`

**Interfaces:**
- Consumes: document metadata with `document_id`, `source_split`, `journal_id`, optional template features
- Produces: JSONL manifest mapping every document to one split and one grouping strategy

- [ ] **Step 1: 写无泄漏测试**

Create `tests/data/test_splits.py`:

```python
from cptla.data.splits import group_disjoint_split, validate_no_group_leakage


def test_group_disjoint_split_keeps_journals_together() -> None:
    rows = [
        {"document_id": "a1", "journal_id": "a"},
        {"document_id": "a2", "journal_id": "a"},
        {"document_id": "b1", "journal_id": "b"},
        {"document_id": "c1", "journal_id": "c"},
        {"document_id": "d1", "journal_id": "d"},
    ]

    assigned = group_disjoint_split(rows, seed=20260724)

    assert validate_no_group_leakage(assigned) == []
    assert assigned["a1"]["split"] == assigned["a2"]["split"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\data\test_splits.py -q`

Expected: FAIL because `cptla.data.splits` does not exist.

- [ ] **Step 3: 实现确定性 group split**

Create `src/cptla/data/splits.py`:

```python
from __future__ import annotations

import hashlib
from typing import Iterable


def _bucket(group: str, seed: int) -> float:
    digest = hashlib.sha256(f"{seed}:{group}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def group_disjoint_split(
    rows: Iterable[dict[str, str]], seed: int
) -> dict[str, dict[str, str]]:
    assigned: dict[str, dict[str, str]] = {}
    for row in rows:
        group = row["journal_id"]
        value = _bucket(group, seed)
        split = "train" if value < 0.8 else "validation" if value < 0.9 else "test"
        assigned[row["document_id"]] = {"group": group, "split": split}
    return assigned


def validate_no_group_leakage(assigned: dict[str, dict[str, str]]) -> list[str]:
    group_splits: dict[str, set[str]] = {}
    for value in assigned.values():
        group_splits.setdefault(value["group"], set()).add(value["split"])
    return [group for group, splits in group_splits.items() if len(splits) > 1]
```

- [ ] **Step 4: 实现划分脚本和分布报告**

`scripts/build_splits.py` must support:

```text
--strategy official
--strategy journal-disjoint
--strategy template-disjoint
--seed 20260724
--input <document-metadata.jsonl>
--output <split-manifest.jsonl>
--report <split-report.json>
```

For `template-disjoint`, standardize numeric template features, cluster with agglomerative clustering using cosine distance, then apply the same deterministic group assignment to cluster IDs. The report must include document/table counts, continuation positives, page-span histogram, journal/group counts, and leakage checks per split.

- [ ] **Step 5: 验证划分**

Run:

```powershell
.venv\Scripts\python -m pytest tests\data\test_splits.py -q
.venv\Scripts\python scripts\build_splits.py --strategy official --input artifacts\metadata\documents.jsonl --output artifacts\splits\official.jsonl --report artifacts\splits\official-report.json --seed 20260724
.venv\Scripts\python scripts\build_splits.py --strategy journal-disjoint --input artifacts\metadata\documents.jsonl --output artifacts\splits\journal-disjoint.jsonl --report artifacts\splits\journal-disjoint-report.json --seed 20260724
```

Expected: tests pass; both reports show zero document/group leakage; no split is empty. If journal metadata coverage is below 90%, record the coverage and use template-disjoint as the primary OOD split.

- [ ] **Step 6: Commit**

```powershell
git add src/cptla/data/splits.py scripts/build_splits.py tests/data/test_splits.py
git commit -m "feat: add document-safe evaluation splits"
```

---

### Task 9: 实现关系、对齐和表格链评价

**Files:**
- Create: `src/cptla/metrics/relations.py`
- Create: `tests/metrics/test_relations.py`
- Create: `scripts/evaluate_baselines.py`

**Interfaces:**
- Produces: `binary_prf`, `edge_prf`, `chain_exact_match`, `alignment_accuracy`
- Later evaluation adapters add official document-level GriTS/TEDS without changing these interfaces.

- [ ] **Step 1: 写指标测试**

Create `tests/metrics/test_relations.py`:

```python
from cptla.metrics.relations import alignment_accuracy, binary_prf, chain_exact_match


def test_binary_prf_counts_exactly() -> None:
    result = binary_prf([True, True, False, False], [True, False, True, False])

    assert result == {"precision": 0.5, "recall": 0.5, "f1": 0.5}


def test_alignment_accuracy_uses_ground_truth_edges() -> None:
    assert alignment_accuracy({(0, 0), (1, 1)}, {(0, 0), (2, 1)}) == 0.5


def test_chain_exact_match_is_order_sensitive() -> None:
    assert chain_exact_match([["a", "b"]], [["a", "b"]]) == 1.0
    assert chain_exact_match([["a", "b"]], [["b", "a"]]) == 0.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\metrics\test_relations.py -q`

Expected: FAIL because `cptla.metrics.relations` does not exist.

- [ ] **Step 3: 实现指标**

Create `src/cptla/metrics/relations.py`:

```python
from __future__ import annotations

from collections.abc import Hashable, Sequence


def binary_prf(targets: Sequence[bool], predictions: Sequence[bool]) -> dict[str, float]:
    if len(targets) != len(predictions):
        raise ValueError("targets and predictions must have equal length")
    tp = sum(target and prediction for target, prediction in zip(targets, predictions))
    fp = sum(not target and prediction for target, prediction in zip(targets, predictions))
    fn = sum(target and not prediction for target, prediction in zip(targets, predictions))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def alignment_accuracy(
    targets: set[tuple[int, int]], predictions: set[tuple[int, int]]
) -> float:
    return len(targets & predictions) / len(targets) if targets else float(not predictions)


def chain_exact_match(
    targets: Sequence[Sequence[Hashable]], predictions: Sequence[Sequence[Hashable]]
) -> float:
    target_set = {tuple(chain) for chain in targets}
    prediction_set = {tuple(chain) for chain in predictions}
    return float(target_set == prediction_set)
```

- [ ] **Step 4: 对接官方文档级指标**

Add an adapter command in `scripts/evaluate_baselines.py` that writes predictions in the exact PubTables-v2 expected format and runs the official evaluator when available. Record the evaluator repository URL and resolved Git SHA in every result JSON. Until the official evaluator is available, label document-level GriTS/TEDS fields as `not_computed`; never substitute a locally different metric under the same name.

- [ ] **Step 5: 验证指标**

Run:

```powershell
.venv\Scripts\python -m pytest tests\metrics\test_relations.py -q
.venv\Scripts\python -m ruff check src/cptla/metrics tests/metrics
```

Expected: `3 passed`, Ruff exits 0.

- [ ] **Step 6: Commit**

```powershell
git add src/cptla/metrics tests/metrics scripts/evaluate_baselines.py
git commit -m "feat: add cross-page relation metrics"
```

---

### Task 10: 实现规则 continuation 与结构感知拼接基线

**Files:**
- Create: `src/cptla/baselines/rules.py`
- Create: `tests/baselines/test_rules.py`
- Modify: `scripts/evaluate_baselines.py`

**Interfaces:**
- Consumes: adjacent `TableFragmentFeatures` and normalized table grids
- Produces: continuation probability, monotonic column pairs, merged logical table

- [ ] **Step 1: 写规则基线测试**

Create `tests/baselines/test_rules.py`:

```python
from cptla.baselines.rules import FragmentFeatures, continuation_score, match_columns


def test_continuation_score_rewards_page_boundary_and_overlap() -> None:
    previous = FragmentFeatures(bottom_gap=0.01, top_gap=0.80, x0=0.10, x1=0.90, columns=(0.1, 0.5, 0.9))
    following = FragmentFeatures(bottom_gap=0.80, top_gap=0.02, x0=0.11, x1=0.89, columns=(0.11, 0.51, 0.89))

    assert continuation_score(previous, following) > 0.8


def test_match_columns_is_monotonic() -> None:
    pairs = match_columns((0.1, 0.5, 0.9), (0.11, 0.52, 0.88), tolerance=0.05)

    assert pairs == [(0, 0), (1, 1), (2, 2)]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\baselines\test_rules.py -q`

Expected: FAIL because `cptla.baselines.rules` does not exist.

- [ ] **Step 3: 实现确定性规则基线**

Create `src/cptla/baselines/rules.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FragmentFeatures:
    bottom_gap: float
    top_gap: float
    x0: float
    x1: float
    columns: tuple[float, ...]


def _interval_iou(a0: float, a1: float, b0: float, b1: float) -> float:
    intersection = max(0.0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return intersection / union if union else 0.0


def continuation_score(previous: FragmentFeatures, following: FragmentFeatures) -> float:
    boundary = max(0.0, 1.0 - (previous.bottom_gap + following.top_gap) / 0.2)
    overlap = _interval_iou(previous.x0, previous.x1, following.x0, following.x1)
    count = 1.0 if len(previous.columns) == len(following.columns) else 0.0
    return 0.4 * boundary + 0.4 * overlap + 0.2 * count


def match_columns(
    previous: tuple[float, ...], following: tuple[float, ...], tolerance: float
) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    following_start = 0
    for previous_index, previous_x in enumerate(previous):
        candidates = [
            (abs(previous_x - following_x), following_index)
            for following_index, following_x in enumerate(following[following_start:], following_start)
            if abs(previous_x - following_x) <= tolerance
        ]
        if candidates:
            _, following_index = min(candidates)
            pairs.append((previous_index, following_index))
            following_start = following_index + 1
    return pairs
```

- [ ] **Step 4: 增加三种可比较配置**

Add to `scripts/evaluate_baselines.py`:

- `position-only`: page-boundary features only;
- `official-simple`: learned continuation prediction plus equal column count concat;
- `structure-aware-rule`: page boundary, horizontal overlap, header text, and monotonic column matching.

All configurations must emit the same JSONL prediction schema and a result JSON containing relation metrics, runtime, source revision, config, and seed.

- [ ] **Step 5: 验证并运行小样本基线**

Run:

```powershell
.venv\Scripts\python -m pytest tests\baselines\test_rules.py -q
.venv\Scripts\python scripts\evaluate_baselines.py --labels artifacts\labels\sample-v1.jsonl --split artifacts\splits\official.jsonl --baseline structure-aware-rule --output outputs\baselines\structure-aware-rule-sample.json
```

Expected: tests pass; result JSON has non-null continuation P/R/F1, alignment accuracy, chain exact match, sample count, runtime, and seed.

- [ ] **Step 6: Commit**

```powershell
git add src/cptla/baselines tests/baselines scripts/evaluate_baselines.py
git commit -m "feat: add reproducible cross-page rule baselines"
```

---

### Task 11: 复现 ViT-B/16 continuation 学习基线

**Files:**
- Create: `configs/experiments/continuation_vit.yaml`
- Create: `src/cptla/baselines/vision.py`
- Create: `scripts/train_continuation.py`
- Create: `tests/baselines/test_vision.py`

**Interfaces:**
- Consumes: two adjacent rendered page images and a binary continuation label
- Produces: probability in `[0, 1]`, checkpoint metadata, validation/test metrics

- [ ] **Step 1: 写图像拼接与模型输出测试**

Create `tests/baselines/test_vision.py`:

```python
import pytest

torch = pytest.importorskip("torch")

from cptla.baselines.vision import concatenate_page_pair, create_model


def test_pair_tensor_shape_is_stable() -> None:
    left = torch.zeros(3, 224, 112)
    right = torch.ones(3, 224, 112)

    pair = concatenate_page_pair(left, right)

    assert pair.shape == (3, 224, 224)


def test_model_returns_one_logit_per_pair() -> None:
    model = create_model(pretrained=False)

    assert model(torch.zeros(2, 3, 224, 224)).shape == (2, 1)
```

- [ ] **Step 2: 安装训练依赖并确认测试失败**

Run:

```powershell
.venv\Scripts\python -m pip install -e ".[dev,train]"
.venv\Scripts\python -m pytest tests\baselines\test_vision.py -q
```

Expected: FAIL because `cptla.baselines.vision` does not exist.

- [ ] **Step 3: 实现 ViT-B/16 分类器接口**

Create `src/cptla/baselines/vision.py`:

```python
from __future__ import annotations

import torch
from torch import Tensor, nn
from torchvision.models import ViT_B_16_Weights, vit_b_16


def concatenate_page_pair(left: Tensor, right: Tensor) -> Tensor:
    if left.shape != right.shape or left.ndim != 3:
        raise ValueError("page tensors must have equal CHW shape")
    return torch.cat((left, right), dim=2)


def create_model(pretrained: bool = True) -> nn.Module:
    weights = ViT_B_16_Weights.DEFAULT if pretrained else None
    model = vit_b_16(weights=weights)
    model.heads.head = nn.Linear(model.heads.head.in_features, 1)
    return model
```

- [ ] **Step 4: 定义固定实验配置**

Create `configs/experiments/continuation_vit.yaml`:

```yaml
model: vit_b_16
pretrained: true
image_size: 224
page_pair_layout: horizontal
optimizer: adamw
learning_rate: 0.0001
weight_decay: 0.01
epochs: 20
batch_size_per_gpu: 64
early_stopping_patience: 4
selection_metric: validation_f1
threshold_selection: validation_f1
seed: 20260724
num_workers: 8
amp: bf16
```

- [ ] **Step 5: 实现训练入口**

`scripts/train_continuation.py` must:

- load only IDs assigned to the requested split manifest;
- horizontally concatenate adjacent page images after aspect-preserving resize/padding;
- train with `BCEWithLogitsLoss` and AdamW;
- choose the probability threshold on validation F1 only;
- save model weights separately from a JSON metadata file;
- record config, data revision, split hash, seed, Git commit, device, CUDA/PyTorch versions, epoch metrics, best threshold, and runtime;
- support `--smoke-test` to train two batches on CPU without downloading pretrained weights.

- [ ] **Step 6: 本地 CPU smoke test**

Run:

```powershell
.venv\Scripts\python -m pytest tests\baselines\test_vision.py -q
.venv\Scripts\python scripts\train_continuation.py --config configs\experiments\continuation_vit.yaml --output outputs\smoke\vit --smoke-test
```

Expected: tests pass; smoke test finishes two batches, writes metadata, and produces finite loss/probabilities.

- [ ] **Step 7: H100 正式训练与复现判据**

Run on the lab server with its environment launcher:

```bash
python scripts/train_continuation.py \
  --config configs/experiments/continuation_vit.yaml \
  --labels artifacts/labels/pubtables-v2-v1.jsonl \
  --split artifacts/splits/official.jsonl \
  --output outputs/continuation/vit-b16-seed-20260724
```

Repeat with seeds `20260725` and `20260726`. The baseline is considered reproduced when all three runs complete, their mean and standard deviation are reported, and discrepancies from PubTables-v2's published F1=0.991 are explained using split, preprocessing, or data revision evidence rather than hidden tuning.

- [ ] **Step 8: Commit**

```powershell
git add configs/experiments/continuation_vit.yaml src/cptla/baselines/vision.py scripts/train_continuation.py tests/baselines/test_vision.py
git commit -m "feat: reproduce ViT cross-page continuation baseline"
```

---

### Task 12: 建立实验注册表并完成第一阶段验收报告

**Files:**
- Create: `src/cptla/experiments/registry.py`
- Create: `tests/experiments/test_registry.py`
- Create: `docs/reports/phase-1-exit.en.md`
- Create: `docs/reports/phase-1-exit.zh-CN.md`

**Interfaces:**
- Produces: immutable experiment record with ID, config hash, split hash, source revision, seed, commit, metrics, and artifact paths
- Produces: phase exit report that makes a go/no-go decision for the graph-model phase

- [ ] **Step 1: 写实验记录确定性测试**

Create `tests/experiments/test_registry.py`:

```python
from cptla.experiments.registry import experiment_id


def test_experiment_id_is_order_independent() -> None:
    first = experiment_id({"seed": 20260724, "model": "vit_b_16"})
    second = experiment_id({"model": "vit_b_16", "seed": 20260724})

    assert first == second
    assert len(first) == 12
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests\experiments\test_registry.py -q`

Expected: FAIL because `cptla.experiments.registry` does not exist.

- [ ] **Step 3: 实现实验 ID 和记录校验**

Create `src/cptla/experiments/registry.py`:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def experiment_id(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def write_record(path: Path, record: dict[str, Any]) -> None:
    required = {"config", "split_hash", "source_revision", "seed", "git_commit", "metrics"}
    missing = required - record.keys()
    if missing:
        raise ValueError(f"missing experiment fields: {sorted(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

- [ ] **Step 4: 运行完整本地质量门**

Run:

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check src tests scripts
```

Expected: all tests pass; Ruff exits 0. Record exact test count and tool versions in the report.

- [ ] **Step 5: 编写第一阶段验收报告**

Create `docs/reports/phase-1-exit.en.md` with these completed sections, then create
`docs/reports/phase-1-exit.zh-CN.md` as a reviewed, content-equivalent Chinese report:

```markdown
# Phase 1 Exit Report

## Evidence Base

Report screened/read paper counts, taxonomy, closest prior work, and the remaining novelty claim.

## Dataset Audit

Report resolved PubTables-v2 revision, collection/schema findings, storage requirements, and
metadata coverage.

## Derived Label Quality

Report automatic counts, 200-300 sample human-audit precision, and error categories for
continuation, column pairs, repeated headers, and split rows.

## Split Integrity

Report official and OOD distribution tables, journal/template coverage, and zero-leakage checks.

## Baselines

Report rule and ViT results over three seeds, runtime, and differences from published results.

## Error Analysis

Report at least 50 inspected failures grouped by detection, continuation, column alignment,
repeated header, split row, rotation, multi-column layout, and annotation noise.

## Phase 2 Decision

Proceed only if labels and metrics are reliable, a baseline runs end to end, and the observed
errors include structure failures not solved by continuation classification alone. Otherwise,
fix the failed foundation before implementing the graph model.
```

Every section in both language versions must contain the same measured values, links to experiment
record IDs, and concrete evidence; empty narrative sections do not satisfy the exit gate. The task
is incomplete until the English and Chinese reports pass structural and factual parity review.

- [ ] **Step 6: Commit**

```powershell
git add src/cptla/experiments tests/experiments docs/reports/phase-1-exit.en.md docs/reports/phase-1-exit.zh-CN.md
git commit -m "docs: complete phase one research baseline report"
```

---

## Phase 1 Completion Gate

Phase 1 is complete only when all of the following are true:

- `papers.csv` contains at least 40 screened papers and 25 fully read papers.
- PubTables-v2 repository revision and schema are recorded from primary sources.
- The normalized data adapter passes tests and a 100-document real-data dry run.
- Derived-label quality is measured on 200-300 human-reviewed samples.
- Official and template/journal-disjoint splits pass zero-leakage checks.
- Rule baselines run end to end with immutable experiment records.
- ViT-B/16 runs for three seeds on H100 and the difference from the published baseline is explained.
- At least 50 baseline failures are manually categorized.
- Full pytest and Ruff verification pass from a clean checkout.
- The exit report supports or rejects proceeding to the hierarchical graph model with evidence.

After this gate passes, create a separate Phase 2 implementation plan for the shared page encoder, hierarchical relation graph, joint losses, and constrained decoder. Phase 3 receives its own plan for full ablations, template-disjoint evaluation, VLM comparisons, statistical analysis, and paper artifacts.
