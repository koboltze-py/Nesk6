"""
Datenbankschicht für die Call-Transcription-Erfassung.
Datenbank: database SQL/call_transcription.db
"""
import os
import sqlite3

from config import BASE_DIR

_DB_PATH = os.path.join(BASE_DIR, "database SQL", "call_transcription.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Erstellt die Tabellen beim ersten Start."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS call_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                datum           TEXT NOT NULL,
                uhrzeit         TEXT NOT NULL,
                flug_richtung   TEXT    DEFAULT '',
                flugnummer      TEXT    DEFAULT '',
                ziel_herkunft   TEXT    DEFAULT '',
                passagier_name  TEXT    DEFAULT '',
                hilfeart        TEXT    DEFAULT '',
                anrufer         TEXT    DEFAULT '',
                telefon         TEXT    DEFAULT '',
                richtung        TEXT    DEFAULT 'Eingehend',
                kategorie       TEXT    DEFAULT '',
                betreff         TEXT    DEFAULT '',
                notiz           TEXT    DEFAULT '',
                erledigt        INTEGER DEFAULT 0,
                erstellt        TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)
        # Textbausteine (benutzerdefiniert)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS textbausteine (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                gruppe      TEXT    NOT NULL,
                text        TEXT    NOT NULL
            )
        """)
        conn.commit()
        _migrate(conn)
        _init_default_bausteine(conn)


def _migrate(conn: sqlite3.Connection):
    """Fügt fehlende Spalten zur bestehenden Tabelle hinzu (Schema-Migration)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(call_logs)")}
    new_cols = [
        ("flug_richtung",  "TEXT DEFAULT ''"),
        ("flugnummer",     "TEXT DEFAULT ''"),
        ("ziel_herkunft",  "TEXT DEFAULT ''"),
        ("passagier_name", "TEXT DEFAULT ''"),
        ("hilfeart",       "TEXT DEFAULT ''"),
    ]
    for col, typedef in new_cols:
        if col not in existing:
            conn.execute(f"ALTER TABLE call_logs ADD COLUMN {col} {typedef}")
    conn.commit()


def _init_default_bausteine(conn: sqlite3.Connection):
    """Legt Standard-Textbausteine an, falls die Tabelle noch leer ist."""
    count = conn.execute("SELECT COUNT(*) FROM textbausteine").fetchone()[0]
    if count > 0:
        return
    defaults = [
        ("PRM Anmeldung", "Passagier angemeldet – Rollstuhlservice angefordert."),
        ("PRM Anmeldung", "Passagier benötigt Begleitung bis zum Gate."),
        ("PRM Anmeldung", "Passagier benötigt Boarding-Hilfe."),
        ("PRM Anmeldung", "Passagier benötigt Treppensteig-Hilfe."),
        ("PRM Anmeldung", "Passagier vollständig immobil – Ambulift erforderlich."),
        ("PRM Anmeldung", "Passagier mit Sehbehinderung – Begleitung erforderlich."),
        ("PRM Anmeldung", "Passagier mit Hörbehinderung."),
        ("PRM Anmeldung", "Passagier mit kognitiver Einschränkung."),
        ("PRM Status", "Passagier wurde abgeholt."),
        ("PRM Status", "Passagier befindet sich am Check-In."),
        ("PRM Status", "Passagier befindet sich am Gate: "),
        ("PRM Status", "Passagier wurde zum Gate begleitet."),
        ("PRM Status", "Passagier wartet am PRM-Wartebereich."),
        ("PRM Status", "Passagier wurde ins Fahrzeug gesetzt."),
        ("PRM Status", "Übergabe an Flugzeugbesatzung erfolgt."),
        ("Allgemein", "Anmeldung weitergeleitet an Schichtleitung."),
        ("Allgemein", "Rückruf wurde zugesagt."),
        ("Allgemein", "Weitergeleitet an zuständige Stelle."),
        ("Allgemein", "Angelegenheit geklärt – kein Handlungsbedarf."),
    ]
    conn.executemany(
        "INSERT INTO textbausteine (gruppe, text) VALUES (?, ?)", defaults
    )
    conn.commit()


# ── CRUD call_logs ─────────────────────────────────────────────────────────────

