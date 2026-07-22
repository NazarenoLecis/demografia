# Roadmap di copertura demografica

Questa roadmap traduce le aree informative del progetto in blocchi dati modulari. Le sezioni gia implementate restano nella pipeline principale; le sezioni pianificate indicano output e fonti candidate.

## Implementato

- Popolazione per anno, eta, sesso, fonte, scenario e stato osservato/proiettato: `population_age_sex_observed_projected`.
- Kebab demografico per uomini e donne: `output/charts/kebab_<paese>_<anno>.png`.
- Indicatori di struttura per eta: `age_structure_indicators`.
- Quote 0-14, 15-64, 65+, 80+, 85+, 100+.
- Eta media, eta mediana e quantili p10, p25, p75, p90.
- Rapporti uomini/donne per fasce di eta.
- Dipendenza giovanile, dipendenza anziani, dipendenza totale e rapporti di sostegno.
- Ricambio della popolazione attiva: 60-64 per 100 persone 15-19.
- Rapporto 20-39 / 60-79.
- Fertilita, natalita, decessi e saldo naturale: `fertility_indicators`, `demographic_balance`.
- Immigrazione, emigrazione e saldo migratorio: `immigration_profile`, `emigration_profile`, `migration_summary`.
- Stock per cittadinanza e paese di nascita: `population_by_citizenship`, `population_by_country_of_birth`.
- Distribuzione per titolo di studio Eurostat LFS: `education_attainment`.
- Migrazioni interne ISTAT quando la discovery individua il dataflow: `italy_internal_migration_*`.
- Proiezioni demografiche Eurostat, WPP e ISTAT quando disponibili.
- Integrazione INPS/RGS per indicatori previdenziali e fiscali.

## Priorita Alta

### Mortalita, sopravvivenza e longevita

Output proposti:

- `mortality_rates_age_sex`;
- `life_expectancy`;
- `survival_tables`;
- `deaths_age_sex`;
- `modal_age_at_death`;
- `healthy_life_expectancy`.

Fonti candidate:

- ISTAT Demo, tavole di mortalita (`https://demo.istat.it/app/?i=TVM&l=it`);
- Eurostat mortality/life expectancy;
- World Bank WDI per confronti sintetici.

### Famiglie e nuclei familiari

Output proposti:

- `households_by_type`;
- `household_size`;
- `people_living_alone_age`;
- `elderly_living_alone`;
- `family_projections`.

Fonti candidate:

- ISTAT famiglie e convivenze;
- ISTAT previsioni delle famiglie (`https://demo.istat.it/app/?i=PRF&l=it`).

### Acquisizioni di cittadinanza e italiani all'estero

Output proposti:

- `citizenship_acquisitions`;
- `aire_population`;
- `italians_abroad_age_sex`;
- `italians_abroad_country`.

Fonti candidate:

- ISTAT cittadinanza;
- AIRE/Ministero degli Affari Esteri (`https://www.esteri.it/it/servizi-opportunita/italiani-all-estero/aire_0/`).

## Priorita Media

### Titoli di studio territoriali e capitale umano

Output proposti:

- `education_attainment_territorial`;
- `graduates_migration`;
- `neet_indicators`;
- `students_enrolment`;
- `education_by_citizenship_birth_country`.

Fonti candidate:

- Eurostat LFS;
- ISTAT Censimento permanente;
- MIUR/MUR open data per istruzione e universita.

### Migrazioni interne avanzate

Output proposti:

- `internal_migration_od_matrix`;
- `internal_migration_south_north`;
- `internal_migration_young_adults`;
- `internal_migration_graduates`;
- `territorial_retention_young_people`.

Fonti candidate:

- ISTAT trasferimenti di residenza (`https://demo.istat.it/tavole/?t=apr4`);
- comunicati e tavole ISTAT sulle migrazioni interne e internazionali.

### Distribuzione territoriale

Output proposti:

- `territorial_population_change`;
- `territorial_density`;
- `territorial_ageing`;
- `municipal_decline`;
- `urban_rural_indicators`;
- `inner_areas_indicators`.

Fonti candidate:

- ISTAT popolazione residente territoriale;
- classificazioni territoriali ISTAT;
- Eurostat grado di urbanizzazione.

## Priorita Media-Bassa

### Stato civile e traiettorie familiari

Output proposti:

- `population_by_marital_status`;
- `marriages_unions_divorces`;
- `young_adults_living_with_parents`;
- `widowhood_age_sex`.

Fonti candidate:

- ISTAT popolazione per stato civile;
- ISTAT famiglie, matrimoni, unioni civili, separazioni e divorzi.

### Analisi per generazioni

Output proposti:

- `cohort_population`;
- `cohort_survival`;
- `cohort_fertility`;
- `cohort_migration`;
- `cohort_education`.

Fonti candidate:

- popolazione per anno di nascita ricostruita da eta e anno;
- tavole di mortalita;
- flussi migratori per eta;
- fonti censuarie e campionarie su istruzione.

## Regole metodologiche

- Stock e flussi restano separati.
- Osservazioni, stime campionarie e proiezioni restano separate.
- Cittadinanza, paese di nascita, provenienza e destinazione restano dimensioni distinte.
- Le quote da indagini campionarie non vengono convertite automaticamente in conteggi assoluti.
- Ogni nuova fonte deve produrre raw data, tabella normalizzata, voce nel catalogo metadati e test minimo.
