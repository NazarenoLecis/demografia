from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from demografia.config import EU27_ISO3, OECD38_ISO3


def coverage_report(population: pd.DataFrame, comparison_panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if not population.empty:
        observed = population[population["status"].eq("observed")]
        projected = population[population["status"].eq("projected")]
        latest = observed.groupby("iso3")["year"].max()
        for iso3 in EU27_ISO3:
            subset = observed[observed["iso3"].eq(iso3)]
            latest_year = latest.get(iso3)
            latest_subset = subset[subset["year"].eq(latest_year)] if pd.notna(latest_year) else subset.iloc[0:0]
            projected_subset = projected[projected["iso3"].eq(iso3)]
            rows.append(
                {
                    "scope": "EU27 age-sex",
                    "iso3": iso3,
                    "available": not latest_subset.empty,
                    "latest_year": latest_year,
                    "male_rows": int(latest_subset["sex"].eq("M").sum()),
                    "female_rows": int(latest_subset["sex"].eq("F").sum()),
                    "projection_available": not projected_subset.empty,
                    "projection_last_year": projected_subset["year"].max()
                    if not projected_subset.empty
                    else None,
                    "scenario_count": projected_subset["scenario"].nunique()
                    if not projected_subset.empty
                    else 0,
                }
            )
    if not comparison_panel.empty:
        for iso3 in OECD38_ISO3:
            subset = comparison_panel[comparison_panel["iso3"].eq(iso3)]
            rows.append(
                {
                    "scope": "OECD indicators",
                    "iso3": iso3,
                    "available": not subset.empty,
                    "latest_year": subset["year"].max() if not subset.empty else None,
                    "male_rows": None,
                    "female_rows": None,
                    "projection_available": None,
                    "projection_last_year": None,
                    "scenario_count": None,
                }
            )
    return pd.DataFrame(rows)


def validate_population(population: pd.DataFrame) -> pd.DataFrame:
    issues: list[dict[str, object]] = []
    if population.empty:
        return pd.DataFrame(
            [
                {
                    "severity": "error",
                    "check": "population_empty",
                    "rows": 0,
                    "details": "Tabella popolazione vuota",
                }
            ]
        )

    required = {"iso3", "year", "age_low", "age_high", "sex", "value", "status", "scenario", "source"}
    missing = sorted(required.difference(population.columns))
    if missing:
        issues.append(
            {
                "severity": "error",
                "check": "missing_columns",
                "rows": len(missing),
                "details": ", ".join(missing),
            }
        )
        return pd.DataFrame(issues)

    key = ["iso3", "year", "age_low", "age_high", "sex", "status", "scenario", "source"]
    duplicates = population.duplicated(key, keep=False)
    if duplicates.any():
        issues.append(
            {
                "severity": "error",
                "check": "duplicate_keys",
                "rows": int(duplicates.sum()),
                "details": "Chiavi demografiche duplicate",
            }
        )

    values = pd.to_numeric(population["value"], errors="coerce")
    negative = values.lt(0)
    if negative.any():
        issues.append(
            {
                "severity": "error",
                "check": "negative_population",
                "rows": int(negative.sum()),
                "details": "Valori di popolazione negativi",
            }
        )

    nonfinite = ~np.isfinite(values)
    if nonfinite.any():
        issues.append(
            {
                "severity": "error",
                "check": "non_finite_values",
                "rows": int(nonfinite.sum()),
                "details": "Valori mancanti o non finiti",
            }
        )

    invalid_age = population["age_low"].lt(0) | population["age_high"].lt(population["age_low"])
    if invalid_age.any():
        issues.append(
            {
                "severity": "error",
                "check": "invalid_age_intervals",
                "rows": int(invalid_age.sum()),
                "details": "Intervalli di età non validi",
            }
        )

    invalid_sex = ~population["sex"].isin(["M", "F"])
    if invalid_sex.any():
        issues.append(
            {
                "severity": "warning",
                "check": "unexpected_sex_codes",
                "rows": int(invalid_sex.sum()),
                "details": "Codici sesso diversi da M/F",
            }
        )

    group_columns = ["iso3", "year", "status", "scenario", "source"]
    sex_counts = population[population["sex"].isin(["M", "F"])].groupby(group_columns)["sex"].nunique()
    missing_sex_groups = int(sex_counts.lt(2).sum())
    if missing_sex_groups:
        issues.append(
            {
                "severity": "warning",
                "check": "incomplete_sex_coverage",
                "rows": missing_sex_groups,
                "details": "Gruppi senza entrambi i sessi",
            }
        )

    overlap_keys = ["iso3", "year", "age_low", "age_high", "sex"]
    status_counts = population.groupby(overlap_keys)["status"].nunique()
    overlap = int(status_counts.gt(1).sum())
    if overlap:
        issues.append(
            {
                "severity": "warning",
                "check": "observed_projected_overlap",
                "rows": overlap,
                "details": "Anni/celle presenti come osservati e proiettati",
            }
        )

    projected = population[population["status"].eq("projected")]
    missing_scenario = projected["scenario"].isna() | projected["scenario"].astype(str).str.strip().eq("")
    if missing_scenario.any():
        issues.append(
            {
                "severity": "error",
                "check": "missing_projection_scenario",
                "rows": int(missing_scenario.sum()),
                "details": "Proiezioni senza scenario",
            }
        )

    if not issues:
        issues.append(
            {
                "severity": "ok",
                "check": "population_integrity",
                "rows": 0,
                "details": "Nessuna anomalia rilevata",
            }
        )
    return pd.DataFrame(issues)


def validate_demographic_balance(balance: pd.DataFrame, tolerance: float = 1.0) -> pd.DataFrame:
    if balance.empty:
        return pd.DataFrame(
            [
                {
                    "severity": "warning",
                    "check": "balance_empty",
                    "rows": 0,
                    "details": "Bilancio demografico non disponibile",
                }
            ]
        )
    issues: list[dict[str, object]] = []
    if "balance_identity_residual" in balance:
        residual = pd.to_numeric(balance["balance_identity_residual"], errors="coerce").abs()
        failed = residual.gt(tolerance)
        if failed.any():
            issues.append(
                {
                    "severity": "warning",
                    "check": "demographic_balance_identity",
                    "rows": int(failed.sum()),
                    "details": f"Residuo assoluto superiore a {tolerance:g}",
                }
            )
    if not issues:
        issues.append(
            {
                "severity": "ok",
                "check": "demographic_balance_integrity",
                "rows": 0,
                "details": "Identità verificata dove calcolabile",
            }
        )
    return pd.DataFrame(issues)


def build_quality_report(population: pd.DataFrame, balance: pd.DataFrame | None = None) -> pd.DataFrame:
    reports = [validate_population(population)]
    if balance is not None:
        reports.append(validate_demographic_balance(balance))
    return pd.concat(reports, ignore_index=True)


def write_quality_markdown(report: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Controlli di qualità", "", f"Controlli eseguiti: {len(report)}", ""]
    if report.empty:
        lines.append("Nessun controllo disponibile.")
    else:
        lines.extend(["| Severità | Controllo | Righe | Dettagli |", "|---|---|---:|---|"])
        for row in report.itertuples(index=False):
            details = str(row.details).replace("|", "\\|")
            lines.append(f"| {row.severity} | {row.check} | {row.rows} | {details} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
