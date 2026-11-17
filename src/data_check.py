"""Data-Quality-Checks fuer den KBV Honorarbericht (tidy CSV aus etl.py).

Jede Pruefung gibt einen DataFrame mit den VERLETZUNGEN zurueck
(leer = Pruefung bestanden). So lassen sich dieselben Funktionen fuer
den Bericht (python src/checks.py) und fuer pytest verwenden.
"""
from pathlib import Path

import numpy as np
import pandas as pd

LONG = Path("data/processed/honorarbericht_long.csv")
REPORT = Path("reports/data_quality_report.md")

TOTAL = "Summe alle Bundesländer"
ALTE = "Summe alte Bundesländer"
NEUE = "Summe neue Bundesländer"
TOTALS = [ALTE, NEUE, TOTAL]

HU = "Honorarumsatz in Euro"
# Kennzahlen, bei denen Summe ueber Regionen = Gesamtwert gelten muss
ADDITIVE = [
    HU,
    "Anzahl Ärzte (nach Teilnahmeumfang)",
    "Leistungsbedarf nach Euro-Gebührenordnung",
    "Leistungsbedarf in Punkten",
    "Leistungsbedarf in Euro",
    "Anzahl Behandlungsfälle",
]
TOL = 1e-9  # relative Toleranz (Gleitkomma-Rauschen liegt bei ~1e-14)


def load(path: Path = LONG) -> pd.DataFrame:
    return pd.read_csv(path)


def _by_region(df: pd.DataFrame, kennzahlen: list[str]) -> pd.DataFrame:
    """Index: Gruppe/Kennzahl/Periode, Spalten: Regionen."""
    x = df[df["Kennzahl"].isin(kennzahlen)]
    return x.set_index(["Abrechnungsgruppe", "Kennzahl", "Periode", "Region"])[
        "Wert"
    ].unstack("Region")


def _kv_columns(w: pd.DataFrame) -> list[str]:
    return [c for c in w.columns if c not in TOTALS]


def check_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    key = ["Abrechnungsgruppe", "Kennzahl", "Region", "Periode"]
    return df[df.duplicated(key, keep=False)]


def check_complete_grid(df: pd.DataFrame) -> int:
    """Fehlende Zeilen gegenueber dem vollstaendigen Raster (0 = vollstaendig)."""
    expected = (
        df["Abrechnungsgruppe"].nunique()
        * df["Kennzahl"].nunique()
        * df["Region"].nunique()
        * df["Periode"].nunique()
    )
    return expected - len(df)


def check_periods(df: pd.DataFrame) -> list[int]:
    """Luecken in der Quartalsfolge (leere Liste = lueckenlos)."""
    idx = sorted((df["Jahr"] * 4 + df["Quartal_Nr"] - 1).unique())
    return [i for i, j in zip(idx, idx[1:]) if j - i != 1]


def check_alte_plus_neue(df: pd.DataFrame) -> pd.DataFrame:
    """Summe alte + Summe neue Bundeslaender = Summe alle Bundeslaender."""
    w = _by_region(df, ADDITIVE)
    diff = (w[ALTE] + w[NEUE] - w[TOTAL]).abs()
    bad = diff > TOL * w[TOTAL].abs().clip(lower=1)
    return diff[bad].rename("abs_abweichung").reset_index()


def check_regions_sum_to_total(df: pd.DataFrame) -> pd.DataFrame:
    """Summe der 17 KVen = Gesamtwert - nur dort, wo alle 17 Werte vorliegen."""
    w = _by_region(df, ADDITIVE)
    kvs = _kv_columns(w)
    complete = w[kvs].notna().all(axis=1)
    diff = (w[kvs].sum(axis=1) - w[TOTAL]).abs()
    bad = complete & (diff > TOL * w[TOTAL].abs().clip(lower=1))
    return diff[bad].rename("abs_abweichung").reset_index()


