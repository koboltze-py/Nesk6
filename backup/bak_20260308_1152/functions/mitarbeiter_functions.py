"""
Mitarbeiter-Funktionen (CRUD + Excel-Import)
Lese-, Schreib- und Löschoperationen für Mitarbeiter,
sowie Import aller Namen aus Dienstplan-Excel-Dateien.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import ma_db_cursor
from database.models import Mitarbeiter


# ── Hilfsfunktion ──────────────────────────────────────────────────────────────

def _row_to_ma(row: dict) -> Mitarbeiter:
    """Wandelt eine DB-Zeile in ein Mitarbeiter-Objekt um."""
    ein = row.get("eintrittsdatum")
    if ein and isinstance(ein, str):
        try:
            ein = date.fromisoformat(ein)
        except ValueError:
            ein = None
    return Mitarbeiter(
        id=row.get("id"),
        vorname=row.get("vorname", ""),
        nachname=row.get("nachname", ""),
        personalnummer=row.get("personalnummer", "") or "",
        funktion=row.get("funktion", "stamm") or "stamm",
        position=row.get("position", "") or "",
        abteilung=row.get("abteilung", "") or "",
        email=row.get("email", "") or "",
        telefon=row.get("telefon", "") or "",
        eintrittsdatum=ein,
        status=row.get("status", "aktiv") or "aktiv",
    )


# ── CRUD ───────────────────────────────────────────────────────────────────────

def get_alle_mitarbeiter(nur_aktive: bool = False) -> list[Mitarbeiter]:
    """Gibt alle Mitarbeiter aus der Datenbank zurück."""
    with ma_db_cursor() as cur:
        if nur_aktive:
            cur.execute(
                "SELECT * FROM mitarbeiter WHERE status='aktiv' "
                "ORDER BY funktion, nachname, vorname"
            )
        else:
            cur.execute(
                "SELECT * FROM mitarbeiter ORDER BY funktion, nachname, vorname"
            )
        return [_row_to_ma(r) for r in cur.fetchall()]


def get_mitarbeiter_by_id(mitarbeiter_id: int) -> Optional[Mitarbeiter]:
    """Gibt einen Mitarbeiter anhand der ID zurück."""
    with ma_db_cursor() as cur:
        cur.execute("SELECT * FROM mitarbeiter WHERE id=?", (mitarbeiter_id,))
        row = cur.fetchone()
        return _row_to_ma(row) if row else None


def mitarbeiter_erstellen(m: Mitarbeiter) -> Mitarbeiter:
    """Erstellt einen neuen Mitarbeiter in der Datenbank."""
    with ma_db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO mitarbeiter
               (vorname, nachname, personalnummer, funktion, position,
                abteilung, email, telefon, eintrittsdatum, status,
                erstellt_am, geaendert_am)
               VALUES (?,?,?,?,?,?,?,?,?,?,
                       datetime('now','localtime'), datetime('now','localtime'))""",
            (
                m.vorname.strip(),
                m.nachname.strip(),
                m.personalnummer.strip() or None,
                m.funktion or "stamm",
                m.position,
                m.abteilung,
                m.email,
                m.telefon,
                str(m.eintrittsdatum) if m.eintrittsdatum else None,
                m.status or "aktiv",
            ),
        )
        m.id = cur.lastrowid
    return m


def mitarbeiter_aktualisieren(m: Mitarbeiter) -> bool:
    """Aktualisiert einen bestehenden Mitarbeiter."""
    with ma_db_cursor(commit=True) as cur:
        cur.execute(
            """UPDATE mitarbeiter SET
               vorname=?, nachname=?, personalnummer=?, funktion=?,
               position=?, abteilung=?, email=?, telefon=?,
               eintrittsdatum=?, status=?,
               geaendert_am=datetime('now','localtime')
               WHERE id=?""",
            (
                m.vorname.strip(),
                m.nachname.strip(),
                m.personalnummer.strip() or None,
                m.funktion or "stamm",
                m.position,
                m.abteilung,
                m.email,
                m.telefon,
                str(m.eintrittsdatum) if m.eintrittsdatum else None,
                m.status or "aktiv",
                m.id,
            ),
        )
        return True


def mitarbeiter_loeschen(mitarbeiter_id: int) -> bool:
    """Löscht einen Mitarbeiter anhand der ID."""
    with ma_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM mitarbeiter WHERE id=?", (mitarbeiter_id,))
        return True


def mitarbeiter_suchen(suchbegriff: str) -> list[Mitarbeiter]:
    """Sucht Mitarbeiter nach Name, Personalnummer oder Position (case-insensitive)."""
    q = f"%{suchbegriff.lower()}%"
    with ma_db_cursor() as cur:
        cur.execute(
            """SELECT * FROM mitarbeiter
               WHERE lower(vorname) LIKE ?
                  OR lower(nachname) LIKE ?
                  OR lower(personalnummer) LIKE ?
                  OR lower(position) LIKE ?
                  OR lower(funktion) LIKE ?
               ORDER BY funktion, nachname, vorname""",
            (q, q, q, q, q),
        )
        return [_row_to_ma(r) for r in cur.fetchall()]


