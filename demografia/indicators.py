from __future__ import annotations

import numpy as np
import pandas as pd

AGE_BANDS = {
    "pop_0_14": (0, 14),
    "pop_15_24": (15, 24),
    "pop_25_49": (25, 49),
    "pop_50_64": (50, 64),
    "pop_15_64": (15, 64),
    "pop_20_64": (20, 64),
    "pop_25_64": (25, 64),
    "pop_65_79": (65, 79),
    "pop_65_plus": (65, 120),
    "pop_80_plus": (80, 120),
    "pop_85_plus": (85, 120),
    "pop_100_plus": (100, 120),
}

GROUP_KEYS = ["iso3", "year", "scenario", "status", "source"]


def _band_sum(group: pd.DataFrame, lower: int, upper: int) -> float:
    contained = group["age_low"].ge(lower) & group["age_high"].le(upper)
    return float(group.loc[contained, "value"].sum())


def _weighted_median_age(group: pd.DataFrame) -> float:
    ordered = group.assign(age_mid=(group["age_low"] + group["age_high"]) / 2).sort_values("age_mid")
    total = ordered["value"].sum()
    if total <= 0:
        return np.nan
    cumulative = ordered["value"].cumsum()
    return float(ordered.loc[cumulative.ge(total / 2), "age_mid"].iloc[0])


def compute_age_structure(population: pd.DataFrame) -> pd.DataFrame:
    if population.empty:
        return pd.DataFrame()
    clean = population[population["sex"].isin(["M", "F"])].copy()
    rows: list[dict[str, float | int | str]] = []

    for key, group in clean.groupby(GROUP_KEYS, dropna=False):
        row = dict(zip(GROUP_KEYS, key, strict=True))
        total = float(group["value"].sum())
        row["population_total"] = total
        for name, (lower, upper) in AGE_BANDS.items():
            row[name] = _band_sum(group, lower, upper)
            row[f"share_{name.removeprefix('pop_')}"] = 100 * row[name] / total if total else np.nan

        male = float(group.loc[group["sex"].eq("M"), "value"].sum())
        female = float(group.loc[group["sex"].eq("F"), "value"].sum())
        fertile_women = _band_sum(group[group["sex"].eq("F")], 15, 49)
        row["population_male"] = male
        row["population_female"] = female
        row["sex_ratio_male_per_100_female"] = 100 * male / female if female else np.nan
        row["women_15_49"] = fertile_women
        row["dependency_youth"] = 100 * row["pop_0_14"] / row["pop_15_64"] if row["pop_15_64"] else np.nan
        row["dependency_old"] = 100 * row["pop_65_plus"] / row["pop_15_64"] if row["pop_15_64"] else np.nan
        row["dependency_total"] = (
            100 * (row["pop_0_14"] + row["pop_65_plus"]) / row["pop_15_64"]
            if row["pop_15_64"]
            else np.nan
        )
        row["support_ratio_15_64_per_65_plus"] = row["pop_15_64"] / row["pop_65_plus"] if row["pop_65_plus"] else np.nan
        row["support_ratio_20_64_per_65_plus"] = row["pop_20_64"] / row["pop_65_plus"] if row["pop_65_plus"] else np.nan
        row["support_ratio_25_64_per_65_plus"] = row["pop_25_64"] / row["pop_65_plus"] if row["pop_65_plus"] else np.nan
        row["mean_age"] = float((((group["age_low"] + group["age_high"]) / 2) * group["value"]).sum() / total) if total else np.nan
        row["median_age"] = _weighted_median_age(group)
        rows.append(row)

    return pd.DataFrame(rows)


def build_pyramid(population: pd.DataFrame, iso3: str, year: int, scenario: str | None = None) -> pd.DataFrame:
    subset = population[population["iso3"].eq(iso3) & population["year"].eq(year)].copy()
    if scenario is not None:
        subset = subset[subset["scenario"].astype(str).eq(scenario)]
    elif subset["status"].nunique() > 1 and subset["status"].eq("observed").any():
        subset = subset[subset["status"].eq("observed")]
    elif subset["scenario"].nunique() > 1:
        baseline = subset["scenario"].astype(str).str.upper().isin({"BSL", "BASELINE", "MEDIUM"})
        if baseline.any():
            subset = subset[baseline]
    if subset.empty:
        raise ValueError(f"Nessun dato per {iso3}, {year}")
    pyramid = subset.groupby(["age_low", "age_high", "sex"], as_index=False)["value"].sum()
    wide = pyramid.pivot(index=["age_low", "age_high"], columns="sex", values="value").fillna(0).reset_index()
    for sex in ("M", "F"):
        if sex not in wide:
            wide[sex] = 0.0
    wide["age_label"] = np.where(
        wide["age_high"].ge(120),
        wide["age_low"].astype(str) + "+",
        np.where(
            wide["age_low"].eq(wide["age_high"]),
            wide["age_low"].astype(str),
            wide["age_low"].astype(str) + "-" + wide["age_high"].astype(str),
        ),
    )
    total = wide[["M", "F"]].to_numpy().sum()
    wide["male_share"] = 100 * wide["M"] / total if total else np.nan
    wide["female_share"] = 100 * wide["F"] / total if total else np.nan
    return wide.sort_values("age_low")


def cohort_heatmap(population: pd.DataFrame, iso3: str, sex: str = "T") -> pd.DataFrame:
    subset = population[population["iso3"].eq(iso3)].copy()
    if sex in {"M", "F"}:
        subset = subset[subset["sex"].eq(sex)]
    subset["age"] = ((subset["age_low"] + subset["age_high"]) / 2).round().astype(int)
    table = subset.groupby(["age", "year"], as_index=False)["value"].sum()
    return table.pivot(index="age", columns="year", values="value").sort_index()


def add_group_benchmarks(panel: pd.DataFrame, group_members: dict[str, tuple[str, ...]]) -> pd.DataFrame:
    frames = [panel]
    for group_name, members in group_members.items():
        subset = panel[panel["iso3"].isin(members)]
        benchmark = subset.groupby(["year", "indicator"], as_index=False)["value"].agg(
            median="median", mean="mean", p25=lambda x: x.quantile(0.25), p75=lambda x: x.quantile(0.75)
        )
        benchmark["iso3"] = group_name
        benchmark["country"] = group_name
        benchmark["indicator_id"] = "benchmark"
        benchmark["source"] = subset["source"].iloc[0] if not subset.empty else ""
        benchmark["value"] = benchmark["median"]
        frames.append(benchmark[panel.columns.intersection(benchmark.columns)])
    return pd.concat(frames, ignore_index=True, sort=False)
