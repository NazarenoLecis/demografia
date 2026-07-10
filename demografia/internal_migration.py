from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd

from demografia.transform import parse_age_code


def _find(columns: Iterable[str], exact: tuple[str, ...], contains: tuple[str, ...]) -> str | None:
    available = list(columns)
    direct = next((candidate for candidate in exact if candidate in available), None)
    if direct:
        return direct
    lowered = {column: str(column).casefold() for column in available}
    return next(
        (
            column
            for column, text in lowered.items()
            if all(term.casefold() in text for term in contains)
        ),
        None,
    )


def normalize_internal_migration(
    frame: pd.DataFrame,
    dataset: str | None = None,
    extraction_date: str | None = None,
) -> pd.DataFrame:
    columns = [
        "source",
        "dataset",
        "extraction_date",
        "year",
        "origin_code",
        "destination_code",
        "age_low",
        "age_high",
        "sex",
        "unit",
        "value",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    origin_col = _find(
        frame.columns,
        ("ORIGINE", "origin", "ITTER_ORIG", "TERR_ORIG"),
        ("orig",),
    )
    destination_col = _find(
        frame.columns,
        ("DESTINAZIONE", "destination", "ITTER_DEST", "TERR_DEST"),
        ("dest",),
    )
    year_col = _find(frame.columns, ("TIME_PERIOD", "ANNO", "year"), ("time",))
    value_col = _find(frame.columns, ("OBS_VALUE", "VALUE", "value"), ("value",))
    age_col = _find(frame.columns, ("ETA", "ETA1", "AGE", "age"), ("eta",))
    sex_col = _find(frame.columns, ("SESSO", "SEXISTAT1", "SEX", "sex"), ("sex",))
    unit_col = _find(frame.columns, ("UNIT", "UNIT_MEASURE", "unit"), ("unit",))
    missing = [
        name
        for name, column in {
            "origine": origin_col,
            "destinazione": destination_col,
            "anno": year_col,
            "valore": value_col,
        }.items()
        if column is None
    ]
    if missing:
        raise ValueError(f"Colonne ISTAT migrazioni interne non riconosciute: {', '.join(missing)}")

    result = pd.DataFrame(index=frame.index)
    result["source"] = "ISTAT"
    result["dataset"] = dataset or frame.get("dataset", "ISTAT internal migration")
    result["extraction_date"] = extraction_date or date.today().isoformat()
    result["year"] = pd.to_numeric(frame[year_col], errors="coerce").astype("Int64")
    result["origin_code"] = frame[origin_col].astype(str)
    result["destination_code"] = frame[destination_col].astype(str)
    if age_col:
        parsed = frame[age_col].map(parse_age_code)
        result["age_low"] = parsed.map(lambda value: value[0] if value else pd.NA).astype("Int64")
        result["age_high"] = parsed.map(lambda value: value[1] if value else pd.NA).astype("Int64")
    else:
        result["age_low"] = pd.NA
        result["age_high"] = pd.NA
    if sex_col:
        result["sex"] = frame[sex_col].astype(str).str.upper().replace(
            {
                "1": "M",
                "2": "F",
                "9": "T",
                "MASCHI": "M",
                "FEMMINE": "F",
                "TOTALE": "T",
            }
        )
    else:
        result["sex"] = "T"
    result["unit"] = frame[unit_col].astype(str) if unit_col else "persons"
    result["value"] = pd.to_numeric(frame[value_col], errors="coerce")
    return result[columns].dropna(subset=["year", "origin_code", "destination_code", "value"])


def total_internal_flows(flows: pd.DataFrame) -> pd.DataFrame:
    """Select published totals when present, otherwise aggregate disjoint profiles."""
    if flows.empty:
        return flows.copy()
    pieces: list[pd.DataFrame] = []
    for (_, _, _), group in flows.groupby(
        ["year", "origin_code", "destination_code"],
        dropna=False,
    ):
        selected = group.copy()
        if selected["sex"].eq("T").any():
            selected = selected[selected["sex"].eq("T")]
        elif {"M", "F"}.issubset(set(selected["sex"].dropna())):
            selected = selected[selected["sex"].isin(["M", "F"])]
        total_age = selected["age_low"].isna() & selected["age_high"].isna()
        if total_age.any():
            selected = selected[total_age]
        value = float(selected["value"].sum())
        row = selected.iloc[[0]].copy()
        row["age_low"] = pd.NA
        row["age_high"] = pd.NA
        row["sex"] = "T"
        row["value"] = value
        pieces.append(row)
    return pd.concat(pieces, ignore_index=True) if pieces else flows.iloc[0:0].copy()


def internal_migration_balances(flows: pd.DataFrame) -> pd.DataFrame:
    totals = total_internal_flows(flows)
    if totals.empty:
        return pd.DataFrame(
            columns=[
                "territory_code",
                "year",
                "internal_inflows",
                "internal_outflows",
                "internal_balance",
            ]
        )
    inflows = (
        totals.groupby(["destination_code", "year"], as_index=False)["value"]
        .sum()
        .rename(columns={"destination_code": "territory_code", "value": "internal_inflows"})
    )
    outflows = (
        totals.groupby(["origin_code", "year"], as_index=False)["value"]
        .sum()
        .rename(columns={"origin_code": "territory_code", "value": "internal_outflows"})
    )
    result = inflows.merge(outflows, on=["territory_code", "year"], how="outer").fillna(0)
    result["internal_balance"] = result["internal_inflows"] - result["internal_outflows"]
    return result


def internal_migration_matrix(
    flows: pd.DataFrame,
    year: int,
    code_length: int | None = None,
) -> pd.DataFrame:
    totals = total_internal_flows(flows)
    subset = totals[totals["year"].eq(year)].copy()
    if code_length:
        subset["origin_code"] = subset["origin_code"].str[:code_length]
        subset["destination_code"] = subset["destination_code"].str[:code_length]
    return subset.pivot_table(
        index="origin_code",
        columns="destination_code",
        values="value",
        aggfunc="sum",
        fill_value=0,
    )


def internal_migration_profiles(flows: pd.DataFrame) -> pd.DataFrame:
    if flows.empty:
        return pd.DataFrame()
    profile = (
        flows.dropna(subset=["age_low"])
        .groupby(["year", "age_low", "age_high", "sex"], as_index=False)["value"]
        .sum()
    )
    totals = profile.groupby("year")["value"].transform("sum")
    profile["share"] = profile["value"] / totals.where(totals.ne(0))
    return profile
