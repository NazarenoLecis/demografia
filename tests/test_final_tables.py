import pandas as pd

from demografia.final_tables import (
    build_demographic_balance_wide,
    build_migration_summary,
    enrich_population_schema,
    normalize_eurostat_demographic_balance,
    normalize_eurostat_education_attainment,
    normalize_eurostat_fertility,
    normalize_eurostat_migration,
    normalize_eurostat_regional_population,
)
from demografia.sources import eurostat
from demografia.transform import parse_age_code


def test_parse_less_than_age_codes():
    assert parse_age_code("Y_LT5") == (0, 4)
    assert parse_age_code("Y_LT15") == (0, 14)


def test_migrant_stock_accepts_birth_country_filter(monkeypatch):
    captured = {}

    def fake_fetch(dataset, filters, start_year, refresh, chunk_size):
        captured["dataset"] = dataset
        captured["filters"] = filters
        captured["start_year"] = start_year
        captured["refresh"] = refresh
        captured["chunk_size"] = chunk_size
        return pd.DataFrame()

    monkeypatch.setattr(eurostat, "fetch", fake_fetch)

    eurostat.migrant_stock(
        "population_birth_country",
        geos=("IT",),
        start_year=2000,
        ages=("Y_LT5",),
        sexes=("M", "F"),
        categories=("FOR",),
        refresh=False,
        chunk_size=1,
    )

    assert captured["dataset"] == "migr_pop3ctb"
    assert captured["filters"]["c_birth"] == ("FOR",)
    assert captured["filters"]["age"] == ("Y_LT5",)
    assert captured["filters"]["sex"] == ("M", "F")


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


def test_education_attainment_normalization():
    raw = pd.DataFrame(
        {
            "geo": ["IT"],
            "time": [2024],
            "age": ["Y25-64"],
            "sex": ["T"],
            "isced11": ["ED5-8"],
            "isced11_label": ["Tertiary education (levels 5-8)"],
            "unit": ["PC"],
            "value": [22.3],
            "dataset": ["edat_lfse_03"],
        }
    )
    result = normalize_eurostat_education_attainment(raw)
    assert result.iloc[0]["iso3"] == "ITA"
    assert result.iloc[0]["age_low"] == 25
    assert result.iloc[0]["education_level"] == "tertiary"


def test_regional_population_normalization():
    raw = pd.DataFrame(
        {
            "geo": ["ITC1"],
            "geo_label": ["Piemonte"],
            "time": [2024],
            "age": ["Y_LT5"],
            "sex": ["T"],
            "unit": ["NR"],
            "value": [135610],
            "dataset": ["demo_r_pjangroup"],
        }
    )
    result = normalize_eurostat_regional_population(raw)
    assert result.iloc[0]["geo_level"] == "region"
    assert result.iloc[0]["geo_code"] == "ITC1"
    assert result.iloc[0]["geo_name"] == "Piemonte"
    assert result.iloc[0]["iso3"] == "ITA"
    assert result.iloc[0]["age_low"] == 0
    assert result.iloc[0]["age_high"] == 4


def test_nuts3_population_normalization_uses_province_level():
    raw = pd.DataFrame(
        {
            "geo": ["ITC11"],
            "geo_label": ["Torino"],
            "time": [2024],
            "age": ["Y_LT5"],
            "sex": ["T"],
            "unit": ["NR"],
            "value": [42000],
            "dataset": ["demo_r_pjangroup"],
        }
    )
    result = normalize_eurostat_regional_population(raw)
    assert result.iloc[0]["geo_level"] == "province"
    assert result.iloc[0]["geo_code"] == "ITC11"
    assert result.iloc[0]["geo_name"] == "Torino"
    assert result.iloc[0]["iso3"] == "ITA"


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
