# Demografia italiana

Repository autonomo per costruire dati e grafici sulla demografia italiana, con confronti UE e OECD.

La pipeline scarica, normalizza e controlla fonti statistiche ufficiali. Gli output sono pensati per analisi successive: tabelle Parquet/CSV, report di qualita e grafici salvati in `output/`.

## Fonti

- ISTAT: popolazione, nascite, decessi, bilancio demografico, migrazioni interne e internazionali, popolazione straniera, territorio e proiezioni italiane.
- Eurostat: popolazione per eta e sesso, indicatori demografici armonizzati, flussi migratori, stock migratorio, titoli di studio e proiezioni UE.
- UN World Population Prospects: popolazione per eta e sesso e proiezioni per i paesi OECD extra-UE.
- World Bank WDI: indicatori comparabili UE-OECD.
- INPS: pensionati, pensioni, contribuenti, assicurati e flussi di pensionamento.
- Ragioneria Generale dello Stato/OpenBDAP: proiezioni di medio-lungo periodo su pensioni, sanita, assistenza e invecchiamento.

## Analisi Coperte

- popolazione per anno, eta e sesso;
- kebab demografico storico e proiettato con uomini e donne;
- evoluzione delle coorti;
- eta media, eta mediana e distribuzione per fasce di eta;
- fertilita, natalita, decessi e saldo naturale;
- immigrazione, emigrazione e saldo migratorio;
- stock per cittadinanza e paese di nascita;
- distribuzione per titolo di studio da Eurostat LFS;
- struttura territoriale regionale, provinciale e comunale quando disponibile;
- tasso di dipendenza degli anziani e altri rapporti di dipendenza;
- pensionati, pensioni, contribuenti e assicurati INPS;
- proiezioni demografiche e proiezioni RGS;
- controlli di qualita e copertura delle fonti.

## Uso Da VS Code

1. Aprire la cartella del repository in VS Code.
2. Creare un ambiente Python con il comando VS Code `Python: Create Environment`.
3. Selezionare `pyproject.toml` o `requirements.txt` quando VS Code chiede le dipendenze.
4. Aprire uno script in `scripts/`.
5. Modificare la sezione `Configurazione per VS Code` in cima al file.
6. Usare `Run Python File`.

Ogni script contiene la propria configurazione in cima al file ed espone una funzione `main(...)` con parametri espliciti, quindi puo essere lanciato da VS Code, importato in notebook o richiamato da test.

## Notebook di analisi

I notebook in `notebooks/` sono fogli di lavoro tematici. Ogni foglio ha una cella di parametri in alto, spiegazioni in markdown e grafici verticali con fonte ed elaborazione in basso a sinistra.

- `notebooks/01_kebab_e_proiezioni.ipynb`: popolazione, Kebab demografico, proiezioni, popolazione nata all'estero, età media, mediana, quantili e dipendenza.
- `notebooks/02_movimento_naturale.ipynb`: natalità, fecondità, nati, decessi, saldo naturale e letture regionali/provinciali.
- `notebooks/03_migrazioni.ipynb`: flussi migratori, saldo migratorio, variazione della popolazione e stock nato all'estero.
- `notebooks/04_istruzione.ipynb`: distribuzione dei titoli di studio, fasce di età, sesso, confronto con popolazione totale e paesi UE.
- `notebooks/05_territori_italiani.ipynb`: classifiche e serie regionali/provinciali per popolazione, struttura per età, nati, decessi, fecondità e saldo migratorio.
- `notebooks/06_confronti_europei.ipynb`: classifiche UE e serie con mediana europea per popolazione, invecchiamento, dipendenza, fecondità e istruzione.

## Script Principali

- `scripts/run_official_pipeline.py`: pipeline completa con Eurostat, WPP, World Bank, ISTAT, INPS e RGS/OpenBDAP.
- `scripts/run_pipeline.py`: pipeline internazionale piu leggera con Eurostat, WPP e World Bank.
- `scripts/check_sources.py`: controllo rapido delle fonti internazionali.
- `scripts/check_official_sources.py`: controllo rapido di ISTAT, INPS e RGS/OpenBDAP.
- `scripts/discover_istat_registry.py`: costruzione del registro dei dataflow demografici ISTAT.
- `scripts/download_wpp.py`: download del file WPP per eta e sesso.

## Roadmap

La roadmap in `docs/roadmap.md` elenca aree gia implementate, priorita dati e fonti candidate per mortalita, famiglie, AIRE, istruzione territoriale, migrazioni interne avanzate, territorio e generazioni.

Gli script partono da un profilo quickstart Italia: 2020-2024, proiezioni fino al 2030, scenario baseline, `EU_GEOS = ("IT",)`, `COMPARISON_COUNTRIES = ("ITA",)` e `AUTO_WPP = False`. Per estendere il confronto a UE/OECD o produrre serie storiche lunghe basta modificare quei valori nella sezione di configurazione.

## Output Principali

```text
output/data/final/
  population_age_sex_observed_projected.*
  age_structure_indicators.*
  fertility_indicators.*
  demographic_balance.*
  education_attainment.*
  immigration_profile.*
  emigration_profile.*
  migration_summary.*
  population_by_citizenship.*
  population_by_country_of_birth.*
  projection_inventory.*

  istat_demographic_dataflows.*
  italy_population_age_sex_territorial.*
  italy_territorial_age_structure.*
  italy_births.*
  italy_deaths.*
  italy_demographic_balance.*
  italy_internal_migration_flows.*
  italy_internal_migration_balances.*
  italy_internal_migration_profiles.*
  italy_internal_migration_matrix_<anno>.csv
  italy_population_projections.*

  inps_catalog.*
  inps_demographic_datasets.*
  inps_demographic_observations.*
  inps_support_indicators.*

  rgs_projection_catalog.*
  rgs_long_term_projections.*
  rgs_long_term_projection_panel.*

  italy_demographic_pension_fiscal_panel.*
  official_source_status.*
  official_quality_report.*
  quality_report.*

output/charts/
  kebab_ita_<anno>.png
  kebab_ita_storico.gif
  coorti_ita.png
```

## Convenzioni Del Repo

- i moduli espongono funzioni parametrizzate;
- la configurazione vive negli script e nelle funzioni `main(...)`;
- il package usa namespace package Python;
- funzioni generali in `demografia/utils.py`;
- fonti osservate, stime campionarie e proiezioni restano separate;
- persone e trattamenti pensionistici restano separati;
- cittadinanza, paese di nascita, provenienza e destinazione non sono variabili intercambiabili.

## Qualita

La suite usa `pytest` e puo essere lanciata dal pannello Testing di VS Code dopo la selezione dell'ambiente Python del repository.
