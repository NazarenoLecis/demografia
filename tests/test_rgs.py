import pandas as pd

from demografia.rgs import backtest_rgs_projections, build_rgs_projection_panel, normalize_rgs_projection


def test_normalize_rgs_wide_projection_and_panel():
    frame = pd.DataFrame(
        {
            "Indicatore": ["Spesa pensionistica in rapporto al PIL", "Tasso di occupazione"],
            "Unità": ["% PIL", "%"],
            "2025": [15.2, 62.0],
            "2030": [15.8, 64.0],
        }
    )
    normalized = normalize_rgs_projection(frame, vintage=2025)
    assert set(normalized["year"]) == {2025, 2030}
    assert "pension_expenditure_gdp" in set(normalized["indicator"])
    panel = build_rgs_projection_panel(normalized)
    assert "pension_expenditure_gdp" in panel.columns


def test_rgs_backtest():
    projections = pd.DataFrame(
        {
            "projection_vintage": [2020],
            "year": [2025],
            "scenario": ["baseline"],
            "indicator": ["pension_expenditure_gdp"],
            "value": [16.0],
        }
    )
    observed = pd.DataFrame({"year": [2025], "value": [15.5]})
    result = backtest_rgs_projections(projections, observed, "pension_expenditure_gdp")
    assert result.iloc[0]["error"] == 0.5
