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
