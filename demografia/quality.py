from __future__ import annotations

import pandas as pd

from demografia.config import EU27_ISO3, OECD38_ISO3


def coverage_report(population: pd.DataFrame, oecd_panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if not population.empty:
        observed = population[population["status"].eq("observed")]
        latest = observed.groupby("iso3")["year"].max()
        for iso3 in EU27_ISO3:
            subset = observed[observed["iso3"].eq(iso3)]
            latest_year = latest.get(iso3)
            latest_subset = subset[subset["year"].eq(latest_year)] if pd.notna(latest_year) else subset.iloc[0:0]
            rows.append(
                {
                    "scope": "EU27 age-sex",
                    "iso3": iso3,
                    "available": not latest_subset.empty,
                    "latest_year": latest_year,
                    "male_rows": int(latest_subset["sex"].eq("M").sum()),
                    "female_rows": int(latest_subset["sex"].eq("F").sum()),
                }
            )
    if not oecd_panel.empty:
        for iso3 in OECD38_ISO3:
            subset = oecd_panel[oecd_panel["iso3"].eq(iso3)]
            rows.append(
                {
                    "scope": "OECD indicators",
                    "iso3": iso3,
                    "available": not subset.empty,
                    "latest_year": subset["year"].max() if not subset.empty else None,
                    "male_rows": None,
                    "female_rows": None,
                }
            )
    return pd.DataFrame(rows)
