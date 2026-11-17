# Data-Quality-Bericht: KBV Honorarbericht

- Zeilen (long): 527,340
- Abrechnungsgruppen: 51, Kennzahlen: 11, Perioden: 2013-Q1 bis 2024-Q3

## Ergebnisse der Prüfungen

| Prüfung | Verletzungen |
|---|---|
| Doppelte Schlüssel | 0 |
| Fehlende Zeilen im vollständigen Raster | 0 |
| Lücken in der Quartalsfolge | 0 |
| Summe alte + neue Länder = Summe alle (6 additive Kennzahlen) | 0 |
| Summe 17 KVen = Gesamtwert (nur bei vollständigen Regionen) | 0 |
| Teil-Fehlwerte je Zelle (Kennzahlen fehlen nur teilweise) | 0 |
| Neuberechnung: Honorarumsatz je Arzt in Euro | 0 |
| Neuberechnung: Honorarumsatz je Behandlungsfall in Euro | 0 |
| Neuberechnung: Anzahl Behandlungsfälle je Arzt | 0 |

## Auffälligkeiten (keine Fehler, aber wichtig für die Analyse)

1. **Nicht ausgewiesene Regionen:** In 639 Kombinationen aus Gruppe und Quartal fehlt mindestens eine KV-Region, obwohl der Bundesgesamtwert vorhanden ist. In 623 davon liegt die Summe der KVen deshalb unter dem Gesamtwert (bis zu 84%). Regionen dürfen in diesen Fällen nicht zu einer Bundessumme addiert werden; dafür 'Summe alle Bundesländer' verwenden.
2. **Auszahlungsquote:** Der Name sagt 'in Prozent', die Werte liegen aber als Anteil vor (Min 0.49, Max 1.38); 0,97 bedeutet 97 %.
3. **Anzahl Ärzte ist nicht additiv:** Summe alte + neue Länder weicht vom Gesamtwert ab (vermutlich Ärzte mit Tätigkeit in mehreren KVen). Für Summen 'Anzahl Ärzte (nach Teilnahmeumfang)' verwenden.
4. **Summenzeilen:** 'Summe …'-Abrechnungsgruppen nie mit Detailgruppen addieren (Spalte ist_summenzeile).
5. **Leistungsbedarf in Punkten:** Bis Q3/2013 mit Faktor 0,35363 multiplizieren, um Zeitreihen vergleichbar zu machen (Fußnote der KBV).
