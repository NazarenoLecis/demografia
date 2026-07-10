from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Iterable

import pandas as pd

from demografia.transform import parse_age_code


def _slug(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _find(columns: Iterable[str], exact: tuple[str, ...], terms: tuple[str, ...] = ()) -> str | None:
    mapping = {column: _slug(column) for column in columns}
    exact_slugs = {_slug(value) for value in exact}
    direct = next((column for column, slug in mapping.items() if slug in exact_slugs), None)
    if direct:
        return direct
    return next((column for column, slug in mapping.items() if all(term in slug for term in terms)), None)


def normalize_istat_indicator_table(
    frame: pd.DataFrame,
    role: str,
    dataset: str,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    columns = [
        "source",
        "dataset",
        "extraction_date",
        "role",
        "year",
        "territory_code",
        "territory_name",
        "age_low",
        "age_high",
        "sex",
        "citizenship",
        "country_of_birth",
        "indicator_code",
        "indicator_label",
        "unit",
        "value",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    year_col = _find(frame.columns, ("TIME_PERIOD", "ANNO", "YEAR", "time"), ("time",))
    value_col = _find(frame.columns, ("OBS_VALUE", "VALUE", "valore"), ("value",))
    territory_col = _find(
        frame.columns,
        ("ITTER107", "ITTER_NUTS3", "TERRITORIO", "geo", "territory_code"),
        ("territ",),
    )
    territory_name_col = _find(
        frame.columns,
        ("Territorio", "TERRITORIO_LABEL", "geo_label", "territory_name"),
        ("territ", "label"),
    )
    age_col = _find(frame.columns, ("ETA1", "ETA", "AGE", "age"), ("eta",))
    sex_col = _find(frame.columns, ("SEXISTAT1", "SESSO", "SEX", "sex"), ("sex",))
    citizen_col = _find(frame.columns, ("CITTADINANZA", "CITIZEN", "citizenship"), ("cittadin",))
    birth_col = _find(frame.columns, ("PAESE_NASCITA", "C_BIRTH", "country_of_birth"), ("nascita",))
    unit_col = _find(frame.columns, ("UNIT_MEASURE", "UNIT", "unita"), ("unit",))
    indicator_col = _find(
        frame.columns,
        ("INDICATORE", "TIPO_DATO", "MISURA", "indicator"),
        ("indic",),
    )
    if year_col is None or value_col is None:
        raise ValueError(f"Dataflow ISTAT {dataset} privo di anno o valore")

    result = pd.DataFrame(index=frame.index)
    result["source"] = "ISTAT"
    result["dataset"] = dataset
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["role"] = role
    result["year"] = pd.to_numeric(frame[year_col], errors="coerce").astype("Int64")
    result["territory_code"] = frame[territory_col].astype(str) if territory_col else "IT"
    result["territory_name"] = frame[territory_name_col].astype(str) if territory_name_col else pd.NA
    if age_col:
        parsed = frame[age_col].map(parse_age_code)
        result["age_low"] = parsed.map(lambda value: value[0] if value else pd.NA).astype("Int64")
        result["age_high"] = parsed.map(lambda value: value[1] if value else pd.NA).astype("Int64")
    else:
        result["age_low"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
        result["age_high"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    result["sex"] = (
        frame[sex_col].astype(str).str.upper().replace(
            {
                "1": "M",
                "2": "F",
                "9": "T",
                "MASCHI": "M",
                "FEMMINE": "F",
                "TOTALE": "T",
            }
        )
        if sex_col
        else "T"
    )
    result["citizenship"] = frame[citizen_col].astype(str) if citizen_col else pd.NA
    result["country_of_birth"] = frame[birth_col].astype(str) if birth_col else pd.NA
    result["indicator_code"] = frame[indicator_col].astype(str) if indicator_col else role
    label_col = f"{indicator_col}_LABEL" if indicator_col else None
    result["indicator_label"] = (
        frame[label_col].astype(str)
        if label_col in frame
        else result["indicator_code"]
    )
    result["unit"] = frame[unit_col].astype(str) if unit_col else "persons"
    result["value"] = pd.to_numeric(frame[value_col], errors="coerce")
    return result[columns].dropna(subset=["year", "value"])


def normalize_istat_projection(
    frame: pd.DataFrame,
    dataset: str,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    result = normalize_istat_indicator_table(
        frame,
        role="population_projections",
        dataset=dataset,
        extraction_date=extraction_date,
    )
    if result.empty:
        return result
    scenario_col = _find(frame.columns, ("SCENARIO", "IPOTESI", "VARIANTE"), ("scenario",))
    quantile_col = _find(frame.columns, ("QUANTILE", "PERCENTILE", "INTERVALLO"), ("quant",))
    result["scenario"] = (
        frame.loc[result.index, scenario_col].astype(str).to_numpy()
        if scenario_col
        else "median"
    )
    result["quantile"] = (
        frame.loc[result.index, quantile_col].astype(str).to_numpy()
        if quantile_col
        else pd.NA
    )
    result["status"] = "projected"
    result["projection_vintage"] = pd.to_numeric(result["year"], errors="coerce").min()
    return result
