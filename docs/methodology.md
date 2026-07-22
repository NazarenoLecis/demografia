# Metodo

La base analitica e la popolazione per anno, eta, sesso e territorio. Dati osservati e proiezioni restano separati tramite `status`, `scenario` e `source`.

## Confronti

Per l'Unione europea si usa Eurostat. La pipeline richiede tutti i 27 Stati membri e produce controlli di copertura per paese. Per i 38 membri OECD si usa un pannello armonizzato World Bank WDI. I kebab demografici e le proiezioni dei membri OECD extraeuropei richiedono il file ufficiale UN World Population Prospects 2024, configurabile in `scripts/run_pipeline.py`.

## Kebab

I kebab demografici utilizzano uomini e donne per singolo anno di eta, quando disponibile. I valori sono espressi in numero di persone e quota della popolazione. L'animazione usa una scala fissa per rendere confrontabili gli anni.

## Dipendenza

La dipendenza demografica e distinta dalla dipendenza economica. La prima usa fasce di eta. La seconda richiederebbe occupati, disoccupati, inattivi e pensionati e va costruita collegando dati del mercato del lavoro e del sistema pensionistico.

## Migrazioni

Cittadinanza e paese di nascita restano variabili separate. I flussi internazionali, la mobilita interna e lo stock di residenti stranieri o nati all'estero non sono intercambiabili.

## Titoli Di Studio

La distribuzione per titolo di studio usa Eurostat LFS (`edat_lfse_03`). Le quote sono salvate per paese, anno, sesso, fascia di eta e livello ISCED 2011. La tabella non viene convertita automaticamente in conteggi assoluti, per evitare di mescolare stime campionarie e popolazione anagrafica senza un passaggio esplicito di ponderazione.

## Proiezioni

Le proiezioni sono scenari condizionati alle ipotesi su fertilita, mortalita e migrazione. Non vengono concatenate automaticamente alle osservazioni senza mantenere l'indicazione della fonte e dello scenario. Le diverse edizioni devono essere conservate per poter valutare gli errori delle proiezioni precedenti.
