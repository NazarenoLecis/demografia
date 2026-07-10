from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd

def projection_vintage_year(value: object) -> int | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if parsed is None or pd.isna(parsed):
        return None
    return int(parsed.year)


RGS_INDICATOR_RULES: dict[str, tuple[str, ...]] = {
    "pension_expenditure_gdp": ("spesa pension", "pil"),
    "health_expenditure_gdp": ("spesa sanit", "pil"),
    "long_term_care_expenditure_gdp": ("long term care", "pil"),
    "total_age_related_expenditure_gdp": ("spesa age related", "pil"),
    "employment_rate": ("tasso occupazione",),
    "old_age_dependency_ratio": ("dipendenza anziani",),
    "fertility_rate": ("fecondita",),
    "life_expectancy": ("speranza di vita",),
    "net_migration": ("saldo migratorio",),
    "pensioners": ("pensionati",),
    "contributors": ("contribuenti",),
}


def _slug(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _find(columns: Iterable[str], exact: tuple[str, ...], terms: tuple[str, ...] = ()) -> str | None:
    mapping = {column: _slug(column) for column in columns}
    exact_slugs = {_slug(value) for value in exact}
    direct = next((column for column, slug in mapping.items() if slug in exact_slugs), None)
    if direct is not None:
        return direct
    return next((column for column, slug in mapping.items() if all(term in slug for term in terms)), None)


def _indicator(value: object) -> str:
    text = _slug(value).replace("_", " ")
    for indicator, terms in RGS_INDICATOR_RULES.items():
        if all(_slug(term).replace("_", " ") in text for term in terms):
            return indicator
    return _slug(value) or "rgs_indicator"


def _wide_year_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if re.fullmatch(r"(?:19|20|21)\d{2}", str(column).strip())]


def normalize_rgs_projection(
    frame: pd.DataFrame,
    dataset: str = "RGS long-term projections",
    source_url: str | None = None,
    vintage: str | int | None = None,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    columns = [
        "source",
        "dataset",
        "source_url",
        "extraction_date",
        "projection_vintage",
        "year",
        "scenario",
        "indicator_raw",
        "indicator",
        "unit",
        "value",
        "lower_bound",
        "upper_bound",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    source = frame.copy()
    year_columns = _wide_year_columns(source)
    indicator_col = _find(source.columns, ("indicatore", "indicator", "voce", "descrizione"), ("indic",))
    scenario_col = _find(source.columns, ("scenario", "ipotesi", "variant"), ("scenario",))
    unit_col = _find(source.columns, ("unita", "unita_misura", "unit"), ("unita",))
    lower_col = _find(source.columns, ("limite_inferiore", "lower_bound", "low"), ("infer",))
    upper_col = _find(source.columns, ("limite_superiore", "upper_bound", "high"), ("super",))

    if year_columns:
        id_vars = [column for column in source.columns if column not in year_columns]
        source = source.melt(id_vars=id_vars, value_vars=year_columns, var_name="year", value_name="value")
        year_col = "year"
        value_col = "value"
    else:
        year_col = _find(source.columns, ("anno", "year", "time_period"), ("anno",))
        value_col = _find(source.columns, ("valore", "value", "obs_value"), ("value",))
        if value_col is None:
            numeric = [column for column in source.columns if pd.api.types.is_numeric_dtype(source[column])]
            numeric = [column for column in numeric if column != year_col]
            value_col = numeric[0] if len(numeric) == 1 else None

    if year_col is None or value_col is None:
        raise ValueError("Tabella RGS priva di anno o valore riconoscibile")
    if indicator_col is None:
        non_numeric = [column for column in source.columns if column not in {year_col, value_col}]
        indicator_col = non_numeric[0] if non_numeric else None
    if indicator_col is None:
        raise ValueError("Tabella RGS priva di indicatore riconoscibile")

    result = pd.DataFrame(index=source.index)
    result["source"] = "RGS"
    result["dataset"] = dataset
    result["source_url"] = source_url
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["projection_vintage"] = str(vintage) if vintage is not None else pd.NA
    result["year"] = pd.to_numeric(source[year_col], errors="coerce").astype("Int64")
    result["scenario"] = source[scenario_col].astype(str) if scenario_col else "baseline"
    result["indicator_raw"] = source[indicator_col].astype(str)
    result["indicator"] = result["indicator_raw"].map(_indicator)
    result["unit"] = source[unit_col].astype(str) if unit_col else pd.NA
    result["value"] = pd.to_numeric(source[value_col], errors="coerce")
    result["lower_bound"] = pd.to_numeric(source[lower_col], errors="coerce") if lower_col else np.nan
    result["upper_bound"] = pd.to_numeric(source[upper_col], errors="coerce") if upper_col else np.nan
    return result[columns].dropna(subset=["year", "value"])


def build_rgs_projection_panel(projections: pd.DataFrame) -> pd.DataFrame:
    if projections.empty:
        return pd.DataFrame()
    keys = ["projection_vintage", "year", "scenario"]
    panel = projections.pivot_table(
        index=keys,
        columns="indicator",
        values="value",
        aggfunc="first",
    ).reset_index()
    panel.columns.name = None
    panel["source"] = "RGS"
    return panel


def backtest_rgs_projections(
    projections: pd.DataFrame,
    observed: pd.DataFrame,
    indicator: str,
    observed_value_column: str = "value",
) -> pd.DataFrame:
    required = {"projection_vintage", "year", "scenario", "indicator", "value"}
    if projections.empty or observed.empty or not required.issubset(projections.columns):
        return pd.DataFrame()
    projected = projections[projections["indicator"].eq(indicator)].copy()
    observed_frame = observed[["year", observed_value_column]].copy().rename(
        columns={observed_value_column: "observed_value"}
    )
    result = projected.merge(observed_frame, on="year", how="inner")
    result["error"] = result["value"] - result["observed_value"]
    result["absolute_error"] = result["error"].abs()
    result["percentage_error"] = 100 * result["error"] / result["observed_value"].replace(0, np.nan)
    return result
