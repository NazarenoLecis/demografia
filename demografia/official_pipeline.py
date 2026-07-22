from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from demografia.config import FINAL_DIR, INPUT_DIR, RAW_DIR, ensure_directories
from demografia.inps import build_inps_support_indicators, discover_inps_roles, normalize_inps_table
from demografia.integration import build_italy_demographic_fiscal_panel
from demografia.internal_migration import (
    internal_migration_balances,
    internal_migration_matrix,
    internal_migration_profiles,
    normalize_internal_migration,
)
from demografia.istat_official import normalize_istat_indicator_table, normalize_istat_projection
from demografia.istat_registry import ROLE_RULES, build_istat_registry
from demografia.official_quality import build_official_quality_report
from demografia.pipeline import pipeline_options, run_pipeline
from demografia.rgs import build_rgs_projection_panel, normalize_rgs_projection, projection_vintage_year
from demografia.sources import inps, istat, rgs
from demografia.sources.inps import read_inps_resource
from demografia.sources.rgs import read_rgs_resource
from demografia.territory import compute_territorial_age_structure, normalize_istat_population
from demografia.utils import save_table


DEFAULT_RGS_QUERIES = (
    "pensioni",
    "sistema pensionistico",
    "medio lungo periodo",
    "spesa sanitaria",
    "long term care",
)


def official_pipeline_options(
    base: Mapping[str, Any] | None = None,
    include_istat: bool = True,
    include_inps: bool = True,
    include_rgs: bool = True,
    strict: bool = False,
    istat_overrides: Mapping[str, str] | None = None,
    istat_key: str = "all",
    inps_page_size: int = 100,
    inps_max_pages: int | None = 30,
    inps_datasets_per_role: int = 2,
    rgs_queries: tuple[str, ...] = DEFAULT_RGS_QUERIES,
    rgs_resources_per_query: int = 2,
) -> dict[str, Any]:
    """Build the configuration used by the official-source pipeline.

    A plain dictionary keeps the pipeline serializable and easy to modify from
    notebooks or from a VS Code run configuration.
    """
    return {
        "base": pipeline_options(**dict(base or {})),
        "include_istat": include_istat,
        "include_inps": include_inps,
        "include_rgs": include_rgs,
        "strict": strict,
        "istat_overrides": dict(istat_overrides or {}),
        "istat_key": istat_key,
        "inps_page_size": inps_page_size,
        "inps_max_pages": inps_max_pages,
        "inps_datasets_per_role": inps_datasets_per_role,
        "rgs_queries": tuple(rgs_queries),
        "rgs_resources_per_query": rgs_resources_per_query,
    }


def _status(
    rows: list[dict[str, Any]],
    source: str,
    role: str,
    status: str,
    message: str = "",
    dataset: str = "",
    rows_count: int | None = None,
) -> None:
    rows.append(
        {
            "source": source,
            "role": role,
            "status": status,
            "dataset": dataset,
            "rows": rows_count,
            "message": message,
        }
    )


def _select_istat_dataflow(
    registry: pd.DataFrame,
    role: str,
    overrides: dict[str, str],
) -> tuple[str, str, bool]:
    """Choose the ISTAT dataflow for one semantic role.

    Overrides are useful when the public registry contains several plausible
    dataflows and a project wants a stable, explicit mapping.
    """
    if role in overrides:
        dataflow_id = overrides[role]
        row = registry[registry["dataflow_id"].astype(str).eq(str(dataflow_id))]
        name = str(row.iloc[0]["name"]) if not row.empty else "manual override"
        return str(dataflow_id), name, False
    selected = registry[registry["role"].eq(role) & registry["selected"]].copy()
    if selected.empty:
        raise LookupError(f"Nessun dataflow ISTAT individuato per {role}")
    selected = selected.sort_values(["score", "version", "dataflow_id"], ascending=[False, False, True])
    row = selected.iloc[0]
    return str(row["dataflow_id"]), str(row["name"]), bool(row["ambiguous"])




