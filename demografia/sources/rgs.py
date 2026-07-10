from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd

from demografia.http import SESSION, download_file, get_json

OPENBDAP_API = "https://bdap-opendata.rgs.mef.gov.it/SpodCkanApi/api/3/action"


def _result(payload: Any) -> Any:
    if isinstance(payload, dict) and payload.get("success") is False:
        raise RuntimeError(str(payload.get("error") or payload))
    return payload.get("result") if isinstance(payload, dict) and "result" in payload else payload


@dataclass
class RgsClient:
    refresh: bool = False

    def package_list(self) -> list[str]:
        payload = get_json(f"{OPENBDAP_API}/package_list", refresh=self.refresh, timeout=180)
        return [str(value) for value in (_result(payload) or [])]

    def package_search(self, query: str, rows: int = 100, start: int = 0) -> dict[str, Any]:
        payload = get_json(
            f"{OPENBDAP_API}/package_search",
            params={"q": query, "rows": rows, "start": start},
            refresh=self.refresh,
            timeout=180,
        )
        result = _result(payload)
        return result if isinstance(result, dict) else {"results": result or [], "count": len(result or [])}

    def search_all(self, query: str, page_size: int = 100, max_pages: int = 20) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for page in range(max_pages):
            result = self.package_search(query, rows=page_size, start=page * page_size)
            batch = [item for item in result.get("results", []) if isinstance(item, dict)]
            rows.extend(batch)
            if len(batch) < page_size or len(rows) >= int(result.get("count", len(rows))):
                break
        return rows

    def package_show(self, package_id: str) -> dict[str, Any]:
        payload = get_json(
            f"{OPENBDAP_API}/package_show",
            params={"id": package_id},
            refresh=self.refresh,
            timeout=180,
        )
        result = _result(payload)
        return result if isinstance(result, dict) else {}

    def search_frame(self, queries: Iterable[str]) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for query in queries:
            for package in self.search_all(query):
                resources = package.get("resources") or [None]
                for resource in resources:
                    resource = resource or {}
                    key = (str(package.get("id", "")), str(resource.get("id", "")))
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append(
                        {
                            "query": query,
                            "package_id": package.get("id", ""),
                            "name": package.get("name", ""),
                            "title": package.get("title", ""),
                            "notes": package.get("notes", ""),
                            "metadata_created": package.get("metadata_created"),
                            "metadata_modified": package.get("metadata_modified"),
                            "resource_id": resource.get("id", ""),
                            "resource_name": resource.get("name", ""),
                            "description": resource.get("description", ""),
                            "format": str(resource.get("format", "")).lower(),
                            "url": resource.get("url", ""),
                            "last_modified": resource.get("last_modified"),
                        }
                    )
        frame = pd.DataFrame(records)
        if not frame.empty:
            frame["metadata_modified"] = pd.to_datetime(frame["metadata_modified"], errors="coerce")
            frame["last_modified"] = pd.to_datetime(frame["last_modified"], errors="coerce")
        return frame

    @staticmethod
    def select_resources(
        frame: pd.DataFrame,
        formats: tuple[str, ...] = ("csv", "xlsx", "xls", "json", "xml"),
        one_per_package: bool = True,
    ) -> pd.DataFrame:
        if frame.empty:
            return frame.copy()
        priorities = {value: index for index, value in enumerate(formats)}
        result = frame[frame["format"].isin(priorities)].copy()
        result["format_priority"] = result["format"].map(priorities)
        result = result.sort_values(
            ["metadata_modified", "last_modified", "format_priority"],
            ascending=[False, False, True],
            na_position="last",
        )
        if one_per_package:
            result = result.drop_duplicates("package_id", keep="first")
        return result.drop(columns="format_priority")

    def download_resource(self, resource: pd.Series | dict[str, Any], target_dir: Path) -> Path:
        item = dict(resource)
        url = str(item.get("url", ""))
        if not url:
            raise ValueError("Risorsa RGS priva di URL")
        name = Path(urlparse(url).path).name or (
            f"rgs_{item.get('package_id', 'dataset')}.{item.get('format', 'dat')}"
        )
        return download_file(url, target_dir / name, refresh=self.refresh, timeout=900)


def read_rgs_resource(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith((".csv", ".txt")):
        raw = path.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(StringIO(raw.decode(encoding)), sep=None, engine="python")
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        raise ValueError(f"CSV RGS non leggibile: {path}")
    if suffixes.endswith((".xlsx", ".xls")):
        sheets = pd.read_excel(path, sheet_name=None)
        parts = []
        for sheet_name, frame in sheets.items():
            if frame.empty:
                continue
            copy = frame.copy()
            copy["sheet_name"] = sheet_name
            parts.append(copy)
        return pd.concat(parts, ignore_index=True, sort=False) if parts else pd.DataFrame()
    if suffixes.endswith(".json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = _result(payload)
        if isinstance(result, list):
            return pd.json_normalize(result)
        if isinstance(result, dict):
            for key in ("records", "results", "data", "items"):
                if isinstance(result.get(key), list):
                    return pd.json_normalize(result[key])
            return pd.json_normalize(result)
    if suffixes.endswith(".xml"):
        return pd.read_xml(path)
    raise ValueError(f"Formato risorsa RGS non supportato: {path.suffix}")


def read_rgs_url(url: str, timeout: int = 300) -> pd.DataFrame:
    response = SESSION.get(url, timeout=timeout)
    response.raise_for_status()
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(StringIO(response.content.decode(encoding)), sep=None, engine="python")
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(BytesIO(response.content))
    if suffix == ".json":
        return pd.json_normalize(_result(response.json()))
    if suffix == ".xml":
        return pd.read_xml(BytesIO(response.content))
    raise ValueError(f"Formato URL RGS non supportato: {suffix}")
