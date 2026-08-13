from __future__ import annotations

from collections.abc import Callable
from multiprocessing import get_context
from multiprocessing.queues import Queue
from pathlib import Path
from typing import Iterable, TypeVar

import pandas as pd

T = TypeVar("T")


def is_none_code(value: object) -> bool:
    """Return True when a user parameter explicitly disables a comparison."""
    return str(value or "").strip().lower() in {"", "none"}


def normalize_country_code(code: object) -> str:
    """Return an uppercase ISO3 country code from a simple or prefixed value.

    Users should write `ITA` or `ESP`. Older examples used values such as
    `country:ITA`; this helper keeps those values valid while hiding the
    internal prefix from user-facing parameter blocks.
    """
    if is_none_code(code):
        return "none"
    text = str(code).strip()
    if ":" in text:
        text = text.split(":", 1)[1]
    return text.upper()


def normalize_eurostat_geo_code(code: object) -> str:
    """Return the Eurostat geo code matching a user-facing country or NUTS code.

    Users can write `ITA`, `ESP`, `ITC4` or `ITC4C`. Eurostat country extracts
    require two-letter country codes such as `IT` and `ES`; NUTS regional and
    provincial codes already use the Eurostat form and are returned unchanged.
    """
    if is_none_code(code):
        return "none"
    text = str(code).strip()
    if ":" in text:
        text = text.split(":", 1)[1]
    text = text.upper()
    if text.startswith("IT") and len(text) in {4, 5}:
        return text
    if len(text) == 2:
        return text

    from demografia.config import EUROSTAT_TO_ISO3

    iso3_to_eurostat = {iso3: eurostat for eurostat, iso3 in EUROSTAT_TO_ISO3.items() if len(eurostat) == 2}
    iso3_to_eurostat["GRC"] = "EL"
    return iso3_to_eurostat.get(text, text)


def normalize_territory_key(territory: object, default_level: str = "country") -> str:
    """Return the internal territory key used by the chart functions.

    Accepted user-facing values are simple codes:

    - `ITA`, `ESP`, `FRA` for countries;
    - `ITC4`, `ITI4` for Italian regions;
    - `ITC4C`, `ITC11` for Italian provinces.

    Existing prefixed values such as `country:ITA` remain supported. The
    returned value always uses the internal `level:code` form so the rest of the
    code can filter tables consistently.
    """
    if is_none_code(territory):
        return "none"
    text = str(territory).strip()
    if ":" in text:
        level, code = text.split(":", 1)
        return f"{level.lower()}:{code.upper()}"

    code = text.upper()
    if code.startswith("IT") and len(code) == 4:
        return f"region:{code}"
    if code.startswith("IT") and len(code) == 5:
        return f"province:{code}"
    return f"{default_level}:{code}"


def split_territory_key(territory: object, default_level: str = "country") -> tuple[str, str]:
    """Split a simple or prefixed territory value into level and code."""
    key = normalize_territory_key(territory, default_level=default_level)
    if key == "none":
        return "none", "none"
    return key.split(":", 1)


def _country_label(code: str) -> str:
    """Return the Italian label for a country code without exposing source details."""
    from demografia.config import COUNTRY_NAMES

    country = normalize_country_code(code)
    return COUNTRY_NAMES.get(country, country)


def regional_options(tables: dict[str, pd.DataFrame], level: str = "province") -> pd.DataFrame:
    """Return available Italian regions or provinces from final tables."""
    frames = []
    for name in ("regional_balance", "regional_fertility", "regional_age_structure"):
        table = tables.get(name, pd.DataFrame())
        if {"geo_level", "geo_code", "geo_name"}.issubset(table.columns):
            frames.append(table[["geo_level", "geo_code", "geo_name"]])
    options = pd.concat(frames, ignore_index=True).drop_duplicates() if frames else pd.DataFrame()
    return options[options["geo_level"].eq(level)].sort_values("geo_name")


def _year_bounds(years: pd.Series) -> tuple[int | None, int | None]:
    """Return first and last available year for a table slice."""
    numeric = pd.to_numeric(years, errors="coerce").dropna()
    if numeric.empty:
        return None, None
    return int(numeric.min()), int(numeric.max())


def _territory_year_bounds(tables: dict[str, pd.DataFrame], level: str, code: str) -> tuple[int | None, int | None]:
    """Collect the broadest year span available for one Italian territory."""
    pieces = []
    for name in ("regional_balance", "regional_fertility", "regional_age_structure", "regional_population"):
        table = tables.get(name, pd.DataFrame())
        if table.empty or "geo_code" not in table or "year" not in table:
            continue
        match = table["geo_code"].astype(str).eq(code)
        if "geo_level" in table:
            match &= table["geo_level"].astype(str).eq(level)
        years = table.loc[match, "year"]
        if not years.empty:
            pieces.append(years)
    return _year_bounds(pd.concat(pieces, ignore_index=True)) if pieces else (None, None)


