import pandas as pd

from demografia.territory import normalize_istat_population


def test_normalize_istat_population():
    frame = pd.DataFrame(
        {
            "ITTER107": ["ITG2", "ITG2"],
            "TIME_PERIOD": [2024, 2024],
            "ETA1": ["Y30", "Y30"],
            "SEXISTAT1": ["1", "2"],
            "OBS_VALUE": [10, 11],
        }
    )
    result = normalize_istat_population(frame)
    assert set(result["sex"]) == {"M", "F"}
    assert result["age_low"].eq(30).all()
    assert result["territory_code"].eq("ITG2").all()
