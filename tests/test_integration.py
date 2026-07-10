import pandas as pd

from demografia.integration import build_italy_demographic_fiscal_panel


def test_integrated_panel_combines_demography_inps_and_rgs():
    age = pd.DataFrame(
        {
            "iso3": ["ITA"],
            "year": [2025],
            "status": ["observed"],
            "source": ["Eurostat"],
            "population_total": [59_000_000],
            "pop_0_14": [7_000_000],
            "pop_15_64": [37_000_000],
            "pop_65_plus": [15_000_000],
            "pop_80_plus": [4_500_000],
            "dependency_youth": [18.9],
            "dependency_old": [40.5],
            "dependency_total": [59.4],
            "support_ratio_15_64_per_65_plus": [2.47],
            "support_ratio_20_64_per_65_plus": [2.2],
            "mean_age": [46.5],
            "median_age": [48.0],
        }
    )
    inps = pd.DataFrame({"year": [2025], "contributors": [24_000_000], "pensioners": [16_000_000]})
    rgs = pd.DataFrame(
        {
            "year": [2025],
            "projection_vintage": [2025],
            "scenario": ["baseline"],
            "pension_expenditure_gdp": [15.5],
        }
    )
    result = build_italy_demographic_fiscal_panel(age, inps, rgs).iloc[0]
    assert result["contributors_per_person_65_plus"] == 1.6
    assert result["pension_expenditure_gdp"] == 15.5
