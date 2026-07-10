from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from xml.etree import ElementTree

import pandas as pd

from demografia.http import get_text

ISTAT_SDMX = "https://esploradati.istat.it/SDMXWS/rest"


@dataclass
class IstatClient:
    """Client generico per catalogo e dataflow ISTAT SDMX 2.1."""

    def dataflows_xml(self) -> str:
        return get_text(
            f"{ISTAT_SDMX}/dataflow/IT1/all/latest",
            headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"},
        )

    def dataflows(self) -> pd.DataFrame:
        root = ElementTree.fromstring(self.dataflows_xml())
        rows: list[dict[str, str]] = []
        for element in root.iter():
            if not element.tag.endswith("Dataflow"):
                continue
            names = [child.text or "" for child in element if child.tag.endswith("Name")]
            rows.append(
                {
                    "agency": element.attrib.get("agencyID", ""),
                    "dataflow_id": element.attrib.get("id", ""),
                    "version": element.attrib.get("version", ""),
                    "name": " | ".join(name for name in names if name),
                }
            )
        return pd.DataFrame(rows).drop_duplicates("dataflow_id")

    def search_dataflows(self, terms: tuple[str, ...]) -> pd.DataFrame:
        flows = self.dataflows()
        if flows.empty:
            return flows
        text = flows["name"].str.lower() + " " + flows["dataflow_id"].str.lower()
        mask = False
        for term in terms:
            mask = mask | text.str.contains(term.lower(), regex=False)
        return flows[mask].sort_values(["name", "dataflow_id"]).reset_index(drop=True)

    def csv(
        self,
        dataflow_id: str,
        key: str = "all",
        start_period: int | None = None,
        end_period: int | None = None,
        version: str = "latest",
    ) -> pd.DataFrame:
        params = {}
        if start_period is not None:
            params["startPeriod"] = start_period
        if end_period is not None:
            params["endPeriod"] = end_period
        text = get_text(
            f"{ISTAT_SDMX}/data/IT1,{dataflow_id},{version}/{key}",
            params=params or None,
            headers={"Accept": "text/csv"},
            timeout=300,
        )
        return pd.read_csv(StringIO(text))
