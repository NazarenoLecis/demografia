from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from demografia.official_pipeline import official_pipeline_options, run_official_pipeline
from demografia.pipeline import pipeline_options
from demografia.utils import print_outputs


# Configurazione modificabile da VS Code con "Run Python File".
# Codici paese: usare ISO3, per esempio "ITA" Italia, "ESP" Spagna.
START_YEAR = 2020  # Primo anno osservato da scaricare.
END_YEAR = 2024  # Ultimo anno osservato da scaricare.
PROJECTION_END = 2030  # Ultimo anno delle proiezioni demografiche.
REFRESH = False  # True forza un nuovo download ignorando la cache locale.
INCLUDE_MIGRATION = True  # True include stock e flussi migratori.
AUTO_WPP = False  # True scarica automaticamente il file UN WPP se configurato.
WPP_AGE_SEX: Path | None = None  # Percorso locale opzionale del file UN WPP per eta e sesso.
WPP_URL: str | None = None  # URL opzionale del file UN WPP.
WPP_SCALE = 1000.0  # Fattore di scala dei valori WPP quando la fonte e in migliaia.
MAKE_ANIMATION = False  # True crea anche la GIF del Kebab.
GENERATE_ALL_COUNTRY_KEBABS = False  # True genera un Kebab per ogni paese disponibile.
EU_GEOS = ("ITA",)  # Paesi da scaricare da Eurostat, in ISO3.
COMPARISON_COUNTRIES = ("ITA",)  # Paesi per confronti estesi, in ISO3.
PROJECTION_SCENARIO: str | None = "BSL"  # Scenario Eurostat: "BSL" e lo scenario baseline.

INCLUDE_ISTAT = True  # True include fonti ISTAT quando disponibili.
INCLUDE_INPS = True  # True include fonti INPS quando disponibili.
INCLUDE_RGS = True  # True include fonti RGS/OpenBDAP quando disponibili.
STRICT = False  # True interrompe la pipeline se una fonte opzionale fallisce.
ISTAT_OVERRIDES: dict[str, str] = {}  # Mappa opzionale ruolo ISTAT -> dataflow ufficiale.
ISTAT_KEY = "all"  # Chiave ISTAT: "all" scarica tutte le combinazioni disponibili.
INPS_MAX_PAGES: int | None = 30  # Numero massimo di pagine per ricerca INPS; None non limita.
INPS_DATASETS_PER_ROLE = 2  # Numero massimo di dataset INPS selezionati per ruolo.


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
