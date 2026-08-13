from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.pipeline import pipeline_options, run_pipeline
from demografia.config import (
    EU27_ISO3,
    EU_OECD_ISO3,
    ITALY_NUTS2,
    MIGRANT_EDUCATION_AGE_GROUPS,
    MIGRANT_EDUCATION_BIRTH_GROUPS,
    MIGRANT_EDUCATION_LEVELS,
    MIGRANT_STOCK_AGE_GROUPS,
    MIGRATION_FLOW_AGE_GROUPS,
    MIGRATION_FLOW_CITIZENSHIP_GROUPS,
)
from demografia.utils import print_outputs


# Configurazione modificabile da VS Code con "Run Python File".
# Codici paese: usare ISO3, per esempio "ITA" Italia, "ESP" Spagna.
# Codici territoriali italiani: usare NUTS, per esempio "ITC4" Lombardia, "ITC4C" Milano.
START_YEAR = 1960  # Primo anno osservato da scaricare.
END_YEAR = 2024  # Ultimo anno osservato da scaricare.
PROJECTION_END = 2050  # Ultimo anno delle proiezioni demografiche.
REFRESH = False  # True forza un nuovo download ignorando la cache locale.
INCLUDE_MIGRATION = True  # True include stock e flussi migratori.
INCLUDE_REGIONAL = True  # True include regioni NUTS2 e province NUTS3 italiane.
INCLUDE_WORLD_BANK = False  # True aggiunge indicatori World Bank per confronti extra-UE.
AUTO_WPP = False  # True scarica automaticamente il file UN WPP se configurato.
WPP_AGE_SEX: Path | None = None  # Percorso locale opzionale del file UN WPP per eta e sesso.
WPP_URL: str | None = None  # URL opzionale del file UN WPP.
WPP_SCALE = 1000.0  # Fattore di scala dei valori WPP quando la fonte e in migliaia.
ISTAT_POPULATION_DATAFLOW: str | None = None  # Dataflow ISTAT opzionale per popolazione territoriale.
ISTAT_KEY = "all"  # Chiave ISTAT: "all" scarica tutte le combinazioni disponibili.
MAKE_ANIMATION = False  # True crea anche la GIF del Kebab.
EU_GEOS = EU27_ISO3  # Paesi da scaricare da Eurostat, in ISO3.
REGIONAL_COUNTRY_PREFIX = "ITA"  # Paese per dati regionali Eurostat; "ITA" significa Italia.
REGIONAL_LEVELS = ("nuts2", "nuts3")  # nuts2 regioni, nuts3 province.
REGIONAL_GEOS: tuple[str, ...] | None = None  # None include tutti; esempio selezione: ("ITC4", "ITI4").
MIGRATION_GEOS = EU27_ISO3  # Paesi dei dati migratori, in ISO3.
MIGRATION_CITIZENSHIP_AGES = MIGRATION_FLOW_AGE_GROUPS  # Classi eta Eurostat dei flussi migratori.
MIGRATION_CITIZENSHIP_GROUPS = MIGRATION_FLOW_CITIZENSHIP_GROUPS  # Gruppi cittadinanza Eurostat.
IMMIGRANT_POPULATION_AGES = MIGRANT_STOCK_AGE_GROUPS  # Classi eta per stock nati all'estero.
IMMIGRANT_POPULATION_CATEGORY = "FOR"  # "FOR" indica residenti nati all'estero.
MIGRANT_EDUCATION_GEOS_SELECTED = ("ITA", *ITALY_NUTS2)  # Italia e regioni NUTS2 per istruzione migranti.
MIGRANT_EDUCATION_AGES = MIGRANT_EDUCATION_AGE_GROUPS  # Fasce eta LFS disponibili.
MIGRANT_EDUCATION_BIRTH_GROUPS_SELECTED = MIGRANT_EDUCATION_BIRTH_GROUPS  # NAT, FOR, UE27, extra UE27.
MIGRANT_EDUCATION_LEVELS_SELECTED = MIGRANT_EDUCATION_LEVELS  # Livelli ISCED della fonte.
COMPARISON_COUNTRIES = EU_OECD_ISO3  # Paesi per confronti estesi, in ISO3.
PROJECTION_SCENARIO: str | None = "BSL"  # Scenario Eurostat: "BSL" e lo scenario baseline.
GENERATE_ALL_COUNTRY_KEBABS = False  # True genera un Kebab per ogni paese disponibile.


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
    regional_country_prefix: str = REGIONAL_COUNTRY_PREFIX,
    regional_levels: tuple[str, ...] = REGIONAL_LEVELS,
    regional_geos: tuple[str, ...] | None = REGIONAL_GEOS,
    migration_geos: tuple[str, ...] = MIGRATION_GEOS,
    migration_citizenship_ages: tuple[str, ...] = MIGRATION_CITIZENSHIP_AGES,
    migration_citizenship_groups: tuple[str, ...] = MIGRATION_CITIZENSHIP_GROUPS,
    immigrant_population_ages: tuple[str, ...] = IMMIGRANT_POPULATION_AGES,
    immigrant_population_category: str = IMMIGRANT_POPULATION_CATEGORY,
    migrant_education_geos: tuple[str, ...] = MIGRANT_EDUCATION_GEOS_SELECTED,
    migrant_education_ages: tuple[str, ...] = MIGRANT_EDUCATION_AGES,
    migrant_education_birth_groups: tuple[str, ...] = MIGRANT_EDUCATION_BIRTH_GROUPS_SELECTED,
    migrant_education_levels: tuple[str, ...] = MIGRANT_EDUCATION_LEVELS_SELECTED,
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
        regional_country_prefix=regional_country_prefix,
        regional_levels=regional_levels,
        regional_geos=regional_geos,
        migration_geos=migration_geos,
        migration_citizenship_ages=migration_citizenship_ages,
        migration_citizenship_groups=migration_citizenship_groups,
        immigrant_population_ages=immigrant_population_ages,
        immigrant_population_category=immigrant_population_category,
        migrant_education_geos=migrant_education_geos,
        migrant_education_ages=migrant_education_ages,
        migrant_education_birth_groups=migrant_education_birth_groups,
        migrant_education_levels=migrant_education_levels,
        comparison_countries=comparison_countries,
        projection_scenario=projection_scenario,
        generate_all_country_kebabs=generate_all_country_kebabs,
    )
    return run_pipeline(options)


if __name__ == "__main__":
    print_outputs(main())
