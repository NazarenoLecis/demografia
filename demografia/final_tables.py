from __future__ import annotations

from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd

from demografia.config import COUNTRY_NAMES, EUROSTAT_TO_ISO3
from demografia.transform import parse_age_code

CENTRAL_POPULATION_COLUMNS = [
    "source",
    "dataset",
    "extraction_date",
    "release_date",
    "projection_vintage",
    "geo_level",
    "geo_code",
    "geo_name",
    "iso2",
    "iso3",
    "year",
    "age_low",
    "age_high",
    "age_label",
    "sex",
    "citizenship",
    "country_of_birth",
    "status",
    "scenario",
    "quantile",
    "lower_bound",
    "upper_bound",
    "unit",
    "value",
]

FERTILITY_CODE_MAP = {
    "TOTFERRT": "total_fertility_rate",
    "TFR": "total_fertility_rate",
    "AGEMOTH": "mean_age_at_childbirth",
    "AGEMOTH1": "mean_age_at_first_birth",
    "MEANAGE1": "mean_age_at_first_birth",
    "LIVEBIRTH": "live_births",
    "LIVEBIRTHS": "live_births",
}

BALANCE_CODE_MAP = {
    "JAN": "population_1_january",
    "POP_JAN": "population_1_january",
    "AVG": "population_average",
    "BIRTH": "live_births",
    "LBIRTH": "live_births",
    "DEATH": "deaths",
    "NATGROW": "natural_change",
    "NATBAL": "natural_change",
    "IMMIGR": "immigration",
    "EMIGR": "emigration",
    "CNMIGRAT": "net_migration_adjustment",
    "NETMIGR": "net_migration",
    "GROW": "population_change",
    "GROWRT": "population_growth_rate",
}

EDUCATION_LEVEL_MAP = {
    "ED0-2": "low_education",
    "ED3_4": "upper_secondary_post_secondary",
    "ED5-8": "tertiary",
    "ED3-8": "upper_secondary_or_more",
    "ED34_44": "upper_secondary_general",
    "ED35_45": "upper_secondary_vocational",
}


def _first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    available = set(columns)
    return next((candidate for candidate in candidates if candidate in available), None)


