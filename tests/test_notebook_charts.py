import pandas as pd
import plotly.graph_objects as go

from demografia.notebook_charts import (
    apply_layout,
    education_display_rows,
    europe_metric_table,
    fig_migrant_education_by_birth,
    fig_migrant_stock_categories,
    fig_migrant_tertiary_region,
    fig_migration_age_profile,
    fig_migration_citizenship_profile,
    finest_non_overlapping_age_rows,
    metric_rows,
    parametri_aree_istruzione_migranti,
    parametri_paesi,
    stock_category_label,
)
from demografia.pipeline import pipeline_options
from demografia.utils import normalize_eurostat_geo_code, normalize_territory_key


def test_apply_layout_places_source_note_in_lower_left_corner():
    fig = apply_layout(go.Figure(), "Titolo", "Fonte: test.<br>Elaborazione di Nazareno Lecis.")
    note = fig.layout.annotations[0]

    assert note.x == 0
    assert note.y < 0
    assert note.xanchor == "left"
    assert "Fonte:" in note.text
    assert "Elaborazione di Nazareno Lecis" in note.text


def test_finest_non_overlapping_age_rows_avoids_summing_aggregates():
    rows = pd.DataFrame(
        [
            {"sex": "M", "age_low": 0, "age_high": 0, "value": 10},
            {"sex": "M", "age_low": 1, "age_high": 1, "value": 11},
            {"sex": "M", "age_low": 0, "age_high": 4, "value": 60},
            {"sex": "F", "age_low": 0, "age_high": 0, "value": 12},
            {"sex": "F", "age_low": 0, "age_high": 4, "value": 65},
        ]
    )

    selected = finest_non_overlapping_age_rows(rows)

    assert sorted(selected["value"].tolist()) == [10, 11, 12]


def test_metric_rows_uses_balance_population_for_provinces():
    tables = {
        "regional_age_structure": pd.DataFrame(columns=["geo_code", "year", "population_total"]),
        "regional_balance": pd.DataFrame(
            [
                {
                    "geo_level": "province",
                    "geo_code": "ITC4C",
                    "year": 2024,
                    "population_1_january": 3_200_000,
                }
            ]
        ),
    }

    rows = metric_rows(tables, "ITC4C", "population_total")

    assert rows.iloc[0]["metric_value"] == 3_200_000


def test_user_facing_codes_are_normalized_without_prefixes():
    assert normalize_territory_key("ITA") == "country:ITA"
    assert normalize_territory_key("ESP") == "country:ESP"
    assert normalize_territory_key("ITC4") == "region:ITC4"
    assert normalize_territory_key("ITC4C") == "province:ITC4C"
    assert normalize_eurostat_geo_code("ITA") == "IT"
    assert normalize_eurostat_geo_code("ESP") == "ES"
    assert normalize_eurostat_geo_code("GRC") == "EL"


def test_pipeline_options_accepts_user_facing_country_codes():
    options = pipeline_options(
        eu_geos=("ITA", "ESP"),
        regional_country_prefix="ITA",
        regional_geos=("ITC4",),
        migration_geos=("ITA", "ESP"),
        migrant_education_geos=("ITA", "ITC4"),
        comparison_countries=("ITA", "ESP"),
    )

    assert options["eu_geos"] == ("IT", "ES")
    assert options["regional_country_prefix"] == "IT"
    assert options["regional_geos"] == ("ITC4",)
    assert options["migration_geos"] == ("IT", "ES")
    assert options["migrant_education_geos"] == ("IT", "ITC4")
    assert options["comparison_countries"] == ("ITA", "ESP")


def test_parameter_country_table_shows_copyable_iso3_codes():
    tables = {
        "age_structure": pd.DataFrame(
            [
                {"iso3": "ITA", "year": 2024},
                {"iso3": "ESP", "year": 2024},
            ]
        )
    }

    options = parametri_paesi(tables)

    assert set(options["codice"]) == {"ITA", "ESP"}
    assert not options["codice"].astype(str).str.contains(":").any()


def test_migrant_education_area_table_shows_country_as_iso3():
    tables = {
        "migrant_education": pd.DataFrame(
            [
                {"geo_code": "IT", "geo_name": "Italia", "geo_level": "country", "iso3": "ITA", "year": 2024},
                {"geo_code": "ITC4", "geo_name": "Lombardia", "geo_level": "region", "iso3": "ITA", "year": 2024},
            ]
        )
    }

    options = parametri_aree_istruzione_migranti(tables)

    assert "ITA" in set(options["codice"])
    assert "ITC4" in set(options["codice"])


def test_europe_metric_table_keeps_eu27_countries_only():
    tables = {
        "age_structure": pd.DataFrame(
            [
                {"iso3": "ITA", "year": 2024, "status": "observed", "share_65_plus": 24.0},
                {"iso3": "USA", "year": 2024, "status": "observed", "share_65_plus": 18.0},
            ]
        )
    }

    rows = europe_metric_table(tables, "share_65_plus")

    assert rows["iso3"].tolist() == ["ITA"]


def test_education_display_rows_uses_level_order_and_avoids_secondary_overlap():
    rows = pd.DataFrame(
        [
            {"education_level": "tertiary", "value": 40},
            {"education_level": "upper_secondary_vocational", "value": 30},
            {"education_level": "low_education", "value": 35},
            {"education_level": "upper_secondary_general", "value": 15},
            {"education_level": "upper_secondary_post_secondary", "value": 45},
            {"education_level": "upper_secondary_or_more", "value": 60},
        ]
    )

    selected = education_display_rows(rows)

    assert selected["education_level"].tolist() == [
        "low_education",
        "upper_secondary_general",
        "upper_secondary_vocational",
        "tertiary",
    ]


