from __future__ import annotations

import numpy as np
import pandas as pd

AGE_BANDS = {
    "pop_0_4": (0, 4),
    "pop_0_14": (0, 14),
    "pop_15_24": (15, 24),
    "pop_15_49": (15, 49),
    "pop_15_64": (15, 64),
    "pop_15_74": (15, 74),
    "pop_20_64": (20, 64),
    "pop_20_69": (20, 69),
    "pop_25_49": (25, 49),
    "pop_25_64": (25, 64),
    "pop_50_64": (50, 64),
    "pop_65_79": (65, 79),
    "pop_65_plus": (65, 120),
    "pop_70_plus": (70, 120),
    "pop_75_plus": (75, 120),
    "pop_80_plus": (80, 120),
    "pop_85_plus": (85, 120),
    "pop_90_plus": (90, 120),
    "pop_100_plus": (100, 120),
}

GROUP_KEY_CANDIDATES = (
    "geo_level",
    "geo_code",
    "geo_name",
    "iso3",
    "year",
    "scenario",
    "status",
    "source",
    "dataset",
    "projection_vintage",
)


def _group_keys(frame: pd.DataFrame) -> list[str]:
    return [column for column in GROUP_KEY_CANDIDATES if column in frame.columns]


def _non_overlapping_intervals(frame: pd.DataFrame) -> pd.DataFrame:
    """Select the finest non-overlapping age partition available."""
    if frame.empty:
        return frame
    grouped = (
        frame.groupby(["age_low", "age_high"], as_index=False, dropna=False)["value"]
        .sum()
        .dropna(subset=["age_low", "age_high", "value"])
    )
    grouped["width"] = grouped["age_high"] - grouped["age_low"]
    grouped = grouped.sort_values(["width", "age_low", "age_high"]).reset_index(drop=True)
    selected: list[int] = []
    intervals: list[tuple[int, int]] = []
    for index, row in grouped.iterrows():
        low, high = int(row["age_low"]), int(row["age_high"])
        overlaps = any(
            not (high < chosen_low or low > chosen_high)
            for chosen_low, chosen_high in intervals
        )
        if overlaps:
            continue
        selected.append(index)
        intervals.append((low, high))
    return grouped.loc[selected].drop(columns="width").sort_values(["age_low", "age_high"])


def atomic_population_rows(population: pd.DataFrame) -> pd.DataFrame:
    """Remove overlapping aggregate ages and total-sex rows without imputation."""
    if population.empty:
        return population.copy()
    keys = _group_keys(population)
    pieces: list[pd.DataFrame] = []
    for key_values, group in population.groupby(keys, dropna=False):
        key_values = key_values if isinstance(key_values, tuple) else (key_values,)
        base = dict(zip(keys, key_values, strict=True))
        sexes = set(group["sex"].dropna().astype(str))
        if {"M", "F"}.issubset(sexes):
            group = group[group["sex"].isin(["M", "F"])]
        elif "T" in sexes:
            group = group[group["sex"].eq("T")]
        for sex, sex_group in group.groupby("sex", dropna=False):
            selected = _non_overlapping_intervals(sex_group)
            for column, value in base.items():
                selected[column] = value
            selected["sex"] = sex
            pieces.append(selected)
    if not pieces:
        return population.iloc[0:0].copy()
    return pd.concat(pieces, ignore_index=True, sort=False)


def _band_sum(group: pd.DataFrame, lower: int, upper: int) -> float:
    intersects = group["age_high"].ge(lower) & group["age_low"].le(upper)
    contained = group["age_low"].ge(lower) & group["age_high"].le(upper)
    if (intersects & ~contained).any():
        return np.nan
    rows = group.loc[contained, "value"]
    return float(rows.sum()) if not rows.empty else np.nan


def _weighted_median_age(group: pd.DataFrame) -> float:
    if group.empty:
        return np.nan
    ordered = group.assign(
        age_mid=(group["age_low"] + group["age_high"].clip(upper=110)) / 2
    ).sort_values("age_mid")
    total = ordered["value"].sum()
    if total <= 0:
        return np.nan
    cumulative = ordered["value"].cumsum()
    return float(ordered.loc[cumulative.ge(total / 2), "age_mid"].iloc[0])


