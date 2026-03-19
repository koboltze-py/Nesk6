"""
Fahrzeug-Funktionen – Datenbankoperationen
CRUD für Fahrzeuge, Status-Historie, Schäden und Termine
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_cursor
from config import DB_PATH as _NESK3_DB_PATH


# ══════════════════════════════════════════════════════════════════════════════
#  FAHRZEUGE – Stammdaten
# ══════════════════════════════════════════════════════════════════════════════

def erstelle_fahrzeug(
    kennzeichen:   str,
    typ:           str = "",
    marke:         str = "",
    modell:        str = "",
    baujahr:       int | None = None,
    fahrgestellnr: str = "",
    tuev_datum:    str = "",
    notizen:       str = "",
) -> int:
    """Legt ein neues Fahrzeug an. Gibt die neue ID zurück."""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO fahrzeuge
                (kennzeichen, typ, marke, modell, baujahr,
                 fahrgestellnr, tuev_datum, notizen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (kennzeichen, typ, marke, modell, baujahr,
              fahrgestellnr, tuev_datum, notizen))
        fid = cur.lastrowid
        # Initialen Status setzen
        cur.execute("""
            INSERT INTO fahrzeug_status (fahrzeug_id, status, von, grund)
            VALUES (?, 'fahrbereit', date('now','localtime'), 'Fahrzeug angelegt')
        """, (fid,))
        return fid


def aktualisiere_fahrzeug(
    fahrzeug_id:   int,
    kennzeichen:   str,
    typ:           str = "",
    marke:         str = "",
    modell:        str = "",
    baujahr:       int | None = None,
    fahrgestellnr: str = "",
    tuev_datum:    str = "",
    notizen:       str = "",
) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE fahrzeuge SET
                kennzeichen   = ?, typ     = ?, marke       = ?,
                modell        = ?, baujahr = ?, fahrgestellnr = ?,
                tuev_datum    = ?, notizen = ?
            WHERE id = ?
        """, (kennzeichen, typ, marke, modell, baujahr,
              fahrgestellnr, tuev_datum, notizen, fahrzeug_id))
        return cur.rowcount > 0


def loesche_fahrzeug(fahrzeug_id: int) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM fahrzeuge WHERE id = ?", (fahrzeug_id,))
        result = cur.rowcount > 0
    try:
        from database.turso_sync import push_delete
        push_delete(_NESK3_DB_PATH, "fahrzeuge", fahrzeug_id)
    except Exception:
        pass
    return result


def lade_alle_fahrzeuge(nur_aktive: bool = False) -> list[dict]:
    with db_cursor() as cur:
        if nur_aktive:
            cur.execute("""
                SELECT f.*,
                       (SELECT status FROM fahrzeug_status
                        WHERE fahrzeug_id = f.id
                        ORDER BY erstellt_am DESC LIMIT 1) AS aktueller_status
                FROM fahrzeuge f WHERE f.aktiv = 1
                ORDER BY f.kennzeichen
            """)
        else:
            cur.execute("""
                SELECT f.*,
                       (SELECT status FROM fahrzeug_status
                        WHERE fahrzeug_id = f.id
                        ORDER BY erstellt_am DESC LIMIT 1) AS aktueller_status
                FROM fahrzeuge f
                ORDER BY f.aktiv DESC, f.kennzeichen
            """)
        return cur.fetchall() or []


def lade_fahrzeug(fahrzeug_id: int) -> dict | None:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM fahrzeuge WHERE id = ?", (fahrzeug_id,))
        return cur.fetchone()


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS-HISTORIE
# ══════════════════════════════════════════════════════════════════════════════

def setze_fahrzeug_status(
    fahrzeug_id: int,
    status:      str,           # fahrbereit|defekt|werkstatt|ausser_dienst|sonstiges
    von:         str,           # YYYY-MM-DD
    grund:       str = "",
    bis:         str = "",      # leer = unbestimmt
) -> int:
    """Fügt einen neuen Status-Eintrag in die Historie ein."""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO fahrzeug_status (fahrzeug_id, status, von, bis, grund)
            VALUES (?, ?, ?, ?, ?)
        """, (fahrzeug_id, status, von, bis, grund))
        return cur.lastrowid


def lade_status_historie(fahrzeug_id: int) -> list[dict]:
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM fahrzeug_status
            WHERE fahrzeug_id = ?
            ORDER BY von DESC, erstellt_am DESC
        """, (fahrzeug_id,))
        return cur.fetchall() or []


