from __future__ import annotations

import pandas as pd


def _row(source: str, check: str, severity: str, failures: int, detail: str) -> dict[str, object]:
    return {
        "source": source,
        "check": check,
        "severity": severity,
        "failures": int(failures),
        "passed": int(failures) == 0,
        "detail": detail,
    }


def build_official_quality_report(
    inps: pd.DataFrame | None = None,
    rgs: pd.DataFrame | None = None,
    internal_migration_balances: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    if inps is not None and not inps.empty:
        key_columns = [
            column
            for column in (
                "dataset_id",
                "role",
                "year",
                "age_low",
                "age_high",
                "sex",
                "territory_code",
                "management",
                "category",
                "metric",
            )
            if column in inps
        ]
        rows.append(
            _row(
                "INPS",
                "duplicate analytical keys",
                "error",
                int(inps.duplicated(key_columns, keep=False).sum()) if key_columns else 0,
                ", ".join(key_columns),
            )
        )
        rows.append(
            _row(
                "INPS",
                "negative counts",
                "error",
                int((pd.to_numeric(inps["value"], errors="coerce") < 0).sum()),
                "Negative persons, pensions or contribution values are not accepted",
            )
        )
        rows.append(
            _row(
                "INPS",
                "missing year",
                "warning",
                int(inps["year"].isna().sum()),
                "Some historical tables may not repeat the year in each row",
            )
        )

    if rgs is not None and not rgs.empty:
        key_columns = [
            column
            for column in ("projection_vintage", "year", "scenario", "indicator")
            if column in rgs
        ]
        rows.append(
            _row(
                "RGS",
                "duplicate projection keys",
                "error",
                int(rgs.duplicated(key_columns, keep=False).sum()) if key_columns else 0,
                ", ".join(key_columns),
            )
        )
        if {"lower_bound", "upper_bound", "value"}.issubset(rgs.columns):
            invalid = (
                rgs["lower_bound"].notna()
                & rgs["upper_bound"].notna()
                & (
                    (rgs["lower_bound"] > rgs["value"])
                    | (rgs["upper_bound"] < rgs["value"])
                    | (rgs["lower_bound"] > rgs["upper_bound"])
                )
            )
            rows.append(
                _row(
                    "RGS",
                    "projection interval consistency",
                    "error",
                    int(invalid.sum()),
                    "lower_bound <= value <= upper_bound",
                )
            )

    balances = internal_migration_balances
    if balances is not None and not balances.empty:
        national = balances.groupby("year", as_index=False)["internal_balance"].sum()
        failures = int(national["internal_balance"].abs().gt(0.5).sum())
        rows.append(
            _row(
                "ISTAT",
                "internal migration conservation",
                "error",
                failures,
                "National sum of territorial internal balances must be zero",
            )
        )

    return pd.DataFrame(rows)
