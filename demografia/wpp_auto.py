from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from demografia.http import SESSION, download_file, get_text

WPP_DOWNLOAD_PAGE = "https://population.un.org/wpp/Download/Standard/CSV/"
WPP_AGE_SEX_CANDIDATES = (
    "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/"
    "WPP2024_PopulationBySingleAgeSex_Medium_1950-2100.csv.gz",
    "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/"
    "WPP2024_PopulationByAge5GroupSex_Medium.csv.gz",
)


def discover_wpp_age_sex_urls(html: str | None = None) -> list[str]:
    """Return official WPP files, preferring single-age medium projections."""
    if html is None:
        try:
            html = get_text(WPP_DOWNLOAD_PAGE, timeout=60)
        except Exception:
            html = ""
    urls: list[str] = []
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    for href in hrefs:
        lower = href.lower()
        if "populationby" not in lower or "age" not in lower or "sex" not in lower:
            continue
        if not (lower.endswith(".csv.gz") or lower.endswith(".zip")):
            continue
        urls.append(urljoin(WPP_DOWNLOAD_PAGE, href))
    urls.extend(WPP_AGE_SEX_CANDIDATES)
    unique = list(dict.fromkeys(urls))
    return sorted(
        unique,
        key=lambda url: (
            "singleage" not in url.lower(),
            "medium" not in url.lower(),
            url,
        ),
    )


def resolve_wpp_age_sex_url() -> str:
    errors: list[str] = []
    for url in discover_wpp_age_sex_urls():
        try:
            response = SESSION.get(url, stream=True, timeout=60)
            if response.ok:
                response.close()
                return url
            errors.append(f"HTTP {response.status_code}: {url}")
            response.close()
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {url}")
    raise RuntimeError("Nessun file WPP age-sex ufficiale raggiungibile. " + "; ".join(errors))


def download_wpp_age_sex(
    target_dir: Path,
    refresh: bool = False,
    url: str | None = None,
) -> Path:
    source_url = url or resolve_wpp_age_sex_url()
    filename = Path(source_url.split("?", 1)[0]).name or "WPP2024_age_sex.csv.gz"
    return download_file(source_url, target_dir / filename, refresh=refresh, timeout=1800)
