from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from demografia.indicators import compute_age_structure
from demografia.transform import parse_age_code


def _find(columns: Iterable[str], candidates: tuple[str, ...], contains: tuple[str, ...] = ()) -> str | None:
    columns = list(columns)
    direct = next((candidate for candidate in candidates if candidate in columns), None)
    if direct is not None:
        return direct
    lowered = {column: column.lower() for column in columns}
    return next((column for column, lower in lowered.items() if all(term in lower for term in contains)), None)


def normalize_istat_population(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalizza un dataflow ISTAT con territorio, anno, età, sesso e valore."""
    territory_col = _find(
        frame.columns,
        ("ITTER107", "ITTER_NUTS3", "TERRITORIO", "territory_code", "geo"),
        ("territ",),
    )
    year_col = _find(frame.columns, ("TIME_PERIOD", "TIME", "ANNO", "year"), ("time",))
    age_col = _find(frame.columns, ("ETA1", "ETA", "AGE", "age"), ("eta",))
    sex_col = _find(frame.columns, ("SEXISTAT1", "SESSO", "SEX", "sex"), ("sex",))
    value_col = _find(frame.columns, ("OBS_VALUE", "Value", "VALUE", "value"), ("value",))
    missing = [
        name
        for name, column in {
            "territorio": territory_col,
            "anno": year_col,
            "età": age_col,
            "sesso": sex_col,
            "valore": value_col,
        }.items()
        if column is None
    ]
    if missing:
        raise ValueError(f"Colonne ISTAT non riconosciute: {', '.join(missing)}")

    result = frame[[territory_col, year_col, age_col, sex_col, value_col]].copy()
    result.columns = ["territory_code", "year", "age_raw", "sex", "value"]
    ages = result["age_raw"].map(parse_age_code)
    result = result[ages.notna()].copy()
    ages = ages[ages.notna()]
    result["age_low"] = ages.str[0].astype(int)
    result["age_high"] = ages.str[1].astype(int)
    result["year"] = pd.to_numeric(result["year"], errors="coerce").astype("Int64")
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    result["sex"] = result["sex"].astype(str).str.upper().replace(
        {"1": "M", "2": "F", "MASCULINE": "M", "MASCHI": "M", "FEMININE": "F", "FEMMINE": "F"}
    )
    result = result[result["sex"].isin(["M", "F"])]
    result["scenario"] = "Observed"
    result["status"] = "observed"
    result["source"] = "ISTAT"
    result["iso3"] = result["territory_code"].astype(str)
    return result[
        ["territory_code", "iso3", "year", "age_low", "age_high", "sex", "value", "scenario", "status", "source"]
    ]


def compute_territorial_age_structure(population: pd.DataFrame) -> pd.DataFrame:
    result = compute_age_structure(population)
    return result.rename(columns={"iso3": "territory_code"})