def get_abteilungen() -> list[str]:
    """Gibt alle Abteilungsnamen zurück."""
    with ma_db_cursor() as cur:
        cur.execute("SELECT name FROM abteilungen ORDER BY name")
        rows = cur.fetchall()
        return [r["name"] for r in rows] if rows else ["Erste-Hilfe-Station"]


def get_positionen() -> list[str]:
    """Gibt alle Positionsnamen zurück."""
    with ma_db_cursor() as cur:
        cur.execute("SELECT name FROM positionen ORDER BY name")
        rows = cur.fetchall()
        return [r["name"] for r in rows] if rows else ["Rettungssanitäter"]

def lade_mitarbeiter_namen(nur_aktive: bool = True) -> list[str]:
    """
    Gibt eine sortierte Liste aller Mitarbeiter-Namen als
    'Nachname, Vorname' zurück (für ComboBoxen in Dokument-Dialogen).
    """
    with ma_db_cursor() as cur:
        sql = "SELECT vorname, nachname FROM mitarbeiter"
        if nur_aktive:
            sql += " WHERE status='aktiv'"
        sql += " ORDER BY nachname, vorname"
        cur.execute(sql)
        return [f"{r['nachname']}, {r['vorname']}" for r in cur.fetchall()]

# ── Excel-Import ───────────────────────────────────────────────────────────────

def importiere_aus_dienstplaenen(
    ordner: str | None = None,
    fortschritt_callback=None,
) -> dict:
    """
    Scannt alle .xlsx-Dateien im Dienstplan-Ordner (inkl. Unterordner),
    extrahiert alle vorkommenden Namen (Stamm + Dispo) und importiert
    diese ohne Duplikate in die mitarbeiter-Tabelle.

    Rückgabe:
        {
          'neu': int,          # Neu angelegte Datensätze
          'übersprungen': int, # Bereits vorhandene (Duplikate)
          'fehler': int,       # Dateien die nicht gelesen werden konnten
          'gesamt': int,       # Anzahl gescannte Excel-Dateien
        }
    """
    from config import BASE_DIR
    from functions.dienstplan_parser import DienstplanParser

    if ordner is None:
        ordner = str(Path(BASE_DIR).parent.parent / "04_Tagesdienstpläne")

    xlsx_files = [
        f for f in Path(ordner).rglob("*.xlsx") if not f.name.startswith("~$")
    ]

    # Alle Personen sammeln: (lower_key) -> (vorname, nachname, funktion)
    # Dispo überschreibt Stamm wenn dieselbe Person in beiden vorkommt
    personen: dict[str, tuple[str, str, str]] = {}

    fehler = 0
    for idx, xf in enumerate(xlsx_files):
        if fortschritt_callback:
            fortschritt_callback(idx + 1, len(xlsx_files), str(xf.name))
        try:
            result = DienstplanParser(str(xf), alle_anzeigen=True).parse()
            if not result.get("success"):
                fehler += 1
                continue

            for p in result.get("betreuer", []):
                vn = p.get("vorname", "").strip()
                nn = p.get("nachname", "").strip()
                if vn and nn and len(vn) > 1 and len(nn) > 1:
                    key = f"{vn.lower()} {nn.lower()}"
                    if key not in personen:
                        personen[key] = (vn, nn, "stamm")

            for p in result.get("dispo", []):
                vn = p.get("vorname", "").strip()
                nn = p.get("nachname", "").strip()
                if vn and nn and len(vn) > 1 and len(nn) > 1:
                    key = f"{vn.lower()} {nn.lower()}"
                    personen[key] = (vn, nn, "dispo")  # Dispo hat Vorrang

            for p in result.get("kranke", []):
                vn = p.get("vorname", "").strip()
                nn = p.get("nachname", "").strip()
                ist_dispo = p.get("ist_dispo", False) or p.get("krank_ist_dispo", False)
                if vn and nn and len(vn) > 1 and len(nn) > 1:
                    key = f"{vn.lower()} {nn.lower()}"
                    funktion = "dispo" if ist_dispo else "stamm"
                    if key not in personen or funktion == "dispo":
                        personen[key] = (vn, nn, funktion)
        except Exception:
            fehler += 1

    # In DB importieren (ohne Duplikate)
    neu = 0
    uebersprungen = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with ma_db_cursor(commit=True) as cur:
        # Bereits vorhandene Namen (lower) laden
        cur.execute("SELECT lower(vorname), lower(nachname) FROM mitarbeiter")
        vorhandene = {
            f"{r.get('lower(vorname)','')} {r.get('lower(nachname)','')}".strip()
            for r in cur.fetchall()
        }

        for key, (vn, nn, funktion) in personen.items():
            if key in vorhandene:
                uebersprungen += 1
                continue
            # Ungültige / Dummy-Einträge filtern
            if "unnamed" in key or key.strip() in ("", " "):
                uebersprungen += 1
                continue
            if len(vn) < 2 or len(nn) < 2:
                uebersprungen += 1
                continue
            cur.execute(
                """INSERT INTO mitarbeiter
                   (vorname, nachname, funktion, status, erstellt_am, geaendert_am)
                   VALUES (?,?,?,?,?,?)""",
                (vn, nn, funktion, "aktiv", now_str, now_str),
            )
            neu += 1

    return {
        "neu": neu,
        "übersprungen": uebersprungen,
        "fehler": fehler,
        "gesamt": len(xlsx_files),
    }
