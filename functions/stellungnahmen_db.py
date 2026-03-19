"""
Stellungnahmen-Datenbank (SQLite)
Speichert Metadaten zu erstellten Stellungnahmen – keine Word-Inhalte,
nur Verweise auf die Dateien und durchsuchbare Felder.
"""
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from config import BASE_DIR

DB_ORDNER = os.path.join(BASE_DIR, "database SQL")
DB_PFAD   = os.path.join(DB_ORDNER, "stellungnahmen.db")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS stellungnahmen (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    erstellt_am     TEXT    NOT NULL,          -- ISO-Datum der DB-Eintragung
    datum_vorfall   TEXT    NOT NULL,          -- dd.MM.yyyy (Datum des Vorfalls)
    verfasst_am     TEXT    NOT NULL,          -- dd.MM.yyyy (Datum der Erstellung)
    mitarbeiter     TEXT    NOT NULL,
    art             TEXT    NOT NULL,          -- flug | beschwerde | nicht_mitgeflogen
    flugnummer      TEXT    DEFAULT '',
    verspaetung     INTEGER DEFAULT 0,         -- 0 / 1
    onblock         TEXT    DEFAULT '',
    offblock        TEXT    DEFAULT '',
    richtung        TEXT    DEFAULT '',        -- inbound | outbound | beides
    ankunft_lfz     TEXT    DEFAULT '',
    auftragsende    TEXT    DEFAULT '',
    paxannahme_zeit TEXT    DEFAULT '',
    paxannahme_ort  TEXT    DEFAULT '',
    sachverhalt     TEXT    DEFAULT '',
    beschwerde_text TEXT    DEFAULT '',
    pfad_intern     TEXT    NOT NULL,          -- vollständiger Dateipfad (intern)
    pfad_extern     TEXT    DEFAULT ''         -- vollständiger Dateipfad (extern)
);
"""

_ART_LABEL = {
    "flug":              "✈️  Flug-Vorfall",
    "beschwerde":        "🗣️  Passagierbeschwerde",
    "nicht_mitgeflogen": "🚶  Nicht mitgeflogen",
}

# ──────────────────────────────────────────────────────────────────────────────
#  Internes Datenbankmanagement
# ──────────────────────────────────────────────────────────────────────────────

def _ensured_db() -> str:
    """Stellt sicher, dass der DB-Ordner existiert und das Schema angelegt ist."""
    os.makedirs(DB_ORDNER, exist_ok=True)
    con = sqlite3.connect(DB_PFAD, timeout=5)
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous  = NORMAL")
    con.execute("PRAGMA busy_timeout  = 5000")
    con.execute(_CREATE_SQL)
    con.commit()
    con.close()
    return DB_PFAD


@contextmanager
def _db():
    """Context-Manager: liefert eine Row-Factory-Connection."""
    _ensured_db()
    con = sqlite3.connect(DB_PFAD, timeout=5)
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous  = NORMAL")
    con.execute("PRAGMA busy_timeout  = 5000")
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


# ──────────────────────────────────────────────────────────────────────────────
#  Schreiben
# ──────────────────────────────────────────────────────────────────────────────

def eintrag_speichern(daten: dict, pfad_intern: str, pfad_extern: str) -> int:
    """
    Legt einen neuen Datensatz in der Datenbank an.
    Gibt die neue Row-ID zurück.
    """
    with _db() as con:
        cur = con.execute(
            """
            INSERT INTO stellungnahmen (
                erstellt_am, datum_vorfall, verfasst_am, mitarbeiter, art,
                flugnummer, verspaetung, onblock, offblock, richtung,
                ankunft_lfz, auftragsende, paxannahme_zeit, paxannahme_ort,
                sachverhalt, beschwerde_text, pfad_intern, pfad_extern
            ) VALUES (
                :erstellt_am, :datum_vorfall, :verfasst_am, :mitarbeiter, :art,
                :flugnummer, :verspaetung, :onblock, :offblock, :richtung,
                :ankunft_lfz, :auftragsende, :paxannahme_zeit, :paxannahme_ort,
                :sachverhalt, :beschwerde_text, :pfad_intern, :pfad_extern
            )
            """,
            {
                "erstellt_am":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "datum_vorfall":  daten.get("datum", ""),
                "verfasst_am":    daten.get("verfasst_am", ""),
                "mitarbeiter":    daten.get("mitarbeiter", ""),
                "art":            daten.get("art", ""),
                "flugnummer":     daten.get("flugnummer", ""),
                "verspaetung":    1 if daten.get("verspaetung") else 0,
                "onblock":        daten.get("onblock", ""),
                "offblock":       daten.get("offblock", ""),
                "richtung":       daten.get("richtung", ""),
                "ankunft_lfz":    daten.get("ankunft_lfz", ""),
                "auftragsende":   daten.get("auftragsende", ""),
                "paxannahme_zeit":daten.get("paxannahme_zeit", ""),
                "paxannahme_ort": daten.get("paxannahme_ort", ""),
                "sachverhalt":    daten.get("sachverhalt", ""),
                "beschwerde_text":daten.get("beschwerde_text", ""),
                "pfad_intern":    pfad_intern,
                "pfad_extern":    pfad_extern,
            },
        )
        new_id = cur.lastrowid
    try:
        from functions.stellungnahmen_html_export import generiere_html as _html_gen
        _html_gen()
    except Exception:
        pass
    return new_id


def eintrag_loeschen(row_id: int) -> None:
    """Entfernt einen Datensatz (nicht aber die Word-Datei) aus der Datenbank."""
    with _db() as con:
        con.execute("DELETE FROM stellungnahmen WHERE id = ?", (row_id,))
    try:
        from database.turso_sync import push_delete
        push_delete(DB_PFAD, "stellungnahmen", row_id)
    except Exception:
        pass
    try:
        from functions.stellungnahmen_html_export import generiere_html as _html_gen
        _html_gen()
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  Abfragen
# ──────────────────────────────────────────────────────────────────────────────

def lade_alle(
    *,
    monat: int | None = None,
    jahr: int | None = None,
    art: str | None = None,
    suchtext: str | None = None,
) -> list[dict]:
    """
    Gibt Stellungnahmen gefiltert zurück (alle Parameter optional).
    Ergebnis: Liste von dicts mit allen Spalten + 'art_label'.
    Sortierung: neueste zuerst (datum_vorfall DESC, id DESC).
    """
    where_parts: list[str] = []
    params: list = []

    # Monat/Jahr-Filter auf datum_vorfall (Format dd.MM.yyyy)
    if monat is not None:
        where_parts.append("substr(datum_vorfall, 4, 2) = ?")
        params.append(f"{monat:02d}")
    if jahr is not None:
        where_parts.append("substr(datum_vorfall, 7, 4) = ?")
        params.append(str(jahr))
    if art:
        where_parts.append("art = ?")
        params.append(art)
    if suchtext:
        term = f"%{suchtext}%"
        where_parts.append(
            "(mitarbeiter LIKE ? OR flugnummer LIKE ? OR sachverhalt LIKE ?"
            " OR beschwerde_text LIKE ?)"
        )
        params.extend([term, term, term, term])

    sql = "SELECT * FROM stellungnahmen"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    sql += " ORDER BY substr(datum_vorfall,7,4)||substr(datum_vorfall,4,2)"
    sql += "||substr(datum_vorfall,1,2) DESC, id DESC"

    with _db() as con:
        rows = con.execute(sql, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["art_label"] = _ART_LABEL.get(d["art"], d["art"])
        result.append(d)
    return result


def verfuegbare_jahre() -> list[int]:
    """Gibt alle Jahre zurück, für die Einträge existieren (absteigend)."""
    with _db() as con:
        rows = con.execute(
            "SELECT DISTINCT substr(datum_vorfall,7,4) AS j FROM stellungnahmen"
            " WHERE length(datum_vorfall)=10 ORDER BY j DESC"
        ).fetchall()
    jahre = []
    for r in rows:
        try:
            jahre.append(int(r["j"]))
        except (ValueError, TypeError):
            pass
    return jahre


def verfuegbare_monate(jahr: int) -> list[int]:
    """Gibt alle Monate zurück, in denen im gegebenen Jahr Einträge existieren."""
    with _db() as con:
        rows = con.execute(
            "SELECT DISTINCT substr(datum_vorfall,4,2) AS m FROM stellungnahmen"
            " WHERE substr(datum_vorfall,7,4)=? ORDER BY m",
            (str(jahr),),
        ).fetchall()
    monate = []
    for r in rows:
        try:
            monate.append(int(r["m"]))
        except (ValueError, TypeError):
            pass
    return monate


def get_eintrag(row_id: int) -> dict | None:
    """Gibt einen einzelnen Eintrag als dict zurück oder None."""
    with _db() as con:
        row = con.execute(
            "SELECT * FROM stellungnahmen WHERE id=?", (row_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["art_label"] = _ART_LABEL.get(d["art"], d["art"])
    return d