def test_migration_detail_figures_use_age_and_citizenship_tables():
    tables = {
        "immigration_citizenship": pd.DataFrame(
            [
                {"iso3": "ITA", "year": 2024, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "citizenship": "NAT", "value": 50},
                {"iso3": "ITA", "year": 2024, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "citizenship": "EU27_2020_FOR", "value": 20},
                {"iso3": "ITA", "year": 2024, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "citizenship": "NEU27_2020_FOR", "value": 80},
                {"iso3": "ITA", "year": 2024, "sex": "T", "age_low": 25, "age_high": 29, "citizenship": "TOTAL", "value": 30},
                {"iso3": "ITA", "year": 2024, "sex": "T", "age_low": 30, "age_high": 34, "citizenship": "TOTAL", "value": 40},
            ]
        )
    }

    age_fig = fig_migration_age_profile(tables, country="ITA", compare="none", year=2024)
    citizenship_fig = fig_migration_citizenship_profile(tables, country="ITA", compare="none", year=2024)

    assert len(age_fig.data) == 1
    assert list(age_fig.data[0].x) == ["25-29", "30-34"]
    assert len(citizenship_fig.data) == 1
    assert "Cittadini del paese" in list(citizenship_fig.data[0].x)
    assert "Fonte: Eurostat migr_imm1ctz" in citizenship_fig.layout.annotations[0].text


def test_migrant_stock_category_figures_use_birth_and_citizenship_tables():
    tables = {
        "population_by_country_of_birth": pd.DataFrame(
            [
                {"iso3": "ITA", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "TOTAL", "value": 59_000_000},
                {"iso3": "ITA", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "FOR", "value": 6_000_000},
                {"iso3": "ITA", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "RO", "value": 950_000},
                {"iso3": "ITA", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "AL", "value": 420_000},
                {"iso3": "ESP", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "TOTAL", "value": 48_000_000},
                {"iso3": "ESP", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "RO", "value": 510_000},
                {"iso3": "ESP", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "AL", "value": 120_000},
            ]
        ),
        "population_by_citizenship": pd.DataFrame(
            [
                {"iso3": "ITA", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "TOTAL", "value": 59_000_000},
                {"iso3": "ITA", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "RO", "value": 1_000_000},
                {"iso3": "ITA", "year": 2025, "sex": "T", "age_low": pd.NA, "age_high": pd.NA, "category": "EU27_2020_FOR", "value": 1_600_000},
            ]
        ),
    }

    birth = fig_migrant_stock_categories(tables, basis="country_of_birth", country="ITA", compare="ESP", year=2025)
    citizenship = fig_migrant_stock_categories(tables, basis="citizenship", country="ITA", year=2025, measure="percent_total")

    assert len(birth.data) == 2
    assert "Romania" in list(birth.data[0].y)
    assert "Albania" in list(birth.data[0].y)
    assert "Nati all'estero" not in list(birth.data[0].y)
    assert "% residenti" in citizenship.layout.xaxis.title.text
    assert stock_category_label("NAT", "citizenship") == "Cittadini del paese"


def test_migrant_education_figures_use_birth_group_and_region():
    migrant_education = pd.DataFrame(
        [
            {"geo_level": "country", "geo_code": "IT", "geo_name": "Italia", "iso3": "ITA", "year": 2024, "age_label": "25-64", "sex": "T", "country_of_birth_group": "NAT", "education_level": "low_education", "value": 30},
            {"geo_level": "country", "geo_code": "IT", "geo_name": "Italia", "iso3": "ITA", "year": 2024, "age_label": "25-64", "sex": "T", "country_of_birth_group": "NAT", "education_level": "tertiary", "value": 25},
            {"geo_level": "country", "geo_code": "IT", "geo_name": "Italia", "iso3": "ITA", "year": 2024, "age_label": "25-64", "sex": "T", "country_of_birth_group": "FOR", "education_level": "low_education", "value": 45},
            {"geo_level": "country", "geo_code": "IT", "geo_name": "Italia", "iso3": "ITA", "year": 2024, "age_label": "25-64", "sex": "T", "country_of_birth_group": "FOR", "education_level": "tertiary", "value": 15},
        ]
    )
    migrant_tertiary = pd.DataFrame(
        [
            {"geo_level": "region", "geo_code": "ITC4", "geo_name": "Lombardia", "iso3": "ITA", "year": 2024, "age_label": "25-64", "sex": "T", "country_of_birth_group": "FOR", "tertiary_share": 18},
            {"geo_level": "region", "geo_code": "ITI4", "geo_name": "Lazio", "iso3": "ITA", "year": 2024, "age_label": "25-64", "sex": "T", "country_of_birth_group": "FOR", "tertiary_share": 22},
        ]
    )
    tables = {"migrant_education": migrant_education, "migrant_tertiary": migrant_tertiary}

    distribution = fig_migrant_education_by_birth(tables, geo_code="IT", year=2024)
    ranking = fig_migrant_tertiary_region(tables, year=2024, limit=2)

    assert len(distribution.data) == 2
    assert "Titoli di studio per paese di nascita" in distribution.layout.title.text
    assert list(ranking.data[0].y) == ["Lombardia", "Lazio"]
    assert "edat_lfs_9917" in ranking.layout.annotations[0].text