def aktueller_status(fahrzeug_id: int) -> dict | None:
    """Gibt den neuesten Status-Eintrag zurück."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM fahrzeug_status
            WHERE fahrzeug_id = ?
            ORDER BY erstellt_am DESC LIMIT 1
        """, (fahrzeug_id,))
        return cur.fetchone()


def loesche_status_eintrag(eintrag_id: int) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM fahrzeug_status WHERE id = ?", (eintrag_id,))
        result = cur.rowcount > 0
    try:
        from database.turso_sync import push_delete
        push_delete(_NESK3_DB_PATH, "fahrzeug_status", eintrag_id)
    except Exception:
        pass
    return result


def aktualisiere_status_eintrag(
    eintrag_id: int,
    status: str,
    von: str,
    bis: str = "",
    grund: str = "",
) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE fahrzeug_status
            SET status = ?, von = ?, bis = ?, grund = ?
            WHERE id = ?
        """, (status, von, bis or None, grund, eintrag_id))
        return cur.rowcount > 0


# ══════════════════════════════════════════════════════════════════════════════
#  SCHÄDEN
# ══════════════════════════════════════════════════════════════════════════════

def erstelle_schaden(
    fahrzeug_id:  int,
    datum:        str,
    beschreibung: str,
    schwere:      str = "gering",
    kommentar:    str = "",
) -> int:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO fahrzeug_schaeden
                (fahrzeug_id, datum, beschreibung, schwere, kommentar)
            VALUES (?, ?, ?, ?, ?)
        """, (fahrzeug_id, datum, beschreibung, schwere, kommentar))
        return cur.lastrowid


def aktualisiere_schaden(
    schaden_id:   int,
    beschreibung: str,
    schwere:      str,
    kommentar:    str,
    behoben:      int = 0,
    behoben_am:   str = "",
) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE fahrzeug_schaeden SET
                beschreibung = ?, schwere = ?, kommentar = ?,
                behoben = ?, behoben_am = ?,
                geaendert_am = datetime('now','localtime')
            WHERE id = ?
        """, (beschreibung, schwere, kommentar, behoben, behoben_am, schaden_id))
        return cur.rowcount > 0


def lade_schaeden(fahrzeug_id: int) -> list[dict]:
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM fahrzeug_schaeden
            WHERE fahrzeug_id = ?
            ORDER BY datum DESC, erstellt_am DESC
        """, (fahrzeug_id,))
        return cur.fetchall() or []


def markiere_schaden_behoben(schaden_id: int, behoben_am: str) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE fahrzeug_schaeden
            SET behoben = 1, behoben_am = ?,
                geaendert_am = datetime('now','localtime')
            WHERE id = ?
        """, (behoben_am, schaden_id))
        return cur.rowcount > 0


def loesche_schaden(schaden_id: int) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM fahrzeug_schaeden WHERE id = ?", (schaden_id,))
        result = cur.rowcount > 0
    try:
        from database.turso_sync import push_delete
        push_delete(_NESK3_DB_PATH, "fahrzeug_schaeden", schaden_id)
    except Exception:
        pass
    return result


def markiere_schaden_gesendet(schaden_id: int) -> bool:
    """Markiert einen Schaden als per E-Mail gesendet."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE fahrzeug_schaeden SET gesendet = 1, geaendert_am = datetime('now','localtime') WHERE id = ?",
            (schaden_id,)
        )
        return cur.rowcount > 0


def lade_schaeden_letzte_tage(tage: int = 7) -> list[dict]:
    """
    Gibt alle Schäden der letzten N Tage über ALLE Fahrzeuge zurück.
    Enthält auch Fahrzeug-Kennzeichen.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT fs.id, fs.fahrzeug_id, f.kennzeichen, f.typ AS fahrzeug_typ,
                   fs.datum, fs.beschreibung, fs.schwere, fs.kommentar,
                   fs.behoben, fs.behoben_am,
                   COALESCE(fs.gesendet, 0) AS gesendet
            FROM fahrzeug_schaeden fs
            JOIN fahrzeuge f ON f.id = fs.fahrzeug_id
            WHERE fs.datum >= date('now','localtime', ?)
            ORDER BY fs.datum DESC, fs.erstellt_am DESC
        """, (f"-{tage} days",))
        return cur.fetchall() or []


