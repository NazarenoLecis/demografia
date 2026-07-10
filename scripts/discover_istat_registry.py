from __future__ import annotations

import argparse
from pathlib import Path

from demografia.config import FINAL_DIR
from demografia.istat_registry import build_istat_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Risolvi i dataflow demografici ISTAT")
    parser.add_argument(
        "--output",
        type=Path,
        default=FINAL_DIR / "istat_demographic_dataflows.csv",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    registry = build_istat_registry()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    registry.to_csv(args.output, index=False)
    print(registry.to_string(index=False))
