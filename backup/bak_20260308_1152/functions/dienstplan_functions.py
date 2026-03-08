"""
Dienstplan-Funktionen (CRUD)
Lese-, Schreib- und Löschoperationen für Dienstpläne/Schichten
"""
from typing import Optional
from datetime import date
from database.connection import db_cursor
from database.models import Dienstplan


def get_alle_schichten(von: Optional[date] = None, bis: Optional[date] = None) -> list[Dienstplan]:
    """Gibt alle Schichten zurück, optional gefiltert nach Datumsbereich."""
    # TODO: Implementierung folgt
    return []


def get_schichten_fuer_mitarbeiter(mitarbeiter_id: int,
                                    von: Optional[date] = None,
                                    bis: Optional[date] = None) -> list[Dienstplan]:
    """Gibt alle Schichten eines Mitarbeiters zurück."""
    # TODO: Implementierung folgt
    return []


def schicht_erstellen(s: Dienstplan) -> Dienstplan:
    """Erstellt eine neue Schicht."""
    # TODO: Implementierung folgt
    return s


def schicht_aktualisieren(s: Dienstplan) -> bool:
    """Aktualisiert eine bestehende Schicht."""
    # TODO: Implementierung folgt
    return False


def schicht_loeschen(schicht_id: int) -> bool:
    """Löscht eine Schicht anhand der ID."""
    # TODO: Implementierung folgt
    return False


def get_statistik() -> dict:
    """Gibt eine Übersicht der aktuellen Statistiken zurück."""
    # TODO: Implementierung folgt
    return {
        "aktive_mitarbeiter":      0,
        "gesamt_mitarbeiter":      0,
        "schichten_heute":         0,
        "schichten_diesen_monat":  0,
    }