# ══════════════════════════════════════════════════════════════════════════════
#  TERMINE
# ══════════════════════════════════════════════════════════════════════════════

def erstelle_termin(
    fahrzeug_id:  int,
    datum:        str,
    titel:        str,
    typ:          str = "sonstiges",
    uhrzeit:      str = "",
    beschreibung: str = "",
    kommentar:    str = "",
) -> int:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO fahrzeug_termine
                (fahrzeug_id, datum, uhrzeit, typ, titel, beschreibung, kommentar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (fahrzeug_id, datum, uhrzeit, typ, titel, beschreibung, kommentar))
        return cur.lastrowid


def aktualisiere_termin(
    termin_id:    int,
    datum:        str,
    titel:        str,
    typ:          str,
    uhrzeit:      str = "",
    beschreibung: str = "",
    kommentar:    str = "",
    erledigt:     int = 0,
) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE fahrzeug_termine SET
                datum = ?, uhrzeit = ?, typ = ?, titel = ?,
                beschreibung = ?, kommentar = ?, erledigt = ?,
                geaendert_am = datetime('now','localtime')
            WHERE id = ?
        """, (datum, uhrzeit, typ, titel, beschreibung, kommentar, erledigt, termin_id))
        return cur.rowcount > 0


def lade_termine(fahrzeug_id: int) -> list[dict]:
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM fahrzeug_termine
            WHERE fahrzeug_id = ?
            ORDER BY datum DESC, uhrzeit DESC
        """, (fahrzeug_id,))
        return cur.fetchall() or []


def markiere_termin_erledigt(termin_id: int) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE fahrzeug_termine
            SET erledigt = 1, geaendert_am = datetime('now','localtime')
            WHERE id = ?
        """, (termin_id,))
        return cur.rowcount > 0


def loesche_termin(termin_id: int) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM fahrzeug_termine WHERE id = ?", (termin_id,))
        result = cur.rowcount > 0
    try:
        from database.turso_sync import push_delete
        push_delete(_NESK3_DB_PATH, "fahrzeug_termine", termin_id)
    except Exception:
        pass
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORIE – kombiniert alle Einträge eines Fahrzeugs
# ══════════════════════════════════════════════════════════════════════════════

def lade_komplette_historie(fahrzeug_id: int) -> list[dict]:
    """
    Gibt alle Ereignisse (Status, Schäden, Termine) eines Fahrzeugs
    als einheitliche Liste zurück, neueste zuerst.
    """
    eintraege: list[dict] = []

    with db_cursor() as cur:
        # Status
        cur.execute("""
            SELECT 'status' AS art, von AS datum,
                   status AS titel,
                   grund AS beschreibung,
                   bis, '' AS kommentar,
                   erstellt_am
            FROM fahrzeug_status WHERE fahrzeug_id = ?
        """, (fahrzeug_id,))
        eintraege.extend(cur.fetchall() or [])

        # Schäden
        cur.execute("""
            SELECT 'schaden' AS art, datum,
                   beschreibung AS titel,
                   schwere AS beschreibung,
                   CASE behoben WHEN 1 THEN behoben_am ELSE '' END AS bis,
                   kommentar,
                   erstellt_am
            FROM fahrzeug_schaeden WHERE fahrzeug_id = ?
        """, (fahrzeug_id,))
        eintraege.extend(cur.fetchall() or [])

        # Termine
        cur.execute("""
            SELECT 'termin' AS art, datum,
                   titel,
                   typ AS beschreibung,
                   CASE erledigt WHEN 1 THEN datum ELSE '' END AS bis,
                   kommentar,
                   erstellt_am
            FROM fahrzeug_termine WHERE fahrzeug_id = ?
        """, (fahrzeug_id,))
        eintraege.extend(cur.fetchall() or [])

    # Sortierung nach Datum absteigend
    eintraege.sort(key=lambda x: (x.get("datum") or "", x.get("erstellt_am") or ""), reverse=True)
    return eintraege