def regional_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Zellen ohne Wert, obwohl der Bundesgesamtwert vorhanden ist.

    Zeigt, welcher Anteil des Gesamtwerts in den Regionen nicht ausgewiesen ist.
    """
    w = _by_region(df, [HU]).xs(HU, level="Kennzahl")
    kvs = _kv_columns(w)
    gaps = w[w[kvs].isna().any(axis=1) & w[TOTAL].notna()].copy()
    gaps["fehlende_regionen"] = gaps[kvs].isna().apply(
        lambda r: ", ".join(r.index[r]), axis=1
    )
    gaps["anteil_nicht_ausgewiesen"] = (gaps[TOTAL] - gaps[kvs].sum(axis=1)) / gaps[TOTAL]
    return gaps[["fehlende_regionen", "anteil_nicht_ausgewiesen"]].reset_index()


def check_nan_pattern(df: pd.DataFrame) -> pd.DataFrame:
    """Fehlt ein Wert, sollten alle 11 Kennzahlen derselben Zelle fehlen."""
    n = (
        df.assign(fehlt=df["Wert"].isna())
        .groupby(["Abrechnungsgruppe", "Region", "Periode"])["fehlt"]
        .agg(["sum", "size"])
    )
    return n[(n["sum"] > 0) & (n["sum"] < n["size"])].reset_index()


DERIVED_RULES = {
    "Honorarumsatz je Arzt in Euro": (HU, "Anzahl Ärzte"),
    "Honorarumsatz je Behandlungsfall in Euro": (HU, "Anzahl Behandlungsfälle"),
    "Anzahl Behandlungsfälle je Arzt": ("Anzahl Behandlungsfälle", "Anzahl Ärzte"),
}


def check_derived_kpis(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Abgeleitete Kennzahlen aus den Basiswerten neu berechnen und vergleichen."""
    w = df.set_index(["Abrechnungsgruppe", "Region", "Periode", "Kennzahl"])[
        "Wert"
    ].unstack("Kennzahl")
    out = {}
    for target, (num, den) in DERIVED_RULES.items():
        calc = w[num] / w[den]
        rel = ((calc - w[target]).abs() / w[target].abs()).rename("rel_abweichung")
        out[target] = rel[rel > TOL].reset_index()
    return out


def auszahlungsquote_range(df: pd.DataFrame) -> tuple[float, float]:
    """Wertebereich der 'Auszahlungsquote in Prozent' (liegt als Anteil vor!)."""
    v = df.loc[df["Kennzahl"] == "Auszahlungsquote in Prozent", "Wert"].dropna()
    return float(v.min()), float(v.max())


def build_report(df: pd.DataFrame) -> str:
    dup = check_duplicates(df)
    gaps = regional_gaps(df)
    derived = check_derived_kpis(df)
    lo, hi = auszahlungsquote_range(df)
    lines = [
        "# Data-Quality-Bericht: KBV Honorarbericht",
        "",
        f"- Zeilen (long): {len(df):,}",
        f"- Abrechnungsgruppen: {df['Abrechnungsgruppe'].nunique()}, "
        f"Kennzahlen: {df['Kennzahl'].nunique()}, "
        f"Perioden: {df['Periode'].min()} bis {df['Periode'].max()}",
        "",
        "## Ergebnisse der Prüfungen",
        "",
        "| Prüfung | Verletzungen |",
        "|---|---|",
        f"| Doppelte Schlüssel | {len(dup)} |",
        f"| Fehlende Zeilen im vollständigen Raster | {check_complete_grid(df)} |",
        f"| Lücken in der Quartalsfolge | {len(check_periods(df))} |",
        f"| Summe alte + neue Länder = Summe alle (6 additive Kennzahlen) | {len(check_alte_plus_neue(df))} |",
        f"| Summe 17 KVen = Gesamtwert (nur bei vollständigen Regionen) | {len(check_regions_sum_to_total(df))} |",
        f"| Teil-Fehlwerte je Zelle (Kennzahlen fehlen nur teilweise) | {len(check_nan_pattern(df))} |",
    ]
    for name, v in derived.items():
        lines.append(f"| Neuberechnung: {name} | {len(v)} |")
    lines += [
        "",
        "## Auffälligkeiten (keine Fehler, aber wichtig für die Analyse)",
        "",
        f"1. **Nicht ausgewiesene Regionen:** In {len(gaps)} Kombinationen aus Gruppe und "
        "Quartal fehlt mindestens eine KV-Region, obwohl der Bundesgesamtwert vorhanden ist. "
        f"In {int((gaps['anteil_nicht_ausgewiesen'] > TOL).sum())} davon liegt die Summe der "
        "KVen deshalb unter dem Gesamtwert (bis zu "
        f"{gaps['anteil_nicht_ausgewiesen'].max():.0%}). Regionen dürfen in diesen Fällen nicht "
        "zu einer Bundessumme addiert werden; dafür 'Summe alle Bundesländer' verwenden.",
        f"2. **Auszahlungsquote:** Der Name sagt 'in Prozent', die Werte liegen aber als "
        f"Anteil vor (Min {lo:.2f}, Max {hi:.2f}); 0,97 bedeutet 97 %.",
        "3. **Anzahl Ärzte ist nicht additiv:** Summe alte + neue Länder weicht vom "
        "Gesamtwert ab (vermutlich Ärzte mit Tätigkeit in mehreren KVen). Für Summen "
        "'Anzahl Ärzte (nach Teilnahmeumfang)' verwenden.",
        "4. **Summenzeilen:** 'Summe …'-Abrechnungsgruppen nie mit Detailgruppen addieren "
        "(Spalte ist_summenzeile).",
        "5. **Leistungsbedarf in Punkten:** Bis Q3/2013 mit Faktor 0,35363 multiplizieren, "
        "um Zeitreihen vergleichbar zu machen (Fußnote der KBV).",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    df = load()
    text = build_report(df)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    print(text)
    print(f"Bericht geschrieben: {REPORT}")


if __name__ == "__main__":
    main()
