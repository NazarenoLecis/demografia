from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.official_pipeline import official_pipeline_options, run_official_pipeline
from demografia.pipeline import pipeline_options
from demografia.utils import print_outputs


# Configurazione per VS Code.
# Questo script usa tutte le fonti ufficiali disponibili e produce le tabelle finali.
START_YEAR = 2020
END_YEAR = 2024
PROJECTION_END = 2030
REFRESH = False
INCLUDE_MIGRATION = True
AUTO_WPP = False
WPP_AGE_SEX: Path | None = None
WPP_URL: str | None = None
WPP_SCALE = 1000.0
MAKE_ANIMATION = False
GENERATE_ALL_COUNTRY_KEBABS = False
EU_GEOS = ("IT",)
COMPARISON_COUNTRIES = ("ITA",)
PROJECTION_SCENARIO: str | None = "BSL"

INCLUDE_ISTAT = True
INCLUDE_INPS = True
INCLUDE_RGS = True
STRICT = False
ISTAT_OVERRIDES: dict[str, str] = {}
ISTAT_KEY = "all"
INPS_MAX_PAGES: int | None = 30
INPS_DATASETS_PER_ROLE = 2


def main(
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
    projection_end: int = PROJECTION_END,
    refresh: bool = REFRESH,
    include_migration: bool = INCLUDE_MIGRATION,
    auto_wpp: bool = AUTO_WPP,
    wpp_age_sex: Path | None = WPP_AGE_SEX,
    wpp_url: str | None = WPP_URL,
    wpp_scale: float = WPP_SCALE,
    make_animation: bool = MAKE_ANIMATION,
    generate_all_country_kebabs: bool = GENERATE_ALL_COUNTRY_KEBABS,
    eu_geos: tuple[str, ...] = EU_GEOS,
    comparison_countries: tuple[str, ...] = COMPARISON_COUNTRIES,
    projection_scenario: str | None = PROJECTION_SCENARIO,
    include_istat: bool = INCLUDE_ISTAT,
    include_inps: bool = INCLUDE_INPS,
    include_rgs: bool = INCLUDE_RGS,
    strict: bool = STRICT,
    istat_overrides: dict[str, str] | None = None,
    istat_key: str = ISTAT_KEY,
    inps_max_pages: int | None = INPS_MAX_PAGES,
    inps_datasets_per_role: int = INPS_DATASETS_PER_ROLE,
) -> dict[str, Path]:
    """Run the complete official-source pipeline.

    The base block controls common demographic extraction settings. The official
    block enables or disables ISTAT, INPS, and RGS/OpenBDAP integrations.
    """
    base = pipeline_options(
        start_year=start_year,
        end_year=end_year,
        projection_end=projection_end,
        refresh=refresh,
        include_migration=include_migration,
        auto_wpp=auto_wpp,
        wpp_age_sex=wpp_age_sex,
        wpp_url=wpp_url,
        wpp_scale=wpp_scale,
        make_animation=make_animation,
        generate_all_country_kebabs=generate_all_country_kebabs,
        eu_geos=eu_geos,
        comparison_countries=comparison_countries,
        projection_scenario=projection_scenario,
    )
    options = official_pipeline_options(
        base=base,
        include_istat=include_istat,
        include_inps=include_inps,
        include_rgs=include_rgs,
        strict=strict,
        istat_overrides=istat_overrides or ISTAT_OVERRIDES,
        istat_key=istat_key,
        inps_max_pages=inps_max_pages,
        inps_datasets_per_role=inps_datasets_per_role,
    )
    return run_official_pipeline(options)


if __name__ == "__main__":
    print_outputs(main())
