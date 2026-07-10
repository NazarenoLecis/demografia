from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd

from demografia.transform import parse_age_code

INPS_ROLE_TERMS: dict[str, tuple[str, ...]] = {
    "pensioners": ("pensionati", "pensionato", "casellario pensionati"),
    "pensions": ("pensioni", "trattamenti pensionistici"),
    "contributors": ("contribuenti", "contributi", "posizioni contributive"),
    "insured_workers": ("assicurati", "iscritti", "lavoratori"),
    "retirement_flows": ("nuove pensioni", "decorrenze", "pensionamenti"),
}


def _slug(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _find(columns: Iterable[str], exact: tuple[str, ...], terms: tuple[str, ...] = ()) -> str | None:
    columns = list(columns)
    slug_map = {column: _slug(column) for column in columns}
    exact_slugs = {_slug(value) for value in exact}
    direct = next((column for column, slug in slug_map.items() if slug in exact_slugs), None)
    if direct is not None:
        return direct
    return next((column for column, slug in slug_map.items() if all(term in slug for term in terms)), None)


def _sex(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().replace(
        {
            "1": "M",
            "2": "F",
            "9": "T",
            "MASCULINE": "M",
            "MASCHI": "M",
            "UOMINI": "M",
            "MALE": "M",
            "FEMININE": "F",
            "FEMMINE": "F",
            "DONNE": "F",
            "FEMALE": "F",
            "TOTALE": "T",
            "TOTAL": "T",
        }
    )


def _age(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    parsed = series.map(parse_age_code)
    low = parsed.map(lambda value: value[0] if value is not None else pd.NA).astype("Int64")
    high = parsed.map(lambda value: value[1] if value is not None else pd.NA).astype("Int64")
    return low, high


def infer_inps_role(dataset_text: str, columns: Iterable[str] = ()) -> str:
    text = f"{dataset_text} {' '.join(map(str, columns))}".casefold()
    scores = {
        role: sum(term in text for term in terms)
        for role, terms in INPS_ROLE_TERMS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "inps_observation"


def _value_columns(frame: pd.DataFrame) -> dict[str, str]:
    aliases: dict[str, tuple[str, ...]] = {
        "people": ("numero", "num", "persone", "pensionati", "contribuenti", "iscritti", "lavoratori"),
        "pensions": ("pensioni", "trattamenti", "prestazioni"),
        "amount": ("importo", "ammontare", "spesa", "valore_monetario"),
        "contributions": ("contributi", "entrate_contributive", "montante"),
    }
    output: dict[str, str] = {}
    for metric, terms in aliases.items():
        column = _find(frame.columns, (), terms=(terms[0],))
        if column is None:
            column = next(
                (
                    candidate
                    for candidate in frame.columns
                    if any(term in _slug(candidate) for term in terms)
                    and pd.api.types.is_numeric_dtype(frame[candidate])
                ),
                None,
            )
        if column is not None:
            output[metric] = column
    if not output:
        numeric = [column for column in frame.columns if pd.api.types.is_numeric_dtype(frame[column])]
        reserved = {
            _find(frame.columns, ("anno", "year"), ("anno",)),
            _find(frame.columns, ("eta", "age"), ("eta",)),
        }
        numeric = [column for column in numeric if column not in reserved]
        if len(numeric) == 1:
            output["value"] = numeric[0]
    return output


def normalize_inps_table(
    frame: pd.DataFrame,
    dataset_id: str = "",
    dataset_title: str = "",
    role: str | None = None,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    columns = [
        "source",
        "dataset_id",
        "dataset_title",
        "extraction_date",
        "role",
        "year",
        "age_low",
        "age_high",
        "sex",
        "territory_code",
        "territory_name",
        "management",
        "category",
        "metric",
        "unit",
        "value",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    year_col = _find(frame.columns, ("anno", "year", "tempo", "periodo"), ("anno",))
    age_col = _find(frame.columns, ("eta", "classe_eta", "fascia_eta", "age"), ("eta",))
    sex_col = _find(frame.columns, ("sesso", "sex", "genere"), ("sess",))
    territory_code_col = _find(
        frame.columns,
        ("codice_territorio", "codice_regione", "codice_provincia", "territory_code"),
        ("codice", "territ"),
    )
    territory_name_col = _find(
        frame.columns,
        ("territorio", "regione", "provincia", "area_geografica", "territory"),
        ("territ",),
    )
    management_col = _find(frame.columns, ("gestione", "fondo", "management"), ("gestion",))
    category_col = _find(
        frame.columns,
        ("categoria", "qualifica", "tipo_pensione", "tipo_lavoratore", "category"),
        ("categor",),
    )
    unit_col = _find(frame.columns, ("unita", "unita_misura", "unit"), ("unita",))
    role = role or infer_inps_role(f"{dataset_title} {dataset_id}", frame.columns)
    value_columns = _value_columns(frame)
    if not value_columns:
        raise ValueError(
            f"Nessuna colonna numerica riconosciuta nel dataset INPS {dataset_id or dataset_title}"
        )

    pieces: list[pd.DataFrame] = []
    for metric, value_col in value_columns.items():
        result = pd.DataFrame(index=frame.index)
        result["source"] = "INPS"
        result["dataset_id"] = str(dataset_id)
        result["dataset_title"] = dataset_title
        result["extraction_date"] = extraction_date or date.today().isoformat()
        result["role"] = role
        result["year"] = (
            pd.to_numeric(frame[year_col], errors="coerce").astype("Int64")
            if year_col
            else pd.Series(pd.NA, index=frame.index, dtype="Int64")
        )
        if age_col:
            result["age_low"], result["age_high"] = _age(frame[age_col])
        else:
            result["age_low"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
            result["age_high"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
        result["sex"] = _sex(frame[sex_col]) if sex_col else "T"
        result["territory_code"] = frame[territory_code_col].astype(str) if territory_code_col else pd.NA
        result["territory_name"] = frame[territory_name_col].astype(str) if territory_name_col else pd.NA
        result["management"] = frame[management_col].astype(str) if management_col else pd.NA
        result["category"] = frame[category_col].astype(str) if category_col else pd.NA
        result["metric"] = metric
        result["unit"] = (
            frame[unit_col].astype(str)
            if unit_col
            else ("euro" if metric == "amount" else "persons")
        )
        result["value"] = pd.to_numeric(frame[value_col], errors="coerce")
        pieces.append(result[columns].dropna(subset=["value"]))
    return pd.concat(pieces, ignore_index=True, sort=False)


def _total_metric(frame: pd.DataFrame, metric: str, role: str) -> pd.DataFrame:
    subset = frame[frame["metric"].eq(metric) & frame["role"].eq(role)].copy()
    if subset.empty:
        return pd.DataFrame(columns=["year", "value"])
    if subset["sex"].eq("T").any():
        subset = subset[subset["sex"].eq("T")]
    elif {"M", "F"}.issubset(set(subset["sex"].dropna())):
        subset = subset[subset["sex"].isin(["M", "F"])]
    total_age = subset["age_low"].isna() & subset["age_high"].isna()
    if total_age.any():
        subset = subset[total_age]
    return subset.groupby("year", as_index=False)["value"].sum()


def build_inps_support_indicators(observations: pd.DataFrame) -> pd.DataFrame:
    if observations.empty:
        return pd.DataFrame()
    pensioners = _total_metric(observations, "people", "pensioners").rename(
        columns={"value": "pensioners"}
    )
    contributor_parts = [
        part
        for part in (
            _total_metric(observations, "people", "contributors"),
            _total_metric(observations, "people", "insured_workers"),
        )
        if not part.empty
    ]
    contributors = (
        pd.concat(contributor_parts, ignore_index=True)
        if contributor_parts
        else pd.DataFrame(columns=["year", "value"])
    )
    contributors = contributors.groupby("year", as_index=False)["value"].max().rename(
        columns={"value": "contributors"}
    )
    pensions = _total_metric(observations, "pensions", "pensions").rename(columns={"value": "pensions"})
    result = pensioners.merge(contributors, on="year", how="outer").merge(pensions, on="year", how="outer")
    result["contributors_per_pensioner"] = result["contributors"] / result["pensioners"].replace(0, np.nan)
    result["pensions_per_pensioner"] = result["pensions"] / result["pensioners"].replace(0, np.nan)
    result["source"] = "INPS"
    return result.sort_values("year").reset_index(drop=True)


def discover_inps_roles(catalog: pd.DataFrame, max_per_role: int = 5) -> pd.DataFrame:
    if catalog.empty:
        return pd.DataFrame()
    text = (
        catalog[["name", "title", "notes", "tags", "resource_name", "resource_description"]]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.casefold()
    )
    outputs: list[pd.DataFrame] = []
    for role, terms in INPS_ROLE_TERMS.items():
        scores = pd.Series(0, index=catalog.index, dtype=int)
        for term in terms:
            scores += text.str.contains(term, regex=False).astype(int)
        candidates = catalog[scores.gt(0)].copy()
        if candidates.empty:
            continue
        candidates["role"] = role
        candidates["role_score"] = scores.loc[candidates.index]
        candidates = candidates.sort_values(
            ["role_score", "metadata_modified", "last_modified"],
            ascending=[False, False, False],
            na_position="last",
        )
        candidates = candidates.drop_duplicates("dataset_id", keep="first").head(max_per_role)
        outputs.append(candidates)
    return pd.concat(outputs, ignore_index=True, sort=False) if outputs else pd.DataFrame()
