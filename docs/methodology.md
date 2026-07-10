# Metodo

La base analitica è la popolazione per anno, età, sesso e territorio. Dati osservati e proiezioni restano separati tramite `status`, `scenario` e `source`.

## Confronti

Per l'Unione europea si usa Eurostat. La pipeline richiede tutti i 27 Stati membri e produce controlli di copertura per paese. Per i 38 membri OECD si usa un pannello armonizzato World Bank WDI. Le piramidi e le proiezioni dei membri OECD extraeuropei richiedono il file ufficiale UN World Population Prospects 2024, importabile con `--wpp-age-sex`.

## Piramidi

Le piramidi utilizzano uomini e donne per singolo anno di età, quando disponibile. I valori sono espressi in numero di persone e quota della popolazione. L'animazione usa una scala fissa per rendere confrontabili gli anni.

## Dipendenza

La dipendenza demografica è distinta dalla dipendenza economica. La prima usa fasce di età. La seconda richiederebbe occupati, disoccupati, inattivi e pensionati e va costruita collegando dati del mercato del lavoro e del sistema pensionistico.

## Migrazioni

Cittadinanza e paese di nascita restano variabili separate. I flussi internazionali, la mobilità interna e lo stock di residenti stranieri o nati all'estero non sono intercambiabili. Le stime da indagini campionarie su istruzione e lavoro restano separate dai dati anagrafici.

## Proiezioni

Le proiezioni sono scenari condizionati alle ipotesi su fertilità, mortalità e migrazione. Non vengono concatenate automaticamente alle osservazioni senza mantenere l'indicazione della fonte e dello scenario. Le diverse edizioni devono essere conservate per poter valutare gli errori delle proiezioni precedenti.
