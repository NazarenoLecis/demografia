from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from demografia.config import COUNTRY_NAMES, EU27_ISO3, FINAL_DIR, ROOT_DIR
from demografia.utils import (
    normalize_country_code,
    normalize_eurostat_geo_code,
    normalize_territory_key,
    parametri_aree_istruzione_migranti,
    parametri_disponibili,
    parametri_paesi,
    parametri_province,
    parametri_regioni,
    regional_options,
    split_territory_key,
)


TABLE_FILES = {
    "population": "population_age_sex_observed_projected",
    "age_structure": "age_structure_indicators",
    "fertility": "fertility_indicators",
    "balance": "demographic_balance",
    "education": "education_attainment",
    "life_expectancy": "life_expectancy",
    "regional_population": "italy_regional_population_age_sex",
    "regional_age_structure": "italy_regional_age_structure",
    "regional_balance": "italy_regional_demographic_balance",
    "regional_fertility": "italy_regional_fertility",
    "immigrant_population": "immigrant_population_age_sex",
}

OPTIONAL_TABLE_FILES = {
    "immigration": "immigration_profile",
    "emigration": "emigration_profile",
    "immigration_citizenship": "immigration_citizenship_profile",
    "emigration_citizenship": "emigration_citizenship_profile",
    "population_by_citizenship": "population_by_citizenship",
    "population_by_country_of_birth": "population_by_country_of_birth",
    "migrant_education": "migrant_education_by_birth_region",
    "migrant_tertiary": "migrant_tertiary_share",
    "internal_migration_flows": "italy_internal_migration_flows",
    "internal_migration_balances": "italy_internal_migration_balances",
}

METRICS = {
    "population_total": {"label": "Popolazione totale", "axis": "Milioni", "scale": 1_000_000},
    "share_0_14": {"label": "Quota 0-14", "axis": "% popolazione"},
    "share_15_64": {"label": "Quota 15-64", "axis": "% popolazione"},
    "share_65_plus": {"label": "Quota 65+", "axis": "% popolazione"},
    "share_80_plus": {"label": "Quota 80+", "axis": "% popolazione"},
    "mean_age": {"label": "Età media", "axis": "Anni"},
    "median_age": {"label": "Età mediana", "axis": "Anni"},
    "dependency_youth": {"label": "Dipendenza giovanile", "axis": "0-14 ogni 100 persone 15-64"},
    "dependency_old": {"label": "Dipendenza anziani", "axis": "65+ ogni 100 persone 15-64"},
    "dependency_total": {"label": "Dipendenza totale", "axis": "Dipendenti ogni 100 persone 15-64"},
    "life_expectancy_birth": {"label": "Speranza di vita alla nascita", "axis": "Anni"},
    "life_expectancy_65": {"label": "Speranza di vita a 65 anni", "axis": "Anni residui"},
    "live_births": {"label": "Nati vivi", "axis": "Migliaia", "scale": 1_000},
    "deaths": {"label": "Decessi", "axis": "Migliaia", "scale": 1_000},
    "natural_change": {"label": "Saldo naturale", "axis": "Migliaia", "scale": 1_000},
    "net_migration_adjustment": {"label": "Saldo migratorio", "axis": "Migliaia", "scale": 1_000},
    "population_change": {"label": "Variazione popolazione", "axis": "Migliaia", "scale": 1_000},
    "total_fertility_rate": {"label": "Fecondità", "axis": "Figli per donna"},
    "balance_gbirthrt": {"label": "Natalità", "axis": "Nati per 1.000 abitanti"},
    "tertiary_25_64": {"label": "Laurea 25-64", "axis": "% popolazione 25-64"},
}

EDUCATION_LABELS = {
    "low_education": "Fino alla licenza media",
    "upper_secondary_or_more": "Secondaria o terziaria",
    "upper_secondary_post_secondary": "Secondaria superiore",
    "upper_secondary_general": "Secondaria generale",
    "upper_secondary_vocational": "Secondaria professionale",
    "tertiary": "Terziario",
}

EDUCATION_ORDER = {
    "low_education": 10,
    "upper_secondary_post_secondary": 20,
    "upper_secondary_general": 30,
    "upper_secondary_vocational": 40,
    "tertiary": 50,
    "upper_secondary_or_more": 60,
}

BIRTH_GROUP_LABELS = {
    "NAT": "Nati nel paese",
    "FOR": "Nati all'estero",
    "EU27_2020_FOR": "Nati in altri paesi UE27",
    "NEU27_2020_FOR": "Nati fuori UE27",
}

CITIZENSHIP_GROUP_LABELS = {
    "NAT": "Cittadini del paese",
    "EU27_2020_FOR": "Cittadini altri paesi UE27",
    "NEU27_2020_FOR": "Cittadini paesi extra UE27",
    "FOR_STLS": "Cittadini stranieri o apolidi",
    "STLS": "Apolidi",
    "TOTAL": "Totale",
}

STOCK_CATEGORY_LABELS = {
    "AFR": "Africa",
    "AFR_C": "Africa centrale",
    "AFR_E": "Africa orientale",
    "AFR_N": "Africa settentrionale",
    "AFR_S": "Africa meridionale",
    "AFR_W": "Africa occidentale",
    "AME": "America",
    "AME_C": "America centrale",
    "AME_N": "America settentrionale",
    "AME_S": "America meridionale",
    "ASI": "Asia",
    "ASI_C": "Asia centrale",
    "ASI_E": "Asia orientale",
    "ASI_S": "Asia meridionale",
    "ASI_S_E": "Asia sud-orientale",
    "ASI_W": "Asia occidentale",
    "AU_NZ": "Australia e Nuova Zelanda",
    "CC9_23_FOR": "Paesi candidati UE",
    "CRB": "Caraibi",
    "CZ_SK": "Cecoslovacchia",
    "EFTA_FOR": "Paesi EFTA",
    "EU27_2020_FOR": "Altri paesi UE27",
    "EUR": "Europa",
    "EX_SU": "Ex Unione Sovietica",
    "EX_YU": "Ex Jugoslavia",
    "FOR": "Nati all'estero",
    "FOR_STLS": "Cittadini stranieri o apolidi",
    "MEL": "Melanesia",
    "MIC": "Micronesia",
    "NAT": "Nati nel paese / cittadini del paese",
    "NEU27_2020_FOR": "Paesi extra UE27",
    "OCE": "Oceania",
    "OTH": "Altro",
    "POL": "Polinesia",
    "RNC": "Cittadinanza non riconosciuta",
    "RS_ME": "Serbia e Montenegro",
    "STLS": "Apolidi",
    "TOTAL": "Totale residenti",
    "UNK": "Sconosciuto",
    "XK": "Kosovo",
}

STOCK_ALPHA2_LABELS = {
    "AD": "Andorra",
    "AE": "Emirati Arabi Uniti",
    "AF": "Afghanistan",
    "AL": "Albania",
    "AM": "Armenia",
    "AO": "Angola",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "AZ": "Azerbaigian",
    "BA": "Bosnia-Erzegovina",
    "BD": "Bangladesh",
    "BE": "Belgio",
    "BG": "Bulgaria",
    "BR": "Brasile",
    "BY": "Bielorussia",
    "CA": "Canada",
    "CH": "Svizzera",
    "CL": "Cile",
    "CN": "Cina",
    "CO": "Colombia",
    "CU": "Cuba",
    "DE": "Germania",
    "DK": "Danimarca",
    "DZ": "Algeria",
    "EC": "Ecuador",
    "EE": "Estonia",
    "EG": "Egitto",
    "EL": "Grecia",
    "ES": "Spagna",
    "ET": "Etiopia",
    "FI": "Finlandia",
    "FR": "Francia",
    "GE": "Georgia",
    "GH": "Ghana",
    "HR": "Croazia",
    "HU": "Ungheria",
    "IE": "Irlanda",
    "IL": "Israele",
    "IN": "India",
    "IQ": "Iraq",
    "IR": "Iran",
    "IT": "Italia",
    "JP": "Giappone",
    "KR": "Corea del Sud",
    "LK": "Sri Lanka",
    "MA": "Marocco",
    "MD": "Moldova",
    "MK": "Macedonia del Nord",
    "MX": "Messico",
    "NG": "Nigeria",
    "NL": "Paesi Bassi",
    "PE": "Peru",
    "PH": "Filippine",
    "PK": "Pakistan",
    "PL": "Polonia",
    "PT": "Portogallo",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "SE": "Svezia",
    "SI": "Slovenia",
    "SK": "Slovacchia",
    "SN": "Senegal",
    "SY": "Siria",
    "TN": "Tunisia",
    "TR": "Turchia",
    "UA": "Ucraina",
    "UK": "Regno Unito",
    "US": "Stati Uniti",
    "VE": "Venezuela",
}

