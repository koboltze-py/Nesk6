"""
Übergabe-Protokoll – Datenbankfunktionen
CRUD-Operationen für Übergabeprotokolle (Tagdienst / Nachtdienst)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_cursor


# ── Erstellen ──────────────────────────────────────────────────────────────────

def erstelle_protokoll(
    datum:            str,
    schicht_typ:      str,   # 'tagdienst' | 'nachtdienst'
    beginn_zeit:      str  = "",
    ende_zeit:        str  = "",
    patienten_anzahl: int  = 0,
    personal:         str  = "",
    ereignisse:       str  = "",
    massnahmen:       str  = "",
    uebergabe_notiz:  str  = "",
    ersteller:        str  = "",
    handys_anzahl:    int  = 0,
    handys_notiz:     str  = "",
) -> int:
    """
    Legt ein neues Übergabeprotokoll an.
    Gibt die neue ID zurück.
    """
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO uebergabe_protokolle
                (datum, schicht_typ, beginn_zeit, ende_zeit,
                 patienten_anzahl, personal, ereignisse, massnahmen,
                 uebergabe_notiz, ersteller, handys_anzahl, handys_notiz)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datum, schicht_typ, beginn_zeit, ende_zeit,
              patienten_anzahl, personal, ereignisse, massnahmen,
              uebergabe_notiz, ersteller, handys_anzahl, handys_notiz))
        return cur.lastrowid


# ── Aktualisieren ──────────────────────────────────────────────────────────────

def aktualisiere_protokoll(
    protokoll_id:     int,
    beginn_zeit:      str  = "",
    ende_zeit:        str  = "",
    patienten_anzahl: int  = 0,
    personal:         str  = "",
    ereignisse:       str  = "",
    massnahmen:       str  = "",
    uebergabe_notiz:  str  = "",
    ersteller:        str  = "",
    abzeichner:       str  = "",
    status:           str  = "offen",
    handys_anzahl:    int  = 0,
    handys_notiz:     str  = "",
) -> bool:
    """Aktualisiert ein vorhandenes Protokoll. Gibt True bei Erfolg zurück."""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE uebergabe_protokolle
            SET beginn_zeit      = ?,
                ende_zeit        = ?,
                patienten_anzahl = ?,
                personal         = ?,
                ereignisse       = ?,
                massnahmen       = ?,
                uebergabe_notiz  = ?,
                ersteller        = ?,
                abzeichner       = ?,
                status           = ?,
                handys_anzahl    = ?,
                handys_notiz     = ?
            WHERE id = ?
        """, (beginn_zeit, ende_zeit, patienten_anzahl, personal,
              ereignisse, massnahmen, uebergabe_notiz,
              ersteller, abzeichner, status,
              handys_anzahl, handys_notiz, protokoll_id))
        return cur.rowcount > 0


# ── Laden ──────────────────────────────────────────────────────────────────────

def lade_protokolle(
    schicht_typ: str | None = None,
    limit:       int        = 60,
    monat:       str | None = None,  # Format 'YYYY-MM'
) -> list[dict]:
    """
    Gibt eine Liste von Protokollen zurück, neueste zuerst.
    Archivierte Protokolle werden standardmäßig ausgeblendet.
    """
    with db_cursor() as cur:
        conditions = ["COALESCE(archiviert,0) = 0"]
        params = []
        if schicht_typ:
            conditions.append("schicht_typ = ?")
            params.append(schicht_typ)
        if monat:
            conditions.append("datum LIKE ?")
            params.append(f"{monat}-%")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        cur.execute(f"""
            SELECT * FROM uebergabe_protokolle
            {where}
            ORDER BY datum DESC, erstellt_am DESC
            LIMIT ?
        """, params)
        return cur.fetchall() or []


def lade_protokoll_by_id(protokoll_id: int) -> dict | None:
    """Gibt ein einzelnes Protokoll anhand der ID zurück."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM uebergabe_protokolle WHERE id = ?",
            (protokoll_id,)
        )
        return cur.fetchone()


# ── Löschen ───────────────────────────────────────────────────────────────────

def loesche_protokoll(protokoll_id: int) -> bool:
    """Löscht ein Protokoll dauerhaft. Gibt True bei Erfolg zurück."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM uebergabe_protokolle WHERE id = ?",
            (protokoll_id,)
        )
        return cur.rowcount > 0


# ── Abschließen ───────────────────────────────────────────────────────────────

