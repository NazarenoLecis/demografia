from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ISO_CANDIDATES = ("ISO3_code", "ISO3", "iso3", "Location code")
YEAR_CANDIDATES = ("Time", "Year", "year")
AGE_CANDIDATES = ("AgeGrp", "Age", "age", "Age group")
SEX_CANDIDATES = ("Sex", "sex")
VALUE_CANDIDATES = ("PopTotal", "Population", "Value", "value")
VARIANT_CANDIDATES = ("Variant", "variant", "Projection")


def _find(columns: pd.Index, candidates: tuple[str, ...]) -> str | None:
    return next((candidate for candidate in candidates if candidate in columns), None)


def read_wpp(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".zip":
        return pd.read_csv(path, compression="zip", low_memory=False)
    return pd.read_csv(path, low_memory=False)


def _parse_age(value: object) -> tuple[int, int]:
    text = str(value).strip().upper().replace("YEARS", "").replace("YEAR", "")
    if text in {"100+", "100 PLUS", "Y_GE100"}:
        return 100, 120
    numbers = [int(number) for number in re.findall(r"\d+", text)]
    if not numbers:
        raise ValueError(f"Età WPP non riconosciuta: {value}")
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return numbers[0], numbers[1]


def normalize_wpp_age_sex(
    frame: pd.DataFrame,
    projected: bool | None = None,
    value_scale: float = 1000.0,
) -> pd.DataFrame:
    iso_col = _find(frame.columns, ISO_CANDIDATES)
    year_col = _find(frame.columns, YEAR_CANDIDATES)
    age_col = _find(frame.columns, AGE_CANDIDATES)
    sex_col = _find(frame.columns, SEX_CANDIDATES)
    value_col = _find(frame.columns, VALUE_CANDIDATES)
    variant_col = _find(frame.columns, VARIANT_CANDIDATES)

    missing = [name for name, column in {"iso3": iso_col, "year": year_col, "age": age_col}.items() if column is None]
    if missing:
        raise ValueError(f"Colonne WPP mancanti: {', '.join(missing)}")

    if sex_col and value_col:
        result = frame[[iso_col, year_col, age_col, sex_col, value_col] + ([variant_col] if variant_col else [])].copy()
        result.columns = ["iso3", "year", "age_raw", "sex", "value"] + (["scenario"] if variant_col else [])
    elif {"PopMale", "PopFemale"}.issubset(frame.columns):
        base = frame[[iso_col, year_col, age_col] + ([variant_col] if variant_col else [])].copy()
        male = base.copy()
        female = base.copy()
        male["sex"] = "M"
        female["sex"] = "F"
        male["value"] = frame["PopMale"].to_numpy()
        female["value"] = frame["PopFemale"].to_numpy()
        result = pd.concat([male, female], ignore_index=True)
        result.columns = ["iso3", "year", "age_raw"] + (["scenario"] if variant_col else []) + ["sex", "value"]
    else:
        raise ValueError("Il file WPP deve contenere Sex+Value oppure PopMale+PopFemale")

    ages = result["age_raw"].map(_parse_age)
    result["age_low"] = ages.str[0]
    result["age_high"] = ages.str[1]
    result["year"] = pd.to_numeric(result["year"], errors="coerce").astype("Int64")
    result["value"] = pd.to_numeric(result["value"], errors="coerce") * value_scale
    result["sex"] = result["sex"].astype(str).str.upper().replace({"MALE": "M", "FEMALE": "F"})
    result["scenario"] = result.get("scenario", "Observed")
    if projected is None:
        result["status"] = result["scenario"].astype(str).str.lower().where(
            result["scenario"].astype(str).str.lower().isin({"estimates", "observed"}), "projected"
        )
        result["status"] = result["status"].replace({"estimates": "observed"})
    else:
        result["status"] = "projected" if projected else "observed"
    result["source"] = "UN World Population Prospects"
    return result[["iso3", "year", "age_low", "age_high", "sex", "value", "scenario", "status", "source"]]
