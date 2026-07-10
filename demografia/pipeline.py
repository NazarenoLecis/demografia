from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from demografia.charts import animate_population_pyramid, plot_cohort_heatmap, plot_population_pyramid
from demografia.config import CHART_DIR, EU27_ISO2, EU27_ISO3, EU_OECD_ISO3, FINAL_DIR, OECD38_ISO3, RAW_DIR, ensure_directories
from demografia.indicators import add_group_benchmarks, compute_age_structure
from demografia.quality import coverage_report
from demografia.sources.eurostat import EurostatClient
from demografia.sources.world_bank import WorldBankClient
from demografia.sources.istat import IstatClient
from demografia.sources.wpp import normalize_wpp_age_sex, read_wpp
from demografia.territory import compute_territorial_age_structure, normalize_istat_population
from demografia.transform import combine_population, normalize_eurostat_population, select_baseline_projection


@dataclass
class PipelineOptions:
    start_year: int = 1960
    end_year: int = 2026
    projection_end: int = 2100
    refresh: bool = False
    include_migration: bool = False
    wpp_age_sex: Path | None = None
    wpp_scale: float = 1000.0
    istat_population_dataflow: str | None = None
    istat_key: str = "all"
    make_animation: bool = False


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
        geos=EU27_ISO2,
        start_year=options.start_year,
        end_year=options.end_year,
    )
    _save(eu_observed_raw, RAW_DIR / "eurostat_population_age_sex.parquet")

    eu_projection_raw = eurostat.projections(
        geos=EU27_ISO2,
        start_year=max(2022, options.end_year - 5),
        end_year=options.projection_end,
    )
    _save(eu_projection_raw, RAW_DIR / "eurostat_population_projections.parquet")

    fertility = eurostat.fertility(start_year=options.start_year)
    balance = eurostat.demographic_balance(start_year=options.start_year)
    _save(fertility, RAW_DIR / "eurostat_fertility.parquet")
    _save(balance, RAW_DIR / "eurostat_demographic_balance.parquet")

    if options.include_migration:
        immigration = eurostat.migration_flows("immigration_profile", start_year=2008, end_year=options.end_year)
        emigration = eurostat.migration_flows("emigration_profile", start_year=2008, end_year=options.end_year)
        citizenship = eurostat.migrant_stock("population_citizenship", start_year=2000)
        birth_country = eurostat.migrant_stock("population_birth_country", start_year=2000)
        _save(immigration, RAW_DIR / "eurostat_immigration_profile.parquet")
        _save(emigration, RAW_DIR / "eurostat_emigration_profile.parquet")
        _save(citizenship, RAW_DIR / "eurostat_population_by_citizenship.parquet")
        _save(birth_country, RAW_DIR / "eurostat_population_by_birth_country.parquet")

    observed = normalize_eurostat_population(eu_observed_raw, projected=False)
    projected = select_baseline_projection(normalize_eurostat_population(eu_projection_raw, projected=True))
    population = combine_population(observed, projected)

    if options.wpp_age_sex is not None:
        wpp = normalize_wpp_age_sex(read_wpp(options.wpp_age_sex), value_scale=options.wpp_scale)
        wpp = wpp[wpp["iso3"].isin(OECD38_ISO3)]
        population = combine_population(population, wpp)
        _save(wpp, RAW_DIR / "wpp_oecd_age_sex.parquet")

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

    _save(population, FINAL_DIR / "population_age_sex_observed_projected.parquet")
    outputs["population"] = FINAL_DIR / "population_age_sex_observed_projected.parquet"

    structure = compute_age_structure(population)
    _save(structure, FINAL_DIR / "age_structure_indicators.parquet")
    outputs["age_structure"] = FINAL_DIR / "age_structure_indicators.parquet"

    comparison_panel = world_bank.panel(
        countries=EU_OECD_ISO3,
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

    italian = population[population["iso3"].eq("ITA")]
    observed_years = sorted(italian.loc[italian["status"].eq("observed"), "year"].dropna().astype(int).unique())
    projected_years = sorted(italian.loc[italian["status"].eq("projected"), "year"].dropna().astype(int).unique())
    chart_years = []
    if observed_years:
        chart_years.extend([observed_years[0], observed_years[-1]])
    chart_years.extend([year for year in (2030, 2050, 2080, 2100) if year in projected_years])
    for year in dict.fromkeys(chart_years):
        output = CHART_DIR / f"piramide_italia_{year}.png"
        plot_population_pyramid(population, "ITA", year, output)
        outputs[f"pyramid_{year}"] = output
    if not italian.empty:
        heatmap = CHART_DIR / "coorti_italia.png"
        plot_cohort_heatmap(population, "ITA", heatmap)
        outputs["cohort_heatmap"] = heatmap
    if options.make_animation and observed_years:
        years = observed_years[:: max(1, len(observed_years) // 40)]
        animation = CHART_DIR / "piramide_italia_storica.gif"
        animate_population_pyramid(population, "ITA", years, animation)
        outputs["animation"] = animation

    return outputs
