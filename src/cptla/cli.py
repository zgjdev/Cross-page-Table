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
