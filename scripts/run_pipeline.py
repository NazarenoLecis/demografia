from __future__ import annotations

import argparse
from pathlib import Path

from demografia.config import EU27_ISO2, EU_OECD_ISO3
from demografia.pipeline import PipelineOptions, run_pipeline


def _codes(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(code.strip().upper() for code in value.split(",") if code.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Esegue la pipeline demografica completa")
    parser.add_argument("--start-year", type=int, default=1960)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--projection-end", type=int, default=2100)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--include-migration", action="store_true")
    parser.add_argument("--wpp-age-sex", type=Path)
    parser.add_argument(
        "--wpp-scale",
        type=float,
        default=1000.0,
        help="Moltiplicatore dei valori WPP",
    )
    parser.add_argument(
        "--istat-population-dataflow",
        help="ID del dataflow ISTAT per territorio, età e sesso",
    )
    parser.add_argument("--istat-key", default="all", help="Chiave SDMX ISTAT")
    parser.add_argument("--make-animation", action="store_true")
    parser.add_argument("--eu-geos", help="Codici Eurostat separati da virgola; default UE27")
    parser.add_argument(
        "--comparison-countries",
        help="Codici ISO3 separati da virgola; default unione UE-OECD",
    )
    parser.add_argument(
        "--projection-scenario",
        help="Codice scenario Eurostat; omesso conserva tutti gli scenari",
    )
    parser.add_argument("--generate-all-country-pyramids", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    outputs = run_pipeline(
        PipelineOptions(
            start_year=args.start_year,
            end_year=args.end_year,
            projection_end=args.projection_end,
            refresh=args.refresh,
            include_migration=args.include_migration,
            wpp_age_sex=args.wpp_age_sex,
            wpp_scale=args.wpp_scale,
            istat_population_dataflow=args.istat_population_dataflow,
            istat_key=args.istat_key,
            make_animation=args.make_animation,
            eu_geos=_codes(args.eu_geos, EU27_ISO2),
            comparison_countries=_codes(args.comparison_countries, EU_OECD_ISO3),
            projection_scenario=args.projection_scenario,
            generate_all_country_pyramids=args.generate_all_country_pyramids,
        )
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
