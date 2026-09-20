"""Score dots.ocr page outputs as document table extraction predictions."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from grits import GritsEvaluator, html_to_cell_list
from json_repair import repair_json


def parse_layout(raw: str):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = repair_json(raw, return_objects=True)
    if isinstance(value, dict):
        for key in ("layouts", "elements", "result", "data"):
            if isinstance(value.get(key), list):
                return value[key]
        return [value]
    if isinstance(value, list):
        return value
    raise ValueError("layout output is neither an object nor a list")


def document_id(image: str) -> str:
    return re.sub(r"_page_\d+\.jpg$", "", Path(image).name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", nargs="+", type=Path)
    parser.add_argument("--truth-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()

    pred_by_doc = defaultdict(list)
    page_status = {"ok": 0, "error": 0, "parse_error": 0, "invalid_table_html": 0}
    seen_pages = set()
    for filename in args.predictions:
        if not filename.exists():
            continue
        for line in filename.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            image = record["image"]
            if image in seen_pages:
                continue
            seen_pages.add(image)
            if record.get("status") != "ok":
                page_status["error"] += 1
                continue
            page_status["ok"] += 1
            try:
                elements = parse_layout(record["output"])
            except Exception:
                page_status["parse_error"] += 1
                continue
            for element in elements:
                if str(element.get("category", "")).lower() == "table":
                    html = element.get("text", "")
                    if "<table" in html.lower() and html_to_cell_list(html) is not None:
                        pred_by_doc[document_id(image)].append(html)
                    elif "<table" in html.lower():
                        page_status["invalid_table_html"] += 1

    truth_by_doc = {}
    for filename in args.truth_dir.glob("*_tables.json"):
        doc = filename.name.removesuffix("_tables.json")
        truth_by_doc[doc] = [table["html"] for table in json.loads(filename.read_text())]

    docs = sorted(pred_by_doc if args.partial else truth_by_doc)
    evaluator = GritsEvaluator(metrics=["top", "con"])
    failed_docs = []
    for doc in docs:
        try:
            evaluator.eval_htmls(truth_by_doc.get(doc, []), pred_by_doc.get(doc, []))
        except ValueError as error:
            failed_docs.append({"document": doc, "error": str(error)[:500]})
            evaluator.eval_htmls(truth_by_doc.get(doc, []), [])
    metrics = evaluator.compute_grits()
    result = {
        "scope": "partial_completed_documents" if args.partial else "full_validation",
        "documents_scored": len(docs),
        "pages_seen": len(seen_pages),
        "page_status": page_status,
        "predicted_tables": sum(map(len, pred_by_doc.values())),
        "parse_failed_documents": failed_docs,
        "Acc-Top": metrics.get("grits_top_grid_exact_match_accuracy"),
        "Acc-Con": metrics.get("grits_con_grid_exact_match_accuracy"),
        **metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
