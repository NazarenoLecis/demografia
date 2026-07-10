from __future__ import annotations

import re
from collections.abc import Iterable

import numpy as np
import pandas as pd

from demografia.config import EUROSTAT_TO_ISO3


def parse_age_code(value: object) -> tuple[int, int] | None:
    text = str(value).strip().upper()
    if text in {"TOTAL", "UNK", "UNKNOWN", "Y_UNKNOWN"}:
        return None
    if text in {"Y_LT1", "LT1", "UNDER 1", "LESS THAN 1"}:
        return 0, 0
    if text in {"Y_OPEN", "Y_GE100", "Y100_MAX", "100+"}:
        return 100, 120
    if text.startswith("Y_GE"):
        numbers = [int(number) for number in re.findall(r"\d+", text)]
        return (numbers[0], 120) if numbers else None
    if text.startswith("Y_LE"):
        numbers = [int(number) for number in re.findall(r"\d+", text)]
        return (0, numbers[0]) if numbers else None
    if text.startswith("Y"):
        text = text[1:]
    numbers = [int(number) for number in re.findall(r"\d+", text)]
    if not numbers:
        return None
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return numbers[0], numbers[1]


def _first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    available = set(columns)
    return next((candidate for candidate in candidates if candidate in available), None)


def normalize_eurostat_population(frame: pd.DataFrame, projected: bool = False) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    geo_col = _first_existing(frame.columns, ("geo", "geo_label"))
    year_col = _first_existing(frame.columns, ("time", "TIME_PERIOD", "year"))
    age_col = _first_existing(frame.columns, ("age", "age_label"))
    sex_col = _first_existing(frame.columns, ("sex", "sex_label"))
    scenario_col = _first_existing(frame.columns, ("projection", "proj", "scenario"))
    if not all((geo_col, year_col, age_col, sex_col)):
        raise ValueError("Dimensioni Eurostat insufficienti per età e sesso")

    result = frame[[geo_col, year_col, age_col, sex_col, "value"] + ([scenario_col] if scenario_col else [])].copy()
    rename = {geo_col: "geo", year_col: "year", age_col: "age_raw", sex_col: "sex"}
    if scenario_col:
        rename[scenario_col] = "scenario"
    result = result.rename(columns=rename)
    ages = result["age_raw"].map(parse_age_code)
    result = result[ages.notna()].copy()
    ages = ages[ages.notna()]
    result["age_low"] = ages.str[0].astype(int)
    result["age_high"] = ages.str[1].astype(int)
    result["iso3"] = result["geo"].map(EUROSTAT_TO_ISO3).fillna(result["geo"])
    result["year"] = pd.to_numeric(result["year"], errors="coerce").astype("Int64")
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    result["sex"] = result["sex"].astype(str).str.upper().replace({"MALE": "M", "FEMALE": "F"})
    result["scenario"] = result.get("scenario", "Baseline" if projected else "Observed")
    result["status"] = "projected" if projected else "observed"
    result["source"] = "Eurostat"
    return result[["iso3", "year", "age_low", "age_high", "sex", "value", "scenario", "status", "source"]]


def select_baseline_projection(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "scenario" not in frame:
        return frame
    scenarios = frame["scenario"].astype(str)
    preferred = scenarios.str.upper().isin({"BSL", "BASELINE", "BASELINE PROJECTIONS"})
    if preferred.any():
        return frame[preferred].copy()
    return frame


def combine_population(*frames: pd.DataFrame) -> pd.DataFrame:
    valid = [frame for frame in frames if frame is not None and not frame.empty]
    if not valid:
        return pd.DataFrame()
    result = pd.concat(valid, ignore_index=True)
    keys = ["iso3", "year", "age_low", "age_high", "sex", "scenario", "status", "source"]
    return result.dropna(subset=["iso3", "year", "sex", "value"]).drop_duplicates(keys, keep="last")


def latest_year_by_geo(frame: pd.DataFrame, status: str = "observed") -> pd.Series:
    subset = frame[frame["status"].eq(status)]
    return subset.groupby("iso3")["year"].max()


def normalize_indicator_labels(frame: pd.DataFrame, mapping: dict[str, tuple[str, ...]]) -> pd.DataFrame:
    if frame.empty:
        return frame
    label_columns = [column for column in frame.columns if column.endswith("_label")]
    if not label_columns:
        return frame
    text = frame[label_columns].astype(str).agg(" | ".join, axis=1).str.lower()
    result = frame.copy()
    result["indicator"] = None
    for indicator, terms in mapping.items():
        mask = np.logical_and.reduce([text.str.contains(term, regex=False) for term in terms])
        result.loc[mask, "indicator"] = indicator
    return result[result["indicator"].notna()].copy()
