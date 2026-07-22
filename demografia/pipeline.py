from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from demografia.charts import animate_population_kebab, plot_cohort_heatmap, plot_population_kebab
from demografia.config import (
    CHART_DIR,
    EU27_ISO2,
    EU27_ISO3,
    EU_OECD_ISO3,
    FINAL_DIR,
    INPUT_DIR,
    MIGRANT_STOCK_AGE_GROUPS,
    OECD38_ISO3,
    RAW_DIR,
    ensure_directories,
)
from demografia.final_tables import (
    build_demographic_balance_wide,
    add_eurostat_geo_metadata,
    build_migration_summary,
    enrich_population_schema,
    normalize_eurostat_demographic_balance,
    normalize_eurostat_education_attainment,
    normalize_eurostat_fertility,
    normalize_eurostat_life_expectancy,
    normalize_eurostat_migration,
    normalize_eurostat_regional_population,
    normalize_migrant_stock,
    projection_inventory,
)
from demografia.indicators import add_group_benchmarks, compute_age_structure
from demografia.quality import build_quality_report, coverage_report, write_quality_markdown
from demografia.sources import eurostat, istat, world_bank
from demografia.sources.wpp import normalize_wpp_age_sex, read_wpp
from demografia.territory import compute_territorial_age_structure, normalize_istat_population
from demografia.transform import combine_population, normalize_eurostat_population
from demografia.utils import save_table
from demografia.wpp_auto import download_wpp_age_sex


DEFAULT_PIPELINE_OPTIONS: dict[str, Any] = {
    "start_year": 1960,
    "end_year": 2026,
    "projection_end": 2100,
    "refresh": False,
    "include_migration": False,
    "include_regional": True,
    "include_world_bank": False,
    "auto_wpp": False,
    "wpp_age_sex": None,
    "wpp_url": None,
    "wpp_scale": 1000.0,
    "istat_population_dataflow": None,
    "istat_key": "all",
    "make_animation": False,
    "eu_geos": EU27_ISO2,
    "regional_country_prefix": "IT",
    "regional_levels": ("nuts2", "nuts3"),
    "regional_geos": None,
    "migration_geos": None,
    "immigrant_population_ages": MIGRANT_STOCK_AGE_GROUPS,
    "immigrant_population_category": "FOR",
    "comparison_countries": EU_OECD_ISO3,
    "projection_scenario": None,
    "generate_all_country_kebabs": False,
}


def pipeline_options(**overrides: Any) -> dict[str, Any]:
    """Create the base pipeline configuration.

    The returned dictionary is intentionally plain: it can be edited in a VS Code
    script, passed from a notebook, serialized, or partially overridden in tests.
    """
    options = DEFAULT_PIPELINE_OPTIONS.copy()
    options.update({key: value for key, value in overrides.items() if value is not None})
    if options["wpp_age_sex"] is not None:
        options["wpp_age_sex"] = Path(options["wpp_age_sex"])
    options["eu_geos"] = tuple(options["eu_geos"])
    options["regional_levels"] = tuple(options["regional_levels"])
    if options["regional_geos"] is not None:
        options["regional_geos"] = tuple(options["regional_geos"])
    options["migration_geos"] = tuple(options["migration_geos"] or options["eu_geos"])
    options["immigrant_population_ages"] = tuple(options["immigrant_population_ages"])
    options["comparison_countries"] = tuple(options["comparison_countries"])
    return options


