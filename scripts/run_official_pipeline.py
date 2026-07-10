from __future__ import annotations

import argparse
from pathlib import Path

from demografia.official_pipeline import OfficialPipelineOptions, run_official_pipeline
from demografia.pipeline import PipelineOptions


def _overrides(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        role, separator, dataflow = value.partition("=")
        if not separator or not role.strip() or not dataflow.strip():
            raise argparse.ArgumentTypeError("Gli override ISTAT devono avere forma ruolo=dataflow")
        result[role.strip()] = dataflow.strip()
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Esegue la pipeline completa con ISTAT, INPS, RGS, Eurostat, OECD e WPP"
    )
    parser.add_argument("--start-year", type=int, default=1960)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--projection-end", type=int, default=2100)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--include-migration", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--auto-wpp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--wpp-age-sex", type=Path)
    parser.add_argument("--wpp-url")
    parser.add_argument("--wpp-scale", type=float, default=1000.0)
    parser.add_argument("--make-animation", action="store_true")
    parser.add_argument("--all-country-pyramids", action="store_true")
    parser.add_argument("--no-istat", action="store_true")
    parser.add_argument("--no-inps", action="store_true")
    parser.add_argument("--no-rgs", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--istat-key", default="all")
    parser.add_argument("--istat-override", action="append", default=[])
    parser.add_argument("--inps-max-pages", type=int, default=30)
    parser.add_argument("--inps-datasets-per-role", type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    base = PipelineOptions(
        start_year=args.start_year,
        end_year=args.end_year,
        projection_end=args.projection_end,
        refresh=args.refresh,
        include_migration=args.include_migration,
        auto_wpp=args.auto_wpp,
        wpp_age_sex=args.wpp_age_sex,
        wpp_url=args.wpp_url,
        wpp_scale=args.wpp_scale,
        make_animation=args.make_animation,
        generate_all_country_pyramids=args.all_country_pyramids,
    )
    outputs = run_official_pipeline(
        OfficialPipelineOptions(
            base=base,
            include_istat=not args.no_istat,
            include_inps=not args.no_inps,
            include_rgs=not args.no_rgs,
            strict=args.strict,
            istat_overrides=_overrides(args.istat_override),
            istat_key=args.istat_key,
            inps_max_pages=args.inps_max_pages,
            inps_datasets_per_role=args.inps_datasets_per_role,
        )
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
