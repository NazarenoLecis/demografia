import pandas as pd

from demografia.quality import validate_demographic_balance, validate_population


def _population() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "iso3": ["ITA", "ITA"],
            "year": [2024, 2024],
            "age_low": [0, 0],
            "age_high": [0, 0],
            "sex": ["M", "F"],
            "value": [100.0, 90.0],
            "status": ["observed", "observed"],
            "scenario": ["Observed", "Observed"],
            "source": ["test", "test"],
        }
    )


def test_population_validation_ok():
    report = validate_population(_population())
    assert not report["severity"].eq("error").any()


def test_population_validation_detects_duplicate():
    frame = pd.concat([_population(), _population().iloc[[0]]], ignore_index=True)
    report = validate_population(frame)
    assert report["check"].eq("duplicate_keys").any()


def test_balance_validation_detects_residual():
    report = validate_demographic_balance(
        pd.DataFrame({"balance_identity_residual": [0.0, 5.0]})
    )
    assert report["check"].eq("demographic_balance_identity").any()
