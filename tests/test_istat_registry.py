import pandas as pd
import pytest

from demografia.istat_registry import resolve_istat_role, score_istat_dataflows


def test_population_role_prefers_age_and_sex_detail():
    dataflows = pd.DataFrame(
        [
            {
                "agency": "IT1",
                "dataflow_id": "A",
                "version": "1.0",
                "name": "Popolazione residente",
            },
            {
                "agency": "IT1",
                "dataflow_id": "B",
                "version": "1.0",
                "name": "Popolazione residente per età e sesso",
            },
        ]
    )
    registry = score_istat_dataflows(dataflows)
    match = resolve_istat_role(registry, "population_age_sex")
    assert match.dataflow_id == "B"


def test_ambiguous_role_is_not_selected_silently():
    dataflows = pd.DataFrame(
        [
            {
                "agency": "IT1",
                "dataflow_id": "A",
                "version": "1.0",
                "name": "Bilancio demografico comunale",
            },
            {
                "agency": "IT1",
                "dataflow_id": "B",
                "version": "1.0",
                "name": "Bilancio demografico comunale",
            },
        ]
    )
    registry = score_istat_dataflows(dataflows)
    with pytest.raises(LookupError, match="ambigua"):
        resolve_istat_role(registry, "demographic_balance")
