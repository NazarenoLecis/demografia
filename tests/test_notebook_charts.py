import pandas as pd
import plotly.graph_objects as go

from demografia.notebook_charts import (
    apply_layout,
    europe_metric_table,
    finest_non_overlapping_age_rows,
    metric_rows,
)


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

    rows = metric_rows(tables, "province:ITC4C", "population_total")

    assert rows.iloc[0]["metric_value"] == 3_200_000


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
