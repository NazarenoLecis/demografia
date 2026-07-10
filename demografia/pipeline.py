from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from demografia.charts import animate_population_pyramid, plot_cohort_heatmap, plot_population_pyramid
from demografia.config import (
    CHART_DIR,
    EU27_ISO2,
    EU27_ISO3,
    EU_OECD_ISO3,
    FINAL_DIR,
    INPUT_DIR,
    OECD38_ISO3,
    RAW_DIR,
    ensure_directories,
)
from demografia.final_tables import (
    build_demographic_balance_wide,
    build_migration_summary,
    enrich_population_schema,
    normalize_eurostat_demographic_balance,
    normalize_eurostat_fertility,
    normalize_eurostat_migration,
    normalize_migrant_stock,
    projection_inventory,
)
from demografia.indicators import add_group_benchmarks, compute_age_structure
from demografia.quality import build_quality_report, coverage_report, write_quality_markdown
from demografia.sources.eurostat import EurostatClient
from demografia.sources.istat import IstatClient
from demografia.sources.world_bank import WorldBankClient
from demografia.sources.wpp import normalize_wpp_age_sex, read_wpp
from demografia.territory import compute_territorial_age_structure, normalize_istat_population
from demografia.transform import combine_population, normalize_eurostat_population
from demografia.wpp_auto import download_wpp_age_sex


@dataclass
class PipelineOptions:
    start_year: int = 1960
    end_year: int = 2026
    projection_end: int = 2100
    refresh: bool = False
    include_migration: bool = False
    auto_wpp: bool = False
    wpp_age_sex: Path | None = None
    wpp_url: str | None = None
    wpp_scale: float = 1000.0
    istat_population_dataflow: str | None = None
    istat_key: str = "all"
    make_animation: bool = False
    eu_geos: tuple[str, ...] = EU27_ISO2
    comparison_countries: tuple[str, ...] = EU_OECD_ISO3
    projection_scenario: str | None = None
    generate_all_country_pyramids: bool = False


