"""
Konfigurationsdatei für Nesk3
SQLite Datenbankverbindung und App-Einstellungen
"""
import os
import sys

# ─── Basispfad ermitteln (Script- UND EXE-Modus, PC-unabhängig) ────────────
# Im EXE-Modus zeigt __file__ auf den temporären _MEIPASS-Ordner.
# Stattdessen wird die Windows-Umgebungsvariable OneDriveCommercial / OneDrive
# verwendet – sie zeigt immer auf den lokalen OneDrive-Ordner des angemeldeten
# Nutzers, egal auf welchem PC.
_ONEDRIVE_SUBPATH = os.path.join(
    "Dateien von Erste-Hilfe-Station-Flughafen - DRK Köln e.V_ - !Gemeinsam.26",
    "Nesk", "Nesk3"
)

def _find_base_dir() -> str:
    if getattr(sys, "frozen", False):
        # EXE-Modus: OneDrive-Umgebungsvariable auslesen
        for var in ("OneDriveCommercial", "OneDrive"):
            od = os.environ.get(var, "")
            if od:
                candidate = os.path.join(od, _ONEDRIVE_SUBPATH)
                if os.path.isdir(candidate):
                    return candidate
        # Fallback: Ordner neben der EXE-Datei
        return os.path.dirname(sys.executable)
    else:
        # Script-Modus: Verzeichnis dieser config.py
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR  = _find_base_dir()

# ─── SQLite Datenbankpfad ─────────────────────────────────────────────────────
# Die Datenbank liegt im Unterordner "database SQL" des Projektverzeichnisses.
# Im EXE-Modus zeigt BASE_DIR auf den OneDrive-Ordner des angemeldeten Nutzers.
_DB_DIR = os.path.join(BASE_DIR, "database SQL")
DB_PATH             = os.path.join(_DB_DIR, "nesk3.db")
ARCHIV_DB_PATH      = os.path.join(_DB_DIR, "archiv.db")
MITARBEITER_DB_PATH = os.path.join(_DB_DIR, "mitarbeiter.db")
os.makedirs(_DB_DIR, exist_ok=True)

# ─── Anwendungseinstellungen ──────────────────────────────────────────────────
APP_NAME    = "Nesk3 – DRK Flughafen Köln"
APP_VERSION = "3.4.1"
APP_LANG    = "de"

# ─── Backup-Einstellungen ─────────────────────────────────────────────────────
BACKUP_DIR      = "backup/exports"
BACKUP_MAX_KEEP = 30    # Maximale Anzahl gespeicherter Backups

# ─── JSON-Einstellungen ───────────────────────────────────────────────────────
JSON_DIR = os.path.join(BASE_DIR, "json")

# ─── Turso (SSOT) ────────────────────────────────────────────────────────────
TURSO_URL   = "https://nesk-koboltze.aws-eu-west-1.turso.io"
TURSO_TOKEN = (
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9"
    ".eyJhIjoicnciLCJnaWQiOiI5MmYxMzNiMS1jYmVkLTQ1NWEtOGU0MS00ZTUxYjYxMjQ0YTYi"
    "LCJpYXQiOjE3NzM4ODgxNjQsInJpZCI6ImY5YTc0NzA1LTE4ZjktNGE2Ny1iNzkyLTM4Yzg4"
    "MTY4N2E3NSJ9"
    ".JSGexxBNRkcbdlAVPGAr8-P0mIiiDuaMWg4elSKf853-xGI5CzcZBxH-ozRLbVjTeM5EhZ6h"
    "N0_OcOvqdVl0Cg"
)
TURSO_SYNC_INTERVAL = 30   # Sekunden zwischen automatischen Syncs

# ─── SAP Fiori Design-Farben ─────────────────────────────────────────────────
FIORI_BLUE        = "#0a6ed1"
FIORI_LIGHT_BLUE  = "#eef4fa"
FIORI_TEXT        = "#32363a"
FIORI_BORDER      = "#d9d9d9"
FIORI_SUCCESS     = "#107e3e"
FIORI_WARNING     = "#e9730c"
FIORI_ERROR       = "#bb0000"
FIORI_WHITE       = "#ffffff"
FIORI_SIDEBAR_BG  = "#354a5e"