def run_pipeline(options: Mapping[str, Any] | None = None) -> dict[str, Path]:
    """Run the reproducible demographic data pipeline.

    The pipeline keeps raw downloads, normalized final tables, quality reports,
    and charts in separate folders under `output/`. Each generated analytical
    table is written as both Parquet and CSV through `utils.save_table`.
    """
    ensure_directories()
    options = pipeline_options(**dict(options or {}))
    outputs: dict[str, Path] = {}

    # Eurostat is the harmonized source for EU observed population by age/sex.
    eu_observed_raw = eurostat.population_age_sex(
        geos=options["eu_geos"],
        start_year=options["start_year"],
        end_year=options["end_year"],
        refresh=options["refresh"],
    )
    save_table(eu_observed_raw, RAW_DIR / "eurostat_population_age_sex.parquet")

    # Eurostat projections are kept as projected records rather than mixed with
    # observed data. The final schema preserves status and scenario fields.
    eu_projection_raw = eurostat.projections(
        geos=options["eu_geos"],
        start_year=max(2022, options["end_year"] - 5),
        end_year=options["projection_end"],
        scenario=options["projection_scenario"],
        refresh=options["refresh"],
    )
    save_table(eu_projection_raw, RAW_DIR / "eurostat_population_projections.parquet")

    # Fertility, demographic balance, educational attainment, and life
    # expectancy are normalized into compact tables used for time-series
    # analysis.
    fertility_raw = eurostat.fertility(
        geos=options["eu_geos"],
        start_year=options["start_year"],
        end_year=options["end_year"],
        refresh=options["refresh"],
    )
    balance_raw = eurostat.demographic_balance(
        geos=options["eu_geos"],
        start_year=options["start_year"],
        end_year=options["end_year"],
        refresh=options["refresh"],
    )
    education_raw = eurostat.education_attainment(
        geos=options["eu_geos"],
        start_year=options["start_year"],
        end_year=options["end_year"],
        refresh=options["refresh"],
    )
    life_expectancy_raw = eurostat.life_expectancy(
        geos=options["eu_geos"],
        start_year=options["start_year"],
        end_year=options["end_year"],
        refresh=options["refresh"],
    )
    save_table(fertility_raw, RAW_DIR / "eurostat_fertility.parquet")
    save_table(balance_raw, RAW_DIR / "eurostat_demographic_balance.parquet")
    save_table(education_raw, RAW_DIR / "eurostat_education_attainment.parquet")
    save_table(life_expectancy_raw, RAW_DIR / "eurostat_life_expectancy.parquet")

    fertility = normalize_eurostat_fertility(fertility_raw)
    balance_long = normalize_eurostat_demographic_balance(balance_raw)
    balance_wide = build_demographic_balance_wide(balance_long)
    education = normalize_eurostat_education_attainment(education_raw)
    life_expectancy = normalize_eurostat_life_expectancy(life_expectancy_raw)
    save_table(fertility, FINAL_DIR / "fertility_indicators.parquet")
    save_table(balance_long, FINAL_DIR / "demographic_balance_long.parquet")
    save_table(balance_wide, FINAL_DIR / "demographic_balance.parquet")
    save_table(education, FINAL_DIR / "education_attainment.parquet")
    save_table(life_expectancy, FINAL_DIR / "life_expectancy.parquet")
    outputs["fertility"] = FINAL_DIR / "fertility_indicators.parquet"
    outputs["demographic_balance"] = FINAL_DIR / "demographic_balance.parquet"
    outputs["education_attainment"] = FINAL_DIR / "education_attainment.parquet"
    outputs["life_expectancy"] = FINAL_DIR / "life_expectancy.parquet"

    if options["include_migration"]:
        # Migration outputs stay separated by concept: inflows, outflows, net
        # balance, citizenship stock, and country-of-birth stock.
        migration_start_year = max(2008, options["start_year"])
        stock_start_year = max(2000, options["start_year"])
        immigration_raw = eurostat.migration_flows(
            "immigration_profile",
            geos=options["migration_geos"],
            start_year=migration_start_year,
            end_year=options["end_year"],
            refresh=options["refresh"],
        )
        emigration_raw = eurostat.migration_flows(
            "emigration_profile",
            geos=options["migration_geos"],
            start_year=migration_start_year,
            end_year=options["end_year"],
            refresh=options["refresh"],
        )
        citizenship_raw = eurostat.migrant_stock(
            "population_citizenship",
            geos=options["migration_geos"],
            start_year=stock_start_year,
            refresh=options["refresh"],
        )
        birth_country_raw = eurostat.migrant_stock(
            "population_birth_country",
            geos=options["migration_geos"],
            start_year=stock_start_year,
            refresh=options["refresh"],
        )
        # A Kebab for the immigrant population needs stock, not flows: this
        # table keeps residents born abroad by age and sex. It is intentionally
        # separate from the top-origin stock tables, which stay at total age.
        immigrant_population_raw = eurostat.migrant_stock(
            "population_birth_country",
            geos=options["migration_geos"],
            start_year=stock_start_year,
            ages=options["immigrant_population_ages"],
            sexes=("M", "F"),
            categories=(options["immigrant_population_category"],),
            refresh=options["refresh"],
        )
        save_table(immigration_raw, RAW_DIR / "eurostat_immigration_profile.parquet")
        save_table(emigration_raw, RAW_DIR / "eurostat_emigration_profile.parquet")
        save_table(citizenship_raw, RAW_DIR / "eurostat_population_by_citizenship.parquet")
        save_table(birth_country_raw, RAW_DIR / "eurostat_population_by_birth_country.parquet")
        save_table(immigrant_population_raw, RAW_DIR / "eurostat_immigrant_population_age_sex.parquet")

        immigration = normalize_eurostat_migration(immigration_raw, "immigration")
        emigration = normalize_eurostat_migration(emigration_raw, "emigration")
        migration_summary = build_migration_summary(immigration, emigration)
        citizenship = normalize_migrant_stock(citizenship_raw, "citizenship")
        birth_country = normalize_migrant_stock(birth_country_raw, "country_of_birth")
        immigrant_population = normalize_migrant_stock(immigrant_population_raw, "country_of_birth")
        save_table(immigration, FINAL_DIR / "immigration_profile.parquet")
        save_table(emigration, FINAL_DIR / "emigration_profile.parquet")
        save_table(migration_summary, FINAL_DIR / "migration_summary.parquet")
        save_table(citizenship, FINAL_DIR / "population_by_citizenship.parquet")
        save_table(birth_country, FINAL_DIR / "population_by_country_of_birth.parquet")
        save_table(immigrant_population, FINAL_DIR / "immigrant_population_age_sex.parquet")
        outputs["migration_summary"] = FINAL_DIR / "migration_summary.parquet"
        outputs["immigrant_population_age_sex"] = FINAL_DIR / "immigrant_population_age_sex.parquet"

    # Population rows are standardized before age-structure indicators are
    # calculated. This avoids hiding source/scenario differences downstream.
    observed = normalize_eurostat_population(eu_observed_raw, projected=False)
    projected = normalize_eurostat_population(eu_projection_raw, projected=True)
    population = combine_population(observed, projected)

    wpp_path = options["wpp_age_sex"]
    if options["auto_wpp"] and wpp_path is None:
        # WPP fills OECD countries outside the EU, where Eurostat does not carry
        # the full age-by-sex panel needed for comparisons.
        wpp_path = download_wpp_age_sex(
            INPUT_DIR / "wpp",
            refresh=options["refresh"],
            url=options["wpp_url"],
        )
    if wpp_path is not None:
        wpp = normalize_wpp_age_sex(read_wpp(wpp_path), value_scale=options["wpp_scale"])
        wpp = wpp[wpp["iso3"].isin(OECD38_ISO3) & ~wpp["iso3"].isin(EU27_ISO3)]
        population = combine_population(population, wpp)
        save_table(wpp, RAW_DIR / "wpp_oecd_extra_eu_age_sex.parquet")
        outputs["wpp_oecd_age_sex"] = RAW_DIR / "wpp_oecd_extra_eu_age_sex.parquet"

    if options["istat_population_dataflow"] is not None:
        # Optional ISTAT territorial population gives national, regional,
        # provincial, or municipal detail when a dataflow is supplied.
        istat_raw = istat.csv(
            options["istat_population_dataflow"],
            key=options["istat_key"],
            start_period=options["start_year"],
            end_period=options["end_year"],
        )
        save_table(istat_raw, RAW_DIR / "istat_population_territorial_raw.parquet")
        istat_population = normalize_istat_population(istat_raw)
        save_table(istat_population, FINAL_DIR / "italy_population_age_sex_territorial.parquet")
        territorial_structure = compute_territorial_age_structure(istat_population)
        save_table(territorial_structure, FINAL_DIR / "italy_territorial_age_structure.parquet")
        outputs["italy_territorial_population"] = FINAL_DIR / "italy_population_age_sex_territorial.parquet"
        outputs["italy_territorial_structure"] = FINAL_DIR / "italy_territorial_age_structure.parquet"

    if options["include_regional"]:
        territorial_geos = options["regional_geos"]
        if territorial_geos is None:
            territorial_geos = eurostat.territorial_geos(
                country_prefix=options["regional_country_prefix"],
                levels=options["regional_levels"],
                reference_year=options["end_year"],
                refresh=options["refresh"],
            )
        territorial_geos = tuple(territorial_geos)

        # Eurostat population by age group is published at NUTS2 level in this
        # table. Balance and fertility are available at NUTS3 as well, so they
        # keep the full territorial list discovered above.
        population_geos = tuple(geo for geo in territorial_geos if len(str(geo)) == 4)

        if population_geos:
            regional_population_raw = eurostat.regional_population_age_groups(
                geos=population_geos,
                start_year=options["start_year"],
                end_year=options["end_year"],
                refresh=options["refresh"],
            )
        else:
            regional_population_raw = pd.DataFrame()
        regional_balance_raw = eurostat.regional_demographic_balance(
            geos=territorial_geos,
            start_year=options["start_year"],
            end_year=options["end_year"],
            refresh=options["refresh"],
        )
        regional_fertility_raw = eurostat.regional_fertility(
            geos=territorial_geos,
            start_year=options["start_year"],
            end_year=options["end_year"],
            refresh=options["refresh"],
        )
        save_table(regional_population_raw, RAW_DIR / "eurostat_regional_population_age_groups.parquet")
        save_table(regional_balance_raw, RAW_DIR / "eurostat_regional_demographic_balance.parquet")
        save_table(regional_fertility_raw, RAW_DIR / "eurostat_regional_fertility.parquet")

        regional_population = normalize_eurostat_regional_population(regional_population_raw)
        regional_structure = compute_age_structure(regional_population)
        regional_balance_long = add_eurostat_geo_metadata(
            normalize_eurostat_demographic_balance(regional_balance_raw),
            regional_balance_raw,
        )
        regional_balance = build_demographic_balance_wide(regional_balance_long)
        regional_fertility = add_eurostat_geo_metadata(
            normalize_eurostat_fertility(regional_fertility_raw),
            regional_fertility_raw,
        )
        save_table(regional_population, FINAL_DIR / "italy_regional_population_age_sex.parquet")
        save_table(regional_structure, FINAL_DIR / "italy_regional_age_structure.parquet")
        save_table(regional_balance, FINAL_DIR / "italy_regional_demographic_balance.parquet")
        save_table(regional_fertility, FINAL_DIR / "italy_regional_fertility.parquet")
        outputs["italy_regional_population"] = FINAL_DIR / "italy_regional_population_age_sex.parquet"
        outputs["italy_regional_structure"] = FINAL_DIR / "italy_regional_age_structure.parquet"
        outputs["italy_regional_balance"] = FINAL_DIR / "italy_regional_demographic_balance.parquet"
        outputs["italy_regional_fertility"] = FINAL_DIR / "italy_regional_fertility.parquet"

    population = enrich_population_schema(population)
    save_table(population, FINAL_DIR / "population_age_sex_observed_projected.parquet")
    outputs["population"] = FINAL_DIR / "population_age_sex_observed_projected.parquet"

    structure = compute_age_structure(population)
    save_table(structure, FINAL_DIR / "age_structure_indicators.parquet")
    outputs["age_structure"] = FINAL_DIR / "age_structure_indicators.parquet"

    inventory = projection_inventory(population)
    save_table(inventory, FINAL_DIR / "projection_inventory.parquet")
    outputs["projection_inventory"] = FINAL_DIR / "projection_inventory.parquet"

    # World Bank WDI is optional because harmonized European comparisons can be
    # built directly from the Eurostat tables generated above.
    if options["include_world_bank"]:
        comparison_panel = world_bank.panel(
            countries=options["comparison_countries"],
            start_year=options["start_year"],
            end_year=options["end_year"],
            refresh=options["refresh"],
        )
        comparison_panel = add_group_benchmarks(
            comparison_panel,
            {"EU27_MEDIAN": EU27_ISO3, "OECD38_MEDIAN": OECD38_ISO3},
        )
    else:
        comparison_panel = pd.DataFrame(
            columns=["iso3", "country", "year", "indicator_id", "indicator", "value", "source"]
        )
    save_table(comparison_panel, FINAL_DIR / "international_demographic_indicators.parquet")
    save_table(
        comparison_panel[comparison_panel["iso3"].isin((*OECD38_ISO3, "OECD38_MEDIAN"))],
        FINAL_DIR / "oecd_demographic_indicators.parquet",
    )
    outputs["international_panel"] = FINAL_DIR / "international_demographic_indicators.parquet"
    outputs["oecd_panel"] = FINAL_DIR / "oecd_demographic_indicators.parquet"

    coverage = coverage_report(population, comparison_panel)
    save_table(coverage, FINAL_DIR / "coverage_report.parquet")
    outputs["coverage"] = FINAL_DIR / "coverage_report.parquet"

    quality = build_quality_report(population, balance_wide)
    save_table(quality, FINAL_DIR / "quality_report.parquet")
    quality_markdown = write_quality_markdown(quality, FINAL_DIR / "quality_report.md")
    outputs["quality"] = FINAL_DIR / "quality_report.parquet"
    outputs["quality_markdown"] = quality_markdown

    # Kebab charts are generated after all observed/projected sources are merged
    # so each country receives the best available age-by-sex distribution.
    chart_countries = (
        tuple(sorted(set(population["iso3"])))
        if options["generate_all_country_kebabs"]
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
            output = CHART_DIR / f"kebab_{iso3.lower()}_{year}.png"
            plot_population_kebab(population, iso3, year, output)
            outputs[f"kebab_{iso3}_{year}"] = output
        if not country.empty:
            heatmap = CHART_DIR / f"coorti_{iso3.lower()}.png"
            plot_cohort_heatmap(population, iso3, heatmap)
            outputs[f"cohort_heatmap_{iso3}"] = heatmap
        if options["make_animation"] and observed_years:
            years = observed_years[:: max(1, len(observed_years) // 40)]
            animation = CHART_DIR / f"kebab_{iso3.lower()}_storico.gif"
            animate_population_kebab(population, iso3, years, animation)
            outputs[f"animation_{iso3}"] = animation

    return outputs
