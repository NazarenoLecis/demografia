from __future__ import annotations

import json
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from zipfile import ZipFile

import pandas as pd

from demografia.http import SESSION, download_file, get_json

INPS_API = "https://serviziweb2.inps.it/odapi"
INPS_OPEN_DATA = "https://opendata.inps.it/opendata"
INPS_DATA_BROWSER = "https://opendata.inps.it/databrowser/"
SUPPORTED_SUFFIXES = (".csv", ".txt", ".xlsx", ".xls", ".json", ".xml")


def _payload_result(payload: Any) -> Any:
    if isinstance(payload, dict) and payload.get("success") is False:
        raise RuntimeError(str(payload.get("error") or payload))
    return payload.get("result") if isinstance(payload, dict) and "result" in payload else payload


def _as_tags(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(
            str(item.get("name", item)) if isinstance(item, dict) else str(item)
            for item in value
        )
    return str(value or "")


def _secure_inps_url(url: str) -> str:
    if url.startswith("http://www.inps.it/"):
        return "https://www.inps.it/" + url.removeprefix("http://www.inps.it/")
    return url


def _resource_filename(item: dict[str, Any], prefix: str = "inps") -> str:
    url = str(item.get("url", ""))
    name = Path(urlparse(url).path).name or f"{prefix}_{item.get('dataset_id', 'dataset')}"
    resource_format = str(item.get("format", "")).lower().strip().lstrip(".")
    if not Path(name).suffix and resource_format:
        name = f"{name}.{resource_format}"
    return name


def _read_csv_bytes(raw: bytes, source: str) -> pd.DataFrame:
    errors: list[Exception] = []
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            return pd.read_csv(StringIO(text), sep=None, engine="python")
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            errors.append(exc)
    raise ValueError(f"CSV INPS non leggibile: {source}") from errors[-1]


def _read_json_bytes(raw: bytes) -> pd.DataFrame:
    payload = json.loads(raw.decode("utf-8-sig"))
    result = _payload_result(payload)
    if isinstance(result, list):
        return pd.json_normalize(result)
    if isinstance(result, dict):
        for key in ("records", "data", "items", "result"):
            if isinstance(result.get(key), list):
                return pd.json_normalize(result[key])
        return pd.json_normalize(result)
    return pd.DataFrame()


def _read_bytes(raw: bytes, suffix: str, source: str) -> pd.DataFrame:
    suffix = suffix.lower()
    if suffix in {".csv", ".txt"}:
        return _read_csv_bytes(raw, source)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(BytesIO(raw))
    if suffix == ".json":
        return _read_json_bytes(raw)
    if suffix == ".xml":
        return pd.read_xml(BytesIO(raw))
    raise ValueError(f"Formato risorsa INPS non supportato: {suffix or source}")


def _read_zip_bytes(raw: bytes, source: str) -> pd.DataFrame:
    with ZipFile(BytesIO(raw)) as archive:
        members = [
            member
            for member in archive.namelist()
            if not member.endswith("/") and Path(member).suffix.lower() in SUPPORTED_SUFFIXES
        ]
        if not members:
            raise ValueError(f"Archivio INPS privo di file supportati: {source}")
        member = sorted(members, key=lambda value: SUPPORTED_SUFFIXES.index(Path(value).suffix.lower()))[0]
        return _read_bytes(archive.read(member), Path(member).suffix.lower(), f"{source}:{member}")


def status(refresh: bool = False, timeout: int = 120) -> dict[str, Any]:
    result = _payload_result(get_json(f"{INPS_API}/status", refresh=refresh, timeout=timeout))
    return result if isinstance(result, dict) else {"result": result}


def package_list(refresh: bool = False, timeout: int = 120) -> list[str]:
    result = _payload_result(get_json(f"{INPS_API}/package_list", refresh=refresh, timeout=timeout))
    return [str(item) for item in (result or [])]


def package_show(dataset_id: str | int, refresh: bool = False, timeout: int = 120) -> dict[str, Any]:
    result = _payload_result(
        get_json(
            f"{INPS_API}/package_show",
            params={"id": str(dataset_id)},
            refresh=refresh,
            timeout=timeout,
        )
    )
    return result if isinstance(result, dict) else {}


def catalog_page(
    limit: int = 100,
    offset: int = 0,
    refresh: bool = False,
    timeout: int = 180,
) -> list[dict[str, Any]]:
    payload = get_json(
        f"{INPS_API}/current_package_list_with_resources",
        params={"limit": limit, "offset": offset},
        refresh=refresh,
        timeout=timeout,
    )
    result = _payload_result(payload)
    return [item for item in (result or []) if isinstance(item, dict)]


def catalog(
    page_size: int = 100,
    max_pages: int | None = None,
    refresh: bool = False,
    timeout: int = 180,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 0
    while True:
        batch = catalog_page(limit=page_size, offset=page * page_size, refresh=refresh, timeout=timeout)
        rows.extend(batch)
        page += 1
        if len(batch) < page_size or (max_pages is not None and page >= max_pages):
            break
    return rows


def catalog_frame(
    page_size: int = 100,
    max_pages: int | None = None,
    refresh: bool = False,
    timeout: int = 180,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for package in catalog(page_size=page_size, max_pages=max_pages, refresh=refresh, timeout=timeout):
        resources = package.get("resources") or [None]
        for resource in resources:
            resource = resource or {}
            records.append(
                {
                    "dataset_id": str(package.get("id", "")),
                    "name": package.get("name", ""),
                    "title": package.get("title", ""),
                    "notes": package.get("notes", ""),
                    "tags": _as_tags(package.get("tags")),
                    "metadata_created": package.get("metadata_created"),
                    "metadata_modified": package.get("metadata_modified"),
                    "state": package.get("state"),
                    "license_id": package.get("license_id"),
                    "resource_id": str(resource.get("id", "")),
                    "resource_name": resource.get("name", ""),
                    "resource_description": resource.get("description", ""),
                    "format": str(resource.get("format", "")).lower(),
                    "mimetype": resource.get("mimetype", ""),
                    "url": str(resource.get("url", "")),
                    "last_modified": resource.get("last_modified"),
                }
            )
    frame = pd.DataFrame(records)
    if not frame.empty:
        frame["metadata_modified"] = pd.to_datetime(frame["metadata_modified"], errors="coerce")
        frame["last_modified"] = pd.to_datetime(frame["last_modified"], errors="coerce")
    return frame


def search_catalog(
    terms: Iterable[str],
    page_size: int = 100,
    max_pages: int | None = None,
    require_all: bool = False,
    refresh: bool = False,
    timeout: int = 180,
) -> pd.DataFrame:
    frame = catalog_frame(page_size=page_size, max_pages=max_pages, refresh=refresh, timeout=timeout)
    if frame.empty:
        return frame
    text = (
        frame[["name", "title", "notes", "tags", "resource_name", "resource_description"]]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.casefold()
    )
    term_list = [term.casefold() for term in terms]
    if require_all:
        mask = pd.Series(True, index=frame.index)
        for term in term_list:
            mask &= text.str.contains(term, regex=False)
    else:
        mask = pd.Series(False, index=frame.index)
        for term in term_list:
            mask |= text.str.contains(term, regex=False)
    result = frame[mask].copy()
    if result.empty:
        return result
    result["match_score"] = 0
    for term in term_list:
        result["match_score"] += text.loc[result.index].str.contains(term, regex=False).astype(int)
    return result.sort_values(
        ["match_score", "metadata_modified", "last_modified"],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)


def select_resources(
    matches: pd.DataFrame,
    formats: tuple[str, ...] = ("csv", "json", "xlsx", "xls", "xml", "zip"),
    one_per_dataset: bool = True,
) -> pd.DataFrame:
    if matches.empty:
        return matches.copy()
    priorities = {value: index for index, value in enumerate(formats)}
    selected = matches[matches["format"].isin(priorities)].copy()
    selected["format_priority"] = selected["format"].map(priorities)
    score_column = "match_score" if "match_score" in selected else "role_score"
    if score_column not in selected:
        selected["_score"] = 0
        score_column = "_score"
    selected = selected.sort_values(
        [score_column, "metadata_modified", "format_priority"],
        ascending=[False, False, True],
        na_position="last",
    )
    if one_per_dataset:
        selected = selected.drop_duplicates("dataset_id", keep="first")
    return selected.drop(columns=["format_priority", "_score"], errors="ignore")


def download_resource(resource: pd.Series | dict[str, Any], target_dir: Path, refresh: bool = False) -> Path:
    item = dict(resource)
    original_url = str(item.get("url", ""))
    if not original_url:
        raise ValueError("Risorsa INPS priva di URL")
    secure_url = _secure_inps_url(original_url)
    target = target_dir / _resource_filename(item)
    try:
        return download_file(secure_url, target, refresh=refresh, timeout=900)
    except Exception:
        if secure_url == original_url:
            raise
        return download_file(original_url, target, refresh=refresh, timeout=900)


def read_inps_resource(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix.lower() == ".zip":
        return _read_zip_bytes(raw, str(path))
    return _read_bytes(raw, path.suffix.lower(), str(path))


def read_inps_url(url: str, timeout: int = 300) -> pd.DataFrame:
    response = SESSION.get(_secure_inps_url(url), timeout=timeout)
    response.raise_for_status()
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix == ".zip":
        return _read_zip_bytes(response.content, url)
    return _read_bytes(response.content, suffix, url)