STOCK_AGGREGATE_CODES = set(STOCK_CATEGORY_LABELS) - {"XK"}

SOURCE_NOTES = {
    "population": "Fonte: Eurostat demo_pjan e proj_23np.<br>Elaborazione di Nazareno Lecis.",
    "age": "Fonte: Eurostat demo_pjan e proj_23np.<br>Elaborazione di Nazareno Lecis.",
    "regional": "Fonte: Eurostat demo_r_pjangroup, demo_r_gind3 e demo_r_find3.<br>Elaborazione di Nazareno Lecis.",
    "fertility": "Fonte: Eurostat demo_frate, demo_gind e demo_r_find3.<br>Elaborazione di Nazareno Lecis.",
    "balance": "Fonte: Eurostat demo_gind e demo_r_gind3.<br>Elaborazione di Nazareno Lecis.",
    "migration": "Fonte: Eurostat demo_gind e demo_r_gind3.<br>Elaborazione di Nazareno Lecis.",
    "migration_flows": (
        "Fonte: Eurostat migr_imm1ctz e migr_emi1ctz.<br>Elaborazione di Nazareno Lecis.<br>"
        "Nota: flussi annuali per età, sesso e cittadinanza; la cittadinanza estera è distinta tra UE27 ed extra UE27."
    ),
    "migrant_stock": (
        "Fonte: Eurostat migr_pop1ctz e migr_pop3ctb.<br>Elaborazione di Nazareno Lecis.<br>"
        "Nota: le tavole mostrano distribuzioni separate per cittadinanza e paese di nascita; "
        "la vista per nazioni esclude continenti e aggregati UE/extra UE."
    ),
    "education": (
        "Fonte: Eurostat edat_lfse_03.<br>Elaborazione di Nazareno Lecis.<br>"
        "Nota: secondaria generale = ISCED 34/44; professionale = ISCED 35/45; "
        "ED0-2 non separa primaria e secondaria inferiore."
    ),
    "migrant_education": (
        "Fonte: Eurostat edat_lfs_9917.<br>Elaborazione di Nazareno Lecis.<br>"
        "Nota: quote LFS sulla popolazione in famiglie private per paese di nascita e regione NUTS2; "
        "non sono flussi annui di ingresso."
    ),
    "internal_migration": (
        "Fonte: ISTAT, trasferimenti di residenza quando disponibili nel registro ufficiale.<br>"
        "Elaborazione di Nazareno Lecis."
    ),
    "life_expectancy": (
        "Fonte: Eurostat demo_mlexpec.<br>Elaborazione di Nazareno Lecis.<br>"
        "Nota: la speranza di vita è una misura di periodo; a 65 anni indica gli anni residui attesi."
    ),
    "europe": "Fonte: Eurostat, paesi UE27 disponibili.<br>Elaborazione di Nazareno Lecis.",
    "immigrant": "Fonte: Eurostat migr_pop3ctb.<br>Elaborazione di Nazareno Lecis.",
}


def read_final_table(final_dir: Path, table_name: str) -> pd.DataFrame:
    """Read a final table from Parquet, falling back to CSV when needed.

    Parameters
    ----------
    final_dir:
        Directory that contains the pipeline final tables.
    table_name:
        File stem without extension, for example `age_structure_indicators`.
    """
    parquet_path = final_dir / f"{table_name}.parquet"
    csv_path = final_dir / f"{table_name}.csv"
    if parquet_path.is_file():
        return pd.read_parquet(parquet_path)
    if csv_path.is_file():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(f"Tabella finale non trovata: {parquet_path} o {csv_path}")


