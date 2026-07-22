# Tabelle finali e copertura

La pipeline mantiene separati dati osservati, stime campionarie e proiezioni. La tabella centrale `population_age_sex_observed_projected` include fonte, dataset, data di estrazione, vintage della proiezione, livello geografico, scenario e campi predisposti per quantili e intervalli.

## Output Principali

- `fertility_indicators`: indicatori di fecondita in formato lungo, con codice originale, eta, sesso, unita e flag statistici.
- `demographic_balance_long`: componenti del bilancio demografico con codici e definizioni originali.
- `demographic_balance`: tabella annuale larga con nascite, decessi, saldo naturale, immigrazione, emigrazione, saldo migratorio e residuo dell'identita demografica quando calcolabile.
- `education_attainment`: quote per titolo di studio, anno, paese, sesso e fascia di eta. La fonte e Eurostat LFS e il dato resta separato dai conteggi anagrafici.
- `immigration_profile` e `emigration_profile`: flussi per eta, sesso, cittadinanza, paese di nascita e paese partner quando presenti nella fonte.
- `migration_summary`: immigrazioni, emigrazioni e saldo per paese e anno.
- `population_by_citizenship` e `population_by_country_of_birth`: stock distinti per le due definizioni.
- `projection_inventory`: copertura per fonte, vintage, scenario, paese e orizzonte.
- `quality_report`: anomalie di chiave, valori negativi, intervalli di eta, copertura per sesso, sovrapposizione osservato-proiettato e identita del bilancio.

## Esecuzione Ridotta

Per una prova rapida da VS Code, aprire `scripts/run_pipeline.py` e modificare la sezione `Configurazione per VS Code`: limitare `START_YEAR`, `END_YEAR`, `EU_GEOS` e `COMPARISON_COUNTRIES`. Se `PROJECTION_SCENARIO` resta vuoto vengono conservati tutti gli scenari restituiti da Eurostat. L'importazione WPP viene limitata ai membri OECD non gia coperti dall'UE, evitando duplicazioni tra fonti.
