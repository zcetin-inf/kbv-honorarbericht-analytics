"""ETL: KBV Honorarbericht (Excel, wide) -> tidy long CSV.

Liest data/raw/honorarbericht-tabellen.xlsx und schreibt
data/processed/honorarbericht_long.csv.

Es werden KEINE Werte veraendert (siehe Nutzungshinweis der KBV);
die Datei wird nur umstrukturiert und um Hilfsspalten ergaenzt.
"""
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/honorarbericht-tabellen.xlsx")
OUT = Path("data/processed/honorarbericht_long.csv")

# Spalten, die keine einzelne KV-Region sind
TOTAL_COLUMNS = [
    "Summe alte Bundesländer",
    "Summe neue Bundesländer",
    "Summe alle Bundesländer",
]


def read_raw(path: Path = RAW) -> pd.DataFrame:
    """Excel einlesen; Kopfzeile automatisch finden, Fussnoten entfernen."""
    raw = pd.read_excel(path, header=None)

    # Kopfzeile = erste Zeile, in der Spalte A 'Abrechnungsgruppe' steht
    header_row = raw.index[raw[0] == "Abrechnungsgruppe"][0]
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = raw.iloc[header_row].tolist()

    # Datenzeilen haben Kennzahl UND Quartal; Fussnoten/Copyright nicht
    df = df.dropna(subset=["Kennzahl", "Quartal"]).reset_index(drop=True)
    return df


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Wide (eine Spalte je KV) -> long (eine Zeile je Wert)."""
    id_cols = ["Abrechnungsgruppe", "Kennzahl", "Quartal"]
    value_cols = [c for c in df.columns if c not in id_cols]

    long = df.melt(
        id_vars=id_cols,
        value_vars=value_cols,
        var_name="Region",
        value_name="Wert",
    )
    long["Wert"] = pd.to_numeric(long["Wert"], errors="coerce")

    # Quartal '20131' -> Jahr 2013, Quartal 1
    q = long["Quartal"].astype(int).astype(str)
    long["Jahr"] = q.str[:4].astype(int)
    long["Quartal_Nr"] = q.str[4].astype(int)
    long["Periode"] = long["Jahr"].astype(str) + "-Q" + long["Quartal_Nr"].astype(str)
    long = long.drop(columns="Quartal")

    # Hilfsspalten: Summenzeilen / Summenspalten kennzeichnen (Doppelzaehlung!)
    long["ist_summenzeile"] = long["Abrechnungsgruppe"].str.startswith("Summe")
    long["ist_summenspalte"] = long["Region"].isin(TOTAL_COLUMNS)

    cols = [
        "Abrechnungsgruppe", "ist_summenzeile", "Kennzahl",
        "Region", "ist_summenspalte",
        "Jahr", "Quartal_Nr", "Periode", "Wert",
    ]
    return long[cols]


def main() -> None:
    df = read_raw()
    long = to_long(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    long.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Zeilen (wide): {len(df):,}")
    print(f"Zeilen (long): {len(long):,}")
    print(f"Abrechnungsgruppen: {long['Abrechnungsgruppe'].nunique()}")
    print(f"Kennzahlen: {long['Kennzahl'].nunique()}")
    print(f"Regionen (inkl. Summen): {long['Region'].nunique()}")
    print(f"Perioden: {long['Periode'].min()} bis {long['Periode'].max()}")
    print(f"Fehlende Werte: {long['Wert'].isna().sum():,}")
    print(f"Geschrieben: {OUT}")


if __name__ == "__main__":
    main()