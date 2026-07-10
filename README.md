# Demografia italiana

Repository per analizzare struttura, evoluzione e proiezioni della popolazione italiana con confronti estesi a tutti i paesi dell'Unione europea e ai 38 membri OECD.

Il progetto copre:

- popolazione per età e sesso;
- piramidi demografiche storiche, confronti tra anni e animazioni;
- evoluzione delle coorti;
- popolazione totale e sue componenti;
- fertilità, natalità, mortalità e speranza di vita;
- dipendenza demografica e rapporti di sostegno;
- distribuzione territoriale;
- immigrazione, emigrazione, cittadinanza e paese di nascita;
- profili per età e sesso dei migranti;
- predisposizione per titolo di studio, occupazione e professione tramite dati LFS e censuari;
- proiezioni per età e sesso fino al 2100 quando disponibili;
- confronto Italia-UE27-OECD38.

## Fonti

- Eurostat per popolazione UE per età e sesso, fertilità, bilancio demografico, migrazioni ed EUROPOP.
- World Bank WDI per un pannello uniforme sui 38 membri OECD.
- UN World Population Prospects 2024 per piramidi e proiezioni dei paesi OECD extraeuropei.
- ISTAT SDMX per il dettaglio italiano nazionale e territoriale. Il client generico è incluso; i dataflow saranno bloccati nel catalogo dopo la verifica dei singoli dataset.

Le fonti e lo stato di implementazione sono in `metadata/source_catalog.csv`.

## Installazione

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Esecuzione

Pipeline UE e OECD:

```bash
python scripts/run_pipeline.py --start-year 1960 --end-year 2026 --projection-end 2100
```

Con i dataset migratori Eurostat:

```bash
python scripts/run_pipeline.py --include-migration
```

Con piramidi e proiezioni per tutti i paesi OECD tramite il file ufficiale WPP 2024:

```bash
python scripts/run_pipeline.py --wpp-age-sex input/WPP2024_age_sex.csv.gz --wpp-scale 1000
```

I file WPP standard riportano normalmente la popolazione in migliaia. `--wpp-scale 1000` converte i valori in persone; usare `--wpp-scale 1` per file già espressi in unità.

Per generare anche l'animazione storica italiana:

```bash
python scripts/run_pipeline.py --make-animation
```

Per individuare i dataflow ISTAT relativi a popolazione, migrazioni, nascite e proiezioni:

```bash
python scripts/discover_istat_dataflows.py
```

Dopo avere identificato il dataflow della popolazione per territorio, età e sesso:

```bash
python scripts/run_pipeline.py --istat-population-dataflow <DATAFLOW_ID> --istat-key all
```

Controllo rapido degli endpoint:

```bash
python scripts/check_sources.py
```

## Output

La pipeline produce sia Parquet sia CSV.

```text
output/data/raw/
  eurostat_population_age_sex.*
  eurostat_population_projections.*
  eurostat_fertility.*
  eurostat_demographic_balance.*
  eurostat_immigration_profile.*
  eurostat_emigration_profile.*
  eurostat_population_by_citizenship.*
  eurostat_population_by_birth_country.*

output/data/final/
  population_age_sex_observed_projected.*
  age_structure_indicators.*
  oecd_demographic_indicators.*
  coverage_report.*
  italy_population_age_sex_territorial.*
  italy_territorial_age_structure.*

output/charts/
  piramide_italia_<anno>.png
  coorti_italia.png
  piramide_italia_storica.gif
```

## Struttura analitica

`population_age_sex_observed_projected` è la tabella centrale. Mantiene distinti dati osservati e proiettati, fonte e scenario. Da questa tabella vengono calcolati piramidi, età media e mediana, fasce di età, tassi di dipendenza e rapporti di sostegno.

Il confronto UE usa tutti i 27 Stati membri. Il pannello OECD usa l'elenco dei 38 membri. `coverage_report` segnala paesi o dimensioni mancanti senza sostituire dati assenti con valori stimati.

## Limiti da mantenere espliciti

Le proiezioni dipendono dalle ipotesi su fertilità, mortalità e migrazione. Le diverse edizioni non devono essere sovrascritte.

Cittadinanza e paese di nascita misurano popolazioni diverse. I dati anagrafici e le stime campionarie su istruzione o lavoro restano separati.

I rapporti di dipendenza presenti nel repository sono demografici. Un rapporto economico tra occupati e persone sostenute richiede dati aggiuntivi sul mercato del lavoro e sulle pensioni.
