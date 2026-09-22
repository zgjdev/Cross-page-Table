# TATR HTML Rebuild and Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct TATR table-header HTML serialization, rebuild evaluation HTML from saved raw cells without GPU inference, and rerun the existing official GriTS scorer in a new server output directory.

**Architecture:** Keep the official GriTS scoring implementation unchanged. Fix the single serialization boundary in `cptla.evaluation.tatr`, add a small streaming rebuild module and CLI, then run the existing `score_pubtables_v2_predictions.py` against the rebuilt JSONL.

**Tech Stack:** Python 3.12, `xml.etree.ElementTree`, Pydantic, pytest, vendored official GriTS.

## Global Constraints

- Do not overwrite existing predictions, metrics, logs, or data.
- Do not rerun model inference or use a GPU.
- Rebuild from `raw_output.cells` and write a new timestamped output directory.
- Preserve image IDs, unit IDs, statuses, errors, warnings, and record count.
- Require exact manifest coverage before reporting full-validation metrics.

---

### Task 1: Correct HTML serialization

**Files:**
- Modify: `tests/evaluation/test_tatr.py`
- Modify: `src/cptla/evaluation/tatr.py:141-174`

**Interfaces:**
- Consumes: `cells_to_html(cells: list[dict[str, object]]) -> str`
- Produces: standards-compliant `table > thead|tbody > tr > th|td` HTML.

- [ ] **Step 1: Change the existing single-header regression expectation and add a multi-row header round-trip test**

```python
def test_cells_to_html_preserves_header_and_spans() -> None:
    ...
    assert cells_to_html(cells) == (
        '<table><thead><tr><th colspan="2">Header</th></tr></thead>'
        '<tbody><tr><td>A</td><td>B</td></tr></tbody></table>'
    )

def test_cells_to_html_round_trips_multilevel_header_grid() -> None:
    cells = [
        {"row_nums": [0], "column_nums": [0, 1], "cell_text": "Group", "header": True},
        {"row_nums": [1], "column_nums": [0], "cell_text": "A", "header": True},
        {"row_nums": [1], "column_nums": [1], "cell_text": "B", "header": True},
        {"row_nums": [2], "column_nums": [0], "cell_text": "1", "header": False},
        {"row_nums": [2], "column_nums": [1], "cell_text": "2", "header": False},
    ]
    parsed = html_to_cell_list(cells_to_html(cells))
    assert parsed is not None
    assert cell_list_to_grid_top(parsed) == cell_list_to_grid_top(
        [TableCell.from_dict({**cell, "is_column_header": cell["header"]}) for cell in cells]
    )
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest tests/evaluation/test_tatr.py -q`

Expected: the existing serializer output assertion fails because `<tr>` and `<tbody>` are absent; the round-trip test fails because the header row index is corrupted.

- [ ] **Step 3: Implement row grouping and valid section nesting**

Group cells by `min(row_nums)`, create one `<tr>` per row, place header rows under one `<thead>` and body rows under one `<tbody>`, then append `th` or `td` cells with the existing span attributes and text.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `pytest tests/evaluation/test_tatr.py -q`

Expected: all tests pass.

### Task 2: Add streaming raw-cell rebuild

**Files:**
- Create: `src/cptla/evaluation/tatr_rebuild.py`
- Create: `scripts/rebuild_tatr_predictions.py`
- Create: `tests/evaluation/test_tatr_rebuild.py`

**Interfaces:**
- Produces: `rebuild_tatr_prediction(record: PredictionRecord) -> PredictionRecord`
- Produces: `rebuild_tatr_predictions_jsonl(source: Path, destination: Path) -> dict[str, int]`

- [ ] **Step 1: Write failing tests for successful, empty, error, and invalid raw records**

The tests construct real `PredictionRecord` values, assert regenerated standard HTML, assert preservation of identity/status metadata, assert omission of `raw_output` from the written lightweight JSONL, and assert a contextual `ValueError` when a successful record has missing or invalid `raw_output.cells`.

- [ ] **Step 2: Run the new test module and verify RED**

Run: `pytest tests/evaluation/test_tatr_rebuild.py -q`

Expected: collection fails because `cptla.evaluation.tatr_rebuild` does not exist.

- [ ] **Step 3: Implement the minimal rebuild module and CLI**

Parse each line with `PredictionRecord.model_validate_json()`. Preserve error records. For successful records, parse the raw JSON object, require a list-valued `cells`, call `cells_to_html()`, and update `tables_html`. Stream records to a new file opened with exclusive creation mode `x`; serialize with `exclude={"raw_output"}` to avoid duplicating the 1.2 GB raw payload.

- [ ] **Step 4: Run rebuild and evaluation tests**

Run: `pytest tests/evaluation/test_tatr_rebuild.py tests/evaluation/test_tatr.py tests/evaluation/test_scoring.py -q`

Expected: all tests pass.

### Task 3: Verify locally and launch the server job

**Files:**
- Server create: new timestamped directories under `outputs/baselines/tatr-v1.1-pub/` and `logs/baselines/tatr-v1.1-pub/`
- Server create: run script, PID, timestamps, exit code, rebuilt predictions, metrics, failures, checksums, and run manifest.

**Interfaces:**
- Consumes: existing full predictions, frozen manifest, frozen validation truth.
- Produces: corrected full-validation metrics from the unchanged official GriTS scorer.

- [ ] **Step 1: Run local verification**

Run: `pytest -q`

Run: `ruff check src/cptla/evaluation/tatr.py src/cptla/evaluation/tatr_rebuild.py scripts/rebuild_tatr_predictions.py tests/evaluation/test_tatr.py tests/evaluation/test_tatr_rebuild.py`

Expected: zero failures and zero lint errors.

- [ ] **Step 2: Synchronize only the relevant committed code to the server**

Push the implementation commit, then fast-forward the server branch without synchronizing `data/`, `artifacts/`, `outputs/`, or `logs/`.

- [ ] **Step 3: Run the fixed 24-sample validation and a timed scoring subset**

Verify the nine known exact matches, unchanged IDs/statuses, valid HTML parsing, deterministic repeated metrics, and measure rebuild plus GriTS throughput.

- [ ] **Step 4: Start the full CPU job in a new timestamped directory**

The background script first rebuilds all 13,384 records, validates exact coverage, scores with `score_pubtables_v2_predictions.py`, writes checksums and a run manifest, and records timestamps and exit status. It must never overwrite an existing path.

- [ ] **Step 5: Estimate completion time from measured throughput**

Report the run ID, PID/process evidence, input/output paths, sample timing, estimated finish window, and the command/evidence the user can request later to check completion.
