# Demografia italiana

Repository per analizzare struttura, evoluzione e proiezioni della popolazione italiana, con confronti estesi a tutti i paesi dell'Unione europea e dell'OECD.

La pipeline completa usa direttamente le fonti ufficiali:

- ISTAT per popolazione, nascite, decessi, bilancio demografico, migrazioni interne e internazionali, popolazione straniera, territorio e proiezioni italiane;
- INPS per pensionati, pensioni, contribuenti, assicurati e flussi di pensionamento;
- Ragioneria Generale dello Stato e OpenBDAP per le proiezioni di medio-lungo periodo su pensioni, sanità, assistenza e altre voci collegate all'invecchiamento;
- Eurostat per dati demografici armonizzati e proiezioni dei paesi UE;
- UN World Population Prospects per serie per età e sesso e proiezioni dei paesi OECD extra-UE;
- World Bank WDI per il pannello sintetico di indicatori comparabili UE-OECD.

## Analisi coperte

- popolazione per singolo anno di età e sesso;
- piramidi demografiche storiche e proiettate;
- evoluzione delle coorti;
- fasce di età, età media e mediana;
- fertilità, natalità, decessi e saldo naturale;
- immigrazione, emigrazione e saldo migratorio;
- migrazioni interne con saldi territoriali e matrici origine-destinazione;
- residenti per cittadinanza e paese di nascita;
- struttura territoriale regionale, provinciale e comunale;
- rapporti di dipendenza demografica;
- pensionati, pensioni, contribuenti e assicurati INPS;
- rapporto tra contribuenti, pensionati e popolazione anziana;
- proiezioni RGS della spesa pensionistica, sanitaria e assistenziale;
- confronto Italia-UE27-OECD38;
- scenari e diverse edizioni delle proiezioni;
- controlli di qualità e copertura delle fonti.

## Installazione

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Su Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Pipeline completa

```bash
python scripts/run_official_pipeline.py \
  --start-year 1960 \
  --end-year 2026 \
  --projection-end 2100 \
  --include-migration \
  --auto-wpp
```

Il comando:

1. esegue la pipeline Eurostat, OECD e WPP;
2. interroga il catalogo SDMX ISTAT e assegna i dataflow ai blocchi demografici;
3. scarica e normalizza i dataset ISTAT selezionati;
4. interroga il catalogo ufficiale INPS e seleziona i dataset demografico-previdenziali;
5. interroga OpenBDAP/RGS per le proiezioni di medio-lungo periodo;
6. costruisce le tabelle finali e il pannello integrato italiano;
7. produce report di copertura, qualità e stato delle fonti.

Per interrompere l'esecuzione quando una fonte obbligatoria non viene acquisita:

```bash
python scripts/run_official_pipeline.py --strict
```

Quando il catalogo ISTAT restituisce più dataflow con lo stesso punteggio, la pipeline usa il primo candidato ordinato e registra l'ambiguità. Un dataflow può essere fissato esplicitamente:

```bash
python scripts/run_official_pipeline.py \
  --istat-override population_age_sex=DATAFLOW_ID \
  --istat-override internal_migration=DATAFLOW_ID
```

## Pipeline internazionale più leggera

```bash
python scripts/run_pipeline.py \
  --start-year 1960 \
  --end-year 2026 \
  --projection-end 2100 \
  --include-migration \
  --auto-wpp
```

## Verifica delle fonti

```bash
python scripts/check_sources.py
python scripts/check_official_sources.py
```

## Test

```bash
ruff check .
python -m compileall -q demografia scripts
pytest
```

## Output principali

```text
output/data/final/
  population_age_sex_observed_projected.*
  age_structure_indicators.*
  fertility_indicators.*
  demographic_balance.*
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
```

## Criteri metodologici

Le persone e i trattamenti pensionistici restano separati. Un pensionato può ricevere più pensioni.

Cittadinanza, paese di nascita, precedente residenza e paese di destinazione restano dimensioni distinte.

I dati osservati e le proiezioni restano separati. Ogni proiezione conserva fonte, scenario ed edizione quando disponibili.

I rapporti demografici usano la popolazione per età. I rapporti previdenziali usano contribuenti, assicurati, pensionati e pensioni INPS. Il pannello integrato mantiene visibili entrambi i numeratori e denominatori.

La disponibilità dei dati non viene trattata come un limite metodologico. `official_source_status` distingue un dato realmente assente da un problema operativo di download, formato, mapping o variazione dell'endpoint.
