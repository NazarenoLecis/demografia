# Tabelle finali e copertura

La pipeline mantiene separati dati osservati, stime e proiezioni. La tabella centrale `population_age_sex_observed_projected` include fonte, dataset, data di estrazione, vintage della proiezione, livello geografico, scenario e campi predisposti per quantili e intervalli.

## Output principali

- `fertility_indicators`: indicatori di fecondità in formato lungo, con codice originale, età, sesso, unità e flag statistici.
- `demographic_balance_long`: componenti del bilancio demografico con codici e definizioni originali.
- `demographic_balance`: tabella annuale larga con nascite, decessi, saldo naturale, immigrazione, emigrazione, saldo migratorio e residuo dell'identità demografica quando calcolabile.
- `immigration_profile` e `emigration_profile`: flussi per età, sesso, cittadinanza, paese di nascita e paese partner quando presenti nella fonte.
- `migration_summary`: immigrazioni, emigrazioni e saldo per paese e anno.
- `population_by_citizenship` e `population_by_country_of_birth`: stock distinti per le due definizioni.
- `projection_inventory`: copertura per fonte, vintage, scenario, paese e orizzonte.
- `quality_report`: anomalie di chiave, valori negativi, intervalli di età, copertura per sesso, sovrapposizione osservato-proiettato e identità del bilancio.

## Esecuzione ridotta

```bash
python scripts/run_pipeline.py \
  --start-year 2020 \
  --end-year 2023 \
  --projection-end 2030 \
  --eu-geos IT,DE,FR \
  --comparison-countries ITA,DEU,FRA,USA,JPN,AUS \
  --projection-scenario BSL
```

Omettendo `--projection-scenario` vengono conservati tutti gli scenari restituiti da Eurostat. L'importazione WPP viene limitata ai membri OECD non già coperti dall'UE, evitando duplicazioni tra fonti.
