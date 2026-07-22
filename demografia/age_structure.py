from __future__ import annotations

import numpy as np
import pandas as pd

AGE_BANDS = {
    "pop_0_4": (0, 4),
    "pop_0_14": (0, 14),
    "pop_15_19": (15, 19),
    "pop_15_24": (15, 24),
    "pop_15_49": (15, 49),
    "pop_15_64": (15, 64),
    "pop_15_74": (15, 74),
    "pop_20_39": (20, 39),
    "pop_20_64": (20, 64),
    "pop_20_69": (20, 69),
    "pop_25_49": (25, 49),
    "pop_25_64": (25, 64),
    "pop_50_64": (50, 64),
    "pop_60_64": (60, 64),
    "pop_65_79": (65, 79),
    "pop_60_79": (60, 79),
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


def _fast_atomic_population_rows(population: pd.DataFrame, keys: list[str]) -> pd.DataFrame | None:
    """Return a cleaned table quickly when age intervals are already disjoint."""
    required = {"age_low", "age_high", "sex", "value"}
    if not required.issubset(population.columns):
        return None
    candidate = population.dropna(subset=["age_low", "age_high", "value"]).copy()
    if candidate.empty:
        return population.iloc[0:0].copy()

    # When male and female rows are available for a geography/year/scenario,
    # total-sex rows are aggregates and should not be counted alongside them.
    has_male_female = candidate.groupby(keys, dropna=False)["sex"].transform(
        lambda values: {"M", "F"}.issubset(set(values.dropna().astype(str)))
    )
    candidate = candidate[~(has_male_female & candidate["sex"].astype(str).eq("T"))].copy()
    group_cols = [*keys, "sex"]
    intervals = candidate.assign(
        interval_length=candidate["age_high"].astype(float) - candidate["age_low"].astype(float) + 1
    )
    coverage = intervals.groupby(group_cols, dropna=False).agg(
        age_min=("age_low", "min"),
        age_max=("age_high", "max"),
        interval_total=("interval_length", "sum"),
    )
    span = coverage["age_max"] - coverage["age_min"] + 1
    if coverage["interval_total"].gt(span).any():
        return None
    return candidate


def atomic_population_rows(population: pd.DataFrame) -> pd.DataFrame:
    """Remove overlapping aggregate ages and total-sex rows without imputation."""
    if population.empty:
        return population.copy()
    keys = _group_keys(population)
    fast = _fast_atomic_population_rows(population, keys)
    if fast is not None:
        return fast
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


def _weighted_quantile_age(group: pd.DataFrame, quantile: float) -> float:
    if group.empty:
        return np.nan
    ordered = group.assign(
        age_mid=(group["age_low"] + group["age_high"].clip(upper=110)) / 2
    ).sort_values("age_mid")
    total = ordered["value"].sum()
    if total <= 0:
        return np.nan
    cumulative = ordered["value"].cumsum()
    return float(ordered.loc[cumulative.ge(total * quantile), "age_mid"].iloc[0])


def _weighted_median_age(group: pd.DataFrame) -> float:
    return _weighted_quantile_age(group, 0.5)


def _band_series(total_by_age: pd.DataFrame, keys: list[str], lower: int, upper: int) -> pd.Series:
    intersects = total_by_age["age_high"].ge(lower) & total_by_age["age_low"].le(upper)
    contained = total_by_age["age_low"].ge(lower) & total_by_age["age_high"].le(upper)
    values = total_by_age.loc[contained].groupby(keys, dropna=False)["value"].sum()
    partial = total_by_age.loc[intersects & ~contained].groupby(keys, dropna=False).size()
    if not partial.empty:
        values = values.reindex(values.index.union(partial.index))
        values.loc[partial.index] = np.nan
    return values


def _band_by_sex(clean: pd.DataFrame, keys: list[str], lower: int, upper: int) -> pd.DataFrame:
    intersects = clean["age_high"].ge(lower) & clean["age_low"].le(upper)
    contained = clean["age_low"].ge(lower) & clean["age_high"].le(upper)
    values = (
        clean.loc[contained]
        .groupby([*keys, "sex"], dropna=False)["value"]
        .sum()
        .unstack("sex")
    )
    partial = clean.loc[intersects & ~contained].groupby(keys, dropna=False).size()
    if not partial.empty:
        values = values.reindex(values.index.union(partial.index))
        values.loc[partial.index, :] = np.nan
    return values


def _divide(numerator: pd.Series, denominator: pd.Series, multiplier: float = 1.0) -> pd.Series:
    return np.where(
        denominator.notna() & denominator.ne(0) & numerator.notna(),
        multiplier * numerator / denominator,
        np.nan,
    )


def compute_age_structure(population: pd.DataFrame) -> pd.DataFrame:
    if population.empty:
        return pd.DataFrame()
    clean = atomic_population_rows(population)
    keys = _group_keys(clean)
    total_by_age = clean.groupby([*keys, "age_low", "age_high"], as_index=False, dropna=False)["value"].sum()
    result = total_by_age.groupby(keys, dropna=False)["value"].sum().to_frame("population_total")

    for name, (lower, upper) in AGE_BANDS.items():
        band = _band_series(total_by_age, keys, lower, upper).reindex(result.index)
        result[name] = band
        result[f"share_{name.removeprefix('pop_')}"] = _divide(band, result["population_total"], 100)

    sex_totals = clean.groupby([*keys, "sex"], dropna=False)["value"].sum().unstack("sex").reindex(result.index)
    male = sex_totals["M"] if "M" in sex_totals else pd.Series(np.nan, index=result.index)
    female = sex_totals["F"] if "F" in sex_totals else pd.Series(np.nan, index=result.index)
    has_sex_detail = male.fillna(0).add(female.fillna(0)).gt(0)
    result["population_male"] = male.where(has_sex_detail)
    result["population_female"] = female.where(has_sex_detail)
    result["sex_ratio_male_per_100_female"] = _divide(male, female, 100)

    for name, (lower, upper) in AGE_BANDS.items():
        suffix = name.removeprefix("pop_")
        by_sex = _band_by_sex(clean, keys, lower, upper).reindex(result.index)
        male_band = by_sex["M"] if "M" in by_sex else pd.Series(np.nan, index=result.index)
        female_band = by_sex["F"] if "F" in by_sex else pd.Series(np.nan, index=result.index)
        result[f"sex_ratio_male_per_100_female_{suffix}"] = _divide(male_band, female_band, 100)
    result["women_15_49"] = (
        _band_by_sex(clean, keys, 15, 49).reindex(result.index).get("F", pd.Series(np.nan, index=result.index))
    )

    working = result["pop_15_64"]
    youth = result["pop_0_14"]
    old = result["pop_65_plus"]
    result["dependency_youth"] = _divide(youth, working, 100)
    result["dependency_old"] = _divide(old, working, 100)
    result["dependency_total"] = _divide(youth.add(old), working, 100)
    result["support_ratio_15_64_per_65_plus"] = _divide(working, old)
    result["support_ratio_20_64_per_65_plus"] = _divide(result["pop_20_64"], old)
    result["support_ratio_25_64_per_65_plus"] = _divide(result["pop_25_64"], old)
    result["support_ratio_20_69_per_70_plus"] = _divide(result["pop_20_69"], result["pop_70_plus"])
    result["active_replacement_60_64_per_100_15_19"] = _divide(result["pop_60_64"], result["pop_15_19"], 100)
    result["young_adult_to_late_life_ratio_20_39_per_60_79"] = _divide(result["pop_20_39"], result["pop_60_79"])
    result["ageing_index_65_plus_per_100_youth"] = _divide(old, youth, 100)

    total_by_age["age_mid"] = (total_by_age["age_low"] + total_by_age["age_high"].clip(upper=110)) / 2
    weighted = total_by_age.assign(weighted_age=total_by_age["age_mid"] * total_by_age["value"])
    result["mean_age"] = _divide(
        weighted.groupby(keys, dropna=False)["weighted_age"].sum().reindex(result.index),
        result["population_total"],
    )
    result["age_min"] = total_by_age.groupby(keys, dropna=False)["age_low"].min().reindex(result.index)
    result["age_max"] = total_by_age.groupby(keys, dropna=False)["age_high"].max().reindex(result.index)
    result["age_classes"] = total_by_age.groupby(keys, dropna=False).size().reindex(result.index)
    max_width = (
        total_by_age.assign(width=total_by_age["age_high"] - total_by_age["age_low"])
        .groupby(keys, dropna=False)["width"]
        .max()
        .reindex(result.index)
    )
    result["age_resolution"] = np.where(max_width.eq(0), "single_year", "grouped")

    quantile_rows: list[dict[str, object]] = []
    for key, group in total_by_age.groupby(keys, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        row: dict[str, object] = dict(zip(keys, key, strict=True))
        row["age_p10"] = _weighted_quantile_age(group, 0.10)
        row["age_p25"] = _weighted_quantile_age(group, 0.25)
        row["median_age"] = _weighted_median_age(group)
        row["age_p75"] = _weighted_quantile_age(group, 0.75)
        row["age_p90"] = _weighted_quantile_age(group, 0.90)
        quantile_rows.append(row)
    if quantile_rows:
        quantiles = pd.DataFrame(quantile_rows).set_index(keys)
        result = result.join(quantiles)

    return result.reset_index()


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


def build_kebab(
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
    kebab = subset.groupby(["age_low", "age_high", "sex"], as_index=False)["value"].sum()
    wide = (
        kebab.pivot(index=["age_low", "age_high"], columns="sex", values="value")
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
