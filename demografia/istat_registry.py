from __future__ import annotations

import pandas as pd

from demografia.sources import istat

ROLE_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "population_age_sex": {
        "required": ("popolazione",),
        "preferred": ("residente", "età", "sesso"),
        "excluded": ("prevision",),
    },
    "demographic_balance": {
        "required": ("bilancio", "demograf"),
        "preferred": ("comun", "movimento"),
        "excluded": ("prevision",),
    },
    "births": {
        "required": ("nasc",),
        "preferred": ("madre", "ordine", "età"),
        "excluded": ("prevision",),
    },
    "deaths": {
        "required": ("decess",),
        "preferred": ("età", "sesso"),
        "excluded": ("cause", "prevision"),
    },
    "internal_migration": {
        "required": ("trasferimenti", "residenza"),
        "preferred": ("origine", "destinazione", "età", "sesso"),
        "excluded": (),
    },
    "international_migration": {
        "required": ("migraz",),
        "preferred": ("estero", "cittadinanza", "provenienza", "destinazione"),
        "excluded": ("intern",),
    },
    "foreign_population": {
        "required": ("popolazione", "stranier"),
        "preferred": ("cittadinanza", "paese di nascita", "età", "sesso"),
        "excluded": ("prevision",),
    },
    "population_projections": {
        "required": ("prevision", "popolazione"),
        "preferred": ("età", "sesso", "regione", "comune"),
        "excluded": (),
    },
}


def _text(frame: pd.DataFrame) -> pd.Series:
    name = frame["name"].fillna("").astype(str) if "name" in frame else ""
    identifier = frame["dataflow_id"].fillna("").astype(str)
    return (name + " " + identifier).str.casefold()


def score_istat_dataflows(dataflows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "role",
        "dataflow_id",
        "name",
        "agency",
        "version",
        "score",
        "required_match",
        "selected",
        "ambiguous",
    ]
    if dataflows.empty:
        return pd.DataFrame(columns=columns)
    source = dataflows.copy()
    text = _text(source)
    outputs: list[pd.DataFrame] = []
    for role, rules in ROLE_RULES.items():
        required = rules["required"]
        preferred = rules["preferred"]
        excluded = rules["excluded"]
        required_mask = pd.Series(True, index=source.index)
        for term in required:
            required_mask &= text.str.contains(term.casefold(), regex=False)
        excluded_mask = pd.Series(False, index=source.index)
        for term in excluded:
            excluded_mask |= text.str.contains(term.casefold(), regex=False)
        candidates = source[required_mask & ~excluded_mask].copy()
        if candidates.empty:
            continue
        candidate_text = _text(candidates)
        candidates["score"] = 100 * len(required)
        for term in preferred:
            candidates["score"] += candidate_text.str.contains(term.casefold(), regex=False).astype(int) * 10
        candidates["role"] = role
        candidates["required_match"] = True
        best_score = candidates["score"].max()
        best = candidates["score"].eq(best_score)
        candidates["selected"] = best
        candidates["ambiguous"] = bool(best.sum() > 1)
        for column in ("agency", "version", "name"):
            if column not in candidates:
                candidates[column] = ""
        outputs.append(candidates[columns])
    return pd.concat(outputs, ignore_index=True) if outputs else pd.DataFrame(columns=columns)


def build_istat_registry(dataflows_frame: pd.DataFrame | None = None) -> pd.DataFrame:
    return score_istat_dataflows(istat.dataflows() if dataflows_frame is None else dataflows_frame)


def resolve_istat_role(registry: pd.DataFrame, role: str) -> dict[str, object]:
    candidates = registry[registry["role"].eq(role) & registry["selected"]].copy()
    if candidates.empty:
        raise LookupError(f"Nessun dataflow ISTAT risolto per il ruolo {role}")
    if candidates["ambiguous"].any() or len(candidates) != 1:
        identifiers = ", ".join(candidates["dataflow_id"].astype(str))
        raise LookupError(f"Risoluzione ISTAT ambigua per {role}: {identifiers}")
    row = candidates.iloc[0]
    return {
        "role": role,
        "dataflow_id": str(row["dataflow_id"]),
        "name": str(row["name"]),
        "agency": str(row["agency"] or "IT1"),
        "version": str(row["version"] or "latest"),
        "score": int(row["score"]),
        "ambiguous": False,
    }
