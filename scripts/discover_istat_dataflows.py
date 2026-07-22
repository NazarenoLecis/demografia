from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.sources import istat
from demografia.utils import save_csv


# Configurazione per VS Code.
# TERMS controlla le parole cercate nel catalogo SDMX ISTAT.
TERMS = ("popolazione", "demograf", "migraz", "nascite", "stranieri", "prevision")
OUTPUT = PROJECT_ROOT / "metadata" / "istat_dataflows_discovered.csv"


def main(terms: tuple[str, ...] = TERMS, output: Path = OUTPUT) -> Path:
    """Search demographic ISTAT dataflows and write the result as CSV."""
    result = istat.search_dataflows(tuple(terms))
    save_csv(result, output)
    print(result.to_string(index=False))
    return output


if __name__ == "__main__":
    print(main())
