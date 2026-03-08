"""
Archiv-Funktionen – separates Archiv-DB-Management
Protokolle können in eine eigene archiv.db exportiert und
von dort wieder in die Haupt-Datenbank (nesk3.db) importiert werden.
"""
from __future__ import annotations
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ARCHIV_DB_PATH
from database.connection import db_cursor


# ── Archiv-DB Schema (ohne FK-Constraints, damit archivierte Dtaen unabhängig) ──
_ARCHIV_SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS uebergabe_protokolle (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    orig_id             INTEGER,
    datum               TEXT NOT NULL,
    schicht_typ         TEXT NOT NULL,
    beginn_zeit         TEXT DEFAULT '',
    ende_zeit           TEXT DEFAULT '',
    patienten_anzahl    INTEGER DEFAULT 0,
    personal            TEXT DEFAULT '',
    ereignisse          TEXT DEFAULT '',
    massnahmen          TEXT DEFAULT '',
    uebergabe_notiz     TEXT DEFAULT '',
    ersteller           TEXT DEFAULT '',
    abzeichner          TEXT DEFAULT '',
    status              TEXT DEFAULT 'offen',
    handys_anzahl       INTEGER DEFAULT 0,
    handys_notiz        TEXT DEFAULT '',
    erstellt_am         TEXT DEFAULT '',
    geaendert_am        TEXT DEFAULT '',
    archiviert_am       TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS uebergabe_fahrzeug_notizen (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    protokoll_id    INTEGER NOT NULL,
    fahrzeug_id     INTEGER NOT NULL,
    fahrzeug_kz     TEXT DEFAULT '',
    notiz           TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS uebergabe_handy_eintraege (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    protokoll_id    INTEGER NOT NULL,
    geraet_nr       TEXT NOT NULL,
    notiz           TEXT DEFAULT ''
);
"""


def _get_archiv_conn(archiv_path: str | None = None) -> sqlite3.Connection:
    """Öffnet eine Verbindung zur Archiv-Datenbank."""
    path = archiv_path or ARCHIV_DB_PATH
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = lambda c, r: dict(zip([x[0] for x in c.description], r))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_archiv_db(archiv_path: str | None = None) -> None:
    """Erstellt die Archiv-DB-Tabellen falls nicht vorhanden."""
    conn = _get_archiv_conn(archiv_path)
    try:
        conn.executescript(_ARCHIV_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def exportiere_in_archiv(
    protokoll_ids: list[int],
    archiv_path: str | None = None,
) -> int:
    """
    Kopiert Protokolle aus der Haupt-DB in die Archiv-DB und löscht
    sie anschließend aus der Haupt-DB.

    Gibt die Anzahl erfolgreich exportierter Protokolle zurück.
    """
    if not protokoll_ids:
        return 0

    init_archiv_db(archiv_path)
    arch_conn = _get_archiv_conn(archiv_path)
    count = 0

    try:
        arch_cur = arch_conn.cursor()
        with db_cursor() as main_cur:
            placeholders = ",".join("?" * len(protokoll_ids))

            # Protokolle laden
            main_cur.execute(
                f"""
                SELECT id, datum, schicht_typ, beginn_zeit, ende_zeit,
                       patienten_anzahl, personal, ereignisse, massnahmen,
                       uebergabe_notiz, ersteller, abzeichner, status,
                       COALESCE(handys_anzahl,0) AS handys_anzahl,
                       COALESCE(handys_notiz,'') AS handys_notiz,
                       erstellt_am, geaendert_am
                FROM uebergabe_protokolle
                WHERE id IN ({placeholders})
                """,
                list(protokoll_ids),
            )
            protokolle = main_cur.fetchall() or []

            for p in protokolle:
                orig_id = p["id"]

                # Fahrzeug-Notizen laden
                main_cur.execute(
                    """
                    SELECT ufn.fahrzeug_id, ufn.notiz,
                           COALESCE(f.kennzeichen,'') AS fahrzeug_kz
                    FROM uebergabe_fahrzeug_notizen ufn
                    LEFT JOIN fahrzeuge f ON f.id = ufn.fahrzeug_id
                    WHERE ufn.protokoll_id = ?
                    """,
                    (orig_id,),
                )
                fz_notizen = main_cur.fetchall() or []

                # Handy-Einträge laden
                main_cur.execute(
                    "SELECT geraet_nr, notiz FROM uebergabe_handy_eintraege WHERE protokoll_id = ?",
                    (orig_id,),
                )
                handys = main_cur.fetchall() or []

                # In Archiv schreiben
                arch_cur.execute(
                    """
                    INSERT INTO uebergabe_protokolle
                        (orig_id, datum, schicht_typ, beginn_zeit, ende_zeit,
                         patienten_anzahl, personal, ereignisse, massnahmen,
                         uebergabe_notiz, ersteller, abzeichner, status,
                         handys_anzahl, handys_notiz, erstellt_am, geaendert_am)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        orig_id,
                        p["datum"], p["schicht_typ"], p["beginn_zeit"], p["ende_zeit"],
                        p["patienten_anzahl"], p["personal"], p["ereignisse"],
                        p["massnahmen"], p["uebergabe_notiz"], p["ersteller"],
                        p["abzeichner"], p["status"],
                        p["handys_anzahl"], p["handys_notiz"],
                        p["erstellt_am"], p["geaendert_am"],
                    ),
                )
                arch_id = arch_cur.lastrowid

                for fn in fz_notizen:
                    arch_cur.execute(
                        "INSERT INTO uebergabe_fahrzeug_notizen (protokoll_id, fahrzeug_id, fahrzeug_kz, notiz) VALUES (?,?,?,?)",
                        (arch_id, fn["fahrzeug_id"], fn["fahrzeug_kz"], fn["notiz"]),
                    )
                for h in handys:
                    arch_cur.execute(
                        "INSERT INTO uebergabe_handy_eintraege (protokoll_id, geraet_nr, notiz) VALUES (?,?,?)",
                        (arch_id, h["geraet_nr"], h["notiz"]),
                    )
                count += 1

        # Commit Archiv
        arch_conn.commit()

        # Aus Haupt-DB löschen (eigene Transaktion)
        with db_cursor(commit=True) as del_cur:
            del_cur.execute(
                f"DELETE FROM uebergabe_protokolle WHERE id IN ({placeholders})",
                list(protokoll_ids),
            )

    finally:
        arch_conn.close()

    return count


