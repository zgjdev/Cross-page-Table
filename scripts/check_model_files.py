"""Create SHA-256 inventories for downloaded model files."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for path in sorted(p for p in args.model_dir.rglob("*") if p.is_file()):
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        rows.append(f"{digest.hexdigest()}  {path.relative_to(args.model_dir)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    print(f"hashed_files={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