def parametri_paesi(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return country codes available to users.

    The `codice` column is the value to copy into parameters, for example `ITA`
    or `ESP`. No internal prefix is needed.
    """
    from demografia.config import EU27_ISO3

    rows = tables.get("age_structure", pd.DataFrame())
    columns = ["codice", "nome", "primo_anno", "ultimo_anno"]
    if rows.empty or "iso3" not in rows:
        return pd.DataFrame(columns=columns)
    available = sorted(set(rows["iso3"].dropna().astype(str)) & set(EU27_ISO3))
    if not available:
        available = sorted(rows["iso3"].dropna().astype(str).unique())
    records = []
    for code in available:
        first_year, last_year = _year_bounds(rows.loc[rows["iso3"].astype(str).eq(code), "year"])
        records.append({"codice": code, "nome": _country_label(code), "primo_anno": first_year, "ultimo_anno": last_year})
    return pd.DataFrame(records, columns=columns).sort_values("nome").reset_index(drop=True)


def _parametri_territoriali(tables: dict[str, pd.DataFrame], level: str) -> pd.DataFrame:
    """Return parameter rows for Italian regions or provinces."""
    options = regional_options(tables, level)
    columns = ["codice", "nome", "primo_anno", "ultimo_anno"]
    if options.empty:
        return pd.DataFrame(columns=columns)
    records = []
    for _, row in options.iterrows():
        code = str(row["geo_code"])
        first_year, last_year = _territory_year_bounds(tables, level, code)
        records.append(
            {
                "codice": code,
                "nome": str(row["geo_name"]),
                "primo_anno": first_year,
                "ultimo_anno": last_year,
            }
        )
    return pd.DataFrame(records, columns=columns).drop_duplicates().sort_values("nome").reset_index(drop=True)


def parametri_regioni(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return Italian region codes available to users."""
    return _parametri_territoriali(tables, "region")


def parametri_province(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return Italian province codes available to users."""
    return _parametri_territoriali(tables, "province")


def parametri_aree_istruzione_migranti(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return geographic codes available in the migrant-education table."""
    rows = tables.get("migrant_education", pd.DataFrame())
    columns = ["codice", "nome", "livello", "primo_anno", "ultimo_anno"]
    if rows.empty or not {"geo_code", "geo_name", "geo_level", "year"}.issubset(rows.columns):
        return pd.DataFrame(columns=columns)
    records = []
    for (code, name, level), group in rows.groupby(["geo_code", "geo_name", "geo_level"], dropna=False):
        first_year, last_year = _year_bounds(group["year"])
        display_code = str(code)
        if str(level) == "country" and "iso3" in group and group["iso3"].notna().any():
            display_code = str(group["iso3"].dropna().iloc[0])
        records.append(
            {
                "codice": display_code,
                "nome": str(name),
                "livello": str(level),
                "primo_anno": first_year,
                "ultimo_anno": last_year,
            }
        )
    return pd.DataFrame(records, columns=columns).sort_values(["livello", "nome"]).reset_index(drop=True)


def _tag_parameter_rows(frame: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Add a user-facing parameter family label to a parameter table."""
    if frame.empty:
        return pd.DataFrame(columns=["tipo", *frame.columns.tolist()])
    result = frame.copy()
    result.insert(0, "tipo", tipo)
    return result


def parametri_disponibili(
    tables: dict[str, pd.DataFrame],
    include_paesi: bool = True,
    include_regioni: bool = True,
    include_province: bool = True,
    include_aree_istruzione_migranti: bool = False,
) -> pd.DataFrame:
    """Return one flat table of codes that can be used in user parameters."""
    pieces = []
    if include_paesi:
        pieces.append(_tag_parameter_rows(parametri_paesi(tables), "paese"))
    if include_regioni:
        pieces.append(_tag_parameter_rows(parametri_regioni(tables), "regione"))
    if include_province:
        pieces.append(_tag_parameter_rows(parametri_province(tables), "provincia"))
    if include_aree_istruzione_migranti:
        pieces.append(_tag_parameter_rows(parametri_aree_istruzione_migranti(tables), "area istruzione migranti"))
    pieces = [piece for piece in pieces if not piece.empty]
    return pd.concat(pieces, ignore_index=True, sort=False) if pieces else pd.DataFrame()


def chunks(values: list[T], size: int) -> Iterable[list[T]]:
    """Yield fixed-size chunks while preserving input order."""
    for start in range(0, len(values), size):
        yield values[start : start + size]


def save_table(frame: pd.DataFrame, path: Path) -> Path:
    """Write a table in both Parquet and CSV formats.

    Parquet is the canonical analytical format. CSV is emitted alongside it so
    the same output can be inspected quickly in spreadsheet tools or plain text.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    frame.to_csv(path.with_suffix(".csv"), index=False)
    return path


def save_csv(frame: pd.DataFrame, path: Path) -> Path:
    """Write a CSV file after creating the target directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def print_outputs(outputs: dict[str, Path]) -> None:
    """Print output labels and paths in deterministic order."""
    for name, path in sorted(outputs.items()):
        print(f"{name}: {path}")


def check_call(name: str, call: Callable[[], object]) -> dict[str, object]:
    """Execute a check function and normalize success or failure metadata."""
    try:
        value = call()
        records = len(value) if hasattr(value, "__len__") else None
        return {"source": name, "status": "ok", "records": records, "message": ""}
    except Exception as exc:
        return {
            "source": name,
            "status": "error",
            "records": None,
            "message": f"{type(exc).__name__}: {exc}",
        }


def _check_call_worker(name: str, call: Callable[[], object], queue: Queue) -> None:
    queue.put(check_call(name, call))


def check_call_in_process(
    name: str,
    call: Callable[[], object],
    timeout: int,
) -> dict[str, object]:
    """Execute a check in a child process and enforce a hard timeout."""
    context = get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_check_call_worker, args=(name, call, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "source": name,
            "status": "timeout",
            "records": None,
            "message": f"Timeout dopo {timeout} secondi",
        }
    if not queue.empty():
        return queue.get()
    return {
        "source": name,
        "status": "error",
        "records": None,
        "message": f"Processo terminato con codice {process.exitcode}",
    }
