from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
RAW_DIR = OUTPUT_DIR / "data" / "raw"
INTERIM_DIR = OUTPUT_DIR / "data" / "interim"
FINAL_DIR = OUTPUT_DIR / "data" / "final"
CACHE_DIR = OUTPUT_DIR / "cache"
CHART_DIR = OUTPUT_DIR / "charts"
LOG_DIR = OUTPUT_DIR / "logs"

EU27_ISO2 = (
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL", "HU",
    "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
)

EU27_ISO3 = (
    "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN",
    "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE",
)

OECD38_ISO3 = (
    "AUS", "AUT", "BEL", "CAN", "CHL", "COL", "CRI", "CZE", "DNK", "EST", "FIN", "FRA", "DEU",
    "GRC", "HUN", "ISL", "IRL", "ISR", "ITA", "JPN", "KOR", "LVA", "LTU", "LUX", "MEX", "NLD",
    "NZL", "NOR", "POL", "PRT", "SVK", "SVN", "ESP", "SWE", "CHE", "TUR", "GBR", "USA",
)

EU_OECD_ISO3 = tuple(dict.fromkeys((*EU27_ISO3, *OECD38_ISO3)))

EUROSTAT_TO_ISO3 = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "HR": "HRV", "CY": "CYP", "CZ": "CZE",
    "DK": "DNK", "EE": "EST", "FI": "FIN", "FR": "FRA", "DE": "DEU", "EL": "GRC",
    "GR": "GRC", "HU": "HUN", "IE": "IRL", "IT": "ITA", "LV": "LVA", "LT": "LTU",
    "LU": "LUX", "MT": "MLT", "NL": "NLD", "PL": "POL", "PT": "PRT", "RO": "ROU",
    "SK": "SVK", "SI": "SVN", "ES": "ESP", "SE": "SWE", "IS": "ISL", "NO": "NOR",
    "CH": "CHE", "TR": "TUR", "UK": "GBR",
}

COUNTRY_NAMES = {
    "AUS": "Australia", "AUT": "Austria", "BEL": "Belgio", "BGR": "Bulgaria", "CAN": "Canada",
    "CHE": "Svizzera", "CHL": "Cile", "COL": "Colombia", "CRI": "Costa Rica", "CYP": "Cipro",
    "CZE": "Repubblica Ceca", "DEU": "Germania", "DNK": "Danimarca", "ESP": "Spagna",
    "EST": "Estonia", "FIN": "Finlandia", "FRA": "Francia", "GBR": "Regno Unito",
    "GRC": "Grecia", "HRV": "Croazia", "HUN": "Ungheria", "IRL": "Irlanda", "ISL": "Islanda",
    "ISR": "Israele", "ITA": "Italia", "JPN": "Giappone", "KOR": "Corea del Sud",
    "LTU": "Lituania", "LUX": "Lussemburgo", "LVA": "Lettonia", "MEX": "Messico",
    "MLT": "Malta", "NLD": "Paesi Bassi", "NOR": "Norvegia", "NZL": "Nuova Zelanda",
    "POL": "Polonia", "PRT": "Portogallo", "ROU": "Romania", "SVK": "Slovacchia",
    "SVN": "Slovenia", "SWE": "Svezia", "TUR": "Turchia", "USA": "Stati Uniti",
}

WORLD_BANK_INDICATORS = {
    "SP.POP.TOTL": "popolazione_totale",
    "SP.POP.GROW": "crescita_popolazione",
    "SP.DYN.TFRT.IN": "fertilita_totale",
    "SP.DYN.CBRT.IN": "natalita_grezza",
    "SP.POP.0014.TO.ZS": "quota_0_14",
    "SP.POP.1564.TO.ZS": "quota_15_64",
    "SP.POP.65UP.TO.ZS": "quota_65_piu",
    "SP.POP.DPND": "dipendenza_totale",
    "SP.POP.DPND.YG": "dipendenza_giovanile",
    "SP.POP.DPND.OL": "dipendenza_anziani",
    "SP.DYN.LE00.IN": "speranza_vita",
    "SP.DYN.LE00.MA.IN": "speranza_vita_uomini",
    "SP.DYN.LE00.FE.IN": "speranza_vita_donne",
    "SM.POP.NETM": "saldo_migratorio",
    "SP.POP.TOTL.MA.IN": "popolazione_uomini",
    "SP.POP.TOTL.FE.IN": "popolazione_donne",
}

EUROSTAT_DATASETS = {
    "population_age_sex": "demo_pjan",
    "fertility": "demo_frate",
    "demographic_balance": "demo_gind",
    "projections": "proj_23np",
    "immigration_profile": "migr_imm5prv",
    "emigration_profile": "migr_emi4ctb",
    "population_citizenship": "migr_pop1ctz",
    "population_birth_country": "migr_pop3ctb",
    "education_attainment": "edat_lfse_03",
}

EDUCATION_ATTAINMENT_AGE_GROUPS = ("Y15-64", "Y25-64", "Y25-34", "Y35-44", "Y45-54", "Y55-64")


def ensure_directories() -> None:
    for path in (INPUT_DIR, RAW_DIR, INTERIM_DIR, FINAL_DIR, CACHE_DIR, CHART_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
