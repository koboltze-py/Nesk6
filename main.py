"""
Nesk3 – DRK Flughafen Köln
Mitarbeiter- und Dienstplanverwaltung
Einstiegspunkt der Anwendung
"""
import sys
import os
import traceback

# Projektverzeichnis in den Python-Pfad aufnehmen
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Alle unbehandelten Exceptions im Terminal sichtbar machen
def _excepthook(exc_type, exc_value, exc_tb):
    print("\n=== UNBEHANDELTER FEHLER ===", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    print("============================\n", file=sys.stderr)

sys.excepthook = _excepthook

import sqlite3
import shutil
import glob
from datetime import datetime
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor
from gui.main_window import MainWindow


def _db_startup_backup():
    """Erstellt beim Programmstart ein SQLite-Backup aller Datenbanken im
    'database SQL'-Verzeichnis. Behält die letzten 7 Backups je Datenbank."""
    try:
        from config import DB_PATH
        db_dir = os.path.dirname(DB_PATH)
        backup_dir = os.path.join(db_dir, "Backup Data", "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        datum = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Alle .db-Dateien direkt im database SQL-Ordner sichern (keine Unterordner)
        for db_path in glob.glob(os.path.join(db_dir, "*.db")):
            name = os.path.splitext(os.path.basename(db_path))[0]
            backup_path = os.path.join(backup_dir, f"{name}_{datum}.db")
            # SQLite-native Online-Backup (atomar, keine Lock-Probleme)
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(backup_path)
            src.backup(dst)
            dst.close()
            src.close()
            # Nur die letzten 7 Backups behalten
            alle = sorted(glob.glob(os.path.join(backup_dir, f"{name}_*.db")))
            for alt in alle[:-7]:
                try:
                    os.remove(alt)
                except Exception:
                    pass
            print(f"[OK] DB-Backup erstellt: {os.path.basename(backup_path)}")
    except Exception as e:
        print(f"[WARNUNG] DB-Backup fehlgeschlagen: {e}")


def main():
    # High-DPI Unterstützung für Qt6 (PySide6)
    # QT_AUTO_SCREEN_SCALE_FACTOR ist nur Qt5 – in Qt6 ist High-DPI standardmäßig aktiv.
    # PassThrough gibt den echten Skalierungsfaktor (z.B. 1.25 bei 125%) direkt weiter
    # statt ihn auf ganze Zahlen zu runden → schärfere Darstellung auf allen Displays.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Nesk3")
    app.setOrganizationName("DRK Flughafen Köln")
    app.setStyle("Fusion")

    # -----------------------------------------------------------------------
    # FONT – plattformunabhängig, identisch auf allen PCs / EXE-Installationen
    # Schrift-Priorität: Segoe UI (Windows) → Arial → Helvetica Neue → OS-default
    # -----------------------------------------------------------------------
    app_font = QFont()
    app_font.setFamilies(["Segoe UI", "Arial", "Helvetica Neue"])
    app_font.setPointSize(10)
    app_font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(app_font)

    # -----------------------------------------------------------------------
    # PALETTE – Textfarbe explizit SCHWARZ; kein Einfluss von Dark Mode /
    # Windows-Theme / High-Contrast-Modus möglich.
    # -----------------------------------------------------------------------
    BLACK    = QColor("#000000")
    WHITE    = QColor("#FFFFFF")
    BG       = QColor("#F5F5F5")   # Fensterhintergrund
    BASE     = QColor("#FFFFFF")   # Eingabefelder, Listen
    ALT      = QColor("#EAEAEA")   # Alternating rows
    BTN      = QColor("#E0E0E0")   # Schaltflächen
    DISABLED = QColor("#A0A0A0")   # Inaktive Elemente
    HILIGHT  = QColor("#0078D4")   # Auswahl / Fokus (DRK-Blau)
    HI_TEXT  = QColor("#FFFFFF")   # Text auf Auswahl

    pal = QPalette()
    # Aktiv & Inaktiv – gleiche Farben (kein "graues Fenster im Hintergrund")
    for grp in (QPalette.ColorGroup.Active,
                QPalette.ColorGroup.Inactive,
                QPalette.ColorGroup.Normal):
        pal.setColor(grp, QPalette.ColorRole.Window,          BG)
        pal.setColor(grp, QPalette.ColorRole.WindowText,      BLACK)
        pal.setColor(grp, QPalette.ColorRole.Base,            BASE)
        pal.setColor(grp, QPalette.ColorRole.AlternateBase,   ALT)
        pal.setColor(grp, QPalette.ColorRole.Text,            BLACK)
        pal.setColor(grp, QPalette.ColorRole.BrightText,      BLACK)
        pal.setColor(grp, QPalette.ColorRole.ButtonText,      BLACK)
        pal.setColor(grp, QPalette.ColorRole.Button,          BTN)
        pal.setColor(grp, QPalette.ColorRole.Highlight,       HILIGHT)
        pal.setColor(grp, QPalette.ColorRole.HighlightedText, HI_TEXT)
        pal.setColor(grp, QPalette.ColorRole.ToolTipBase,     QColor("#FFFFC4"))
        pal.setColor(grp, QPalette.ColorRole.ToolTipText,     BLACK)
        pal.setColor(grp, QPalette.ColorRole.PlaceholderText, QColor("#808080"))
        pal.setColor(grp, QPalette.ColorRole.Link,            QColor("#0078D4"))
        pal.setColor(grp, QPalette.ColorRole.LinkVisited,     QColor("#5C2D91"))
    # Disabled
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, DISABLED)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       DISABLED)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, DISABLED)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base,       QColor("#F0F0F0"))
    app.setPalette(pal)

    # -----------------------------------------------------------------------
    # GLOBAL STYLESHEET – Font-Familie und Schriftgröße für alle QWidgets,
    # die kein eigenes Stylesheet haben. Farbe wird durch die Palette geregelt;
    # explizite widget-eigene Stylesheets (z.B. "color: white" in der Sidebar)
    # haben höhere Spezifizität und überschreiben diesen Basis-Style problemlos.
    # -----------------------------------------------------------------------
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', Arial, 'Helvetica Neue', sans-serif;
            font-size: 10pt;
            color: #000000;
        }
        QToolTip {
            color: #000000;
            background-color: #FFFFC4;
            border: 1px solid #C0C0C0;
            font-size: 9pt;
        }
    """)

    # DB-Backup vor Programmstart
    _db_startup_backup()

    # Datenbanktabellen beim ersten Start erstellen
    try:
        from database.migrations import run_migrations
        run_migrations()
    except Exception as e:
        print(f"[WARNUNG] Datenbankinitialisierung fehlgeschlagen: {e}")
        print("[INFO] Bitte Datenbankverbindung in config.py konfigurieren.")

    # Mitarbeiter-Datenbank initialisieren (database SQL/mitarbeiter.db)
    try:
        from database.connection import init_mitarbeiter_db
        init_mitarbeiter_db()
    except Exception as e:
        print(f"[WARNUNG] Mitarbeiter-DB Initialisierung fehlgeschlagen: {e}")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