def _as_year(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _iso3(series: pd.Series) -> pd.Series:
    return series.astype(str).map(EUROSTAT_TO_ISO3).fillna(series.astype(str))


def _age_columns(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    parsed = series.map(parse_age_code)
    low = parsed.map(lambda value: value[0] if value is not None else pd.NA).astype("Int64")
    high = parsed.map(lambda value: value[1] if value is not None else pd.NA).astype("Int64")
    label = np.where(
        high.ge(120).fillna(False),
        low.astype("string") + "+",
        np.where(
            low.eq(high).fillna(False),
            low.astype("string"),
            low.astype("string") + "-" + high.astype("string"),
        ),
    )
    return low, high, pd.Series(label, index=series.index, dtype="string")


def _eurostat_geo_metadata(frame: pd.DataFrame, geo_col: str) -> pd.DataFrame:
    metadata = pd.DataFrame(index=frame.index)
    metadata["geo_level"] = np.where(frame[geo_col].astype(str).str.len().gt(2), "region", "country")
    metadata["geo_code"] = frame[geo_col].astype(str)
    label_col = f"{geo_col}_label"
    metadata["geo_name"] = (
        frame[label_col].astype(str)
        if label_col in frame
        else metadata["geo_code"].map(COUNTRY_NAMES).fillna(metadata["geo_code"])
    )
    metadata["iso3"] = np.where(
        metadata["geo_level"].eq("region"),
        "ITA",
        _iso3(frame[geo_col]),
    )
    return metadata


def add_eurostat_geo_metadata(frame: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or raw.empty:
        return frame
    geo_col = _first_existing(raw.columns, ("geo", "geo_label"))
    if not geo_col:
        return frame
    metadata = _eurostat_geo_metadata(raw.loc[frame.index], geo_col)
    result = frame.copy()
    for column in ("geo_level", "geo_code", "geo_name", "iso3"):
        result[column] = metadata[column].to_numpy()
    return result


def normalize_eurostat_regional_population(
    frame: pd.DataFrame,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    columns = [
        "source",
        "dataset",
        "extraction_date",
        "geo_level",
        "geo_code",
        "geo_name",
        "iso3",
        "year",
        "age_low",
        "age_high",
        "age_label",
        "sex",
        "status",
        "scenario",
        "unit",
        "value",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    geo_col = _first_existing(frame.columns, ("geo", "geo_label"))
    year_col = _first_existing(frame.columns, ("time", "TIME_PERIOD", "year"))
    age_col = _first_existing(frame.columns, ("age", "age_label"))
    sex_col = _first_existing(frame.columns, ("sex", "sex_label"))
    if not all((geo_col, year_col, age_col, sex_col)) or "value" not in frame:
        raise ValueError("Dimensioni Eurostat insufficienti per la popolazione regionale")

    metadata = _eurostat_geo_metadata(frame, geo_col)
    result = pd.DataFrame(index=frame.index)
    result["source"] = "Eurostat"
    result["dataset"] = frame.get("dataset", "demo_r_pjangroup")
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["geo_level"] = metadata["geo_level"]
    result["geo_code"] = metadata["geo_code"]
    result["geo_name"] = metadata["geo_name"]
    result["iso3"] = metadata["iso3"]
    result["year"] = _as_year(frame[year_col])
    result["age_low"], result["age_high"], result["age_label"] = _age_columns(frame[age_col])
    result["sex"] = frame[sex_col].astype(str).str.upper().replace({"MALE": "M", "FEMALE": "F"})
    result["status"] = "observed"
    result["scenario"] = "Observed"
    result["unit"] = frame.get("unit", "NR").astype(str) if "unit" in frame else "NR"
    result["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return result[columns].dropna(subset=["geo_code", "year", "value"])


def _indicator_from_label(code: object, label: object, mapping: dict[str, str], family: str) -> str:
    code_text = str(code).upper().strip()
    if code_text in mapping:
        return mapping[code_text]
    text = f"{code} {label}".lower()
    rules = {
        "total_fertility_rate": ("total fertility", "fertility rate", "figli per donna"),
        "mean_age_at_first_birth": ("first child", "first birth", "primo figlio"),
        "mean_age_at_childbirth": ("mean age", "childbirth", "maternity"),
        "live_births": ("live birth", "nati vivi"),
        "deaths": ("death", "decess"),
        "natural_change": ("natural change", "natural increase", "saldo naturale"),
        "immigration": ("immigration", "immigrat"),
        "emigration": ("emigration", "emigrat"),
        "net_migration": ("net migration", "saldo migratorio"),
        "population_change": ("population change", "total increase", "variazione della popolazione"),
        "population_1_january": ("1 january", "january population", "popolazione al 1"),
    }
    for indicator, terms in rules.items():
        if any(term in text for term in terms):
            return indicator
    return f"{family}_{code_text.lower()}"


def normalize_eurostat_fertility(frame: pd.DataFrame, extraction_date: str | None = None) -> pd.DataFrame:
    columns = [
        "source",
        "dataset",
        "extraction_date",
        "iso3",
        "year",
        "indicator_code",
        "indicator",
        "indicator_label",
        "age_low",
        "age_high",
        "sex",
        "unit",
        "value",
        "status_flag",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    geo_col = _first_existing(frame.columns, ("geo", "geo_label"))
    year_col = _first_existing(frame.columns, ("time", "TIME_PERIOD", "year"))
    indicator_col = _first_existing(frame.columns, ("indic_de", "indicator", "indic", "unit"))
    if not geo_col or not year_col or not indicator_col or "value" not in frame:
        raise ValueError("Dimensioni Eurostat insufficienti per la fecondità")
    result = pd.DataFrame(index=frame.index)
    result["source"] = "Eurostat"
    result["dataset"] = frame.get("dataset", "demo_frate")
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["iso3"] = _iso3(frame[geo_col])
    result["year"] = _as_year(frame[year_col])
    result["indicator_code"] = frame[indicator_col].astype(str)
    label_col = f"{indicator_col}_label"
    result["indicator_label"] = frame[label_col].astype(str) if label_col in frame else result["indicator_code"]
    result["indicator"] = [
        _indicator_from_label(code, label, FERTILITY_CODE_MAP, "fertility")
        for code, label in zip(result["indicator_code"], result["indicator_label"], strict=False)
    ]
    age_col = _first_existing(frame.columns, ("age", "age_label"))
    if age_col:
        result["age_low"], result["age_high"], _ = _age_columns(frame[age_col])
    else:
        result["age_low"] = pd.NA
        result["age_high"] = pd.NA
    result["sex"] = frame.get("sex", "F").astype(str).str.upper() if "sex" in frame else "F"
    result["unit"] = frame.get("unit", "").astype(str) if "unit" in frame else ""
    result["value"] = pd.to_numeric(frame["value"], errors="coerce")
    result["status_flag"] = frame.get("status_flag", pd.Series(pd.NA, index=frame.index))
    return result[columns].dropna(subset=["iso3", "year", "value"])


def normalize_eurostat_demographic_balance(
    frame: pd.DataFrame,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    columns = [
        "source",
        "dataset",
        "extraction_date",
        "iso3",
        "year",
        "indicator_code",
        "indicator",
        "indicator_label",
        "unit",
        "value",
        "status_flag",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    geo_col = _first_existing(frame.columns, ("geo", "geo_label"))
    year_col = _first_existing(frame.columns, ("time", "TIME_PERIOD", "year"))
    indicator_col = _first_existing(frame.columns, ("indic_de", "indicator", "indic"))
    if not geo_col or not year_col or not indicator_col or "value" not in frame:
        raise ValueError("Dimensioni Eurostat insufficienti per il bilancio demografico")
    result = pd.DataFrame(index=frame.index)
    result["source"] = "Eurostat"
    result["dataset"] = frame.get("dataset", "demo_gind")
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["iso3"] = _iso3(frame[geo_col])
    result["year"] = _as_year(frame[year_col])
    result["indicator_code"] = frame[indicator_col].astype(str)
    label_col = f"{indicator_col}_label"
    result["indicator_label"] = frame[label_col].astype(str) if label_col in frame else result["indicator_code"]
    result["indicator"] = [
        _indicator_from_label(code, label, BALANCE_CODE_MAP, "balance")
        for code, label in zip(result["indicator_code"], result["indicator_label"], strict=False)
    ]
    result["unit"] = frame.get("unit", "").astype(str) if "unit" in frame else ""
    result["value"] = pd.to_numeric(frame["value"], errors="coerce")
    result["status_flag"] = frame.get("status_flag", pd.Series(pd.NA, index=frame.index))
    return result[columns].dropna(subset=["iso3", "year", "value"])


def build_demographic_balance_wide(balance: pd.DataFrame) -> pd.DataFrame:
    if balance.empty:
        return pd.DataFrame()
    preferred = balance.copy()
    if "unit" in preferred:
        numeric_units = preferred["unit"].astype(str).str.upper().isin({"NR", "NUMBER", "PERSON", "PERSONS", ""})
        if numeric_units.any():
            preferred = preferred[numeric_units]
    index = [column for column in ("geo_level", "geo_code", "geo_name", "iso3", "year") if column in preferred]
    if "year" not in index:
        index.append("year")
    if "iso3" not in index and "iso3" in preferred:
        index.insert(0, "iso3")
    wide = preferred.pivot_table(index=index, columns="indicator", values="value", aggfunc="first").reset_index()
    wide.columns.name = None
    if {"live_births", "deaths"}.issubset(wide):
        wide["natural_change_derived"] = wide["live_births"] - wide["deaths"]
    if {"immigration", "emigration"}.issubset(wide):
        wide["net_migration_derived"] = wide["immigration"] - wide["emigration"]
    natural = "natural_change" if "natural_change" in wide else "natural_change_derived"
    migration = "net_migration" if "net_migration" in wide else "net_migration_derived"
    if {"population_change", natural, migration}.issubset(wide):
        wide["balance_identity_residual"] = wide["population_change"] - wide[natural] - wide[migration]
    return wide


def normalize_eurostat_education_attainment(
    frame: pd.DataFrame,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    """Normalize Eurostat educational-attainment percentages.

    The table intentionally stores percentages and keeps age group, sex, and
    ISCED level explicit. It should not be merged into population counts without
    an explicit weighting step.
    """
    columns = [
        "source",
        "dataset",
        "extraction_date",
        "iso3",
        "year",
        "age_low",
        "age_high",
        "age_label",
        "sex",
        "education_level_code",
        "education_level",
        "education_level_label",
        "unit",
        "value",
        "status_flag",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    geo_col = _first_existing(frame.columns, ("geo", "geo_label"))
    year_col = _first_existing(frame.columns, ("time", "TIME_PERIOD", "year"))
    education_col = _first_existing(frame.columns, ("isced11", "education_level"))
    age_col = _first_existing(frame.columns, ("age", "age_label"))
    if not geo_col or not year_col or not education_col or not age_col or "value" not in frame:
        raise ValueError("Dimensioni Eurostat insufficienti per i titoli di studio")

    result = pd.DataFrame(index=frame.index)
    result["source"] = "Eurostat"
    result["dataset"] = frame.get("dataset", "edat_lfse_03")
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["iso3"] = _iso3(frame[geo_col])
    result["year"] = _as_year(frame[year_col])
    result["age_low"], result["age_high"], result["age_label"] = _age_columns(frame[age_col])
    result["sex"] = frame.get("sex", "T").astype(str).str.upper() if "sex" in frame else "T"
    result["education_level_code"] = frame[education_col].astype(str)
    label_col = f"{education_col}_label"
    result["education_level_label"] = (
        frame[label_col].astype(str) if label_col in frame else result["education_level_code"]
    )
    result["education_level"] = result["education_level_code"].map(EDUCATION_LEVEL_MAP).fillna(
        result["education_level_code"].str.lower()
    )
    result["unit"] = frame.get("unit", "PC").astype(str) if "unit" in frame else "PC"
    result["value"] = pd.to_numeric(frame["value"], errors="coerce")
    result["status_flag"] = frame.get("status_flag", pd.Series(pd.NA, index=frame.index))
    return result[columns].dropna(subset=["iso3", "year", "value"])


def normalize_eurostat_migration(
    frame: pd.DataFrame,
    flow: str,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    if flow not in {"immigration", "emigration"}:
        raise ValueError("flow deve essere immigration o emigration")
    core = [
        "source",
        "dataset",
        "extraction_date",
        "flow",
        "iso3",
        "year",
        "age_low",
        "age_high",
        "sex",
        "citizenship",
        "country_of_birth",
        "partner_country",
        "unit",
        "value",
        "status_flag",
    ]
    if frame.empty:
        return pd.DataFrame(columns=core)
    geo_col = _first_existing(frame.columns, ("geo", "geo_label"))
    year_col = _first_existing(frame.columns, ("time", "TIME_PERIOD", "year"))
    if not geo_col or not year_col or "value" not in frame:
        raise ValueError("Dimensioni Eurostat insufficienti per i flussi migratori")
    result = pd.DataFrame(index=frame.index)
    result["source"] = "Eurostat"
    result["dataset"] = frame.get("dataset", "")
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["flow"] = flow
    result["iso3"] = _iso3(frame[geo_col])
    result["year"] = _as_year(frame[year_col])
    age_col = _first_existing(frame.columns, ("age", "age_label"))
    if age_col:
        result["age_low"], result["age_high"], _ = _age_columns(frame[age_col])
    else:
        result["age_low"] = pd.NA
        result["age_high"] = pd.NA
    result["sex"] = frame.get("sex", "T").astype(str).str.upper() if "sex" in frame else "T"
    citizenship_col = _first_existing(frame.columns, ("citizen", "citizenship", "citizen_label"))
    birth_col = _first_existing(frame.columns, ("c_birth", "country_of_birth", "c_birth_label"))
    partner_col = _first_existing(frame.columns, ("partner", "resid", "geo_dest", "geo_orig", "partner_label"))
    result["citizenship"] = frame[citizenship_col].astype(str) if citizenship_col else pd.NA
    result["country_of_birth"] = frame[birth_col].astype(str) if birth_col else pd.NA
    result["partner_country"] = frame[partner_col].astype(str) if partner_col else pd.NA
    result["unit"] = frame.get("unit", "NR").astype(str) if "unit" in frame else "NR"
    result["value"] = pd.to_numeric(frame["value"], errors="coerce")
    result["status_flag"] = frame.get("status_flag", pd.Series(pd.NA, index=frame.index))
    return result[core].dropna(subset=["iso3", "year", "value"])


def build_migration_summary(*frames: pd.DataFrame) -> pd.DataFrame:
    valid = [frame for frame in frames if frame is not None and not frame.empty]
    if not valid:
        return pd.DataFrame(columns=["iso3", "year", "immigration", "emigration", "net_migration"])
    combined = pd.concat(valid, ignore_index=True)
    totals = combined.groupby(["iso3", "year", "flow"], as_index=False)["value"].sum()
    wide = totals.pivot_table(index=["iso3", "year"], columns="flow", values="value", aggfunc="sum").reset_index()
    wide.columns.name = None
    for column in ("immigration", "emigration"):
        if column not in wide:
            wide[column] = 0.0
    wide["net_migration"] = wide["immigration"] - wide["emigration"]
    return wide


def normalize_migrant_stock(
    frame: pd.DataFrame,
    basis: str,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    if basis not in {"citizenship", "country_of_birth"}:
        raise ValueError("basis non riconosciuta")
    columns = [
        "source",
        "dataset",
        "extraction_date",
        "basis",
        "iso3",
        "year",
        "age_low",
        "age_high",
        "sex",
        "category",
        "unit",
        "value",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    geo_col = _first_existing(frame.columns, ("geo", "geo_label"))
    year_col = _first_existing(frame.columns, ("time", "TIME_PERIOD", "year"))
    category_col = _first_existing(frame.columns, ("citizen", "citizenship", "c_birth", "country_of_birth"))
    if not geo_col or not year_col or not category_col or "value" not in frame:
        raise ValueError("Dimensioni Eurostat insufficienti per lo stock migratorio")
    result = pd.DataFrame(index=frame.index)
    result["source"] = "Eurostat"
    result["dataset"] = frame.get("dataset", "")
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["basis"] = basis
    result["iso3"] = _iso3(frame[geo_col])
    result["year"] = _as_year(frame[year_col])
    age_col = _first_existing(frame.columns, ("age", "age_label"))
    if age_col:
        result["age_low"], result["age_high"], _ = _age_columns(frame[age_col])
    else:
        result["age_low"] = pd.NA
        result["age_high"] = pd.NA
    result["sex"] = frame.get("sex", "T").astype(str).str.upper() if "sex" in frame else "T"
    result["category"] = frame[category_col].astype(str)
    result["unit"] = frame.get("unit", "NR").astype(str) if "unit" in frame else "NR"
    result["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return result[columns].dropna(subset=["iso3", "year", "value"])


def enrich_population_schema(population: pd.DataFrame, extraction_date: str | None = None) -> pd.DataFrame:
    if population.empty:
        return pd.DataFrame(columns=CENTRAL_POPULATION_COLUMNS)
    result = population.copy()
    reverse_iso2 = {iso3: iso2 for iso2, iso3 in EUROSTAT_TO_ISO3.items() if len(iso2) == 2}
    result["dataset"] = result.get("dataset", pd.Series(pd.NA, index=result.index))
    missing_dataset = result["dataset"].isna() | result["dataset"].astype(str).eq("")
    result.loc[missing_dataset & result["source"].astype(str).str.contains("Eurostat"), "dataset"] = "demo_pjan/proj_23np"
    result.loc[
        missing_dataset & result["source"].astype(str).str.contains("World Population"), "dataset"
    ] = "WPP2024"
    result["extraction_date"] = result.get("extraction_date", extraction_date or date.today().isoformat())
    result["release_date"] = result.get("release_date", pd.NA)
    result["projection_vintage"] = result.get("projection_vintage", pd.NA)
    projected = result["status"].astype(str).eq("projected")
    result.loc[
        projected & result["source"].astype(str).str.contains("Eurostat"), "projection_vintage"
    ] = "EUROPOP2023"
    result.loc[
        projected & result["source"].astype(str).str.contains("World Population"), "projection_vintage"
    ] = "WPP2024"
    result["geo_level"] = result.get("geo_level", "country")
    result["geo_code"] = result.get("geo_code", result["iso3"])
    result["geo_name"] = result.get("geo_name", result["iso3"].map(COUNTRY_NAMES).fillna(result["iso3"]))
    result["iso2"] = result.get("iso2", result["iso3"].map(reverse_iso2))
    result["age_label"] = np.where(
        result["age_high"].ge(120),
        result["age_low"].astype("Int64").astype("string") + "+",
        np.where(
            result["age_low"].eq(result["age_high"]),
            result["age_low"].astype("Int64").astype("string"),
            result["age_low"].astype("Int64").astype("string")
            + "-"
            + result["age_high"].astype("Int64").astype("string"),
        ),
    )
    result["citizenship"] = result.get("citizenship", pd.NA)
    result["country_of_birth"] = result.get("country_of_birth", pd.NA)
    result["quantile"] = result.get("quantile", pd.NA)
    result["lower_bound"] = pd.to_numeric(
        result.get("lower_bound", pd.Series(np.nan, index=result.index)), errors="coerce"
    )
    result["upper_bound"] = pd.to_numeric(
        result.get("upper_bound", pd.Series(np.nan, index=result.index)), errors="coerce"
    )
    result["unit"] = result.get("unit", "persons")
    for column in CENTRAL_POPULATION_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    return result[CENTRAL_POPULATION_COLUMNS].sort_values(
        ["iso3", "year", "status", "scenario", "sex", "age_low"]
    )


def projection_inventory(population: pd.DataFrame) -> pd.DataFrame:
    columns = ["source", "projection_vintage", "scenario", "iso3", "first_year", "last_year", "rows"]
    if population.empty:
        return pd.DataFrame(columns=columns)
    subset = population[population["status"].astype(str).eq("projected")].copy()
    if subset.empty:
        return pd.DataFrame(columns=columns)
    for column in ("projection_vintage", "scenario"):
        if column not in subset:
            subset[column] = pd.NA
    return (
        subset.groupby(["source", "projection_vintage", "scenario", "iso3"], dropna=False)
        .agg(first_year=("year", "min"), last_year=("year", "max"), rows=("value", "size"))
        .reset_index()
    )
