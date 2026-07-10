from __future__ import annotations

import pandas as pd


def build_italy_demographic_fiscal_panel(
    age_structure: pd.DataFrame,
    inps_support: pd.DataFrame | None = None,
    rgs_panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if age_structure.empty:
        base = pd.DataFrame(columns=["year"])
    else:
        subset = age_structure.copy()
        if "iso3" in subset:
            subset = subset[subset["iso3"].eq("ITA")]
        if "status" in subset and subset["status"].eq("observed").any():
            subset = subset[subset["status"].eq("observed")]
        if "source" in subset:
            priorities = {"ISTAT": 0, "Eurostat": 1, "UN World Population Prospects": 2}
            subset["_priority"] = subset["source"].map(priorities).fillna(99)
            subset = subset.sort_values(["year", "_priority"]).drop_duplicates("year", keep="first")
            subset = subset.drop(columns="_priority")
        base_columns = [
            "year",
            "population_total",
            "pop_0_14",
            "pop_15_64",
            "pop_65_plus",
            "pop_80_plus",
            "dependency_youth",
            "dependency_old",
            "dependency_total",
            "support_ratio_15_64_per_65_plus",
            "support_ratio_20_64_per_65_plus",
            "mean_age",
            "median_age",
        ]
        base = subset[[column for column in base_columns if column in subset]].copy()

    if inps_support is not None and not inps_support.empty:
        base = base.merge(inps_support, on="year", how="outer")
    if rgs_panel is not None and not rgs_panel.empty:
        rgs = rgs_panel.copy()
        baseline_scenarios = {"baseline", "base", "centrale", "median"}
        if (
            "scenario" in rgs
            and rgs["scenario"].astype(str).str.casefold().isin(baseline_scenarios).any()
        ):
            mask = rgs["scenario"].astype(str).str.casefold().isin(baseline_scenarios)
            rgs = rgs[mask]
        keys = [column for column in ("year", "projection_vintage", "scenario") if column in rgs]
        rgs = rgs.sort_values(keys).drop_duplicates("year", keep="last")
        base = base.merge(rgs, on="year", how="outer", suffixes=("", "_rgs"))

    if {"contributors", "pop_65_plus"}.issubset(base.columns):
        base["contributors_per_person_65_plus"] = base["contributors"] / base["pop_65_plus"].replace(0, pd.NA)
    if {"pensioners", "pop_65_plus"}.issubset(base.columns):
        base["pensioners_per_person_65_plus"] = base["pensioners"] / base["pop_65_plus"].replace(0, pd.NA)
    return base.sort_values("year").reset_index(drop=True)
