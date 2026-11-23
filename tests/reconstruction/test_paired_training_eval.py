import hashlib
import importlib
import json
from argparse import Namespace
from pathlib import Path

import pytest

from cptla.reconstruction.data import DATASET_REVISION


def test_dev_generation_is_target_blind_and_receipts_resume(tmp_path, monkeypatch):
    scripts = Path(__file__).parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    evaluation = importlib.import_module("evaluate_reconstruction_paired_training")
    review = importlib.import_module("review_reconstruction_qwen_smoke")
    group_ids = [f"dev{i}" for i in range(16)]
    fit_ids = [f"fit{i}" for i in range(250)]
    artifact_hashes = {}

    def put(name, value, *, jsonl=False):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = (
            "\n".join(json.dumps(row) for row in value) if jsonl else json.dumps(value)
        ).encode()
        path.write_bytes(data)
        artifact_hashes[name] = hashlib.sha256(data).hexdigest()
        return name

    dev = [
        dict(
            group_id=key,
            document_id=key,
            cluster_id=key,
            dataset_revision=DATASET_REVISION,
            split="train_dev",
            source_split="train",
            fragments=[{}] * (2 if i < 8 else 3),
        )
        for i, key in enumerate(group_ids)
    ]
    inputs = put(
        "audit/paired-inputs.jsonl",
        dev + [dict(group_id=key, document_id=key, cluster_id=key) for key in fit_ids],
        jsonl=True,
    )
    put("audit/dev-inputs.jsonl", dev, jsonl=True)
    overlay = put(
        evaluation.OVERLAY,
        [
            dict(
                document_id=g,
                cluster_id=g,
                effective_split="train_dev",
                observed_cluster=False,
            )
            for g in group_ids
        ],
        jsonl=True,
    )
    original_selection = put(
        "audit/original.json",
        dict(
            groups=[
                dict(
                    group_id=row["group_id"],
                    document_id=row["document_id"],
                    cluster_id=row["cluster_id"],
                    fragments=len(row["fragments"]),
                )
                for row in dev
            ],
            overlay_sha256=artifact_hashes[overlay],
        ),
    )
    selection = put(
        "audit/selection.json",
        dict(
            dataset_revision=DATASET_REVISION,
            split="train_dev",
            groups=group_ids,
            original_selection=original_selection,
            upstream_runs=[evaluation.DEV_UPSTREAM],
            targets_sha256="original-hash",
        ),
    )
    reference = "<table><tr><td>A</td></tr></table>"
    targets = put(
        "audit/dev-targets.jsonl",
        [dict(group_id=g, source_pages=[1, 2], html=reference) for g in group_ids],
        jsonl=True,
    )
    put(
        "audit/dev-targets-receipt.json",
        dict(
            path=targets,
            sha256=artifact_hashes[targets],
            source_targets_sha256="original-hash",
            groups=group_ids,
        ),
    )
    audit = put(
        "audit/audit.json",
        dict(
            status="completed",
            dataset_revision=DATASET_REVISION,
            training_groups=250,
            dev_groups=16,
            input_overlap=0,
            doc_overlap=0,
            cluster_overlap=0,
            dev_upstream=evaluation.DEV_UPSTREAM,
            files_sha256={k: artifact_hashes[k] for k in (overlay, original_selection)},
        ),
    )
    put(
        "training/summary.json",
        dict(status="completed", scope="train_only", complete=True, train_steps=500),
    )
    put(
        "training/manifest.json",
        dict(
            config=dict(
                arm="direct",
                inputs=inputs,
                targets="training-targets-must-not-be-read.jsonl",
                heldout_selection=selection,
                model="model",
                output_format="html",
            ),
            revision=DATASET_REVISION,
            train=fit_ids,
            heldout=group_ids,
            model_revision="pinned-model",
            dtype="float32",
        ),
    )
    put("training/input-hashes.json", {k: artifact_hashes[k] for k in (inputs, selection)})
    model = put("model/test.safetensors", "model")
    put("training/model-hashes.json", {model: artifact_hashes[model]})
    files = ["lora/adapter_config.json", "lora/adapter_model.safetensors"]
    for file in files:
        put("training/" + file, "checkpoint")
    put(
        "training/checkpoint-hashes.json",
        {file: artifact_hashes["training/" + file] for file in files},
    )

    def input_examples(root, config, read, *, expected_split):
        assert expected_split == "train_dev"
        assert config["inputs"] == root / "audit/dev-inputs.jsonl"
        return [
            dict(group_id=g, source_pages=[1, 2], messages=[{"role": "user"}])
            for g in config["group_id"]
        ], {}

    monkeypatch.setattr(review, "input_examples", input_examples)
    monkeypatch.setattr(
        evaluation, "generation_backend", lambda *args: lambda m, budget: (reference, 20, True)
    )
    args = Namespace(
        project_root=tmp_path,
        run="20261123T120000Z-direct-eval",
        training_run="training",
        data_audit=audit,
        gpu=0,
        max_new_tokens=8192,
        resume_from=None,
    )
    output_root = tmp_path / "artifacts/reconstruction-paired-training-eval"
    read_bytes = Path.read_bytes

    def checked_read(path):
        if path == tmp_path / targets:
            run = output_root / args.run
            assert len(list(run.glob("receipt-*.json"))) == 16
            assert (run / "predictions.json").exists()
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", checked_read)
    evaluation.run(args)
    old_output = output_root / args.run
    assert (
        json.loads((old_output / "scores.json").read_bytes())["diagnostic_rates"]["joint_exact"]
        == 1.0
    )

    def no_gpu(*args):
        pytest.fail("all 16 records are already durably published")

    monkeypatch.setattr(evaluation, "generation_backend", no_gpu)
    args.resume_from = old_output
    args.run = "20261123T120001Z-direct-resumed"
    evaluation.run(args)
    new_output = output_root / args.run
    assert json.loads((new_output / "summary.json").read_bytes())["reused_predictions"] == 16
    assert (new_output / "predictions.json").read_bytes() == (
        old_output / "predictions.json"
    ).read_bytes()

    (old_output / "prediction-001.json").write_text('{"group_id":"different"}')
    args.run = "20261123T120002Z-direct-tamper"
    with pytest.raises(ValueError, match="identity or checksum"):
        evaluation.run(args)
