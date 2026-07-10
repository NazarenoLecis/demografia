import pandas as pd

from demografia.final_tables import (
    build_demographic_balance_wide,
    build_migration_summary,
    enrich_population_schema,
    normalize_eurostat_demographic_balance,
    normalize_eurostat_fertility,
    normalize_eurostat_migration,
)


def test_fertility_normalization():
    raw = pd.DataFrame(
        {
            "geo": ["IT"],
            "time": [2023],
            "indic_de": ["TOTFERRT"],
            "indic_de_label": ["Total fertility rate"],
            "unit": ["NR"],
            "value": [1.2],
            "dataset": ["demo_frate"],
        }
    )
    result = normalize_eurostat_fertility(raw)
    assert result.iloc[0]["iso3"] == "ITA"
    assert result.iloc[0]["indicator"] == "total_fertility_rate"


def test_demographic_balance_identity():
    raw = pd.DataFrame(
        {
            "geo": ["IT"] * 6,
            "time": [2023] * 6,
            "indic_de": ["BIRTH", "DEATH", "IMMIGR", "EMIGR", "GROW", "JAN"],
            "value": [10, 8, 5, 4, 3, 100],
            "unit": ["NR"] * 6,
        }
    )
    wide = build_demographic_balance_wide(normalize_eurostat_demographic_balance(raw))
    assert wide.iloc[0]["natural_change_derived"] == 2
    assert wide.iloc[0]["net_migration_derived"] == 1
    assert wide.iloc[0]["balance_identity_residual"] == 0


def test_migration_summary():
    raw_in = pd.DataFrame(
        {"geo": ["IT"], "time": [2023], "sex": ["T"], "unit": ["NR"], "value": [10]}
    )
    raw_out = pd.DataFrame(
        {"geo": ["IT"], "time": [2023], "sex": ["T"], "unit": ["NR"], "value": [4]}
    )
    summary = build_migration_summary(
        normalize_eurostat_migration(raw_in, "immigration"),
        normalize_eurostat_migration(raw_out, "emigration"),
    )
    assert summary.iloc[0]["net_migration"] == 6


def test_central_population_schema():
    population = pd.DataFrame(
        {
            "iso3": ["ITA"],
            "year": [2024],
            "age_low": [0],
            "age_high": [0],
            "sex": ["F"],
            "value": [100],
            "scenario": ["Observed"],
            "status": ["observed"],
            "source": ["Eurostat"],
        }
    )
    result = enrich_population_schema(population)
    assert result.iloc[0]["geo_name"] == "Italia"
    assert result.iloc[0]["age_label"] == "0"
    assert result.iloc[0]["unit"] == "persons"
