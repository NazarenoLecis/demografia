from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.pipeline import pipeline_options, run_pipeline
from demografia.config import EU27_ISO2, EU_OECD_ISO3, ITALY_NUTS2
from demografia.utils import print_outputs


# Configurazione per VS Code.
# Aprire questo file, modificare i valori se necessario e usare "Run Python File".
START_YEAR = 1990
END_YEAR = 2024
PROJECTION_END = 2050
REFRESH = False
INCLUDE_MIGRATION = True
INCLUDE_REGIONAL = True
INCLUDE_WORLD_BANK = False
AUTO_WPP = False
WPP_AGE_SEX: Path | None = None
WPP_URL: str | None = None
WPP_SCALE = 1000.0
ISTAT_POPULATION_DATAFLOW: str | None = None
ISTAT_KEY = "all"
MAKE_ANIMATION = False
EU_GEOS = EU27_ISO2
REGIONAL_GEOS = ITALY_NUTS2
MIGRATION_GEOS = ("IT",)
COMPARISON_COUNTRIES = EU_OECD_ISO3
PROJECTION_SCENARIO: str | None = "BSL"
GENERATE_ALL_COUNTRY_KEBABS = False


def main(
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
    projection_end: int = PROJECTION_END,
    refresh: bool = REFRESH,
    include_migration: bool = INCLUDE_MIGRATION,
    include_regional: bool = INCLUDE_REGIONAL,
    include_world_bank: bool = INCLUDE_WORLD_BANK,
    auto_wpp: bool = AUTO_WPP,
    wpp_age_sex: Path | None = WPP_AGE_SEX,
    wpp_url: str | None = WPP_URL,
    wpp_scale: float = WPP_SCALE,
    istat_population_dataflow: str | None = ISTAT_POPULATION_DATAFLOW,
    istat_key: str = ISTAT_KEY,
    make_animation: bool = MAKE_ANIMATION,
    eu_geos: tuple[str, ...] = EU_GEOS,
    regional_geos: tuple[str, ...] = REGIONAL_GEOS,
    migration_geos: tuple[str, ...] = MIGRATION_GEOS,
    comparison_countries: tuple[str, ...] = COMPARISON_COUNTRIES,
    projection_scenario: str | None = PROJECTION_SCENARIO,
    generate_all_country_kebabs: bool = GENERATE_ALL_COUNTRY_KEBABS,
) -> dict[str, Path]:
    """Run the international demographic pipeline.

    Parameters are explicit so the script can be imported by notebooks, tests,
    or a VS Code launch configuration without relying on command-line parsing.
    """
    options = pipeline_options(
        start_year=start_year,
        end_year=end_year,
        projection_end=projection_end,
        refresh=refresh,
        include_migration=include_migration,
        include_regional=include_regional,
        include_world_bank=include_world_bank,
        auto_wpp=auto_wpp,
        wpp_age_sex=wpp_age_sex,
        wpp_url=wpp_url,
        wpp_scale=wpp_scale,
        istat_population_dataflow=istat_population_dataflow,
        istat_key=istat_key,
        make_animation=make_animation,
        eu_geos=eu_geos,
        regional_geos=regional_geos,
        migration_geos=migration_geos,
        comparison_countries=comparison_countries,
        projection_scenario=projection_scenario,
        generate_all_country_kebabs=generate_all_country_kebabs,
    )
    return run_pipeline(options)


if __name__ == "__main__":
    print_outputs(main())