def load_notebook_tables(final_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load the tables used by the notebook charts.

    Parameters
    ----------
    final_dir:
        Optional output directory. When omitted, the repository default
        `output/data/final` is used.
    """
    base_dir = final_dir or FINAL_DIR
    tables = {key: read_final_table(base_dir, filename) for key, filename in TABLE_FILES.items()}
    for key, filename in OPTIONAL_TABLE_FILES.items():
        try:
            tables[key] = read_final_table(base_dir, filename)
        except FileNotFoundError:
            # Optional thematic tables are generated only when the related
            # source is enabled. Empty frames let notebooks stay runnable.
            tables[key] = pd.DataFrame()
    return tables


def country_name(iso3: str) -> str:
    """Return the Italian country label used in the charts."""
    code = normalize_country_code(iso3)
    return COUNTRY_NAMES.get(code, code)


def birth_group_label(code: str) -> str:
    """Return a readable label for a country-of-birth group."""
    return BIRTH_GROUP_LABELS.get(str(code), str(code))


def citizenship_group_label(code: str) -> str:
    """Return a readable label for a citizenship group."""
    return CITIZENSHIP_GROUP_LABELS.get(str(code), str(code))


def as_number(value: Any) -> float | None:
    """Convert a value to float and return None for missing/non-numeric values."""
    if value is None or value is pd.NA:
        return None
    parsed = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(parsed) else float(parsed)


def scaled_series(values: pd.Series, metric: str) -> pd.Series:
    """Scale a metric for display without changing the source data."""
    scale = METRICS.get(metric, {}).get("scale")
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric / scale if scale else numeric


def metric_source_key(metric: str) -> str:
    """Return the source-note family that matches a plotted metric."""
    if metric in {"live_births", "deaths", "natural_change", "net_migration_adjustment", "population_change"}:
        return "balance"
    if metric in {"total_fertility_rate", "balance_gbirthrt"}:
        return "fertility"
    if metric == "tertiary_25_64":
        return "education"
    return "population"


def base_layout(title: str, source_note: str, height: int = 560) -> dict[str, Any]:
    """Return a shared Plotly layout with source note in the lower-left corner."""
    return {
        "title": {"text": title, "x": 0.0, "xanchor": "left"},
        "template": "plotly_white",
        "height": height,
        "margin": {"l": 70, "r": 40, "t": 78, "b": 96},
        "legend": {"orientation": "h", "y": -0.16, "x": 0.0, "xanchor": "left"},
        "annotations": [
            {
                "text": source_note,
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": -0.24,
                "showarrow": False,
                "xanchor": "left",
                "yanchor": "top",
                "align": "left",
                "font": {"size": 11},
            }
        ],
    }


def apply_layout(fig: go.Figure, title: str, source_note: str, height: int = 560) -> go.Figure:
    """Apply the shared notebook chart layout to an existing figure."""
    fig.update_layout(**base_layout(title, source_note, height=height))
    return fig


def complete_age_coverage(row: pd.Series) -> bool:
    """Keep only age distributions that cover the full age span."""
    age_min = as_number(row.get("age_min"))
    age_max = as_number(row.get("age_max"))
    age_classes = as_number(row.get("age_classes"))
    if age_min is None or age_max is None or age_classes is None:
        return True
    return age_min <= 0 and age_max >= 85 and age_classes >= 16


def continuous_country_scope(row: pd.Series) -> bool:
    """Avoid drawing pre-1991 Germany as a continuous country series."""
    year = as_number(row.get("year"))
    return not (row.get("iso3") == "DEU" and year is not None and year < 1991)


def preferred_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Prefer observed rows over projected rows when both exist for a year."""
    if rows.empty:
        return rows.copy()
    order = rows.assign(
        _status_priority=np.where(rows["status"].astype(str).eq("observed"), 1, 0)
        if "status" in rows
        else 0
    )
    order = order.sort_values(["year", "_status_priority"])
    return order.drop_duplicates("year", keep="last").drop(columns="_status_priority")


def territory_label(tables: dict[str, pd.DataFrame], territory: str) -> str:
    """Return a label for a country, region, or province code."""
    level, code = split_territory_key(territory)
    if level == "none":
        return "Nessun confronto"
    if level == "country":
        return country_name(code)
    for table_name in ("regional_age_structure", "regional_balance", "regional_fertility"):
        table = tables.get(table_name, pd.DataFrame())
        if "geo_code" not in table:
            continue
        match = table[table["geo_code"].astype(str).eq(code)]
        if not match.empty:
            return str(match.iloc[0].get("geo_name") or code)
    return code


def age_rows(tables: dict[str, pd.DataFrame], territory: str) -> pd.DataFrame:
    """Return age-structure rows for a country or Italian region."""
    level, code = split_territory_key(territory)
    if level == "country":
        rows = tables["age_structure"][tables["age_structure"]["iso3"].eq(code)].copy()
        if rows.empty:
            return rows
        rows = rows[rows.apply(complete_age_coverage, axis=1)]
        rows = rows[rows.apply(continuous_country_scope, axis=1)]
        return rows.sort_values("year")
    rows = tables["regional_age_structure"][tables["regional_age_structure"]["geo_code"].eq(code)].copy()
    if rows.empty:
        return rows
    rows = rows[rows.apply(complete_age_coverage, axis=1)]
    return rows.sort_values("year")


def balance_rows(tables: dict[str, pd.DataFrame], territory: str) -> pd.DataFrame:
    """Return demographic-balance rows for a country, region, or province."""
    level, code = split_territory_key(territory)
    if level == "country":
        rows = tables["balance"][tables["balance"]["iso3"].eq(code)].copy()
        rows = rows[rows.apply(continuous_country_scope, axis=1)]
        return rows.sort_values("year")
    rows = tables["regional_balance"]
    return rows[(rows["geo_level"].eq(level)) & (rows["geo_code"].eq(code))].copy().sort_values("year")


def fertility_rows(tables: dict[str, pd.DataFrame], territory: str, indicator: str) -> pd.DataFrame:
    """Return fertility or birth-rate rows for a selected territory."""
    level, code = split_territory_key(territory)
    if level == "country":
        rows = tables["fertility"][tables["fertility"]["iso3"].eq(code)].copy()
        rows = rows[rows.apply(continuous_country_scope, axis=1)]
    else:
        source = tables["regional_fertility"]
        rows = source[(source["geo_level"].eq(level)) & (source["geo_code"].eq(code))].copy()
    if indicator == "total_fertility_rate":
        keep = rows["indicator"].isin(["total_fertility_rate", "fertility_nr"])
    else:
        keep = rows["indicator"].eq(indicator)
    return rows[keep].sort_values("year")


def metric_rows(tables: dict[str, pd.DataFrame], territory: str, metric: str) -> pd.DataFrame:
    """Return a year/value table for the metric used in line and rank charts."""
    territory = normalize_territory_key(territory)
    if metric == "tertiary_25_64":
        level, code = split_territory_key(territory)
        if level != "country":
            return pd.DataFrame(columns=["year", "metric_value"])
        rows = tables["education"]
        rows = rows[
            rows["iso3"].eq(code)
            & rows["age_label"].astype(str).eq("25-64")
            & rows["sex"].astype(str).eq("T")
            & rows["education_level"].astype(str).eq("tertiary")
        ].copy()
        rows["metric_value"] = rows["value"]
        return rows.sort_values("year")
    if metric in {
        "population_total",
        "share_0_14",
        "share_15_64",
        "share_65_plus",
        "share_80_plus",
        "mean_age",
        "median_age",
        "dependency_youth",
        "dependency_old",
        "dependency_total",
    }:
        rows = age_rows(tables, territory)
        if metric in rows and rows[metric].notna().any():
            rows = rows.copy()
            rows["metric_value"] = rows[metric]
            return preferred_rows(rows).sort_values("year")
        if metric != "population_total":
            return pd.DataFrame(columns=["year", "metric_value"])
    if metric in {
        "population_total",
        "live_births",
        "deaths",
        "natural_change",
        "net_migration_adjustment",
        "population_change",
    }:
        rows = balance_rows(tables, territory)
        rows = rows.copy()
        rows["metric_value"] = rows.get(metric, pd.Series(np.nan, index=rows.index))
        if metric == "population_total" and rows["metric_value"].isna().all():
            rows["metric_value"] = rows.get("population_1_january", np.nan)
        return rows.sort_values("year")
    if metric in {"total_fertility_rate", "balance_gbirthrt"}:
        rows = fertility_rows(tables, territory, metric).copy()
        rows["metric_value"] = rows["value"]
        return rows.sort_values("year")
    if metric in {"life_expectancy_birth", "life_expectancy_65"}:
        level, code = split_territory_key(territory)
        if level != "country" or "life_expectancy" not in tables:
            return pd.DataFrame(columns=["year", "metric_value"])
        rows = tables["life_expectancy"]
        rows = rows[
            rows["iso3"].eq(code)
            & rows["indicator"].astype(str).eq(metric)
            & rows["sex"].astype(str).eq("T")
        ].copy()
        rows["metric_value"] = rows["value"]
        return rows.sort_values("year")
    return pd.DataFrame(columns=["year", "metric_value"])


def age_label(row: pd.Series) -> str:
    """Return a readable age label for single-year or grouped ages."""
    if pd.notna(row.get("age_label")):
        return str(row.get("age_label"))
    low = as_number(row.get("age_low"))
    high = as_number(row.get("age_high"))
    if low is None:
        return "ND"
    if high is None or low == high:
        return str(int(low))
    if high >= 120:
        return f"{int(low)}+"
    return f"{int(low)}-{int(high)}"


def finest_non_overlapping_age_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Select the finest non-overlapping age partition for each sex.

    Eurostat projection files may contain single ages and broader age groups in
    the same extract. The notebook charts must not sum those together.
    """
    if rows.empty:
        return rows.copy()
    pieces = []
    for _, sex_group in rows.groupby("sex", dropna=False):
        ordered = sex_group.assign(
            _low=pd.to_numeric(sex_group["age_low"], errors="coerce"),
            _high=pd.to_numeric(sex_group["age_high"], errors="coerce"),
        ).dropna(subset=["_low", "_high"])
        ordered["_width"] = ordered["_high"] - ordered["_low"]
        selected_indexes = []
        selected_intervals: list[tuple[float, float]] = []
        for index, row in ordered.sort_values(["_width", "_low", "_high"]).iterrows():
            low = float(row["_low"])
            high = float(row["_high"])
            overlaps = any(not (high < chosen_low or low > chosen_high) for chosen_low, chosen_high in selected_intervals)
            if not overlaps:
                selected_indexes.append(index)
                selected_intervals.append((low, high))
        pieces.append(ordered.loc[selected_indexes].drop(columns=["_low", "_high", "_width"]))
    return pd.concat(pieces, ignore_index=True) if pieces else rows.iloc[0:0].copy()


def kebab_data(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    year: int = 2024,
    population_kind: str = "total",
) -> pd.DataFrame:
    """Build a male/female age table for the Kebab chart."""
    if population_kind == "foreign_born":
        rows = tables["immigrant_population"]
        subset = rows[
            rows["iso3"].eq("ITA")
            & rows["category"].astype(str).eq("FOR")
            & rows["year"].astype(int).eq(int(year))
            & rows["sex"].isin(["M", "F"])
        ].copy()
    else:
        level, code = split_territory_key(territory)
        source = tables["regional_population"] if level == "region" else tables["population"]
        match = source["geo_code"].eq(code) if level == "region" else source["iso3"].eq(code)
        subset = source[match & source["year"].astype(int).eq(int(year)) & source["sex"].isin(["M", "F"])].copy()
        if "status" in subset:
            status = "observed" if subset["status"].eq("observed").any() else "projected"
            subset = subset[subset["status"].eq(status)]
    subset = finest_non_overlapping_age_rows(subset)
    if subset.empty:
        return pd.DataFrame(columns=["age_label", "age_low", "M", "F"])
    subset["age_label_plot"] = subset.apply(age_label, axis=1)
    wide = (
        subset.pivot_table(index=["age_low", "age_label_plot"], columns="sex", values="value", aggfunc="sum")
        .fillna(0)
        .reset_index()
        .sort_values("age_low")
    )
    for sex in ("M", "F"):
        if sex not in wide:
            wide[sex] = 0.0
    return wide.rename(columns={"age_label_plot": "age_label"})


def fig_kebab(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    year: int = 2024,
    population_kind: str = "total",
) -> go.Figure:
    """Draw the age/sex distribution for a selected year."""
    data = kebab_data(tables, territory=territory, year=year, population_kind=population_kind)
    title_kind = "nati all'estero" if population_kind == "foreign_born" else "totale residenti"
    title = f"Kebab demografico - {territory_label(tables, territory)}, {title_kind}, {year}"
    fig = go.Figure()
    fig.add_bar(
        x=-data["M"] / 1_000_000,
        y=data["age_label"],
        orientation="h",
        name="Uomini",
        hovertemplate="Età %{y}<br>Uomini %{customdata:,.0f}<extra></extra>",
        customdata=data["M"],
    )
    fig.add_bar(
        x=data["F"] / 1_000_000,
        y=data["age_label"],
        orientation="h",
        name="Donne",
        hovertemplate="Età %{y}<br>Donne %{customdata:,.0f}<extra></extra>",
        customdata=data["F"],
    )
    max_value = float(np.nanmax(np.abs(pd.concat([data["M"], data["F"]]) / 1_000_000))) if not data.empty else 1.0
    limit = max(0.1, np.ceil(max_value * 12) / 10)
    fig.update_layout(barmode="relative")
    fig.update_xaxes(title="Milioni di persone", range=[-limit, limit], tickformat=".1f")
    fig.update_yaxes(title="Età")
    return apply_layout(fig, title, SOURCE_NOTES["immigrant" if population_kind == "foreign_born" else "population"], 680)


def fig_kebab_animation(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    start_year: int = 1960,
    end_year: int = 2050,
    step: int = 5,
) -> go.Figure:
    """Create a Plotly animation of the Kebab across selected years."""
    years = list(range(int(start_year), int(end_year) + 1, int(step)))
    frames = []
    max_value = 0.1
    for year in years:
        frame_data = kebab_data(tables, territory=territory, year=year)
        if frame_data.empty:
            continue
        max_value = max(max_value, float(np.nanmax(np.abs(pd.concat([frame_data["M"], frame_data["F"]]) / 1_000_000))))
        frames.append(
            go.Frame(
                name=str(year),
                data=[
                    go.Bar(x=-frame_data["M"] / 1_000_000, y=frame_data["age_label"], orientation="h", name="Uomini"),
                    go.Bar(x=frame_data["F"] / 1_000_000, y=frame_data["age_label"], orientation="h", name="Donne"),
                ],
            )
        )
    if not frames:
        return apply_layout(go.Figure(), "Kebab demografico - evoluzione", SOURCE_NOTES["population"], 680)
    fig = go.Figure(data=frames[0].data, frames=frames)
    fig.update_layout(
        barmode="relative",
        updatemenus=[
            {
                "type": "buttons",
                "x": 0,
                "y": 1.08,
                "buttons": [
                    {"label": "Avvia", "method": "animate", "args": [None, {"frame": {"duration": 650, "redraw": True}}]},
                    {"label": "Ferma", "method": "animate", "args": [[None], {"mode": "immediate"}]},
                ],
            }
        ],
        sliders=[
            {
                "steps": [
                    {"label": frame.name, "method": "animate", "args": [[frame.name], {"mode": "immediate"}]}
                    for frame in frames
                ]
            }
        ],
    )
    limit = np.ceil(max_value * 12) / 10
    fig.update_xaxes(title="Milioni di persone", range=[-limit, limit], tickformat=".1f")
    fig.update_yaxes(title="Età")
    return apply_layout(fig, "Kebab demografico - evoluzione storica e proiezioni", SOURCE_NOTES["population"], 720)


def fig_population_series(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    compare: str = "ESP",
    metric: str = "population_total",
) -> go.Figure:
    """Draw one demographic metric over time for a territory and comparison."""
    fig = go.Figure()
    for selected, dash in ((territory, "solid"), (compare, "dash")):
        if normalize_territory_key(selected) == "none":
            continue
        rows = metric_rows(tables, selected, metric)
        fig.add_scatter(
            x=rows["year"],
            y=scaled_series(rows["metric_value"], metric),
            mode="lines+markers",
            name=territory_label(tables, selected),
            line={"dash": dash},
        )
    fig.update_yaxes(title=METRICS[metric]["axis"])
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, METRICS[metric]["label"], SOURCE_NOTES[metric_source_key(metric)])


def fig_age_shares(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    compare: str = "ESP",
) -> go.Figure:
    """Draw population shares by broad age class."""
    fig = go.Figure()
    specs = [("0-14", "share_0_14"), ("15-64", "share_15_64"), ("65+", "share_65_plus"), ("80+", "share_80_plus")]
    for selected, dash in ((territory, "solid"), (compare, "dash")):
        if normalize_territory_key(selected) == "none":
            continue
        rows = preferred_rows(age_rows(tables, selected))
        for label, column in specs:
            fig.add_scatter(x=rows["year"], y=rows[column], mode="lines", name=f"{territory_label(tables, selected)} {label}", line={"dash": dash})
    fig.update_yaxes(title="% popolazione")
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, "Quote per grandi classi di età", SOURCE_NOTES["age"])


def fig_age_distribution(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    compare: str = "ESP",
) -> go.Figure:
    """Draw mean age, median age and distribution quantiles."""
    rows = preferred_rows(age_rows(tables, territory))
    fig = go.Figure()
    for label, column, dash in [
        ("P10", "age_p10", "dot"),
        ("P25", "age_p25", "dot"),
        ("Mediana", "median_age", "solid"),
        ("Media", "mean_age", "solid"),
        ("P75", "age_p75", "dot"),
        ("P90", "age_p90", "dot"),
    ]:
        fig.add_scatter(x=rows["year"], y=rows[column], mode="lines+markers", name=f"{territory_label(tables, territory)} {label}", line={"dash": dash})
    if normalize_territory_key(compare) != "none":
        comparison = preferred_rows(age_rows(tables, compare))
        fig.add_scatter(x=comparison["year"], y=comparison["median_age"], mode="lines+markers", name=f"{territory_label(tables, compare)} mediana", line={"dash": "dash"})
    fig.update_yaxes(title="Anni")
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, "Età media, mediana e quantili", SOURCE_NOTES["age"])


def fig_dependency(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    compare: str = "ESP",
) -> go.Figure:
    """Draw youth, old-age, and total dependency ratios."""
    fig = go.Figure()
    rows = preferred_rows(age_rows(tables, territory))
    fig.add_scatter(x=rows["year"], y=rows["dependency_youth"], mode="lines+markers", name=f"{territory_label(tables, territory)} giovani")
    fig.add_scatter(x=rows["year"], y=rows["dependency_old"], mode="lines+markers", name=f"{territory_label(tables, territory)} anziani")
    fig.add_scatter(x=rows["year"], y=rows["dependency_total"], mode="lines+markers", name=f"{territory_label(tables, territory)} totale")
    if normalize_territory_key(compare) != "none":
        comparison = preferred_rows(age_rows(tables, compare))
        fig.add_scatter(x=comparison["year"], y=comparison["dependency_youth"], mode="lines+markers", name=f"{territory_label(tables, compare)} giovani", line={"dash": "dash"})
        fig.add_scatter(x=comparison["year"], y=comparison["dependency_old"], mode="lines+markers", name=f"{territory_label(tables, compare)} anziani", line={"dash": "dash"})
        fig.add_scatter(x=comparison["year"], y=comparison["dependency_total"], mode="lines+markers", name=f"{territory_label(tables, compare)} totale", line={"dash": "dash"})
    fig.update_yaxes(title="Persone ogni 100 in età 15-64")
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, "Dipendenza demografica", SOURCE_NOTES["age"])


def fig_regional_rank(
    tables: dict[str, pd.DataFrame],
    level: str = "province",
    metric: str = "live_births",
    year: int | None = None,
    limit: int = 35,
) -> go.Figure:
    """Rank regions or provinces by a selected indicator."""
    territories = regional_options(tables, level)
    rows = []
    for _, territory in territories.iterrows():
        data = metric_rows(tables, f"{level}:{territory['geo_code']}", metric)
        if data.empty:
            continue
        selected_year = int(year) if year is not None else int(data["year"].max())
        selected = data[data["year"].astype(int).eq(selected_year)]
        if not selected.empty and pd.notna(selected.iloc[0]["metric_value"]):
            rows.append({"geo_name": territory["geo_name"], "value": selected.iloc[0]["metric_value"], "year": selected_year})
    table = pd.DataFrame(rows)
    if table.empty:
        fig = go.Figure()
        return apply_layout(fig, f"Classifica territoriale - {METRICS[metric]['label']}", SOURCE_NOTES["regional"], 760)
    table = table.sort_values("value", ascending=True).tail(limit)
    fig = go.Figure(
        go.Bar(
            x=scaled_series(table["value"], metric),
            y=table["geo_name"],
            orientation="h",
            name=METRICS[metric]["label"],
        )
    )
    fig.update_xaxes(title=METRICS[metric]["axis"])
    fig.update_yaxes(title="")
    title_year = int(table["year"].max()) if not table.empty else year
    return apply_layout(fig, f"Classifica territoriale - {METRICS[metric]['label']}, {title_year}", SOURCE_NOTES["regional"], 760)


def fig_regional_series(
    tables: dict[str, pd.DataFrame],
    focus: str = "ITC11",
    compare: str = "ITC4C",
    metric: str = "live_births",
) -> go.Figure:
    """Compare two regional or provincial series."""
    fig = go.Figure()
    for territory, dash in ((focus, "solid"), (compare, "dash")):
        if normalize_territory_key(territory) == "none":
            continue
        rows = metric_rows(tables, territory, metric)
        fig.add_scatter(x=rows["year"], y=scaled_series(rows["metric_value"], metric), mode="lines+markers", name=territory_label(tables, territory), line={"dash": dash})
    fig.update_yaxes(title=METRICS[metric]["axis"])
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, f"Serie territoriale - {METRICS[metric]['label']}", SOURCE_NOTES["regional"])


def fig_fertility(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    compare: str = "ESP",
) -> go.Figure:
    """Draw fertility and crude birth rate."""
    fig = go.Figure()
    for selected, dash in ((territory, "solid"), (compare, "dash")):
        if normalize_territory_key(selected) == "none":
            continue
        fertility = fertility_rows(tables, selected, "total_fertility_rate")
        birth_rate = fertility_rows(tables, selected, "balance_gbirthrt")
        fig.add_scatter(x=fertility["year"], y=fertility["value"], mode="lines+markers", name=f"{territory_label(tables, selected)} fecondità", line={"dash": dash})
        fig.add_scatter(x=birth_rate["year"], y=birth_rate["value"], mode="lines+markers", name=f"{territory_label(tables, selected)} natalità", yaxis="y2", line={"dash": dash})
    fig.update_layout(yaxis={"title": "Figli per donna"}, yaxis2={"title": "Nati per 1.000 abitanti", "overlaying": "y", "side": "right"})
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, "Natalità e fecondità", SOURCE_NOTES["fertility"])


def fig_births_deaths(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    compare: str = "ESP",
) -> go.Figure:
    """Draw births, deaths and natural balance."""
    fig = go.Figure()
    for selected, dash in ((territory, "solid"), (compare, "dash")):
        if normalize_territory_key(selected) == "none":
            continue
        rows = balance_rows(tables, selected)
        for column in ("live_births", "deaths", "natural_change"):
            fig.add_scatter(x=rows["year"], y=rows[column] / 1_000, mode="lines+markers", name=f"{territory_label(tables, selected)} {METRICS[column]['label']}", line={"dash": dash})
    fig.update_yaxes(title="Migliaia di persone")
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, "Nati, decessi e saldo naturale", SOURCE_NOTES["balance"])


def fig_migration(
    tables: dict[str, pd.DataFrame],
    territory: str = "ITA",
    compare: str = "ESP",
) -> go.Figure:
    """Draw immigration, estimated emigration and migration balance."""
    fig = go.Figure()
    rows = balance_rows(tables, territory)
    label = territory_label(tables, territory)
    if {"immigration", "net_migration_adjustment"}.issubset(rows.columns) and rows["immigration"].notna().any():
        fig.add_bar(x=rows["year"], y=rows["immigration"] / 1_000, name=f"{label} immigrazione")
        estimated_emigration = rows["immigration"] - rows["net_migration_adjustment"]
        fig.add_bar(x=rows["year"], y=-estimated_emigration / 1_000, name=f"{label} emigrazione stimata")
    fig.add_scatter(x=rows["year"], y=rows["net_migration_adjustment"] / 1_000, mode="lines+markers", name=f"{label} saldo")
    if normalize_territory_key(compare) != "none":
        comparison = balance_rows(tables, compare)
        fig.add_scatter(x=comparison["year"], y=comparison["net_migration_adjustment"] / 1_000, mode="lines+markers", name=f"{territory_label(tables, compare)} saldo", line={"dash": "dash"})
    fig.update_layout(barmode="relative")
    fig.update_yaxes(title="Migliaia di persone")
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, "Migrazioni e saldo", SOURCE_NOTES["migration"])


def _migration_flow_label(flow: str) -> str:
    """Return the chart label for a migration flow direction."""
    return "Immigrazione" if flow == "immigration" else "Emigrazione"


def migration_citizenship_rows(
    tables: dict[str, pd.DataFrame],
    flow: str = "immigration",
    country: str = "ITA",
    sex: str = "T",
    year: int | None = None,
) -> pd.DataFrame:
    """Return migration rows by age, sex, and citizenship for one country."""
    country = normalize_country_code(country)
    table_name = "immigration_citizenship" if flow == "immigration" else "emigration_citizenship"
    rows = tables.get(table_name, pd.DataFrame())
    if rows.empty or not {"iso3", "year", "sex", "value"}.issubset(rows.columns):
        return pd.DataFrame(columns=rows.columns)
    selected = rows[
        rows["iso3"].astype(str).eq(country)
        & rows["sex"].astype(str).str.upper().eq(sex)
    ].copy()
    if selected.empty:
        return selected
    selected_year = int(year) if year is not None else int(selected["year"].max())
    return selected[selected["year"].astype(int).eq(selected_year)].copy()


def _total_age_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Keep total-age rows when the table contains both totals and age groups."""
    if rows.empty or not {"age_low", "age_high"}.issubset(rows.columns):
        return rows.copy()
    total_age = rows["age_low"].isna() & rows["age_high"].isna()
    return rows[total_age].copy() if total_age.any() else rows.copy()


def _migration_year(tables: dict[str, pd.DataFrame], flow: str, country: str, sex: str, year: int | None) -> int | None:
    """Return the selected year or the latest available year for a flow."""
    country = normalize_country_code(country)
    if year is not None:
        return int(year)
    rows = migration_citizenship_rows(tables, flow=flow, country=country, sex=sex, year=None)
    if rows.empty:
        return None
    return int(rows["year"].max())


def fig_migration_age_profile(
    tables: dict[str, pd.DataFrame],
    flow: str = "immigration",
    country: str = "ITA",
    compare: str = "ESP",
    sex: str = "T",
    year: int | None = None,
) -> go.Figure:
    """Draw the age profile of immigration or emigration flows."""
    country = normalize_country_code(country)
    compare = normalize_country_code(compare)
    selected_year = _migration_year(tables, flow, country, sex, year)
    title_year = selected_year if selected_year is not None else "ND"
    fig = go.Figure()
    for iso3, dash in ((country, "solid"), (compare, "dash")):
        if iso3 == "none" or selected_year is None:
            continue
        rows = migration_citizenship_rows(tables, flow=flow, country=iso3, sex=sex, year=selected_year)
        if rows.empty or "citizenship" not in rows:
            continue
        if rows["citizenship"].astype(str).eq("TOTAL").any():
            rows = rows[rows["citizenship"].astype(str).eq("TOTAL")].copy()
        rows = rows[rows["age_low"].notna()].copy()
        if rows.empty:
            continue
        rows["age_label_plot"] = rows.apply(age_label, axis=1)
        profile = rows.groupby(["age_low", "age_label_plot"], as_index=False)["value"].sum().sort_values("age_low")
        fig.add_scatter(
            x=profile["age_label_plot"],
            y=profile["value"] / 1_000,
            mode="lines+markers",
            name=country_name(iso3),
            line={"dash": dash},
        )
    fig.update_yaxes(title="Migliaia di persone")
    fig.update_xaxes(title="Età")
    title = f"{_migration_flow_label(flow)} per età - {title_year}"
    return apply_layout(fig, title, SOURCE_NOTES["migration_flows"], 620)


def fig_migration_citizenship_profile(
    tables: dict[str, pd.DataFrame],
    flow: str = "immigration",
    country: str = "ITA",
    compare: str = "ESP",
    sex: str = "T",
    year: int | None = None,
) -> go.Figure:
    """Draw migration flows by citizenship group for one or two countries."""
    country = normalize_country_code(country)
    compare = normalize_country_code(compare)
    selected_year = _migration_year(tables, flow, country, sex, year)
    title_year = selected_year if selected_year is not None else "ND"
    order = ["NAT", "EU27_2020_FOR", "NEU27_2020_FOR"]
    fig = go.Figure()
    for iso3 in (country, compare):
        if iso3 == "none" or selected_year is None:
            continue
        rows = migration_citizenship_rows(tables, flow=flow, country=iso3, sex=sex, year=selected_year)
        rows = _total_age_rows(rows)
        rows = rows[rows["citizenship"].astype(str).isin(order)].copy() if "citizenship" in rows else rows
        if rows.empty:
            continue
        grouped = rows.groupby("citizenship", as_index=False)["value"].sum()
        values = grouped.set_index("citizenship")["value"].to_dict()
        fig.add_bar(
            x=[citizenship_group_label(code) for code in order],
            y=[values.get(code) / 1_000 if values.get(code) is not None else None for code in order],
            name=country_name(iso3),
        )
    fig.update_yaxes(title="Migliaia di persone")
    fig.update_xaxes(title="Cittadinanza")
    title = f"{_migration_flow_label(flow)} per cittadinanza - {title_year}"
    return apply_layout(fig, title, SOURCE_NOTES["migration_flows"], 620)


def stock_category_label(code: object, basis: str | None = None) -> str:
    """Return a readable label for migrant-stock categories.

    Parameters
    ----------
    code:
        Eurostat category code. Country categories usually use two-letter
        codes such as `RO`, `AL` or `MA`; aggregate categories use codes such
        as `EU27_2020_FOR`, `FOR` or `TOTAL`.
    basis:
        Optional stock dimension. Use `country_of_birth` for country of birth
        and `citizenship` for citizenship. The `NAT` code changes meaning
        depending on this dimension.
    """
    text = str(code or "").strip().upper()
    if basis == "country_of_birth" and text == "NAT":
        return "Nati nel paese"
    if basis == "citizenship" and text == "NAT":
        return "Cittadini del paese"
    if text in STOCK_CATEGORY_LABELS:
        return STOCK_CATEGORY_LABELS[text]
    if text in STOCK_ALPHA2_LABELS:
        return STOCK_ALPHA2_LABELS[text]
    return text


def _stock_table_name(basis: str) -> str:
    """Map a user-facing stock dimension to the notebook table key."""
    normalized = str(basis or "").strip().lower()
    if normalized in {"country_of_birth", "birth", "nascita", "paese_nascita"}:
        return "population_by_country_of_birth"
    if normalized in {"citizenship", "cittadinanza"}:
        return "population_by_citizenship"
    raise ValueError("basis deve essere 'country_of_birth' oppure 'citizenship'")


def _stock_basis_label(basis: str) -> str:
    """Return the Italian label for the stock dimension."""
    table_name = _stock_table_name(basis)
    return "paese di nascita" if table_name == "population_by_country_of_birth" else "cittadinanza"


def _is_stock_country_category(code: object) -> bool:
    """Return True for rows that represent a single nation rather than an aggregate."""
    text = str(code or "").strip().upper()
    return len(text) == 2 and text not in STOCK_AGGREGATE_CODES


def _stock_country_slice(
    tables: dict[str, pd.DataFrame],
    basis: str,
    country: str,
    sex: str,
    year: int | None,
) -> tuple[pd.DataFrame, int | None, float | None]:
    """Return stock rows for one country, sex and year, plus the total denominator."""
    table_name = _stock_table_name(basis)
    country = normalize_country_code(country)
    rows = tables.get(table_name, pd.DataFrame())
    columns = list(rows.columns) if not rows.empty else ["iso3", "year", "sex", "category", "value"]
    if country == "none" or rows.empty or not {"iso3", "year", "sex", "category", "value"}.issubset(rows.columns):
        return pd.DataFrame(columns=columns), None, None
    selected = rows[
        rows["iso3"].astype(str).eq(country)
        & rows["sex"].astype(str).str.upper().eq(str(sex).upper())
    ].copy()
    selected = _total_age_rows(selected)
    if selected.empty:
        return selected, None, None
    selected_year = int(year) if year is not None else int(pd.to_numeric(selected["year"], errors="coerce").max())
    selected = selected[selected["year"].astype(int).eq(selected_year)].copy()
    selected["value"] = pd.to_numeric(selected["value"], errors="coerce")
    selected = selected.dropna(subset=["value"])
    total_row = selected[selected["category"].astype(str).str.upper().eq("TOTAL")]
    total = float(total_row["value"].sum()) if not total_row.empty else float(selected["value"].sum())
    return selected, selected_year, total


def _filter_stock_detail(rows: pd.DataFrame, detail: str, selected_country: str | None = None) -> pd.DataFrame:
    """Filter stock rows according to the requested category detail."""
    mode = str(detail or "countries").strip().lower()
    if rows.empty:
        return rows.copy()
    categories = rows["category"].astype(str).str.upper()
    if mode == "countries":
        result = rows[categories.map(_is_stock_country_category)].copy()
        if selected_country is not None:
            own_country_code = normalize_eurostat_geo_code(selected_country)
            result = result[~result["category"].astype(str).str.upper().eq(own_country_code)]
        return result
    if mode == "aggregates":
        return rows[~categories.map(_is_stock_country_category)].copy()
    return rows.copy()


def _stock_measure_value(values: pd.Series, total: float | None, measure: str) -> pd.Series:
    """Convert stock counts into the requested chart measure."""
    numeric = pd.to_numeric(values, errors="coerce")
    if measure == "percent_total":
        return (numeric / total) * 100 if total else numeric * np.nan
    return numeric / 1_000


def fig_migrant_stock_categories(
    tables: dict[str, pd.DataFrame],
    basis: str = "country_of_birth",
    country: str = "ITA",
    compare: str = "none",
    sex: str = "T",
    year: int | None = None,
    detail: str = "countries",
    measure: str = "absolute",
    limit: int = 25,
) -> go.Figure:
    """Rank resident stock by nation of birth or citizenship.

    Parameters
    ----------
    tables:
        Dictionary returned by `load_notebook_tables`.
    basis:
        Dimension to display. Use `country_of_birth` for paese di nascita or
        `citizenship` for cittadinanza.
    country:
        Main country code in ISO3 form, for example `ITA`.
    compare:
        Optional comparison country in ISO3 form, for example `ESP`. Use
        `none` to disable the comparison.
    sex:
        Sex code from Eurostat: `T`, `M` or `F`.
    year:
        Calendar year. If omitted, the latest available year for the main
        country and selected sex is used.
    detail:
        Category detail: `countries` keeps single nations, `aggregates` keeps
        Eurostat aggregates, `all` keeps both.
    measure:
        Display measure: `absolute` shows thousands of residents;
        `percent_total` shows the share of all residents in the selected
        country, sex and year.
    limit:
        Maximum number of categories shown, ranked by the main country.
    """
    country = normalize_country_code(country)
    compare = normalize_country_code(compare)
    measure = str(measure or "absolute").strip().lower()
    primary, selected_year, primary_total = _stock_country_slice(tables, basis, country, sex, year)
    primary = _filter_stock_detail(primary, detail, country)
    if primary.empty or selected_year is None:
        title = f"Stock residenti per {_stock_basis_label(basis)}"
        return apply_layout(go.Figure(), title, SOURCE_NOTES["migrant_stock"], 760)

    ranked = primary.groupby("category", as_index=False)["value"].sum().sort_values("value", ascending=False)
    categories = ranked.head(int(limit))["category"].astype(str).tolist()
    categories = list(reversed(categories))
    category_labels = [stock_category_label(code, _stock_table_name(basis).replace("population_by_", "")) for code in categories]

    fig = go.Figure()
    for selected_country, dash in ((country, "solid"), (compare, "dash")):
        if selected_country == "none":
            continue
        rows, country_year, total = _stock_country_slice(tables, basis, selected_country, sex, selected_year)
        rows = _filter_stock_detail(rows, detail, selected_country)
        values = rows.groupby("category")["value"].sum().to_dict()
        display = pd.Series([values.get(code, np.nan) for code in categories], dtype="float64")
        fig.add_bar(
            x=_stock_measure_value(display, total, measure),
            y=category_labels,
            orientation="h",
            name=f"{country_name(selected_country)} {country_year}",
            opacity=1.0 if dash == "solid" else 0.72,
        )

    axis_title = "% residenti" if measure == "percent_total" else "Migliaia di persone"
    fig.update_xaxes(title=axis_title, ticksuffix="%" if measure == "percent_total" else "")
    fig.update_yaxes(title="")
    detail_label = "nazioni" if detail == "countries" else "categorie"
    title = f"Residenti per {_stock_basis_label(basis)} e {detail_label} - {country_name(country)}, {selected_year}"
    return apply_layout(fig, title, SOURCE_NOTES["migrant_stock"], max(680, len(categories) * 24 + 260))


def fig_migrant_education_by_birth(
    tables: dict[str, pd.DataFrame],
    geo_code: str = "IT",
    age_label_value: str = "25-64",
    sex: str = "T",
    year: int | None = None,
) -> go.Figure:
    """Draw education distribution by country-of-birth group."""
    geo_code = normalize_eurostat_geo_code(geo_code)
    rows = tables.get("migrant_education", pd.DataFrame())
    if rows.empty:
        return apply_layout(go.Figure(), "Titoli di studio per paese di nascita", SOURCE_NOTES["migrant_education"], 620)
    selected = rows[
        rows["geo_code"].astype(str).eq(geo_code)
        & rows["age_label"].astype(str).eq(age_label_value)
        & rows["sex"].astype(str).str.upper().eq(sex)
    ].copy()
    if selected.empty:
        return apply_layout(go.Figure(), "Titoli di studio per paese di nascita", SOURCE_NOTES["migrant_education"], 620)
    selected_year = int(year) if year is not None else int(selected["year"].max())
    selected = education_display_rows(selected[selected["year"].astype(int).eq(selected_year)])
    birth_order = [code for code in ("NAT", "FOR", "EU27_2020_FOR", "NEU27_2020_FOR") if code in set(selected["country_of_birth_group"])]
    levels = sorted(selected["education_level"].dropna().unique(), key=lambda level: EDUCATION_ORDER.get(level, 999))
    fig = go.Figure()
    for birth_group in birth_order:
        data = selected[selected["country_of_birth_group"].astype(str).eq(birth_group)]
        values = data.groupby("education_level")["value"].sum().to_dict()
        fig.add_bar(
            x=[EDUCATION_LABELS.get(level, level) for level in levels],
            y=[values.get(level) for level in levels],
            name=birth_group_label(birth_group),
        )
    geo_name = selected["geo_name"].dropna().iloc[0] if not selected.empty else geo_code
    if not selected.empty and selected["geo_level"].astype(str).eq("country").any():
        geo_name = country_name(str(selected["iso3"].dropna().iloc[0]))
    fig.update_yaxes(title="% popolazione")
    fig.update_xaxes(title="Livello di istruzione")
    title = f"Titoli di studio per paese di nascita - {geo_name}, {age_label_value}, {selected_year}"
    return apply_layout(fig, title, SOURCE_NOTES["migrant_education"], 660)


def _migrant_tertiary_rows(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return tertiary-share rows, deriving them from the full table if needed."""
    tertiary = tables.get("migrant_tertiary", pd.DataFrame())
    if not tertiary.empty:
        return tertiary.copy()
    education = tables.get("migrant_education", pd.DataFrame())
    if education.empty or "education_level" not in education:
        return pd.DataFrame()
    result = education[education["education_level"].astype(str).eq("tertiary")].copy()
    return result.rename(columns={"value": "tertiary_share"})


def fig_migrant_tertiary_region(
    tables: dict[str, pd.DataFrame],
    country: str = "ITA",
    birth_group: str = "FOR",
    age_label_value: str = "25-64",
    sex: str = "T",
    year: int | None = None,
    limit: int = 21,
) -> go.Figure:
    """Rank NUTS2 regions by tertiary-education share among a birth group."""
    country = normalize_country_code(country)
    rows = _migrant_tertiary_rows(tables)
    if rows.empty:
        return apply_layout(go.Figure(), "Laureati per regione e paese di nascita", SOURCE_NOTES["migrant_education"], 760)
    selected = rows[
        rows["iso3"].astype(str).eq(country)
        & rows["geo_level"].astype(str).eq("region")
        & rows["country_of_birth_group"].astype(str).eq(birth_group)
        & rows["age_label"].astype(str).eq(age_label_value)
        & rows["sex"].astype(str).str.upper().eq(sex)
    ].copy()
    if selected.empty:
        return apply_layout(go.Figure(), "Laureati per regione e paese di nascita", SOURCE_NOTES["migrant_education"], 760)
    selected_year = int(year) if year is not None else int(selected["year"].max())
    selected = selected[selected["year"].astype(int).eq(selected_year)].sort_values("tertiary_share")
    selected = selected.tail(limit)
    fig = go.Figure(
        go.Bar(
            x=selected["tertiary_share"],
            y=selected["geo_name"],
            orientation="h",
            name=birth_group_label(birth_group),
        )
    )
    fig.update_xaxes(title="% popolazione")
    fig.update_yaxes(title="")
    title = f"Laureati tra {birth_group_label(birth_group).lower()} - regioni, {age_label_value}, {selected_year}"
    return apply_layout(fig, title, SOURCE_NOTES["migrant_education"], 760)


def fig_migration_destination_rank(
    tables: dict[str, pd.DataFrame],
    level: str = "region",
    metric: str = "immigration",
    year: int | None = None,
    limit: int = 25,
) -> go.Figure:
    """Rank regions or provinces by migration component from demographic balance."""
    territories = regional_options(tables, level)
    rows = []
    for _, territory in territories.iterrows():
        data = metric_rows(tables, f"{level}:{territory['geo_code']}", metric)
        if data.empty:
            continue
        selected_year = int(year) if year is not None else int(data["year"].max())
        selected = data[data["year"].astype(int).eq(selected_year)]
        if not selected.empty and pd.notna(selected.iloc[0]["metric_value"]):
            rows.append({"geo_name": territory["geo_name"], "value": selected.iloc[0]["metric_value"], "year": selected_year})
    table = pd.DataFrame(rows)
    if table.empty:
        title = f"Territori per {METRICS[metric]['label'].lower()}"
        return apply_layout(go.Figure(), title, SOURCE_NOTES["migration"], 760)
    table = table.sort_values("value", ascending=True).tail(limit)
    fig = go.Figure(go.Bar(x=scaled_series(table["value"], metric), y=table["geo_name"], orientation="h", name=METRICS[metric]["label"]))
    fig.update_xaxes(title=METRICS[metric]["axis"])
    fig.update_yaxes(title="")
    title_year = int(table["year"].max()) if not table.empty else year
    title = f"Territori per {METRICS[metric]['label'].lower()} - {title_year}"
    return apply_layout(fig, title, SOURCE_NOTES["migration"], 760)


def fig_internal_migration_destinations(
    tables: dict[str, pd.DataFrame],
    year: int | None = None,
    origin_code: str | None = None,
    limit: int = 30,
) -> go.Figure:
    """Rank destinations in the optional ISTAT origin-destination table."""
    flows = tables.get("internal_migration_flows", pd.DataFrame())
    if flows.empty:
        return apply_layout(go.Figure(), "Migrazioni interne per destinazione", SOURCE_NOTES["internal_migration"], 760)
    selected_year = int(year) if year is not None else int(flows["year"].max())
    rows = flows[flows["year"].astype(int).eq(selected_year)].copy()
    if origin_code is not None:
        rows = rows[rows["origin_code"].astype(str).str.startswith(str(origin_code))]
    if "sex" in rows and rows["sex"].astype(str).eq("T").any():
        rows = rows[rows["sex"].astype(str).eq("T")]
    if {"age_low", "age_high"}.issubset(rows.columns):
        total_age = rows["age_low"].isna() & rows["age_high"].isna()
        if total_age.any():
            rows = rows[total_age]
    grouped = rows.groupby("destination_code", as_index=False)["value"].sum().sort_values("value").tail(limit)
    name_frames = [regional_options(tables, "region"), regional_options(tables, "province")]
    names = pd.concat(name_frames, ignore_index=True) if name_frames else pd.DataFrame()
    name_map = names.set_index("geo_code")["geo_name"].to_dict() if not names.empty else {}
    grouped["destination_name"] = grouped["destination_code"].map(name_map).fillna(grouped["destination_code"])
    fig = go.Figure(go.Bar(x=grouped["value"] / 1_000, y=grouped["destination_name"], orientation="h", name="Arrivi interni"))
    fig.update_xaxes(title="Migliaia di persone")
    fig.update_yaxes(title="")
    title = f"Migrazioni interne per destinazione - {selected_year}"
    return apply_layout(fig, title, SOURCE_NOTES["internal_migration"], 760)


def education_display_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Keep education categories readable by avoiding duplicate aggregates."""
    if rows.empty:
        return rows.copy()
    has_sublevels = rows["education_level"].isin(["upper_secondary_general", "upper_secondary_vocational"]).any()
    keep = ~rows["education_level"].eq("upper_secondary_or_more")
    if has_sublevels:
        keep &= ~rows["education_level"].eq("upper_secondary_post_secondary")
    result = rows[keep].copy()
    result["_education_order"] = result["education_level"].map(EDUCATION_ORDER).fillna(999)
    return result.sort_values(["_education_order", "value"], ascending=[True, False]).drop(
        columns="_education_order"
    )


def fig_education_distribution(
    tables: dict[str, pd.DataFrame],
    country: str = "ITA",
    compare: str = "ESP",
    age_label_value: str = "25-64",
    sex: str = "T",
    year: int | None = None,
) -> go.Figure:
    """Draw education attainment distribution for two countries."""
    country = normalize_country_code(country)
    compare = normalize_country_code(compare)
    rows = tables["education"]
    if year is None:
        year = int(rows[rows["iso3"].eq(country)]["year"].max())
    primary = education_display_rows(rows[rows["iso3"].eq(country) & rows["age_label"].astype(str).eq(age_label_value) & rows["sex"].astype(str).eq(sex) & rows["year"].astype(int).eq(int(year))])
    comparison = (
        education_display_rows(rows[rows["iso3"].eq(compare) & rows["age_label"].astype(str).eq(age_label_value) & rows["sex"].astype(str).eq(sex) & rows["year"].astype(int).eq(int(year))])
        if compare != "none"
        else pd.DataFrame(columns=primary.columns)
    )
    levels = list(dict.fromkeys(primary["education_level"].tolist() + comparison["education_level"].tolist()))
    levels = sorted(levels, key=lambda level: EDUCATION_ORDER.get(level, 999))
    fig = go.Figure()
    series = [(primary, country_name(country))]
    if compare != "none":
        series.append((comparison, country_name(compare)))
    for data, label in series:
        mapped = data.set_index("education_level")["value"].to_dict()
        fig.add_bar(x=[EDUCATION_LABELS.get(level, level) for level in levels], y=[mapped.get(level) for level in levels], name=label)
    fig.update_yaxes(title="% popolazione")
    fig.update_xaxes(title="Livello di istruzione")
    return apply_layout(fig, f"Distribuzione titoli di studio - {age_label_value}, {year}", SOURCE_NOTES["education"])


def fig_education_trend(
    tables: dict[str, pd.DataFrame],
    country: str = "ITA",
    compare: str = "ESP",
    age_label_value: str = "25-64",
    sex: str = "T",
    education_level: str = "tertiary",
) -> go.Figure:
    """Draw education attainment over time and total population."""
    country = normalize_country_code(country)
    compare = normalize_country_code(compare)
    rows = tables["education"]
    primary = rows[rows["iso3"].eq(country) & rows["age_label"].astype(str).eq(age_label_value) & rows["sex"].astype(str).eq(sex) & rows["education_level"].astype(str).eq(education_level)].sort_values("year")
    population = preferred_rows(age_rows(tables, country))
    fig = go.Figure()
    fig.add_scatter(x=primary["year"], y=primary["value"], mode="lines+markers", name=f"{country_name(country)} - {EDUCATION_LABELS.get(education_level, education_level)}")
    if compare != "none":
        comparison = rows[rows["iso3"].eq(compare) & rows["age_label"].astype(str).eq(age_label_value) & rows["sex"].astype(str).eq(sex) & rows["education_level"].astype(str).eq(education_level)].sort_values("year")
        fig.add_scatter(x=comparison["year"], y=comparison["value"], mode="lines+markers", name=country_name(compare), line={"dash": "dash"})
    fig.add_scatter(x=population["year"], y=population["population_total"] / 1_000_000, mode="lines+markers", name=f"Popolazione totale {country_name(country)}", yaxis="y2", line={"dash": "dot"})
    fig.update_layout(yaxis={"title": "% livello selezionato"}, yaxis2={"title": "Milioni residenti", "overlaying": "y", "side": "right"})
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, "Istruzione e popolazione totale", SOURCE_NOTES["education"])


def fig_life_expectancy(
    tables: dict[str, pd.DataFrame],
    country: str = "ITA",
    compare: str = "ESP",
) -> go.Figure:
    """Draw life expectancy at birth and remaining life expectancy at age 65."""
    country = normalize_country_code(country)
    compare = normalize_country_code(compare)
    fig = go.Figure()
    for iso3, dash in ((country, "solid"), (compare, "dash")):
        if iso3 == "none":
            continue
        for metric, label in (
            ("life_expectancy_birth", "alla nascita"),
            ("life_expectancy_65", "a 65 anni"),
        ):
            rows = metric_rows(tables, iso3, metric)
            fig.add_scatter(
                x=rows["year"],
                y=rows["metric_value"],
                mode="lines+markers",
                name=f"{country_name(iso3)} {label}",
                line={"dash": dash},
            )
    fig.update_yaxes(title="Anni")
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, "Speranza di vita", SOURCE_NOTES["life_expectancy"])


