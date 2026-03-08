"""
E-Mobby-Fahrer Verwaltung
Liest die Liste aus der TXT-Datei und spiegelt sie in der DB-Settings.
"""
import json
from pathlib import Path

from config import BASE_DIR

_TXT_PATH = Path(BASE_DIR) / "Daten" / "E-Mobby" / "mobby.txt"
_SETTINGS_KEY = "emobby_fahrer"


def _names_from_txt() -> list[str]:
    """Liest Namen aus der TXT-Datei (Kommentarzeilen mit # werden übersprungen)."""
    if not _TXT_PATH.exists():
        return []
    names = []
    for line in _TXT_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def get_emobby_fahrer() -> list[str]:
    """
    Gibt die kombinierte Liste der E-Mobby-Fahrer zurück.
    Reihenfolge: TXT-Datei + eventuelle Ergänzungen in der DB.
    Beim ersten Aufruf werden die TXT-Namen automatisch in die DB gespeichert.
    """
    from functions.settings_functions import get_setting, set_setting

    # Aus TXT laden
    txt_names = _names_from_txt()

    # Aus DB laden (JSON)
    db_raw = get_setting(_SETTINGS_KEY, "")
    try:
        db_names: list[str] = json.loads(db_raw) if db_raw else []
    except Exception:
        db_names = []

    # TXT-Namen in DB synchronisieren (nur neue hinzufügen)
    changed = False
    for n in txt_names:
        if n not in db_names:
            db_names.append(n)
            changed = True
    if changed:
        set_setting(_SETTINGS_KEY, json.dumps(db_names, ensure_ascii=False))

    return db_names


def is_emobby_fahrer(name: str) -> bool:
    """
    Prüft ob 'name' (i.d.R. Nachname aus dem Dienstplan) in der E-Mobby-Liste ist.
    Vergleich: case-insensitiv, der Eintrag muss 'name' enthalten oder umgekehrt.
    """
    name_lower = name.strip().lower()
    for entry in get_emobby_fahrer():
        entry_lower = entry.strip().lower()
        if name_lower in entry_lower or entry_lower.startswith(name_lower):
            return True
    return False


def add_emobby_fahrer(name: str) -> bool:
    """Fügt einen Fahrer zur DB-Liste hinzu (falls noch nicht vorhanden)."""
    from functions.settings_functions import get_setting, set_setting
    import json

    db_raw = get_setting(_SETTINGS_KEY, "")
    try:
        db_names: list[str] = json.loads(db_raw) if db_raw else []
    except Exception:
        db_names = []

    if name.strip() and name.strip() not in db_names:
        db_names.append(name.strip())
        set_setting(_SETTINGS_KEY, json.dumps(db_names, ensure_ascii=False))
        return True
    return False