def _save(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    frame.to_csv(path.with_suffix(".csv"), index=False)


def run_pipeline(options: PipelineOptions) -> dict[str, Path]:
    ensure_directories()
    eurostat = EurostatClient(refresh=options.refresh)
    world_bank = WorldBankClient(refresh=options.refresh)
    outputs: dict[str, Path] = {}

    eu_observed_raw = eurostat.population_age_sex(
        geos=options.eu_geos,
        start_year=options.start_year,
        end_year=options.end_year,
    )
    _save(eu_observed_raw, RAW_DIR / "eurostat_population_age_sex.parquet")

    eu_projection_raw = eurostat.projections(
        geos=options.eu_geos,
        start_year=max(2022, options.end_year - 5),
        end_year=options.projection_end,
        scenario=options.projection_scenario,
    )
    _save(eu_projection_raw, RAW_DIR / "eurostat_population_projections.parquet")

    fertility_raw = eurostat.fertility(geos=options.eu_geos, start_year=options.start_year)
    balance_raw = eurostat.demographic_balance(geos=options.eu_geos, start_year=options.start_year)
    _save(fertility_raw, RAW_DIR / "eurostat_fertility.parquet")
    _save(balance_raw, RAW_DIR / "eurostat_demographic_balance.parquet")

    fertility = normalize_eurostat_fertility(fertility_raw)
    balance_long = normalize_eurostat_demographic_balance(balance_raw)
    balance_wide = build_demographic_balance_wide(balance_long)
    _save(fertility, FINAL_DIR / "fertility_indicators.parquet")
    _save(balance_long, FINAL_DIR / "demographic_balance_long.parquet")
    _save(balance_wide, FINAL_DIR / "demographic_balance.parquet")
    outputs["fertility"] = FINAL_DIR / "fertility_indicators.parquet"
    outputs["demographic_balance"] = FINAL_DIR / "demographic_balance.parquet"

    if options.include_migration:
        immigration_raw = eurostat.migration_flows(
            "immigration_profile",
            geos=options.eu_geos,
            start_year=2008,
            end_year=options.end_year,
        )
        emigration_raw = eurostat.migration_flows(
            "emigration_profile",
            geos=options.eu_geos,
            start_year=2008,
            end_year=options.end_year,
        )
        citizenship_raw = eurostat.migrant_stock(
            "population_citizenship",
            geos=options.eu_geos,
            start_year=2000,
        )
        birth_country_raw = eurostat.migrant_stock(
            "population_birth_country",
            geos=options.eu_geos,
            start_year=2000,
        )
        _save(immigration_raw, RAW_DIR / "eurostat_immigration_profile.parquet")
        _save(emigration_raw, RAW_DIR / "eurostat_emigration_profile.parquet")
        _save(citizenship_raw, RAW_DIR / "eurostat_population_by_citizenship.parquet")
        _save(birth_country_raw, RAW_DIR / "eurostat_population_by_birth_country.parquet")

        immigration = normalize_eurostat_migration(immigration_raw, "immigration")
        emigration = normalize_eurostat_migration(emigration_raw, "emigration")
        migration_summary = build_migration_summary(immigration, emigration)
        citizenship = normalize_migrant_stock(citizenship_raw, "citizenship")
        birth_country = normalize_migrant_stock(birth_country_raw, "country_of_birth")
        _save(immigration, FINAL_DIR / "immigration_profile.parquet")
        _save(emigration, FINAL_DIR / "emigration_profile.parquet")
        _save(migration_summary, FINAL_DIR / "migration_summary.parquet")
        _save(citizenship, FINAL_DIR / "population_by_citizenship.parquet")
        _save(birth_country, FINAL_DIR / "population_by_country_of_birth.parquet")
        outputs["migration_summary"] = FINAL_DIR / "migration_summary.parquet"

    observed = normalize_eurostat_population(eu_observed_raw, projected=False)
    projected = normalize_eurostat_population(eu_projection_raw, projected=True)
    population = combine_population(observed, projected)

    wpp_path = options.wpp_age_sex
    if options.auto_wpp and wpp_path is None:
        wpp_path = download_wpp_age_sex(
            INPUT_DIR / "wpp",
            refresh=options.refresh,
            url=options.wpp_url,
        )
    if wpp_path is not None:
        wpp = normalize_wpp_age_sex(read_wpp(wpp_path), value_scale=options.wpp_scale)
        wpp = wpp[wpp["iso3"].isin(OECD38_ISO3) & ~wpp["iso3"].isin(EU27_ISO3)]
        population = combine_population(population, wpp)
        _save(wpp, RAW_DIR / "wpp_oecd_extra_eu_age_sex.parquet")
        outputs["wpp_oecd_age_sex"] = RAW_DIR / "wpp_oecd_extra_eu_age_sex.parquet"

    if options.istat_population_dataflow is not None:
        istat_raw = IstatClient().csv(
            options.istat_population_dataflow,
            key=options.istat_key,
            start_period=options.start_year,
            end_period=options.end_year,
        )
        _save(istat_raw, RAW_DIR / "istat_population_territorial_raw.parquet")
        istat_population = normalize_istat_population(istat_raw)
        _save(istat_population, FINAL_DIR / "italy_population_age_sex_territorial.parquet")
        territorial_structure = compute_territorial_age_structure(istat_population)
        _save(territorial_structure, FINAL_DIR / "italy_territorial_age_structure.parquet")
        outputs["italy_territorial_population"] = FINAL_DIR / "italy_population_age_sex_territorial.parquet"
        outputs["italy_territorial_structure"] = FINAL_DIR / "italy_territorial_age_structure.parquet"

    population = enrich_population_schema(population)
    _save(population, FINAL_DIR / "population_age_sex_observed_projected.parquet")
    outputs["population"] = FINAL_DIR / "population_age_sex_observed_projected.parquet"

    structure = compute_age_structure(population)
    _save(structure, FINAL_DIR / "age_structure_indicators.parquet")
    outputs["age_structure"] = FINAL_DIR / "age_structure_indicators.parquet"

    inventory = projection_inventory(population)
    _save(inventory, FINAL_DIR / "projection_inventory.parquet")
    outputs["projection_inventory"] = FINAL_DIR / "projection_inventory.parquet"

    comparison_panel = world_bank.panel(
        countries=options.comparison_countries,
        start_year=options.start_year,
        end_year=options.end_year,
    )
    comparison_panel = add_group_benchmarks(
        comparison_panel,
        {"EU27_MEDIAN": EU27_ISO3, "OECD38_MEDIAN": OECD38_ISO3},
    )
    _save(comparison_panel, FINAL_DIR / "international_demographic_indicators.parquet")
    _save(
        comparison_panel[comparison_panel["iso3"].isin((*OECD38_ISO3, "OECD38_MEDIAN"))],
        FINAL_DIR / "oecd_demographic_indicators.parquet",
    )
    outputs["international_panel"] = FINAL_DIR / "international_demographic_indicators.parquet"
    outputs["oecd_panel"] = FINAL_DIR / "oecd_demographic_indicators.parquet"

    coverage = coverage_report(population, comparison_panel)
    _save(coverage, FINAL_DIR / "coverage_report.parquet")
    outputs["coverage"] = FINAL_DIR / "coverage_report.parquet"

    quality = build_quality_report(population, balance_wide)
    _save(quality, FINAL_DIR / "quality_report.parquet")
    quality_markdown = write_quality_markdown(quality, FINAL_DIR / "quality_report.md")
    outputs["quality"] = FINAL_DIR / "quality_report.parquet"
    outputs["quality_markdown"] = quality_markdown

    chart_countries = (
        tuple(sorted(set(population["iso3"])))
        if options.generate_all_country_pyramids
        else ("ITA",)
    )
    for iso3 in chart_countries:
        country = population[population["iso3"].eq(iso3)]
        observed_years = sorted(
            country.loc[country["status"].eq("observed"), "year"].dropna().astype(int).unique()
        )
        projected_years = sorted(
            country.loc[country["status"].eq("projected"), "year"].dropna().astype(int).unique()
        )
        chart_years: list[int] = []
        if observed_years:
            chart_years.extend([observed_years[0], observed_years[-1]])
        chart_years.extend([year for year in (2030, 2050, 2080, 2100) if year in projected_years])
        for year in dict.fromkeys(chart_years):
            output = CHART_DIR / f"piramide_{iso3.lower()}_{year}.png"
            plot_population_pyramid(population, iso3, year, output)
            outputs[f"pyramid_{iso3}_{year}"] = output
        if not country.empty:
            heatmap = CHART_DIR / f"coorti_{iso3.lower()}.png"
            plot_cohort_heatmap(population, iso3, heatmap)
            outputs[f"cohort_heatmap_{iso3}"] = heatmap
        if options.make_animation and observed_years:
            years = observed_years[:: max(1, len(observed_years) // 40)]
            animation = CHART_DIR / f"piramide_{iso3.lower()}_storica.gif"
            animate_population_pyramid(population, iso3, years, animation)
            outputs[f"animation_{iso3}"] = animation

    return outputs