def _run_istat(options: Mapping[str, Any], status_rows: list[dict[str, Any]]) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    base = options["base"]

    # The registry is rebuilt from the official SDMX catalog and scored against
    # role rules such as population, births, deaths, migration, and projections.
    registry = build_istat_registry()
    outputs["istat_registry"] = save_table(registry, FINAL_DIR / "istat_demographic_dataflows.parquet")

    for role in ROLE_RULES:
        try:
            dataflow_id, name, ambiguous = _select_istat_dataflow(
                registry,
                role,
                options["istat_overrides"],
            )
            raw = istat.csv(
                dataflow_id,
                key=options["istat_key"],
                start_period=base["start_year"],
                end_period=(
                    base["projection_end"]
                    if role == "population_projections"
                    else base["end_year"]
                ),
            )
            raw_path = RAW_DIR / f"istat_{role}_{dataflow_id}.parquet"
            save_table(raw, raw_path)

            if role == "population_age_sex":
                normalized = normalize_istat_population(raw)
                output = save_table(normalized, FINAL_DIR / "italy_population_age_sex_territorial.parquet")
                structure = compute_territorial_age_structure(normalized)
                outputs["istat_territorial_structure"] = save_table(
                    structure,
                    FINAL_DIR / "italy_territorial_age_structure.parquet",
                )
            elif role == "internal_migration":
                normalized = normalize_internal_migration(raw, dataset=dataflow_id)
                output = save_table(normalized, FINAL_DIR / "italy_internal_migration_flows.parquet")
                balances = internal_migration_balances(normalized)
                profiles = internal_migration_profiles(normalized)
                outputs["istat_internal_migration_balances"] = save_table(
                    balances,
                    FINAL_DIR / "italy_internal_migration_balances.parquet",
                )
                outputs["istat_internal_migration_profiles"] = save_table(
                    profiles,
                    FINAL_DIR / "italy_internal_migration_profiles.parquet",
                )
                years = normalized["year"].dropna().astype(int)
                if not years.empty:
                    latest_year = int(years.max())
                    matrix = internal_migration_matrix(normalized, latest_year)
                    matrix_path = FINAL_DIR / f"italy_internal_migration_matrix_{latest_year}.csv"
                    matrix.to_csv(matrix_path)
                    outputs["istat_internal_migration_matrix"] = matrix_path
            elif role == "population_projections":
                normalized = normalize_istat_projection(raw, dataflow_id)
                output = save_table(normalized, FINAL_DIR / "italy_population_projections.parquet")
            else:
                normalized = normalize_istat_indicator_table(raw, role=role, dataset=dataflow_id)
                output = save_table(normalized, FINAL_DIR / f"italy_{role}.parquet")
            outputs[f"istat_{role}"] = output
            note = "selection ambiguous: top-ranked dataflow used" if ambiguous else ""
            _status(status_rows, "ISTAT", role, "ok", note, f"{dataflow_id} - {name}", len(normalized))
        except Exception as exc:
            _status(status_rows, "ISTAT", role, "error", f"{type(exc).__name__}: {exc}")
            if options["strict"]:
                raise
    return outputs


def _run_inps(options: Mapping[str, Any], status_rows: list[dict[str, Any]]) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    refresh = options["base"]["refresh"]

    # INPS exposes a CKAN-like open-data catalog. The pipeline discovers
    # demographic-previdential datasets, selects usable resources, and normalizes
    # people, pension, contributor, insured-worker, and retirement-flow tables.
    status = inps.status(refresh=refresh)
    (FINAL_DIR / "inps_api_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    catalog = inps.catalog_frame(
        page_size=options["inps_page_size"],
        max_pages=options["inps_max_pages"],
        refresh=refresh,
    )
    outputs["inps_catalog"] = save_table(catalog, FINAL_DIR / "inps_catalog.parquet")
    matches = discover_inps_roles(catalog, max_per_role=options["inps_datasets_per_role"])
    matches = inps.select_resources(matches, one_per_dataset=True)
    outputs["inps_role_catalog"] = save_table(matches, FINAL_DIR / "inps_demographic_datasets.parquet")
    if matches.empty:
        message = "Nessuna risorsa demografico-previdenziale selezionata dal catalogo INPS"
        _status(status_rows, "INPS", "catalog", "error", message)
        if options["strict"]:
            raise LookupError(message)

    observations: list[pd.DataFrame] = []
    for row in matches.to_dict("records"):
        role = str(row.get("role", "inps_observation"))
        dataset_id = str(row.get("dataset_id", ""))
        try:
            path = inps.download_resource(row, INPUT_DIR / "inps", refresh=refresh)
            frame = read_inps_resource(path)
            normalized = normalize_inps_table(
                frame,
                dataset_id=dataset_id,
                dataset_title=str(row.get("title", "")),
                role=role,
            )
            observations.append(normalized)
            _status(status_rows, "INPS", role, "ok", dataset=dataset_id, rows_count=len(normalized))
        except Exception as exc:
            _status(
                status_rows,
                "INPS",
                role,
                "error",
                f"{type(exc).__name__}: {exc}",
                dataset_id,
            )
            if options["strict"]:
                raise
    combined = pd.concat(observations, ignore_index=True, sort=False) if observations else pd.DataFrame()
    outputs["inps_observations"] = save_table(combined, FINAL_DIR / "inps_demographic_observations.parquet")
    support = build_inps_support_indicators(combined)
    outputs["inps_support"] = save_table(support, FINAL_DIR / "inps_support_indicators.parquet")
    return outputs


