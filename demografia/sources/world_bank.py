from __future__ import annotations

from typing import Iterable

import pandas as pd

from demografia.config import CACHE_DIR, EU_OECD_ISO3, OECD38_ISO3, WORLD_BANK_INDICATORS
from demografia.http import get_json

WORLD_BANK_API = "https://api.worldbank.org/v2"


def indicator(
    indicator_id: str,
    countries: Iterable[str] = OECD38_ISO3,
    start_year: int = 1960,
    end_year: int = 2100,
    refresh: bool = False,
) -> pd.DataFrame:
    country_path = ";".join(countries)
    payload = get_json(
        f"{WORLD_BANK_API}/country/{country_path}/indicator/{indicator_id}",
        params={"format": "json", "per_page": 20000, "date": f"{start_year}:{end_year}"},
        cache_dir=CACHE_DIR / "world_bank" / indicator_id.replace(".", "_"),
        refresh=refresh,
    )
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame()

    rows = []
    for item in payload[1]:
        if item.get("value") is None:
            continue
        rows.append(
            {
                "iso3": item.get("countryiso3code"),
                "country": item.get("country", {}).get("value"),
                "year": int(item["date"]),
                "indicator_id": indicator_id,
                "indicator": WORLD_BANK_INDICATORS.get(indicator_id, indicator_id),
                "value": float(item["value"]),
                "source": "World Bank WDI",
            }
        )
    return pd.DataFrame(rows)


def panel(
    countries: Iterable[str] = EU_OECD_ISO3,
    start_year: int = 1960,
    end_year: int = 2100,
    refresh: bool = False,
) -> pd.DataFrame:
    countries = tuple(countries)
    frames = [
        indicator(indicator_id, countries=countries, start_year=start_year, end_year=end_year, refresh=refresh)
        for indicator_id in WORLD_BANK_INDICATORS
    ]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def oecd_panel(start_year: int = 1960, end_year: int = 2100, refresh: bool = False) -> pd.DataFrame:
    return panel(OECD38_ISO3, start_year=start_year, end_year=end_year, refresh=refresh)
