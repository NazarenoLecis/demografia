from __future__ import annotations

import json
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from zipfile import ZipFile

import pandas as pd

from demografia.http import SESSION, download_file, get_json

OPENBDAP_API = "https://bdap-opendata.rgs.mef.gov.it/SpodCkanApi/api/3/action"
SUPPORTED_SUFFIXES = (".csv", ".txt", ".xlsx", ".xls", ".json", ".xml")


def _result(payload: Any) -> Any:
    if isinstance(payload, dict) and payload.get("success") is False:
        raise RuntimeError(str(payload.get("error") or payload))
    return payload.get("result") if isinstance(payload, dict) and "result" in payload else payload


def _resource_filename(item: dict[str, Any], prefix: str = "rgs") -> str:
    url = str(item.get("url", ""))
    name = Path(urlparse(url).path).name or f"{prefix}_{item.get('package_id', 'dataset')}"
    resource_format = str(item.get("format", "")).lower().strip().lstrip(".")
    if not Path(name).suffix and resource_format:
        name = f"{name}.{resource_format}"
    return name


def _read_csv_bytes(raw: bytes, source: str) -> pd.DataFrame:
    errors: list[Exception] = []
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(StringIO(raw.decode(encoding)), sep=None, engine="python")
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            errors.append(exc)
    raise ValueError(f"CSV RGS non leggibile: {source}") from errors[-1]


def _read_excel_bytes(raw: bytes) -> pd.DataFrame:
    sheets = pd.read_excel(BytesIO(raw), sheet_name=None)
    parts: list[pd.DataFrame] = []
    for sheet_name, frame in sheets.items():
        if frame.empty:
            continue
        copy = frame.copy()
        copy["sheet_name"] = sheet_name
        parts.append(copy)
    return pd.concat(parts, ignore_index=True, sort=False) if parts else pd.DataFrame()


def _read_json_bytes(raw: bytes) -> pd.DataFrame:
    payload = json.loads(raw.decode("utf-8-sig"))
    result = _result(payload)
    if isinstance(result, list):
        return pd.json_normalize(result)
    if isinstance(result, dict):
        for key in ("records", "results", "data", "items"):
            if isinstance(result.get(key), list):
                return pd.json_normalize(result[key])
        return pd.json_normalize(result)
    return pd.DataFrame()


def _read_bytes(raw: bytes, suffix: str, source: str) -> pd.DataFrame:
    suffix = suffix.lower()
    if suffix in {".csv", ".txt"}:
        return _read_csv_bytes(raw, source)
    if suffix in {".xlsx", ".xls"}:
        return _read_excel_bytes(raw)
    if suffix == ".json":
        return _read_json_bytes(raw)
    if suffix == ".xml":
        return pd.read_xml(BytesIO(raw))
    raise ValueError(f"Formato risorsa RGS non supportato: {suffix or source}")


def _read_zip_bytes(raw: bytes, source: str) -> pd.DataFrame:
    with ZipFile(BytesIO(raw)) as archive:
        members = [
            member
            for member in archive.namelist()
            if not member.endswith("/") and Path(member).suffix.lower() in SUPPORTED_SUFFIXES
        ]
        if not members:
            raise ValueError(f"Archivio RGS privo di file supportati: {source}")
        member = sorted(members, key=lambda value: SUPPORTED_SUFFIXES.index(Path(value).suffix.lower()))[0]
        return _read_bytes(archive.read(member), Path(member).suffix.lower(), f"{source}:{member}")


def package_list(refresh: bool = False, timeout: int = 180) -> list[str]:
    payload = get_json(f"{OPENBDAP_API}/package_list", refresh=refresh, timeout=timeout)
    return [str(value) for value in (_result(payload) or [])]


def package_search(
    query: str,
    rows: int = 100,
    start: int = 0,
    refresh: bool = False,
    timeout: int = 180,
) -> dict[str, Any]:
    payload = get_json(
        f"{OPENBDAP_API}/package_search",
        params={"q": query, "rows": rows, "start": start},
        refresh=refresh,
        timeout=timeout,
    )
    result = _result(payload)
    return result if isinstance(result, dict) else {"results": result or [], "count": len(result or [])}


def search_all(
    query: str,
    page_size: int = 100,
    max_pages: int = 20,
    refresh: bool = False,
    timeout: int = 180,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(max_pages):
        result = package_search(query, rows=page_size, start=page * page_size, refresh=refresh, timeout=timeout)
        batch = [item for item in result.get("results", []) if isinstance(item, dict)]
        rows.extend(batch)
        if len(batch) < page_size or len(rows) >= int(result.get("count", len(rows))):
            break
    return rows


def package_show(package_id: str, refresh: bool = False, timeout: int = 180) -> dict[str, Any]:
    payload = get_json(
        f"{OPENBDAP_API}/package_show",
        params={"id": package_id},
        refresh=refresh,
        timeout=timeout,
    )
    result = _result(payload)
    return result if isinstance(result, dict) else {}


def search_frame(queries: Iterable[str], refresh: bool = False, timeout: int = 180) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for query in queries:
        for package in search_all(query, refresh=refresh, timeout=timeout):
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


def select_resources(
    frame: pd.DataFrame,
    formats: tuple[str, ...] = ("csv", "xlsx", "xls", "json", "xml", "zip"),
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


def download_resource(resource: pd.Series | dict[str, Any], target_dir: Path, refresh: bool = False) -> Path:
    item = dict(resource)
    url = str(item.get("url", ""))
    if not url:
        raise ValueError("Risorsa RGS priva di URL")
    return download_file(
        url,
        target_dir / _resource_filename(item),
        refresh=refresh,
        timeout=900,
    )


def read_rgs_resource(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix.lower() == ".zip":
        return _read_zip_bytes(raw, str(path))
    return _read_bytes(raw, path.suffix.lower(), str(path))


def read_rgs_url(url: str, timeout: int = 300) -> pd.DataFrame:
    response = SESSION.get(url, timeout=timeout)
    response.raise_for_status()
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix == ".zip":
        return _read_zip_bytes(response.content, url)
    return _read_bytes(response.content, suffix, url)
