"""
Verspätungs-Datenbank
Protokollierung von Meldungen über unpünktlichen Dienstantritt.
"""
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
_DB_PFAD = BASE_DIR / "database SQL" / "verspaetungen.db"


def _connect() -> sqlite3.Connection:
    """Gibt eine Verbindung mit WAL-Modus und busy_timeout zurück."""
    conn = sqlite3.connect(_DB_PFAD, timeout=5)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous  = NORMAL")
    conn.execute("PRAGMA busy_timeout  = 5000")
    return conn


def _init_db():
    _DB_PFAD.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS verspaetungen (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            erstellt_am      TEXT NOT NULL,
            mitarbeiter      TEXT NOT NULL,
            datum            TEXT NOT NULL,          -- dd.MM.yyyy
            dienst           TEXT NOT NULL,          -- T | T10 | N | N10
            dienstbeginn     TEXT NOT NULL,          -- HH:MM
            dienstantritt    TEXT NOT NULL,          -- HH:MM
            verspaetung_min  INTEGER,
            begruendung      TEXT,
            aufgenommen_von  TEXT,
            dokument_pfad    TEXT
        )
        """)
        conn.commit()


def verspaetung_speichern(daten: dict) -> int:
    """Neuen Eintrag speichern, gibt die neue ID zurück."""
    _init_db()
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO verspaetungen
              (erstellt_am, mitarbeiter, datum, dienst, dienstbeginn, dienstantritt,
               verspaetung_min, begruendung, aufgenommen_von, dokument_pfad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                daten.get("mitarbeiter", ""),
                daten.get("datum", ""),
                daten.get("dienst", ""),
                daten.get("dienstbeginn", ""),
                daten.get("dienstantritt", ""),
                daten.get("verspaetung_min"),
                daten.get("begruendung", ""),
                daten.get("aufgenommen_von", ""),
                daten.get("dokument_pfad", ""),
            ),
        )
        conn.commit()
        return cur.lastrowid


def verspaetung_aktualisieren(entry_id: int, daten: dict):
    """Bestehenden Eintrag aktualisieren."""
    _init_db()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE verspaetungen
               SET mitarbeiter=?, datum=?, dienst=?, dienstbeginn=?, dienstantritt=?,
                   verspaetung_min=?, begruendung=?, aufgenommen_von=?, dokument_pfad=?
             WHERE id=?
            """,
            (
                daten.get("mitarbeiter", ""),
                daten.get("datum", ""),
                daten.get("dienst", ""),
                daten.get("dienstbeginn", ""),
                daten.get("dienstantritt", ""),
                daten.get("verspaetung_min"),
                daten.get("begruendung", ""),
                daten.get("aufgenommen_von", ""),
                daten.get("dokument_pfad", ""),
                entry_id,
            ),
        )
        conn.commit()


def verspaetung_loeschen(entry_id: int):
    """Eintrag aus der Datenbank löschen."""
    _init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM verspaetungen WHERE id=?", (entry_id,))
        conn.commit()


def lade_verspaetungen(
    monat: int | None = None,
    jahr: int | None = None,
    suchtext: str | None = None,
) -> list[dict]:
    """Einträge laden; optionale Filterung nach Monat/Jahr/Suchtext."""
    _init_db()
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM verspaetungen WHERE 1=1"
        params: list = []
        if monat:
            q += " AND substr(datum, 4, 2) = ?"
            params.append(f"{monat:02d}")
        if jahr:
            q += " AND substr(datum, 7, 4) = ?"
            params.append(str(jahr))
        if suchtext:
            q += " AND (mitarbeiter LIKE ? OR begruendung LIKE ? OR aufgenommen_von LIKE ?)"
            params += [f"%{suchtext}%"] * 3
        q += " ORDER BY datum DESC, erstellt_am DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def verfuegbare_jahre() -> list[int]:
    """Liste aller Jahre mit Einträgen zurückgeben."""
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT CAST(substr(datum, 7, 4) AS INTEGER) AS j "
            "FROM verspaetungen WHERE length(datum) = 10 ORDER BY j DESC"
        ).fetchall()
        return [r[0] for r in rows if r[0]]
