from __future__ import annotations

import json
from dataclasses import dataclass, field
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
from demografia.pipeline import PipelineOptions, run_pipeline
from demografia.rgs import build_rgs_projection_panel, normalize_rgs_projection, projection_vintage_year
from demografia.sources.inps import InpsClient, read_inps_resource
from demografia.sources.istat import IstatClient
from demografia.sources.rgs import RgsClient, read_rgs_resource
from demografia.territory import compute_territorial_age_structure, normalize_istat_population


@dataclass
class OfficialPipelineOptions:
    base: PipelineOptions = field(default_factory=PipelineOptions)
    include_istat: bool = True
    include_inps: bool = True
    include_rgs: bool = True
    strict: bool = False
    istat_overrides: dict[str, str] = field(default_factory=dict)
    istat_key: str = "all"
    inps_page_size: int = 100
    inps_max_pages: int | None = 30
    inps_datasets_per_role: int = 2
    rgs_queries: tuple[str, ...] = (
        "pensioni",
        "sistema pensionistico",
        "medio lungo periodo",
        "spesa sanitaria",
        "long term care",
    )
    rgs_resources_per_query: int = 2


def _save(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    frame.to_csv(path.with_suffix(".csv"), index=False)
    return path


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




def _run_istat(options: OfficialPipelineOptions, status_rows: list[dict[str, Any]]) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    client = IstatClient()
    registry = build_istat_registry(client)
    outputs["istat_registry"] = _save(registry, FINAL_DIR / "istat_demographic_dataflows.parquet")

    for role in ROLE_RULES:
        try:
            dataflow_id, name, ambiguous = _select_istat_dataflow(
                registry,
                role,
                options.istat_overrides,
            )
            raw = client.csv(
                dataflow_id,
                key=options.istat_key,
                start_period=options.base.start_year,
                end_period=(
                    options.base.projection_end
                    if role == "population_projections"
                    else options.base.end_year
                ),
            )
            raw_path = RAW_DIR / f"istat_{role}_{dataflow_id}.parquet"
            _save(raw, raw_path)

            if role == "population_age_sex":
                normalized = normalize_istat_population(raw)
                output = _save(normalized, FINAL_DIR / "italy_population_age_sex_territorial.parquet")
                structure = compute_territorial_age_structure(normalized)
                outputs["istat_territorial_structure"] = _save(
                    structure,
                    FINAL_DIR / "italy_territorial_age_structure.parquet",
                )
            elif role == "internal_migration":
                normalized = normalize_internal_migration(raw, dataset=dataflow_id)
                output = _save(normalized, FINAL_DIR / "italy_internal_migration_flows.parquet")
                balances = internal_migration_balances(normalized)
                profiles = internal_migration_profiles(normalized)
                outputs["istat_internal_migration_balances"] = _save(
                    balances,
                    FINAL_DIR / "italy_internal_migration_balances.parquet",
                )
                outputs["istat_internal_migration_profiles"] = _save(
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
                output = _save(normalized, FINAL_DIR / "italy_population_projections.parquet")
            else:
                normalized = normalize_istat_indicator_table(raw, role=role, dataset=dataflow_id)
                output = _save(normalized, FINAL_DIR / f"italy_{role}.parquet")
            outputs[f"istat_{role}"] = output
            note = "selection ambiguous: top-ranked dataflow used" if ambiguous else ""
            _status(status_rows, "ISTAT", role, "ok", note, f"{dataflow_id} - {name}", len(normalized))
        except Exception as exc:
            _status(status_rows, "ISTAT", role, "error", f"{type(exc).__name__}: {exc}")
            if options.strict:
                raise
    return outputs


def _run_inps(options: OfficialPipelineOptions, status_rows: list[dict[str, Any]]) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    client = InpsClient(refresh=options.base.refresh)
    status = client.status()
    (FINAL_DIR / "inps_api_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    catalog = client.catalog_frame(
        page_size=options.inps_page_size,
        max_pages=options.inps_max_pages,
    )
    outputs["inps_catalog"] = _save(catalog, FINAL_DIR / "inps_catalog.parquet")
    matches = discover_inps_roles(catalog, max_per_role=options.inps_datasets_per_role)
    matches = client.select_resources(matches, one_per_dataset=True)
    outputs["inps_role_catalog"] = _save(matches, FINAL_DIR / "inps_demographic_datasets.parquet")
    if matches.empty:
        message = "Nessuna risorsa demografico-previdenziale selezionata dal catalogo INPS"
        _status(status_rows, "INPS", "catalog", "error", message)
        if options.strict:
            raise LookupError(message)

    observations: list[pd.DataFrame] = []
    for row in matches.to_dict("records"):
        role = str(row.get("role", "inps_observation"))
        dataset_id = str(row.get("dataset_id", ""))
        try:
            path = client.download_resource(row, INPUT_DIR / "inps")
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
            if options.strict:
                raise
    combined = pd.concat(observations, ignore_index=True, sort=False) if observations else pd.DataFrame()
    outputs["inps_observations"] = _save(combined, FINAL_DIR / "inps_demographic_observations.parquet")
    support = build_inps_support_indicators(combined)
    outputs["inps_support"] = _save(support, FINAL_DIR / "inps_support_indicators.parquet")
    return outputs


def _run_rgs(options: OfficialPipelineOptions, status_rows: list[dict[str, Any]]) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    client = RgsClient(refresh=options.base.refresh)
    catalog = client.search_frame(options.rgs_queries)
    outputs["rgs_catalog"] = _save(catalog, FINAL_DIR / "rgs_projection_catalog.parquet")
    selected = client.select_resources(catalog, one_per_package=True)
    if not selected.empty:
        selected = selected.groupby("query", group_keys=False).head(options.rgs_resources_per_query)
    outputs["rgs_selected_resources"] = _save(
        selected,
        FINAL_DIR / "rgs_selected_projection_resources.parquet",
    )
    if selected.empty:
        message = "Nessuna risorsa di proiezione selezionata dal catalogo OpenBDAP/RGS"
        _status(status_rows, "RGS", "catalog", "error", message)
        if options.strict:
            raise LookupError(message)

    projections: list[pd.DataFrame] = []
    for row in selected.to_dict("records"):
        package_id = str(row.get("package_id", ""))
        try:
            path = client.download_resource(row, INPUT_DIR / "rgs")
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
            if options.strict:
                raise
    combined = pd.concat(projections, ignore_index=True, sort=False) if projections else pd.DataFrame()
    outputs["rgs_projections"] = _save(combined, FINAL_DIR / "rgs_long_term_projections.parquet")
    panel = build_rgs_projection_panel(combined)
    outputs["rgs_projection_panel"] = _save(panel, FINAL_DIR / "rgs_long_term_projection_panel.parquet")
    return outputs


def run_official_pipeline(options: OfficialPipelineOptions) -> dict[str, Path]:
    ensure_directories()
    outputs = run_pipeline(options.base)
    status_rows: list[dict[str, Any]] = []

    if options.include_istat:
        try:
            outputs.update(_run_istat(options, status_rows))
        except Exception as exc:
            _status(status_rows, "ISTAT", "pipeline", "error", f"{type(exc).__name__}: {exc}")
            if options.strict:
                raise
    if options.include_inps:
        try:
            outputs.update(_run_inps(options, status_rows))
        except Exception as exc:
            _status(status_rows, "INPS", "pipeline", "error", f"{type(exc).__name__}: {exc}")
            if options.strict:
                raise
    if options.include_rgs:
        try:
            outputs.update(_run_rgs(options, status_rows))
        except Exception as exc:
            _status(status_rows, "RGS", "pipeline", "error", f"{type(exc).__name__}: {exc}")
            if options.strict:
                raise

    age_structure = pd.read_parquet(FINAL_DIR / "age_structure_indicators.parquet")
    inps_support_path = FINAL_DIR / "inps_support_indicators.parquet"
    rgs_panel_path = FINAL_DIR / "rgs_long_term_projection_panel.parquet"
    inps_support = pd.read_parquet(inps_support_path) if inps_support_path.exists() else pd.DataFrame()
    rgs_panel = pd.read_parquet(rgs_panel_path) if rgs_panel_path.exists() else pd.DataFrame()
    integrated = build_italy_demographic_fiscal_panel(age_structure, inps_support, rgs_panel)
    outputs["italy_integrated_panel"] = _save(
        integrated,
        FINAL_DIR / "italy_demographic_pension_fiscal_panel.parquet",
    )

    status_frame = pd.DataFrame(status_rows)
    outputs["official_source_status"] = _save(
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
    outputs["official_quality"] = _save(
        official_quality,
        FINAL_DIR / "official_quality_report.parquet",
    )
    if options.strict and not status_frame.empty and status_frame["status"].eq("error").any():
        errors = status_frame[status_frame["status"].eq("error")]
        raise RuntimeError(errors.to_string(index=False))
    return outputs
