from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session() -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "demografia-italiana/0.1"})
    return session


SESSION = build_session()


def _cache_key(url: str, params: Iterable[tuple[str, Any]] | dict[str, Any] | None) -> str:
    if params is None:
        encoded = ""
    elif isinstance(params, dict):
        encoded = urlencode(sorted(params.items()), doseq=True)
    else:
        encoded = urlencode(list(params), doseq=True)
    return hashlib.sha256(f"{url}?{encoded}".encode("utf-8")).hexdigest()


def get_json(
    url: str,
    params: Iterable[tuple[str, Any]] | dict[str, Any] | None = None,
    cache_dir: Path | None = None,
    refresh: bool = False,
    timeout: int = 120,
) -> dict[str, Any] | list[Any]:
    cache_path = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{_cache_key(url, params)}.json"
        if cache_path.exists() and not refresh:
            return json.loads(cache_path.read_text(encoding="utf-8"))

    response = SESSION.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if cache_path is not None:
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def get_text(
    url: str,
    params: Iterable[tuple[str, Any]] | dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 180,
) -> str:
    response = SESSION.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def download_file(url: str, target: Path, refresh: bool = False, timeout: int = 300) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not refresh:
        return target
    with SESSION.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return target
