import pandas as pd

from demografia.istat_official import normalize_istat_indicator_table, normalize_istat_projection


def test_normalize_istat_indicator_table():
    frame = pd.DataFrame(
        {
            "TIME_PERIOD": [2024],
            "ITTER107": ["IT"],
            "ETA1": ["Y65"],
            "SEXISTAT1": ["1"],
            "OBS_VALUE": [100],
        }
    )
    result = normalize_istat_indicator_table(frame, role="deaths", dataset="TEST")
    assert result.iloc[0]["age_low"] == 65
    assert result.iloc[0]["sex"] == "M"


def test_normalize_istat_projection_keeps_scenario():
    frame = pd.DataFrame(
        {
            "TIME_PERIOD": [2050],
            "ITTER107": ["IT"],
            "ETA1": ["Y65"],
            "SEXISTAT1": ["2"],
            "SCENARIO": ["MEDIAN"],
            "OBS_VALUE": [120],
        }
    )
    result = normalize_istat_projection(frame, dataset="PROJ")
    assert result.iloc[0]["status"] == "projected"
    assert result.iloc[0]["scenario"] == "MEDIAN"
