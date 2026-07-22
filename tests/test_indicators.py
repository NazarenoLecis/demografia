import pandas as pd

from demografia.config import EU27_ISO3, EU_OECD_ISO3, OECD38_ISO3
from demografia.indicators import atomic_population_rows, compute_age_structure


def _single_age_population(source: str = "test") -> pd.DataFrame:
    rows = []
    for sex in ("M", "F"):
        for age in range(0, 101):
            rows.append(
                {
                    "iso3": "ITA",
                    "year": 2024,
                    "age_low": age,
                    "age_high": age,
                    "sex": sex,
                    "value": 1.0,
                    "scenario": "Observed",
                    "status": "observed",
                    "source": source,
                }
            )
    return pd.DataFrame(rows)


def test_dependency_ratios_and_extended_bands():
    result = compute_age_structure(_single_age_population()).iloc[0]
    assert result["population_total"] == 202
    assert result["pop_0_14"] == 30
    assert result["pop_15_64"] == 100
    assert result["pop_15_74"] == 120
    assert result["pop_20_39"] == 40
    assert result["pop_65_plus"] == 72
    assert result["pop_90_plus"] == 22
    assert result["dependency_youth"] == 30
    assert result["dependency_old"] == 72
    assert result["ageing_index_65_plus_per_100_youth"] == 240
    assert result["active_replacement_60_64_per_100_15_19"] == 100
    assert result["young_adult_to_late_life_ratio_20_39_per_60_79"] == 1
    assert result["age_p10"] == 10
    assert result["age_p25"] == 25
    assert result["age_p75"] == 75
    assert result["age_p90"] == 90


def test_aggregate_age_classes_are_not_double_counted():
    rows = []
    for sex in ("M", "F"):
        rows.extend(
            [
                {
                    "iso3": "ITA",
                    "year": 2024,
                    "age_low": 0,
                    "age_high": 0,
                    "sex": sex,
                    "value": 1.0,
                    "scenario": "Observed",
                    "status": "observed",
                    "source": "Eurostat",
                },
                {
                    "iso3": "ITA",
                    "year": 2024,
                    "age_low": 1,
                    "age_high": 1,
                    "sex": sex,
                    "value": 1.0,
                    "scenario": "Observed",
                    "status": "observed",
                    "source": "Eurostat",
                },
                {
                    "iso3": "ITA",
                    "year": 2024,
                    "age_low": 0,
                    "age_high": 1,
                    "sex": sex,
                    "value": 2.0,
                    "scenario": "Observed",
                    "status": "observed",
                    "source": "Eurostat",
                },
            ]
        )
    atomic = atomic_population_rows(pd.DataFrame(rows))
    assert atomic["value"].sum() == 4
    assert len(atomic) == 4


def test_sources_remain_separate():
    combined = pd.concat(
        [_single_age_population("Eurostat"), _single_age_population("UN World Population Prospects")],
        ignore_index=True,
    )
    result = compute_age_structure(combined)
    assert set(result["source"]) == {"Eurostat", "UN World Population Prospects"}
    assert len(result) == 2


def test_comparison_universe_covers_full_eu_and_oecd():
    assert set(EU27_ISO3).issubset(EU_OECD_ISO3)
    assert set(OECD38_ISO3).issubset(EU_OECD_ISO3)
    assert {"BGR", "HRV", "CYP", "MLT", "ROU"}.issubset(EU_OECD_ISO3)
