import pandas as pd

from demografia.indicators import compute_age_structure


def test_dependency_ratios():
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
                    "source": "test",
                }
            )
    result = compute_age_structure(pd.DataFrame(rows)).iloc[0]
    assert result["population_total"] == 202
    assert result["pop_0_14"] == 30
    assert result["pop_15_64"] == 100
    assert result["pop_65_plus"] == 72
    assert result["dependency_youth"] == 30
    assert result["dependency_old"] == 72
