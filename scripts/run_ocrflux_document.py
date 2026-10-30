"""Instrumented official OCRFlux API; all-page image-only PDFs, no truth input."""

import argparse
import datetime
import hashlib
import json
import subprocess
import time
from pathlib import Path

from cptla.evaluation.document_run import digest, write_new_json
from cptla.evaluation.ocrflux_document import ResourceSafetyStop, reconstruct


def gpu_free():
    return int(
        subprocess.check_output(
            ["nvidia-smi", "-i", "0", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            text=True,
        ).strip()
    )


def run(inputs, output, model):
    if output.exists():
        raise FileExistsError(output)
    packing = json.loads((inputs / "packing-manifest.json").read_text())
    if packing["pdf_text_audit"] != "empty" or packing["embedded_image_audit"] != "byte-identical":
        raise ValueError("Require audited image-only PDFs")
    for pdf in packing["pdfs"]:
        target = (inputs / pdf["file"]).resolve()
        if not target.is_relative_to(inputs.resolve()) or digest(target) != pdf["sha256"]:
            raise ValueError("PDF integrity/path mismatch")
    if gpu_free() < 30000:
        raise RuntimeError("Need at least 30000MiB free before model load")
    output.mkdir(parents=True, exist_ok=False)
    raw = output / "raw"
    raw.mkdir()
    import torch
    from ocrflux.inference import (
        build_element_merge_detect_query,
        build_html_table_merge_query,
        build_page_to_markdown_query,
    )
    from ocrflux.prompts import PageResponse
    from ocrflux.table_format import table_matrix2html
    from vllm import LLM, SamplingParams

    config = dict(
        model=str(model.resolve()),
        gpu_memory_utilization=0.20,
        max_model_len=16384,
        max_num_seqs=1,
        enforce_eager=True,
        tensor_parallel_size=1,
        dtype="bfloat16",
        seed=0,
        limit_mm_per_prompt={"image": 1, "video": 0},
    )
    metadata = {
        "engine": config,
        "max_tokens": 8192,
        "temperature": 0,
        "max_page_retries": 0,
        "input_track": "image-only",
        "input_sha256": digest(inputs / "packing-manifest.json"),
        "data_revision": "aa575e798cb00a296925e2086addb3e3fd9a1903",
        "model_revision": "e68592278bbc8ab32edf7b65e6e411f1d878ef72",
        "official_commit": "c1b315aa4c8309f8dc436a5d90fc4977bcf0d865",
        "started_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "code_sha256": {
            str(p): digest(p)
            for p in [
                Path(__file__),
                Path(__import__("cptla.evaluation.ocrflux_document", fromlist=[""]).__file__),
            ]
        },
    }
    write_new_json(output / "run-manifest.json", metadata)
    count = 0
    llm = None
    summary = {"status": "failed", "documents": [], "pages": 0}
    try:
        llm = LLM(**config)
        params = SamplingParams(temperature=0, max_tokens=8192, seed=0)

        def generate(stage, identity, query):
            nonlocal count
            if gpu_free() < 8192:
                raise ResourceSafetyStop("Shared GPU below 8192MiB safety threshold")
            count += 1
            start = time.monotonic()
            record = {
                "stage": stage,
                "identity": identity,
                "prompt": query["prompt"],
                "prompt_sha256": hashlib.sha256(query["prompt"].encode()).hexdigest(),
            }
            try:
                response = llm.generate([query], sampling_params=params, use_tqdm=False)[0]
                item = response.outputs[0]
                record.update(
                    text=item.text, finish_reason=item.finish_reason, tokens=len(item.token_ids)
                )
                if item.finish_reason != "stop":
                    raise ValueError("Generation truncated or incomplete")
                return item.text
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                record["elapsed_sec"] = time.monotonic() - start
                write_new_json(raw / f"{count:06d}.json", record)
                print(
                    json.dumps(
                        {
                            "event": "request",
                            "stage": stage,
                            "identity": identity,
                            "elapsed_sec": record["elapsed_sec"],
                            "error": record.get("error"),
                        }
                    ),
                    flush=True,
                )

        for doc in packing["pdfs"]:
            identifier = doc["document_id"]
            pages, records = [], []
            for page in range(doc["pages"]):
                start = time.monotonic()
                warnings = []
                try:
                    query = build_page_to_markdown_query(str(inputs / doc["file"]), page + 1)
                    text = generate("page", [identifier, page], query)
                    parsed = PageResponse(**json.loads(text))
                    elements = []
                    for element in parsed.natural_text.split("\n\n"):
                        if element.startswith("<Image>") and element.endswith("</Image>"):
                            continue
                        if element.startswith("<table>") and element.endswith("</table>"):
                            try:
                                element = table_matrix2html(element)
                            except Exception:
                                warnings.append("official_table_conversion_fallback")
                                element = (
                                    element.replace("<t>", "")
                                    .replace("<l>", "")
                                    .replace("<lt>", "")
                                )
                        elements.append(element)
                    pages.append(elements)
                    record = {"status": "ok", "warnings": warnings}
                except (RuntimeError, MemoryError):
                    raise
                except Exception as exc:
                    pages.append(None)
                    record = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
                record["elapsed_sec"] = time.monotonic() - start
                records.append(record)
                write_new_json(
                    raw / f"{identifier}-page-{page}.json", {"elements": pages[-1], **record}
                )
            result = reconstruct(
                identifier,
                pages,
                lambda a, b, doc_id=identifier: generate(
                    "detect", doc_id, build_element_merge_detect_query(a, b)
                ),
                lambda a, b, doc_id=identifier: generate(
                    "merge", doc_id, build_html_table_merge_query(a, b)
                ),
            )
            write_new_json(
                output / f"{identifier}.json",
                {"document_id": identifier, "pages": records, **result},
            )
            summary["documents"].append(identifier)
            summary["pages"] += doc["pages"]
        summary["status"] = "completed"
    except BaseException as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        summary["ended_utc"] = datetime.datetime.now(datetime.UTC).isoformat()
        write_new_json(output / "summary.json", summary)
        if torch.distributed.is_initialized():
            torch.distributed.destroy_process_group()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    run(args.inputs, args.output_dir, args.model)
