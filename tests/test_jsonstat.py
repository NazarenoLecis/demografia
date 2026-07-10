from demografia.transform import parse_age_code
from demografia.jsonstat import jsonstat_to_frame


def test_jsonstat_sparse_values():
    payload = {
        "id": ["sex", "time"],
        "size": [2, 2],
        "dimension": {
            "sex": {"category": {"index": {"M": 0, "F": 1}, "label": {"M": "Male", "F": "Female"}}},
            "time": {"category": {"index": {"2020": 0, "2021": 1}}},
        },
        "value": {"0": 10, "3": 12},
    }
    frame = jsonstat_to_frame(payload)
    assert len(frame) == 2
    assert frame.iloc[0]["sex"] == "M"
    assert frame.iloc[1]["sex"] == "F"
    assert frame.iloc[1]["time"] == "2021"


def test_parse_eurostat_infant_age():
    assert parse_age_code("Y_LT1") == (0, 0)
    assert parse_age_code("Y_GE85") == (85, 120)