def lade_archiv_protokolle(
    archiv_path: str | None = None,
    schicht_typ: str | None = None,
) -> list[dict]:
    """
    Gibt alle Protokolle aus der Archiv-DB zurück.
    schicht_typ: 'tagdienst' | 'nachtdienst' | None (= alle)
    """
    if not os.path.exists(archiv_path or ARCHIV_DB_PATH):
        return []

    init_archiv_db(archiv_path)
    conn = _get_archiv_conn(archiv_path)
    try:
        cur = conn.cursor()
        if schicht_typ:
            cur.execute(
                """
                SELECT id, orig_id, datum, schicht_typ, ersteller,
                       abzeichner, status, archiviert_am
                FROM uebergabe_protokolle
                WHERE schicht_typ = ?
                ORDER BY datum DESC, id DESC
                """,
                (schicht_typ,),
            )
        else:
            cur.execute(
                """
                SELECT id, orig_id, datum, schicht_typ, ersteller,
                       abzeichner, status, archiviert_am
                FROM uebergabe_protokolle
                ORDER BY datum DESC, id DESC
                """
            )
        return cur.fetchall() or []
    finally:
        conn.close()


def lade_archiv_protokoll_detail(
    archiv_id: int,
    archiv_path: str | None = None,
) -> dict:
    """
    Gibt ein vollständiges Protokoll mit Untereinträgen aus dem Archiv zurück.
    Returns: { "protokoll": {...}, "fahrzeuge": [...], "handys": [...] }
    """
    conn = _get_archiv_conn(archiv_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM uebergabe_protokolle WHERE id = ?", (archiv_id,)
        )
        proto = cur.fetchone() or {}

        cur.execute(
            "SELECT fahrzeug_id, fahrzeug_kz, notiz FROM uebergabe_fahrzeug_notizen WHERE protokoll_id = ?",
            (archiv_id,),
        )
        fz = cur.fetchall() or []

        cur.execute(
            "SELECT geraet_nr, notiz FROM uebergabe_handy_eintraege WHERE protokoll_id = ? ORDER BY id",
            (archiv_id,),
        )
        handys = cur.fetchall() or []

        return {"protokoll": proto, "fahrzeuge": fz, "handys": handys}
    finally:
        conn.close()


