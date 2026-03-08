"""
SQLite Datenbankverbindung
Verwaltet Verbindungen zur Nesk3 SQLite-Datenbank.
WAL-Modus für sicheres gleichzeitiges Lesen von mehreren PCs.
"""
import sqlite3
from contextlib import contextmanager
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH, MITARBEITER_DB_PATH


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Gibt jede Zeile als dict zurück (Spaltenname → Wert)."""
    cols = [c[0] for c in cursor.description]
    return dict(zip(cols, row))


def get_connection() -> sqlite3.Connection:
    """Gibt eine neue SQLite-Verbindung zurück (WAL-Modus, dict-Zeilen)."""
    conn = sqlite3.connect(DB_PATH, timeout=3, check_same_thread=False)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def test_connection() -> tuple[bool, str]:
    """
    Testet die Datenbankverbindung.
    Gibt (True, Info) oder (False, Fehlermeldung) zurück.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT sqlite_version()")
        row = cur.fetchone()
        version = row["sqlite_version()"] if row else "?"
        conn.close()
        return True, f"SQLite {version}  |  {DB_PATH}"
    except Exception as e:
        return False, str(e)


@contextmanager
def db_cursor(commit: bool = False):
    """
    Kontextmanager für DB-Cursor mit automatischem Commit/Rollback.
    Cursor liefert Zeilen als dict.

    Verwendung:
        with db_cursor(commit=True) as cur:
            cur.execute("INSERT ...")
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# ── Mitarbeiter-Datenbank (database SQL/mitarbeiter.db) ───────────────────────

_MA_SCHEMA = """
CREATE TABLE IF NOT EXISTS positionen (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT UNIQUE NOT NULL
);
INSERT OR IGNORE INTO positionen(name) VALUES
    ('Notfallsanitäter'),('Rettungssanitäter'),('Sanitätshelfer'),
    ('Arzt'),('Verwaltung'),('Führungskraft');

CREATE TABLE IF NOT EXISTS abteilungen (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT UNIQUE NOT NULL
);
INSERT OR IGNORE INTO abteilungen(name) VALUES
    ('Erste-Hilfe-Station'),('Sanitätsdienst'),('Verwaltung');

CREATE TABLE IF NOT EXISTS mitarbeiter (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vorname         TEXT NOT NULL,
    nachname        TEXT NOT NULL,
    personalnummer  TEXT DEFAULT '',
    funktion        TEXT DEFAULT 'stamm' CHECK (funktion IN ('stamm','dispo')),
    position        TEXT DEFAULT '',
    abteilung       TEXT DEFAULT '',
    email           TEXT DEFAULT '',
    telefon         TEXT DEFAULT '',
    eintrittsdatum  TEXT,
    status          TEXT DEFAULT 'aktiv',
    erstellt_am     TEXT DEFAULT (datetime('now','localtime')),
    geaendert_am    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ma_nachname ON mitarbeiter(nachname);
CREATE INDEX IF NOT EXISTS idx_ma_funktion ON mitarbeiter(funktion);
"""


def get_ma_connection() -> sqlite3.Connection:
    """Gibt eine Verbindung zur Mitarbeiter-Datenbank zurück."""
    conn = sqlite3.connect(MITARBEITER_DB_PATH, timeout=3, check_same_thread=False)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_mitarbeiter_db() -> None:
    """
    Erstellt die Mitarbeiter-Datenbank und Tabellen, falls noch nicht vorhanden.
    Wird beim App-Start aufgerufen.
    """
    conn = get_ma_connection()
    conn.executescript(_MA_SCHEMA)
    conn.commit()
    conn.close()


@contextmanager
def ma_db_cursor(commit: bool = False):
    """
    Kontextmanager für die Mitarbeiter-Datenbank (mitarbeiter.db).
    Verwendung identisch zu db_cursor().
    """
    conn = None
    try:
        conn = get_ma_connection()
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
