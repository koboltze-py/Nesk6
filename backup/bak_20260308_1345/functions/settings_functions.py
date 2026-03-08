"""
Einstellungs-Funktionen
Liest und schreibt Schlüssel-Wert-Paare aus der settings-Tabelle (SQLite).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_cursor

# ─── Portables Pfad-System ────────────────────────────────────────────────────
# Pfade, die im gemeinsamen OneDrive-Ordner liegen, werden mit {SHARED}
# gespeichert, damit sie auf jedem PC (unabhängig vom Windows-Benutzernamen)
# automatisch korrekt aufgelöst werden.
_SHARED_PLACEHOLDER = "{SHARED}"

def _shared_root() -> str:
    """Gibt den gemeinsamen Ordner zurück (2 Ebenen über BASE_DIR)."""
    from pathlib import Path
    from config import BASE_DIR
    return str(Path(BASE_DIR).parent.parent)

def _to_stored(path: str) -> str:
    """Ersetzt den OneDrive-Shared-Pfad durch {SHARED} (portabel speichern)."""
    if not path:
        return path
    shared = _shared_root()
    if path.startswith(shared):
        return _SHARED_PLACEHOLDER + path[len(shared):]
    return path

def _from_stored(path: str) -> str:
    """Löst {SHARED} zum aktuellen lokalen OneDrive-Pfad auf."""
    if not path:
        return path
    if path.startswith(_SHARED_PLACEHOLDER):
        return _shared_root() + path[len(_SHARED_PLACEHOLDER):]
    return path


def _get_defaults() -> dict[str, str]:
    """Berechnet Standard-Pfade dynamisch aus BASE_DIR (PC-unabhängig)."""
    from pathlib import Path
    from config import BASE_DIR
    shared = Path(BASE_DIR).parent.parent  # ...!Gemeinsam.26
    return {
        'dienstplan_ordner': str(shared / "04_Tagesdienstpläne"),
        'sonderaufgaben_ordner': str(shared / "04_Tagesdienstpläne"),
        'aocc_datei': str(
            Path(BASE_DIR) / "Daten" / "AOCC" / "AOCC Lagebericht.xlsm"
        ),
        'code19_datei': str(shared / "00_CODE 19" / "Code 19.xlsx"),
    }


def get_setting(key: str, default: str = '') -> str:
    """
    Gibt den gespeicherten Wert für *key* zurück.
    Fällt auf _get_defaults() oder *default* zurück, wenn der Schlüssel nicht existiert.
    Löst portable {SHARED}-Platzhalter auf.
    """
    try:
        with db_cursor() as cur:
            cur.execute("SELECT wert FROM settings WHERE schluessel = ?", (key,))
            row = cur.fetchone()
            if row:
                return _from_stored(row['wert'])
    except Exception:
        pass
    return _get_defaults().get(key, default)


def set_setting(key: str, value: str) -> bool:
    """
    Speichert *value* unter *key* (portabel: {SHARED}-Platzhalter).
    Gibt True bei Erfolg zurück.
    """
    try:
        stored = _to_stored(value)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT OR REPLACE INTO settings (schluessel, wert) VALUES (?, ?)",
                (key, stored)
            )
        return True
    except Exception:
        return False


def get_alle_settings() -> dict[str, str]:
    """Gibt alle gespeicherten Einstellungen als dict zurück (Platzhalter aufgelöst)."""
    try:
        with db_cursor() as cur:
            cur.execute("SELECT schluessel, wert FROM settings")
            return {row['schluessel']: _from_stored(row['wert']) for row in cur.fetchall()}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Ausschluss-Liste für Word-Export
# ---------------------------------------------------------------------------
import json as _json


def get_ausgeschlossene_namen() -> list[str]:
    """Gibt die persistierte Liste der ausgeschlossenen Vollnamen (lowercase) zurück."""
    raw = get_setting('export_ausgeschlossen', '[]')
    try:
        return _json.loads(raw)
    except Exception:
        return []


def set_ausgeschlossene_namen(namen: list[str]) -> bool:
    """Setzt die Ausschlussliste komplett neu."""
    try:
        bereinigt = list({n.lower().strip() for n in namen if n.strip()})
        return set_setting('export_ausgeschlossen', _json.dumps(bereinigt))
    except Exception:
        return False


def toggle_ausgeschlossener_name(vollname: str) -> bool:
    """
    Togglet einen Vollnamen in der Ausschlussliste.
    Rückgabe: True = jetzt ausgeschlossen, False = jetzt eingeschlossen.
    """
    key   = vollname.lower().strip()
    namen = get_ausgeschlossene_namen()
    if key in namen:
        namen.remove(key)
        set_ausgeschlossene_namen(namen)
        return False
    else:
        namen.append(key)
        set_ausgeschlossene_namen(namen)
        return True


def ist_ausgeschlossen(vollname: str) -> bool:
    """Prüft ob ein Vollname in der Ausschlussliste steht."""
    return vollname.lower().strip() in get_ausgeschlossene_namen()