def europe_metric_table(tables: dict[str, pd.DataFrame], metric: str) -> pd.DataFrame:
    """Build a country-year metric table for European comparisons."""
    if metric == "tertiary_25_64":
        rows = tables["education"]
        result = rows[
            rows["iso3"].isin(EU27_ISO3)
            & rows["age_label"].astype(str).eq("25-64")
            & rows["sex"].astype(str).eq("T")
            & rows["education_level"].astype(str).eq("tertiary")
        ].copy()
        result["metric_value"] = result["value"]
        return result
    pieces = []
    for iso3 in sorted(tables["age_structure"]["iso3"].dropna().unique()):
        if iso3 not in EU27_ISO3:
            continue
        data = metric_rows(tables, iso3, metric)
        if not data.empty:
            data = data.assign(iso3=iso3, geo_name=country_name(iso3))
            pieces.append(data)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(columns=["iso3", "year", "metric_value"])


def fig_europe_rank(
    tables: dict[str, pd.DataFrame],
    metric: str = "share_65_plus",
    year: int = 2024,
) -> go.Figure:
    """Rank European countries by a selected metric and year."""
    rows = europe_metric_table(tables, metric)
    selected = rows[rows["year"].astype(int).eq(int(year)) & rows["metric_value"].notna()].copy()
    selected["country_label"] = selected["iso3"].map(country_name)
    selected = selected.sort_values("metric_value")
    fig = go.Figure(go.Bar(x=scaled_series(selected["metric_value"], metric), y=selected["country_label"], orientation="h", name=METRICS[metric]["label"]))
    fig.update_xaxes(title=METRICS[metric]["axis"])
    fig.update_yaxes(title="")
    return apply_layout(fig, f"Classifica paesi UE - {METRICS[metric]['label']}, {year}", SOURCE_NOTES["europe"], 760)


