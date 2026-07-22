from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.sources import eurostat, world_bank
from demografia.utils import check_call


# Configurazione per VS Code.
# Le finestre temporali sono volutamente corte: servono a verificare gli endpoint.
CHECK_START_YEAR = 2023
CHECK_END_YEAR = 2024


def main(start_year: int = CHECK_START_YEAR, end_year: int = CHECK_END_YEAR) -> list[dict[str, object]]:
    """Check the lightweight international sources used by the base pipeline."""
    checks = (
        (
            "Eurostat population",
            lambda: eurostat.population_age_sex(("IT",), start_year=start_year, end_year=end_year),
        ),
        ("Eurostat fertility", lambda: eurostat.fertility(("IT",), start_year=start_year)),
        (
            "Eurostat education attainment",
            lambda: eurostat.education_attainment(("IT",), start_year=start_year, end_year=end_year),
        ),
        (
            "Eurostat projections",
            lambda: eurostat.projections(("IT",), start_year=2030, end_year=2031),
        ),
        (
            "World Bank OECD",
            lambda: world_bank.indicator("SP.DYN.TFRT.IN", ("ITA",), start_year, end_year),
        ),
    )
    return [check_call(name, call) for name, call in checks]


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(item["status"] == "error" for item in result):
        raise SystemExit(1)
