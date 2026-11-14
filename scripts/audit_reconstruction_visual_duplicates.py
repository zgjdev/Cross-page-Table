"""训练图像 dHash 近重复候选审计；不校准阈值、不修改划分。"""

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image
from PIL import __version__ as pillow_version

from cptla.evaluation.pubtables_v2 import parse_full_document_image_id
from cptla.reconstruction.data import DATASET_REVISION, TRAIN_RELATIVE_PATH


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inside(root, path):
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError("path escapes project")
    return result


def candidates(rows):
    """5 disjoint bands guarantee candidate recall for 64-bit Hamming <=4."""
    buckets = defaultdict(list)
    for index, row in enumerate(rows):
        value = row["dhash"]
        keys = [
            (band, (value >> offset) & ((1 << width) - 1))
            for band, (offset, width) in enumerate(
                [(0, 13), (13, 13), (26, 13), (39, 13), (52, 12)]
            )
        ]
        possible = set()
        for key in keys:
            possible.update(buckets[key])
            buckets[key].append(index)
        for other in sorted(possible):
            if rows[other]["document_id"] == row["document_id"]:
                continue
            distance = (rows[other]["dhash"] ^ value).bit_count()
            if distance <= 4:
                yield other, index, distance


def dhash(path):
    with Image.open(path) as image:
        pixels = list(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).getdata())
    return sum(
        1 << (y * 8 + x)
        for y in range(8)
        for x in range(8)
        if pixels[y * 9 + x] > pixels[y * 9 + x + 1]
    )


def audit(project_root, inputs, run, *, limit_images=None):
    root = Path(project_root).resolve()
    inputs = inside(root, Path(inputs))
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z(?:-[A-Za-z0-9_-]+)?", run):
        raise ValueError("timestamp run required")
    if limit_images is not None and limit_images < 1:
        raise ValueError("positive limit required")
    output = inside(root, Path("artifacts/reconstruction-visual-duplicates") / run)
    output.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")

    try:
        input_hash = sha(inputs)
        write(
            "run-manifest.json",
            dict(
                started_utc=datetime.now(UTC).isoformat(),
                inputs=str(inputs.relative_to(root)),
                inputs_sha256=input_hash,
                dataset_revision=DATASET_REVISION,
                code_sha256=sha(Path(__file__)),
                code_commit=subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip(),
                argv=sys.argv,
                python=platform.python_version(),
                pillow=pillow_version,
                config=dict(
                    run=run,
                    limit_images=limit_images,
                    algorithm="dHash grayscale LANCZOS 9x8 horizontal >, 64 bits; NOT pHash",
                    max_hamming=4,
                    bands=[13, 13, 13, 13, 12],
                    source_split="train",
                ),
                training_authorized=False,
            ),
        )
        unique = {}
        expected_image_root = root / TRAIN_RELATIVE_PATH / "images"
        image_root = inside(root, expected_image_root)
        if image_root != expected_image_root:
            raise ValueError("train image directory redirected")
        with inputs.open(encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("source_split") != "train":
                    raise ValueError("only official train permitted")
                if row.get("dataset_revision") != DATASET_REVISION:
                    raise ValueError("dataset revision mismatch")
                for fragment in row["fragments"]:
                    path = inside(root, Path(fragment["image_relpath"]))
                    if not path.is_relative_to(image_root):
                        raise ValueError("source outside official train images")
                    document_id, page_num = parse_full_document_image_id(path.name)
                    if (
                        document_id != row["document_id"]
                        or type(fragment.get("page_num")) is not int
                        or page_num != fragment["page_num"]
                    ):
                        raise ValueError("source document/page identity mismatch")
                    identity = (row["document_id"], fragment["image_sha256"])
                    record = dict(
                        document_id=row["document_id"],
                        image_relpath=path.relative_to(root).as_posix(),
                        image_sha256=fragment["image_sha256"],
                    )
                    old = unique.get(str(path))
                    if old and (old["document_id"], old["image_sha256"]) != identity:
                        raise ValueError("conflicting source identity")
                    unique[str(path)] = record
        selected = sorted(unique.items())
        if limit_images:
            selected = selected[:limit_images]
        rows = []
        for path_string, record in selected:
            path = Path(path_string)
            if sha(path) != record["image_sha256"]:
                raise ValueError("source SHA mismatch")
            value = dhash(path)
            if sha(path) != record["image_sha256"]:
                raise ValueError("source SHA changed")
            rows.append(dict(record, dhash=value))
        write("image-hashes.json", rows)
        count = 0
        with (output / "candidates.jsonl").open("x", encoding="utf-8") as stream:
            for left, right, distance in candidates(rows):
                stream.write(
                    json.dumps(
                        dict(
                            left_index=left,
                            right_index=right,
                            distance=distance,
                            status="uncalibrated_candidate",
                        ),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                count += 1
        if sha(inputs) != input_hash:
            raise ValueError("input SHA changed")
        for record in rows:
            if sha(inside(root, Path(record["image_relpath"]))) != record["image_sha256"]:
                raise ValueError("final source SHA mismatch")
        write(
            "summary.json",
            dict(
                status="partial" if limit_images else "completed_candidates_only",
                ended_utc=datetime.now(UTC).isoformat(),
                images=len(rows),
                total_unique_images=len(unique),
                candidate_pairs=count,
                training_authorized=False,
                split_changes=False,
                limitations=[
                    "Threshold uncalibrated; visual candidates are not proven duplicate documents.",
                    "Blank pages may collide; crops, rotation and layout changes may be missed.",
                    "Train only; no cross-official-split or pretraining contamination conclusion.",
                ],
                artifact_hashes={p.name: sha(p) for p in sorted(output.iterdir())},
            ),
        )
    except (Exception, KeyboardInterrupt) as exc:
        write(
            "failure.json",
            dict(
                status="failed",
                exception_type=type(exc).__name__,
                ended_utc=datetime.now(UTC).isoformat(),
            ),
        )
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--limit-images", type=int)
    args = parser.parse_args()
    print(audit(args.project_root, args.inputs, args.run, limit_images=args.limit_images))


if __name__ == "__main__":
    main()