def compute_age_structure(population: pd.DataFrame) -> pd.DataFrame:
    if population.empty:
        return pd.DataFrame()
    clean = atomic_population_rows(population)
    rows: list[dict[str, object]] = []
    keys = _group_keys(clean)

    for key, group in clean.groupby(keys, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        row: dict[str, object] = dict(zip(keys, key, strict=True))
        total = float(group["value"].sum())
        row["population_total"] = total
        total_by_age = group.groupby(["age_low", "age_high"], as_index=False)["value"].sum()
        for name, (lower, upper) in AGE_BANDS.items():
            value = _band_sum(total_by_age, lower, upper)
            row[name] = value
            row[f"share_{name.removeprefix('pop_')}"] = (
                100 * value / total if total and pd.notna(value) else np.nan
            )

        male = float(group.loc[group["sex"].eq("M"), "value"].sum())
        female = float(group.loc[group["sex"].eq("F"), "value"].sum())
        row["population_male"] = male if male or female else np.nan
        row["population_female"] = female if male or female else np.nan
        row["sex_ratio_male_per_100_female"] = 100 * male / female if female else np.nan
        row["women_15_49"] = (
            _band_sum(group[group["sex"].eq("F")], 15, 49) if female else np.nan
        )

        working = row["pop_15_64"]
        youth = row["pop_0_14"]
        old = row["pop_65_plus"]
        row["dependency_youth"] = 100 * youth / working if working and pd.notna(youth) else np.nan
        row["dependency_old"] = 100 * old / working if working and pd.notna(old) else np.nan
        row["dependency_total"] = (
            100 * (youth + old) / working
            if working and pd.notna(youth) and pd.notna(old)
            else np.nan
        )
        row["support_ratio_15_64_per_65_plus"] = (
            working / old if old and pd.notna(working) else np.nan
        )
        row["support_ratio_20_64_per_65_plus"] = (
            row["pop_20_64"] / old if old and pd.notna(row["pop_20_64"]) else np.nan
        )
        row["support_ratio_25_64_per_65_plus"] = (
            row["pop_25_64"] / old if old and pd.notna(row["pop_25_64"]) else np.nan
        )
        row["support_ratio_20_69_per_70_plus"] = (
            row["pop_20_69"] / row["pop_70_plus"]
            if row["pop_70_plus"] and pd.notna(row["pop_20_69"])
            else np.nan
        )
        row["ageing_index_65_plus_per_100_youth"] = (
            100 * old / youth if youth and pd.notna(old) else np.nan
        )

        midpoint = (total_by_age["age_low"] + total_by_age["age_high"].clip(upper=110)) / 2
        row["mean_age"] = (
            float((midpoint * total_by_age["value"]).sum() / total) if total else np.nan
        )
        row["median_age"] = _weighted_median_age(total_by_age)
        row["age_min"] = int(total_by_age["age_low"].min()) if not total_by_age.empty else None
        row["age_max"] = int(total_by_age["age_high"].max()) if not total_by_age.empty else None
        row["age_classes"] = int(len(total_by_age))
        widths = total_by_age["age_high"] - total_by_age["age_low"]
        row["age_resolution"] = (
            "single_year" if not widths.empty and widths.max() == 0 else "grouped"
        )
        rows.append(row)

    return pd.DataFrame(rows)


def _select_plot_source(subset: pd.DataFrame, iso3: str) -> pd.DataFrame:
    if subset.empty or "source" not in subset:
        return subset
    priorities = (
        ("ISTAT", "Eurostat", "UN World Population Prospects")
        if iso3 == "ITA"
        else ("Eurostat", "UN World Population Prospects", "ISTAT")
    )
    for source in priorities:
        selected = subset[subset["source"].eq(source)]
        if not selected.empty:
            return selected
    return subset


def build_pyramid(
    population: pd.DataFrame,
    iso3: str,
    year: int,
    scenario: str | None = None,
) -> pd.DataFrame:
    subset = population[population["iso3"].eq(iso3) & population["year"].eq(year)].copy()
    subset = _select_plot_source(subset, iso3)
    if scenario is not None:
        subset = subset[subset["scenario"].astype(str).eq(scenario)]
    elif subset["status"].nunique() > 1 and subset["status"].eq("observed").any():
        subset = subset[subset["status"].eq("observed")]
    elif subset["scenario"].nunique() > 1:
        baseline = subset["scenario"].astype(str).str.upper().isin(
            {"BSL", "BASELINE", "BASELINE PROJECTIONS", "MEDIUM", "OBSERVED"}
        )
        if baseline.any():
            subset = subset[baseline]
    if subset.empty:
        raise ValueError(f"Nessun dato per {iso3}, {year}")
    subset = atomic_population_rows(subset)
    pyramid = subset.groupby(["age_low", "age_high", "sex"], as_index=False)["value"].sum()
    wide = (
        pyramid.pivot(index=["age_low", "age_high"], columns="sex", values="value")
        .fillna(0)
        .reset_index()
    )
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
    subset = _select_plot_source(subset, iso3)
    if subset["status"].eq("observed").any():
        subset = subset[subset["status"].eq("observed")]
    subset = atomic_population_rows(subset)
    if sex in {"M", "F"}:
        subset = subset[subset["sex"].eq(sex)]
    subset = subset[subset["age_low"].eq(subset["age_high"])]
    table = subset.groupby(["age_low", "year"], as_index=False)["value"].sum()
    return table.pivot(index="age_low", columns="year", values="value").sort_index()


def add_group_benchmarks(
    panel: pd.DataFrame,
    group_members: dict[str, tuple[str, ...]],
) -> pd.DataFrame:
    frames = [panel]
    for group_name, members in group_members.items():
        subset = panel[panel["iso3"].isin(members)]
        if subset.empty:
            continue
        benchmark = subset.groupby(["year", "indicator"], as_index=False)["value"].agg(
            median="median",
            mean="mean",
            p25=lambda values: values.quantile(0.25),
            p75=lambda values: values.quantile(0.75),
        )
        benchmark["iso3"] = group_name
        benchmark["country"] = group_name
        benchmark["indicator_id"] = "benchmark"
        benchmark["source"] = "calculated benchmark"
        benchmark["value"] = benchmark["median"]
        frames.append(benchmark[panel.columns.intersection(benchmark.columns)])
    return pd.concat(frames, ignore_index=True, sort=False)