def importiere_aus_archiv(
    archiv_ids: list[int],
    archiv_path: str | None = None,
) -> int:
    """
    Kopiert Protokolle aus dem Archiv zurück in die Haupt-DB und löscht
    sie danach aus dem Archiv.

    Gibt die Anzahl erfolgreich importierter Protokolle zurück.
    """
    if not archiv_ids:
        return 0

    arch_conn = _get_archiv_conn(archiv_path)
    count = 0

    try:
        arch_cur = arch_conn.cursor()
        placeholders = ",".join("?" * len(archiv_ids))
        arch_cur.execute(
            f"SELECT * FROM uebergabe_protokolle WHERE id IN ({placeholders})",
            list(archiv_ids),
        )
        protokolle = arch_cur.fetchall() or []

        for p in protokolle:
            arch_id = p["id"]

            arch_cur.execute(
                "SELECT fahrzeug_id, notiz FROM uebergabe_fahrzeug_notizen WHERE protokoll_id = ?",
                (arch_id,),
            )
            fz_notizen = arch_cur.fetchall() or []

            arch_cur.execute(
                "SELECT geraet_nr, notiz FROM uebergabe_handy_eintraege WHERE protokoll_id = ? ORDER BY id",
                (arch_id,),
            )
            handys = arch_cur.fetchall() or []

            with db_cursor(commit=True) as main_cur:
                main_cur.execute(
                    """
                    INSERT INTO uebergabe_protokolle
                        (datum, schicht_typ, beginn_zeit, ende_zeit,
                         patienten_anzahl, personal, ereignisse, massnahmen,
                         uebergabe_notiz, ersteller, abzeichner, status,
                         handys_anzahl, handys_notiz, erstellt_am, archiviert)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                    """,
                    (
                        p["datum"], p["schicht_typ"], p["beginn_zeit"], p["ende_zeit"],
                        p["patienten_anzahl"], p["personal"], p["ereignisse"],
                        p["massnahmen"], p["uebergabe_notiz"], p["ersteller"],
                        p["abzeichner"], p["status"],
                        p.get("handys_anzahl", 0), p.get("handys_notiz", ""),
                        p.get("erstellt_am", ""),
                    ),
                )
                new_id = main_cur.lastrowid

                for fn in fz_notizen:
                    if fn.get("notiz"):
                        main_cur.execute(
                            """
                            INSERT OR IGNORE INTO uebergabe_fahrzeug_notizen
                                (protokoll_id, fahrzeug_id, notiz)
                            VALUES (?, ?, ?)
                            """,
                            (new_id, fn["fahrzeug_id"], fn["notiz"]),
                        )
                for h in handys:
                    main_cur.execute(
                        "INSERT INTO uebergabe_handy_eintraege (protokoll_id, geraet_nr, notiz) VALUES (?,?,?)",
                        (new_id, h["geraet_nr"], h["notiz"]),
                    )

            count += 1

        # Aus Archiv löschen
        arch_cur.execute(
            f"DELETE FROM uebergabe_protokolle WHERE id IN ({placeholders})",
            list(archiv_ids),
        )
        # Zugehörige Untereinträge löschen (kein ON DELETE CASCADE in archiv)
        arch_cur.execute(
            f"DELETE FROM uebergabe_fahrzeug_notizen WHERE protokoll_id IN ({placeholders})",
            list(archiv_ids),
        )
        arch_cur.execute(
            f"DELETE FROM uebergabe_handy_eintraege WHERE protokoll_id IN ({placeholders})",
            list(archiv_ids),
        )
        arch_conn.commit()

    finally:
        arch_conn.close()

    return count
