# Dizionario dati

La tabella finale `population_age_sex_observed_projected` contiene:

- `iso3`: paese in codice ISO3;
- `year`: anno;
- `age_low`, `age_high`: estremi della classe di eta;
- `sex`: `M` o `F`;
- `value`: popolazione;
- `scenario`: osservato, baseline o variante della proiezione;
- `status`: `observed` o `projected`;
- `source`: fonte statistica.

La tabella `age_structure_indicators` contiene livelli, quote per fascia di eta, eta media e mediana, quantili della distribuzione (`age_p10`, `age_p25`, `age_p75`, `age_p90`), rapporti di dipendenza, rapporti di sostegno, rapporti uomini/donne per fascia e indicatori di ricambio generazionale.

La tabella `education_attainment` contiene:

- `iso3`: paese in codice ISO3;
- `year`: anno;
- `age_low`, `age_high`, `age_label`: fascia di eta;
- `sex`: `T`, `M` o `F`;
- `education_level_code`: codice ISCED 2011 originale;
- `education_level`: livello normalizzato;
- `education_level_label`: etichetta della fonte;
- `unit`: `PC` per percentuale;
- `value`: quota della popolazione nella fascia considerata.

La tabella `oecd_demographic_indicators` e in formato lungo con paese, anno, indicatore e valore. Include tutti i membri OECD presenti nella configurazione e righe aggregate di benchmark.
