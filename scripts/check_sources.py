from __future__ import annotations

from demografia.config import EU27_ISO2
from demografia.sources.eurostat import EurostatClient
from demografia.sources.world_bank import WorldBankClient


if __name__ == "__main__":
    eurostat = EurostatClient()
    world_bank = WorldBankClient()
    checks = {
        "Eurostat population": lambda: eurostat.population_age_sex(("IT",), 2023, 2024),
        "Eurostat fertility": lambda: eurostat.fertility(("IT",), 2020),
        "Eurostat projections": lambda: eurostat.projections(("IT",), 2030, 2031),
        "World Bank OECD": lambda: world_bank.indicator("SP.DYN.TFRT.IN", ("ITA",), 2020, 2024),
    }
    for name, call in checks.items():
        try:
            frame = call()
            print(f"{name}: OK, {len(frame)} righe")
        except Exception as exc:
            print(f"{name}: ERRORE, {exc}")
