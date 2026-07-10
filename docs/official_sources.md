# Fonti ufficiali italiane

## ISTAT

La pipeline interroga il catalogo SDMX e assegna i dataflow ai ruoli definiti in `demografia/istat_registry.py`. Il registro completo viene salvato in `istat_demographic_dataflows`.

L'assegnazione automatica conserva punteggio e indicatore di ambiguità. Gli override passati dalla CLI hanno priorità.

## INPS

La pipeline usa le API ufficiali del DataCatalog INPS:

- `package_list`;
- `package_show`;
- `current_package_list_with_resources`;
- `status`.

Il catalogo viene normalizzato a livello di risorsa. I dataset vengono classificati come pensionati, pensioni, contribuenti, assicurati o flussi di pensionamento. CSV, JSON, XLSX, XLS e XML sono letti in ordine di preferenza.

Le tabelle finali mantengono distinti:

- persone;
- pensioni o trattamenti;
- importi;
- contributi;
- gestione o fondo;
- categoria professionale ricostruibile dalla gestione;
- sesso, età e territorio.

## Ragioneria Generale dello Stato

La pipeline usa le API CKAN di OpenBDAP per cercare pacchetti e risorse relativi a pensioni, sistema pensionistico, proiezioni di medio-lungo periodo, sanità e assistenza di lungo periodo.

Le tabelle vengono trasformate in formato lungo con:

- edizione della proiezione;
- anno;
- scenario;
- indicatore;
- unità;
- valore;
- eventuali limiti inferiore e superiore.

Il pannello integrato collega gli indicatori demografici, previdenziali e fiscali per anno senza confondere dati osservati e proiezioni.