def _run_rgs(options: Mapping[str, Any], status_rows: list[dict[str, Any]]) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    refresh = options["base"]["refresh"]

    # RGS/OpenBDAP resources are discovered by thematic queries because the
    # catalog contains multiple package names for long-term public-finance series.
    catalog = rgs.search_frame(options["rgs_queries"], refresh=refresh)
    outputs["rgs_catalog"] = save_table(catalog, FINAL_DIR / "rgs_projection_catalog.parquet")
    selected = rgs.select_resources(catalog, one_per_package=True)
    if not selected.empty:
        selected = selected.groupby("query", group_keys=False).head(options["rgs_resources_per_query"])
    outputs["rgs_selected_resources"] = save_table(
        selected,
        FINAL_DIR / "rgs_selected_projection_resources.parquet",
    )
    if selected.empty:
        message = "Nessuna risorsa di proiezione selezionata dal catalogo OpenBDAP/RGS"
        _status(status_rows, "RGS", "catalog", "error", message)
        if options["strict"]:
            raise LookupError(message)

    projections: list[pd.DataFrame] = []
    for row in selected.to_dict("records"):
        package_id = str(row.get("package_id", ""))
        try:
            path = rgs.download_resource(row, INPUT_DIR / "rgs", refresh=refresh)
            frame = read_rgs_resource(path)
            normalized = normalize_rgs_projection(
                frame,
                dataset=str(row.get("title") or row.get("name") or package_id),
                source_url=str(row.get("url", "")),
                vintage=projection_vintage_year(row.get("metadata_modified")),
            )
            projections.append(normalized)
            _status(
                status_rows,
                "RGS",
                str(row.get("query", "projection")),
                "ok",
                dataset=package_id,
                rows_count=len(normalized),
            )
        except Exception as exc:
            _status(
                status_rows,
                "RGS",
                str(row.get("query", "projection")),
                "error",
                f"{type(exc).__name__}: {exc}",
                package_id,
            )
            if options["strict"]:
                raise
    combined = pd.concat(projections, ignore_index=True, sort=False) if projections else pd.DataFrame()
    outputs["rgs_projections"] = save_table(combined, FINAL_DIR / "rgs_long_term_projections.parquet")
    panel = build_rgs_projection_panel(combined)
    outputs["rgs_projection_panel"] = save_table(panel, FINAL_DIR / "rgs_long_term_projection_panel.parquet")
    return outputs


def run_official_pipeline(options: Mapping[str, Any] | None = None) -> dict[str, Path]:
    """Run the base pipeline plus official Italian source integrations."""
    ensure_directories()
    options = official_pipeline_options(**dict(options or {}))
    outputs = run_pipeline(options["base"])
    status_rows: list[dict[str, Any]] = []

    if options["include_istat"]:
        try:
            outputs.update(_run_istat(options, status_rows))
        except Exception as exc:
            _status(status_rows, "ISTAT", "pipeline", "error", f"{type(exc).__name__}: {exc}")
            if options["strict"]:
                raise
    if options["include_inps"]:
        try:
            outputs.update(_run_inps(options, status_rows))
        except Exception as exc:
            _status(status_rows, "INPS", "pipeline", "error", f"{type(exc).__name__}: {exc}")
            if options["strict"]:
                raise
    if options["include_rgs"]:
        try:
            outputs.update(_run_rgs(options, status_rows))
        except Exception as exc:
            _status(status_rows, "RGS", "pipeline", "error", f"{type(exc).__name__}: {exc}")
            if options["strict"]:
                raise

    age_structure = pd.read_parquet(FINAL_DIR / "age_structure_indicators.parquet")
    inps_support_path = FINAL_DIR / "inps_support_indicators.parquet"
    rgs_panel_path = FINAL_DIR / "rgs_long_term_projection_panel.parquet"
    inps_support = pd.read_parquet(inps_support_path) if inps_support_path.exists() else pd.DataFrame()
    rgs_panel = pd.read_parquet(rgs_panel_path) if rgs_panel_path.exists() else pd.DataFrame()
    integrated = build_italy_demographic_fiscal_panel(age_structure, inps_support, rgs_panel)
    outputs["italy_integrated_panel"] = save_table(
        integrated,
        FINAL_DIR / "italy_demographic_pension_fiscal_panel.parquet",
    )

    status_frame = pd.DataFrame(status_rows)
    outputs["official_source_status"] = save_table(
        status_frame,
        FINAL_DIR / "official_source_status.parquet",
    )

    inps_observations_path = FINAL_DIR / "inps_demographic_observations.parquet"
    rgs_projections_path = FINAL_DIR / "rgs_long_term_projections.parquet"
    internal_balances_path = FINAL_DIR / "italy_internal_migration_balances.parquet"
    official_quality = build_official_quality_report(
        inps=(pd.read_parquet(inps_observations_path) if inps_observations_path.exists() else None),
        rgs=(pd.read_parquet(rgs_projections_path) if rgs_projections_path.exists() else None),
        internal_migration_balances=(
            pd.read_parquet(internal_balances_path) if internal_balances_path.exists() else None
        ),
    )
    outputs["official_quality"] = save_table(
        official_quality,
        FINAL_DIR / "official_quality_report.parquet",
    )
    if options["strict"] and not status_frame.empty and status_frame["status"].eq("error").any():
        errors = status_frame[status_frame["status"].eq("error")]
        raise RuntimeError(errors.to_string(index=False))
    return outputs
