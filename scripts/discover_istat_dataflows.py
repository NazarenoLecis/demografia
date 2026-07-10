from __future__ import annotations

import argparse
from pathlib import Path

from demografia.sources.istat import IstatClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cerca dataflow demografici nel catalogo ISTAT")
    parser.add_argument(
        "terms",
        nargs="*",
        default=["popolazione", "demograf", "migraz", "nascite", "stranieri", "prevision"],
    )
    parser.add_argument("--output", type=Path, default=Path("metadata/istat_dataflows_discovered.csv"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = IstatClient().search_dataflows(tuple(args.terms))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))
