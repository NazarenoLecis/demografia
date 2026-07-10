from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from demografia.config import CACHE_DIR, EU27_ISO2, EUROSTAT_DATASETS
from demografia.http import get_json
from demografia.jsonstat import jsonstat_to_frame

EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


@dataclass
class EurostatClient:
    refresh: bool = False
    chunk_size: int = 5

    def fetch(
        self,
        dataset: str,
        filters: Mapping[str, str | int | Iterable[str | int]] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> pd.DataFrame:
        filters = dict(filters or {})
        geos = filters.pop("geo", None)
        geo_values = list(geos) if geos is not None and not isinstance(geos, str) else [geos] if geos else [None]
        frames: list[pd.DataFrame] = []

        for geo_chunk in _chunks([geo for geo in geo_values if geo is not None], self.chunk_size) if geos else [[None]]:
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
                refresh=self.refresh,
            )
            frame = jsonstat_to_frame(payload)
            if not frame.empty:
                frame["dataset"] = dataset
                frame["source"] = "Eurostat"
                frames.append(frame)

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def population_age_sex(
        self,
        geos: Iterable[str] = EU27_ISO2,
        start_year: int = 1960,
        end_year: int | None = None,
    ) -> pd.DataFrame:
        return self.fetch(
            EUROSTAT_DATASETS["population_age_sex"],
            filters={"geo": tuple(geos), "sex": ("M", "F"), "unit": "NR"},
            start_year=start_year,
            end_year=end_year,
        )

    def projections(
        self,
        geos: Iterable[str] = EU27_ISO2,
        start_year: int = 2022,
        end_year: int = 2100,
    ) -> pd.DataFrame:
        dataset = EUROSTAT_DATASETS["projections"]
        try:
            frame = self.fetch(
                dataset,
                filters={"geo": tuple(geos), "sex": ("M", "F"), "unit": "NR", "projection": "BSL"},
                start_year=start_year,
                end_year=end_year,
            )
            if not frame.empty:
                return frame
        except Exception:
            pass
        return self.fetch(
            dataset,
            filters={"geo": tuple(geos), "sex": ("M", "F"), "unit": "NR"},
            start_year=start_year,
            end_year=end_year,
        )

    def fertility(self, geos: Iterable[str] = EU27_ISO2, start_year: int = 1960) -> pd.DataFrame:
        return self.fetch(
            EUROSTAT_DATASETS["fertility"],
            filters={"geo": tuple(geos)},
            start_year=start_year,
        )

    def demographic_balance(self, geos: Iterable[str] = EU27_ISO2, start_year: int = 1960) -> pd.DataFrame:
        return self.fetch(
            EUROSTAT_DATASETS["demographic_balance"],
            filters={"geo": tuple(geos)},
            start_year=start_year,
        )

    def migration_flows(
        self,
        kind: str,
        geos: Iterable[str] = EU27_ISO2,
        start_year: int = 2008,
        end_year: int | None = None,
    ) -> pd.DataFrame:
        if kind not in {"immigration_profile", "emigration_profile"}:
            raise ValueError("kind deve essere immigration_profile o emigration_profile")
        return self.fetch(
            EUROSTAT_DATASETS[kind],
            filters={"geo": tuple(geos), "unit": "NR"},
            start_year=start_year,
            end_year=end_year,
        )

    def migrant_stock(
        self,
        dimension: str,
        geos: Iterable[str] = EU27_ISO2,
        start_year: int = 2000,
    ) -> pd.DataFrame:
        if dimension not in {"population_citizenship", "population_birth_country"}:
            raise ValueError("dimension non riconosciuta")
        return self.fetch(
            EUROSTAT_DATASETS[dimension],
            filters={"geo": tuple(geos), "unit": "NR"},
            start_year=start_year,
        )
