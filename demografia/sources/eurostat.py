from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from demografia.config import (
    CACHE_DIR,
    EDUCATION_ATTAINMENT_AGE_GROUPS,
    EU27_ISO2,
    EUROSTAT_DATASETS,
    ITALY_NUTS2,
)
from demografia.http import get_json
from demografia.jsonstat import jsonstat_to_frame
from demografia.utils import chunks

EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


def fetch(
    dataset: str,
    filters: Mapping[str, str | int | Iterable[str | int]] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    filters = dict(filters or {})
    geos = filters.pop("geo", None)
    geo_values = (
        list(geos)
        if geos is not None and not isinstance(geos, str)
        else [geos]
        if geos
        else [None]
    )
    frames: list[pd.DataFrame] = []

    geo_chunks = chunks([geo for geo in geo_values if geo is not None], chunk_size) if geos else [[None]]
    for geo_chunk in geo_chunks:
        params: list[tuple[str, Any]] = [("lang", "en")]
        if start_year is not None:
            params.append(("sinceTimePeriod", start_year))
        if end_year is not None:
            params.append(("untilTimePeriod", end_year))
        if geos:
            params.extend(("geo", geo) for geo in geo_chunk)
        for key, raw_values in filters.items():
            if isinstance(raw_values, (str, int)):
                params.append((key, raw_values))
            else:
                params.extend((key, value) for value in raw_values)

        payload = get_json(
            f"{EUROSTAT_API}/{dataset}",
            params=params,
            cache_dir=CACHE_DIR / "eurostat" / dataset,
            refresh=refresh,
        )
        if isinstance(payload, dict) and "error" in payload and "id" not in payload:
            continue
        frame = jsonstat_to_frame(payload)
        if not frame.empty:
            frame["dataset"] = dataset
            frame["source"] = "Eurostat"
            frames.append(frame)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def territorial_geos(
    country_prefix: str = "IT",
    levels: Iterable[str] = ("nuts2", "nuts3"),
    reference_year: int | None = None,
    refresh: bool = False,
) -> tuple[str, ...]:
    """Return Eurostat NUTS codes for one country and one or more levels.

    Eurostat regional tables evolve when territorial boundaries are updated.
    This helper discovers the available geography codes from the demographic
    balance table instead of storing a long static list. `country_prefix`
    selects the country code prefix, while `levels` accepts Eurostat values
    such as `nuts2` and `nuts3`. When `reference_year` is provided, the lookup
    is restricted to that year so the returned geographies match the latest
    period used by the analytical pipeline.
    """
    discovered: list[str] = []
    for level in levels:
        frame = fetch(
            EUROSTAT_DATASETS["regional_demographic_balance"],
            filters={"geoLevel": level},
            start_year=reference_year,
            end_year=reference_year,
            refresh=refresh,
            chunk_size=100,
        )
        if frame.empty or "geo" not in frame:
            continue
        for code in frame["geo"].dropna().astype(str).drop_duplicates():
            if code.startswith(country_prefix):
                discovered.append(code)
    return tuple(dict.fromkeys(discovered))


def population_age_sex(
    geos: Iterable[str] = EU27_ISO2,
    start_year: int = 1960,
    end_year: int | None = None,
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    return fetch(
        EUROSTAT_DATASETS["population_age_sex"],
        filters={"geo": tuple(geos), "sex": ("M", "F"), "unit": "NR"},
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def projections(
    geos: Iterable[str] = EU27_ISO2,
    start_year: int = 2022,
    end_year: int = 2100,
    scenario: str | None = None,
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    filters: dict[str, object] = {
        "geo": tuple(geos),
        "sex": ("M", "F"),
        "unit": "PER",
    }
    if scenario is not None:
        filters["projection"] = scenario
    return fetch(
        EUROSTAT_DATASETS["projections"],
        filters=filters,
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def fertility(
    geos: Iterable[str] = EU27_ISO2,
    start_year: int = 1960,
    end_year: int | None = None,
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    return fetch(
        EUROSTAT_DATASETS["fertility"],
        filters={"geo": tuple(geos)},
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def demographic_balance(
    geos: Iterable[str] = EU27_ISO2,
    start_year: int = 1960,
    end_year: int | None = None,
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    return fetch(
        EUROSTAT_DATASETS["demographic_balance"],
        filters={"geo": tuple(geos)},
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def life_expectancy(
    geos: Iterable[str] = EU27_ISO2,
    start_year: int = 1960,
    end_year: int | None = None,
    ages: Iterable[str] = ("Y_LT1", "Y65"),
    sexes: Iterable[str] = ("T", "M", "F"),
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    """Fetch period life expectancy at birth and at age 65.

    Eurostat `demo_mlexpec` stores life expectancy by sex and reference age.
    The default age codes keep the two measures most useful for this project:
    `Y_LT1`, read as life expectancy at birth, and `Y65`, read as remaining
    life expectancy for people who have reached age 65.
    """
    return fetch(
        EUROSTAT_DATASETS["life_expectancy"],
        filters={"geo": tuple(geos), "age": tuple(ages), "sex": tuple(sexes), "unit": "YR"},
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def regional_population_age_groups(
    geos: Iterable[str] = ITALY_NUTS2,
    start_year: int = 1990,
    end_year: int | None = None,
    refresh: bool = False,
    chunk_size: int = 30,
) -> pd.DataFrame:
    """Fetch NUTS2 population by five-year age group and sex."""
    return fetch(
        EUROSTAT_DATASETS["regional_population_age_groups"],
        filters={"geo": tuple(geos), "sex": ("T", "M", "F"), "unit": "NR"},
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def regional_demographic_balance(
    geos: Iterable[str] = ITALY_NUTS2,
    start_year: int = 1990,
    end_year: int | None = None,
    refresh: bool = False,
    chunk_size: int = 30,
) -> pd.DataFrame:
    """Fetch NUTS2 or NUTS3 demographic balance indicators."""
    return fetch(
        EUROSTAT_DATASETS["regional_demographic_balance"],
        filters={"geo": tuple(geos)},
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def regional_fertility(
    geos: Iterable[str] = ITALY_NUTS2,
    start_year: int = 1990,
    end_year: int | None = None,
    refresh: bool = False,
    chunk_size: int = 30,
) -> pd.DataFrame:
    """Fetch NUTS2 or NUTS3 fertility indicators."""
    return fetch(
        EUROSTAT_DATASETS["regional_fertility"],
        filters={"geo": tuple(geos)},
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def education_attainment(
    geos: Iterable[str] = EU27_ISO2,
    start_year: int = 1960,
    end_year: int | None = None,
    ages: Iterable[str] = EDUCATION_ATTAINMENT_AGE_GROUPS,
    sexes: Iterable[str] = ("T", "M", "F"),
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    """Fetch population distribution by educational attainment level.

    Eurostat `edat_lfse_03` reports percentages by ISCED 2011 group, sex, age
    group, geography, and year.
    """
    return fetch(
        EUROSTAT_DATASETS["education_attainment"],
        filters={"geo": tuple(geos), "sex": tuple(sexes), "unit": "PC", "age": tuple(ages)},
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def migration_flows(
    kind: str,
    geos: Iterable[str] = EU27_ISO2,
    start_year: int = 2008,
    end_year: int | None = None,
    ages: Iterable[str] = ("TOTAL",),
    sexes: Iterable[str] = ("T", "M", "F"),
    age_definition: str = "COMPLET",
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    if kind not in {"immigration_profile", "emigration_profile"}:
        raise ValueError("kind deve essere immigration_profile o emigration_profile")
    return fetch(
        EUROSTAT_DATASETS[kind],
        filters={
            "geo": tuple(geos),
            "unit": "NR",
            "age": tuple(ages),
            "sex": tuple(sexes),
            "agedef": age_definition,
        },
        start_year=start_year,
        end_year=end_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )


def migrant_stock(
    dimension: str,
    geos: Iterable[str] = EU27_ISO2,
    start_year: int = 2000,
    ages: Iterable[str] = ("TOTAL",),
    sexes: Iterable[str] = ("T", "M", "F"),
    categories: Iterable[str] | None = None,
    refresh: bool = False,
    chunk_size: int = 5,
) -> pd.DataFrame:
    if dimension not in {"population_citizenship", "population_birth_country"}:
        raise ValueError("dimension non riconosciuta")
    filters: dict[str, object] = {
        "geo": tuple(geos),
        "unit": "NR",
        "age": tuple(ages),
        "sex": tuple(sexes),
    }
    if categories is not None:
        category_dimension = "citizen" if dimension == "population_citizenship" else "c_birth"
        filters[category_dimension] = tuple(categories)
    return fetch(
        EUROSTAT_DATASETS[dimension],
        filters=filters,
        start_year=start_year,
        refresh=refresh,
        chunk_size=chunk_size,
    )
