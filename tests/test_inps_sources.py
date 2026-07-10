import pandas as pd

from demografia.inps import build_inps_support_indicators, discover_inps_roles, normalize_inps_table
from demografia.sources.inps import InpsClient


def test_inps_catalog_role_discovery_and_resource_selection():
    catalog = pd.DataFrame(
        [
            {
                "dataset_id": "1",
                "name": "pensionati-per-eta-e-sesso-2024",
                "title": "Pensionati per età e sesso 2024",
                "notes": "Numero di pensionati",
                "tags": "Pensioni",
                "metadata_modified": pd.Timestamp("2025-01-01"),
                "last_modified": pd.Timestamp("2025-01-01"),
                "resource_name": "pensionati",
                "resource_description": "",
                "format": "csv",
                "url": "https://example.test/pensionati.csv",
            },
            {
                "dataset_id": "2",
                "name": "lavoratori-iscritti-per-eta",
                "title": "Lavoratori iscritti per età",
                "notes": "Numero di iscritti",
                "tags": "Contributi",
                "metadata_modified": pd.Timestamp("2025-01-02"),
                "last_modified": pd.Timestamp("2025-01-02"),
                "resource_name": "iscritti",
                "resource_description": "",
                "format": "xlsx",
                "url": "https://example.test/iscritti.xlsx",
            },
        ]
    )
    matches = discover_inps_roles(catalog, max_per_role=3)
    assert {"pensioners", "insured_workers"}.issubset(set(matches["role"]))
    selected = InpsClient.select_resources(matches)
    assert set(selected["dataset_id"]) == {"1", "2"}


def test_normalize_inps_and_support_ratio():
    pensioners = pd.DataFrame(
        {"Anno": [2024], "Sesso": ["Totale"], "Numero pensionati": [16_000_000]}
    )
    contributors = pd.DataFrame(
        {"Anno": [2024], "Sesso": ["Totale"], "Numero lavoratori": [24_000_000]}
    )
    p = normalize_inps_table(pensioners, dataset_id="p", role="pensioners")
    c = normalize_inps_table(contributors, dataset_id="c", role="insured_workers")
    support = build_inps_support_indicators(pd.concat([p, c], ignore_index=True)).iloc[0]
    assert support["contributors_per_pensioner"] == 1.5


def test_read_inps_zip_resource(tmp_path):
    from zipfile import ZipFile

    from demografia.sources.inps import read_inps_resource

    archive_path = tmp_path / "inps.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("pensionati.csv", "Anno,Numero pensionati\n2024,16000000\n")
    result = read_inps_resource(archive_path)
    assert result.iloc[0]["Numero pensionati"] == 16_000_000
