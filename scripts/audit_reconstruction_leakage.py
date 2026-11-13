"""Audit exact text overlap without changing source data or split assignments."""

import argparse
from pathlib import Path

from cptla.reconstruction.leakage import audit_leakage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument(
        "--official-splits", action="store_true", help="Explicitly hash train/val/test"
    )
    parser.add_argument("--splits-path", type=Path)
    args = parser.parse_args()
    print(
        audit_leakage(
            args.project_root,
            args.run,
            official_splits=args.official_splits,
            splits_path=args.splits_path,
        )
    )


if __name__ == "__main__":
    main()
