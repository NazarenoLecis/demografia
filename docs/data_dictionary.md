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

La tabella `migrant_education_by_birth_region` contiene:

- `geo_level`, `geo_code`, `geo_name`: livello, codice e nome del territorio; i paesi sono `country`, le regioni italiane sono `region`;
- `iso3`: paese di riferimento in codice ISO3;
- `year`: anno;
- `age_low`, `age_high`, `age_label`: fascia di eta;
- `sex`: `T`, `M` o `F`;
- `country_of_birth_group`: gruppo Eurostat del paese di nascita (`NAT`, `FOR`, `EU27_2020_FOR`, `NEU27_2020_FOR`);
- `country_of_birth_group_label`: etichetta originale della fonte;
- `education_level_code`, `education_level`, `education_level_label`: codice ISCED, livello normalizzato ed etichetta originale;
- `unit`: `PC` per percentuale;
- `value`: quota della popolazione nella fascia, sesso, territorio e gruppo di nascita selezionati.

La tabella `migrant_tertiary_share` contiene le stesse dimensioni territoriali, anagrafiche e di paese di nascita, ma solo la quota ISCED 5-8 nel campo `tertiary_share`.

La tabella `oecd_demographic_indicators` e in formato lungo con paese, anno, indicatore e valore. Include tutti i membri OECD presenti nella configurazione e righe aggregate di benchmark.