def schliesse_protokoll_ab(protokoll_id: int, abzeichner: str) -> bool:
    """Setzt Status auf 'abgeschlossen' und trägt den Abzeichner ein."""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE uebergabe_protokolle
            SET status = 'abgeschlossen', abzeichner = ?
            WHERE id = ?
        """, (abzeichner, protokoll_id))
        return cur.rowcount > 0


# ── Statistik ─────────────────────────────────────────────────────────────────

def protokoll_statistik() -> dict:
    """Gibt eine Übersicht über alle gespeicherten Protokolle zurück."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*)                                        AS gesamt,
                SUM(CASE WHEN schicht_typ='tagdienst'   THEN 1 ELSE 0 END) AS tag_ges,
                SUM(CASE WHEN schicht_typ='nachtdienst' THEN 1 ELSE 0 END) AS nacht_ges,
                SUM(CASE WHEN status='offen'           THEN 1 ELSE 0 END) AS offen,
                SUM(CASE WHEN status='abgeschlossen'   THEN 1 ELSE 0 END) AS abgeschlossen,
                SUM(COALESCE(patienten_anzahl, 0))              AS patienten_gesamt
            FROM uebergabe_protokolle
        """)
        return cur.fetchone() or {}


# ── Fahrzeug-Notizen in Protokollen ──────────────────────────────────────────────

def speichere_fahrzeug_notizen(protokoll_id: int, notizen: dict) -> None:
    """
    Speichert Fahrzeug-Notizen für ein Protokoll.
    notizen: {fahrzeug_id: notiz_text}
    Leere Notizen werden nicht gespeichert.
    """
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM uebergabe_fahrzeug_notizen WHERE protokoll_id = ?",
            (protokoll_id,)
        )
        for fid, notiz in notizen.items():
            if notiz and notiz.strip():
                cur.execute("""
                    INSERT INTO uebergabe_fahrzeug_notizen
                        (protokoll_id, fahrzeug_id, notiz)
                    VALUES (?, ?, ?)
                """, (protokoll_id, fid, notiz.strip()))


def lade_fahrzeug_notizen(protokoll_id: int) -> dict:
    """
    Gibt Fahrzeug-Notizen für ein Protokoll zurück.
    Returns: {fahrzeug_id: notiz_text}
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT fahrzeug_id, notiz
            FROM uebergabe_fahrzeug_notizen
            WHERE protokoll_id = ?
        """, (protokoll_id,))
        rows = cur.fetchall() or []
        return {row["fahrzeug_id"]: row["notiz"] for row in rows}


# ── Handy-Einträge in Protokollen ────────────────────────────────────────────

def speichere_handy_eintraege(protokoll_id: int, eintraege: list) -> None:
    """
    Speichert Handy-Einträge für ein Protokoll.
    eintraege: list of (geraet_nr: str, notiz: str)
    """
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM uebergabe_handy_eintraege WHERE protokoll_id = ?",
            (protokoll_id,)
        )
        for geraet_nr, notiz in eintraege:
            if geraet_nr and geraet_nr.strip():
                cur.execute("""
                    INSERT INTO uebergabe_handy_eintraege
                        (protokoll_id, geraet_nr, notiz)
                    VALUES (?, ?, ?)
                """, (protokoll_id, geraet_nr.strip(), notiz.strip() if notiz else ""))


def lade_handy_eintraege(protokoll_id: int) -> list:
    """
    Gibt Handy-Einträge für ein Protokoll zurück.
    Returns: list of {geraet_nr: str, notiz: str}
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT geraet_nr, notiz
            FROM uebergabe_handy_eintraege
            WHERE protokoll_id = ?
            ORDER BY id
        """, (protokoll_id,))
        return cur.fetchall() or []


# ── Verspätete Mitarbeiter ────────────────────────────────────────────────────

def speichere_verspaetungen(protokoll_id: int, eintraege: list) -> None:
    """Speichert Verspätungseinträge (löscht alte, fügt neue ein)."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM uebergabe_verspaetungen WHERE protokoll_id = ?",
            (protokoll_id,)
        )
        for name, soll, ist in eintraege:
            if name:
                cur.execute(
                    "INSERT INTO uebergabe_verspaetungen "
                    "(protokoll_id, mitarbeiter, soll_zeit, ist_zeit) VALUES (?, ?, ?, ?)",
                    (protokoll_id, name, soll, ist)
                )


def lade_verspaetungen(protokoll_id: int) -> list:
    """Gibt Verspätungseinträge für ein Protokoll zurück."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT mitarbeiter, soll_zeit, ist_zeit "
            "FROM uebergabe_verspaetungen WHERE protokoll_id = ? ORDER BY id",
            (protokoll_id,)
        )
        return cur.fetchall() or []


# ── Bulk-Aktionen (Verwaltung) ────────────────────────────────────────────────────

def lade_alle_protokolle_verwaltung(schicht_typ: str | None = None) -> list:
    """Lädt alle Protokolle (inkl. archivierte) für die Verwaltungsansicht."""
    with db_cursor() as cur:
        if schicht_typ:
            cur.execute("""
                SELECT id, datum, schicht_typ, ersteller, status,
                       COALESCE(archiviert,0) AS archiviert
                FROM uebergabe_protokolle
                WHERE schicht_typ = ?
                ORDER BY datum DESC, erstellt_am DESC
            """, (schicht_typ,))
        else:
            cur.execute("""
                SELECT id, datum, schicht_typ, ersteller, status,
                       COALESCE(archiviert,0) AS archiviert
                FROM uebergabe_protokolle
                ORDER BY datum DESC, erstellt_am DESC
            """)
        return cur.fetchall() or []


def loesche_protokolle_bulk(ids: list) -> int:
    """Löscht mehrere Protokolle dauerhaft. Gibt Anzahl zurück."""
    if not ids:
        return 0
    with db_cursor(commit=True) as cur:
        placeholders = ','.join('?' * len(ids))
        cur.execute(
            f"DELETE FROM uebergabe_protokolle WHERE id IN ({placeholders})",
            list(ids)
        )
        return cur.rowcount


def archiviere_protokolle_bulk(ids: list) -> int:
    """Archiviert mehrere Protokolle (setzt archiviert=1). Gibt Anzahl zurück."""
    if not ids:
        return 0
    with db_cursor(commit=True) as cur:
        placeholders = ','.join('?' * len(ids))
        cur.execute(
            f"UPDATE uebergabe_protokolle SET archiviert = 1 WHERE id IN ({placeholders})",
            list(ids)
        )
        return cur.rowcount

