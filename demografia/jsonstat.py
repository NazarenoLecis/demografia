from __future__ import annotations

from itertools import product
from typing import Any

import pandas as pd


def _ordered_codes(index: dict[str, int] | list[str]) -> list[str]:
    if isinstance(index, list):
        return index
    return [code for code, _ in sorted(index.items(), key=lambda item: item[1])]


def jsonstat_to_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert a Eurostat JSON-stat 2 response to a tidy DataFrame."""
    if "id" not in payload or "size" not in payload or "dimension" not in payload:
        raise ValueError("Risposta JSON-stat priva di id, size o dimension")

    dimensions = list(payload["id"])
    sizes = list(payload["size"])
    if len(dimensions) != len(sizes):
        raise ValueError("Numero di dimensioni incompatibile con size")

    codes: dict[str, list[str]] = {}
    labels: dict[str, dict[str, str]] = {}
    for dimension in dimensions:
        category = payload["dimension"][dimension]["category"]
        codes[dimension] = _ordered_codes(category["index"])
        labels[dimension] = category.get("label", {})

    values = payload.get("value", {})
    statuses = payload.get("status", {})
    rows: list[dict[str, Any]] = []

    for flat_index, coordinate in enumerate(product(*[range(size) for size in sizes])):
        key = str(flat_index)
        if isinstance(values, dict):
            if key not in values and flat_index not in values:
                continue
            value = values.get(key, values.get(flat_index))
        else:
            value = values[flat_index]
        if value is None:
            continue

        row: dict[str, Any] = {}
        for dimension, position in zip(dimensions, coordinate, strict=True):
            code = codes[dimension][position]
            row[dimension] = code
            row[f"{dimension}_label"] = labels[dimension].get(code, code)
        row["value"] = value
        if isinstance(statuses, dict):
            row["status_flag"] = statuses.get(key, statuses.get(flat_index))
        rows.append(row)

    return pd.DataFrame(rows)