def speichern(daten: dict) -> int:
    """Neu anlegen oder bestehenden Eintrag aktualisieren."""
    with _get_conn() as conn:
        if daten.get("id"):
            conn.execute("""
                UPDATE call_logs
                SET datum=?, uhrzeit=?, flug_richtung=?, flugnummer=?,
                    ziel_herkunft=?, passagier_name=?, hilfeart=?,
                    anrufer=?, telefon=?, richtung=?,
                    kategorie=?, betreff=?, notiz=?, erledigt=?
                WHERE id=?
            """, (
                daten.get("datum", ""),
                daten.get("uhrzeit", ""),
                daten.get("flug_richtung", ""),
                daten.get("flugnummer", ""),
                daten.get("ziel_herkunft", ""),
                daten.get("passagier_name", ""),
                daten.get("hilfeart", ""),
                daten.get("anrufer", ""),
                daten.get("telefon", ""),
                daten.get("richtung", "Eingehend"),
                daten.get("kategorie", ""),
                daten.get("betreff", ""),
                daten.get("notiz", ""),
                1 if daten.get("erledigt") else 0,
                daten["id"],
            ))
            conn.commit()
            return daten["id"]
        else:
            cur = conn.execute("""
                INSERT INTO call_logs
                    (datum, uhrzeit, flug_richtung, flugnummer, ziel_herkunft,
                     passagier_name, hilfeart, anrufer, telefon, richtung,
                     kategorie, betreff, notiz, erledigt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                daten.get("datum", ""),
                daten.get("uhrzeit", ""),
                daten.get("flug_richtung", ""),
                daten.get("flugnummer", ""),
                daten.get("ziel_herkunft", ""),
                daten.get("passagier_name", ""),
                daten.get("hilfeart", ""),
                daten.get("anrufer", ""),
                daten.get("telefon", ""),
                daten.get("richtung", "Eingehend"),
                daten.get("kategorie", ""),
                daten.get("betreff", ""),
                daten.get("notiz", ""),
                1 if daten.get("erledigt") else 0,
            ))
            conn.commit()
            return cur.lastrowid


def alle_laden(filter_text: str = "", kategorie: str = "", nur_offen: bool = False) -> list[dict]:
    sql = "SELECT * FROM call_logs WHERE 1=1"
    params: list = []
    if filter_text:
        sql += " AND (anrufer LIKE ? OR betreff LIKE ? OR notiz LIKE ? OR telefon LIKE ?)"
        t = f"%{filter_text}%"
        params += [t, t, t, t]
    if kategorie:
        sql += " AND kategorie=?"
        params.append(kategorie)
    if nur_offen:
        sql += " AND erledigt=0"
    sql += " ORDER BY datum DESC, uhrzeit DESC"
    with _get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def laden_by_id(record_id: int) -> dict | None:
    with _get_conn() as conn:
        r = conn.execute("SELECT * FROM call_logs WHERE id=?", (record_id,)).fetchone()
        return dict(r) if r else None


def loeschen(record_id: int):
    with _get_conn() as conn:
        conn.execute("DELETE FROM call_logs WHERE id=?", (record_id,))
        conn.commit()
    try:
        from database.turso_sync import push_delete
        push_delete(_DB_PATH, "call_logs", record_id)
    except Exception:
        pass


# ── Textbausteine ──────────────────────────────────────────────────────────────

def textbausteine_laden() -> dict[str, list[dict]]:
    """Gibt {gruppe: [{id, gruppe, text}, ...]} zurück."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM textbausteine ORDER BY gruppe, id"
        ).fetchall()
    result: dict[str, list[dict]] = {}
    for row in rows:
        g = row["gruppe"]
        result.setdefault(g, []).append(dict(row))
    return result


def textbaustein_speichern(gruppe: str, text: str) -> int:
    with _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO textbausteine (gruppe, text) VALUES (?,?)", (gruppe, text)
        )
        conn.commit()
        return cur.lastrowid


def textbaustein_loeschen(baustein_id: int):
    with _get_conn() as conn:
        conn.execute("DELETE FROM textbausteine WHERE id=?", (baustein_id,))
        conn.commit()
    try:
        from database.turso_sync import push_delete
        push_delete(_DB_PATH, "textbausteine", baustein_id)
    except Exception:
        pass