def fig_europe_series(
    tables: dict[str, pd.DataFrame],
    country: str = "ESP",
    metric: str = "share_65_plus",
) -> go.Figure:
    """Compare Italy, a selected country, and the yearly European median."""
    country = normalize_country_code(country)
    rows = europe_metric_table(tables, metric)
    median_by_year = rows.groupby("year", as_index=False)["metric_value"].median()
    fig = go.Figure()
    selected_countries = list(dict.fromkeys(["ITA", country]))
    for iso3 in selected_countries:
        if iso3 == "none":
            continue
        data = metric_rows(tables, iso3, metric)
        fig.add_scatter(x=data["year"], y=scaled_series(data["metric_value"], metric), mode="lines+markers", name=country_name(iso3), line={"dash": "solid"})
    fig.add_scatter(x=median_by_year["year"], y=scaled_series(median_by_year["metric_value"], metric), mode="lines+markers", name="Mediana UE", line={"dash": "dash"})
    fig.update_yaxes(title=METRICS[metric]["axis"])
    fig.update_xaxes(title="Anno")
    return apply_layout(fig, f"Italia, mediana UE e {country_name(country)} - {METRICS[metric]['label']}", SOURCE_NOTES["europe"])


def notebook_paths(root_dir: Path | None = None) -> dict[str, Path]:
    """Return useful repository paths for notebooks opened from VS Code."""
    root = root_dir or ROOT_DIR
    return {"root": root, "final": root / "output" / "data" / "final", "notebooks": root / "notebooks"}
