import pandas as pd

from demografia.official_quality import build_official_quality_report


def test_official_quality_detects_balanced_internal_migration():
    balances = pd.DataFrame(
        {
            "territory_code": ["A", "B"],
            "year": [2024, 2024],
            "internal_balance": [10.0, -10.0],
        }
    )
    report = build_official_quality_report(internal_migration_balances=balances)
    row = report[report["check"].eq("internal migration conservation")].iloc[0]
    assert row["passed"]
