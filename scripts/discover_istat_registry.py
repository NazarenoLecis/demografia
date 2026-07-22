from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.config import FINAL_DIR
from demografia.istat_registry import build_istat_registry
from demografia.utils import save_csv


# Configurazione per VS Code.
OUTPUT = FINAL_DIR / "istat_demographic_dataflows.csv"


def main(output: Path = OUTPUT) -> Path:
    """Resolve demographic roles against the ISTAT SDMX catalog."""
    registry = build_istat_registry()
    save_csv(registry, output)
    print(registry.to_string(index=False))
    return output


if __name__ == "__main__":
    print(main())
