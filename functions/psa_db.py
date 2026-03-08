"""
PSA-Datenbank
Protokollierung von PSA-Verstößen (fehlende persönliche Schutzausrüstung).
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from config import BASE_DIR as _BASE_DIR

_DB_PFAD = Path(_BASE_DIR) / "database SQL" / "psa.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PFAD, timeout=5)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous  = NORMAL")
    conn.execute("PRAGMA busy_timeout  = 5000")
    return conn


def _init_db():
    _DB_PFAD.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS psa_verstoss (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            erstellt_am      TEXT NOT NULL,
            mitarbeiter      TEXT NOT NULL,
            datum            TEXT NOT NULL,
            psa_typ          TEXT NOT NULL,
            bemerkung        TEXT,
            aufgenommen_von  TEXT,
            gesendet         INTEGER DEFAULT 0
        )
        """)
        # Migration: gesendet-Spalte für bestehende Datenbanken ergänzen
        try:
            conn.execute("ALTER TABLE psa_verstoss ADD COLUMN gesendet INTEGER DEFAULT 0")
        except Exception:
            pass  # Spalte existiert bereits
        conn.commit()


def psa_speichern(daten: dict) -> int:
    _init_db()
    now = datetime.now().isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO psa_verstoss
              (erstellt_am, mitarbeiter, datum, psa_typ, bemerkung, aufgenommen_von)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                daten.get("mitarbeiter", ""),
                daten.get("datum", ""),
                daten.get("psa_typ", ""),
                daten.get("bemerkung", ""),
                daten.get("aufgenommen_von", ""),
            ),
        )
        conn.commit()
        return cur.lastrowid


def psa_aktualisieren(entry_id: int, daten: dict):
    _init_db()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE psa_verstoss
               SET mitarbeiter=?, datum=?, psa_typ=?, bemerkung=?, aufgenommen_von=?
             WHERE id=?
            """,
            (
                daten.get("mitarbeiter", ""),
                daten.get("datum", ""),
                daten.get("psa_typ", ""),
                daten.get("bemerkung", ""),
                daten.get("aufgenommen_von", ""),
                entry_id,
            ),
        )
        conn.commit()


def psa_loeschen(entry_id: int):
    _init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM psa_verstoss WHERE id=?", (entry_id,))
        conn.commit()


def lade_psa_eintraege(
    monat: int | None = None,
    jahr: int | None = None,
    suchtext: str | None = None,
) -> list[dict]:
    _init_db()
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM psa_verstoss WHERE 1=1"
        params: list = []
        if monat:
            q += " AND substr(datum, 4, 2) = ?"
            params.append(f"{monat:02d}")
        if jahr:
            q += " AND substr(datum, 7, 4) = ?"
            params.append(str(jahr))
        if suchtext:
            q += " AND (mitarbeiter LIKE ? OR psa_typ LIKE ? OR bemerkung LIKE ? OR aufgenommen_von LIKE ?)"
            params += [f"%{suchtext}%"] * 4
        q += " ORDER BY datum DESC, erstellt_am DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def verfuegbare_jahre() -> list[int]:
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT CAST(substr(datum, 7, 4) AS INTEGER) AS j "
            "FROM psa_verstoss WHERE length(datum) = 10 ORDER BY j DESC"
        ).fetchall()
        return [r[0] for r in rows if r[0]]


def markiere_psa_gesendet(entry_id: int):
    """Markiert einen PSA-Verstoß als per E-Mail versendet."""
    _init_db()
    with _connect() as conn:
        conn.execute("UPDATE psa_verstoss SET gesendet=1 WHERE id=?", (entry_id,))
        conn.commit()


def lade_psa_fuer_datum(datum_ddmmyyyy: str) -> list[dict]:
    """Gibt alle PSA-Verstöße für ein bestimmtes Datum zurück (dd.MM.yyyy)."""
    _init_db()
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM psa_verstoss WHERE datum=? ORDER BY erstellt_am ASC",
            (datum_ddmmyyyy,)
        ).fetchall()
        return [dict(r) for r in rows]
