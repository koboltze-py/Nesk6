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
from PySide6.QtGui import QFont, QPalette, QColor, QIcon
from gui.main_window import MainWindow
from gui.splash_screen import SplashScreen


def _db_startup_backup():
    """Erstellt beim Programmstart ein SQLite-Backup aller Datenbanken.
    Struktur: db_backups/YYYY-MM-DD/<name>_HHMMSS.db
    Pro Tag max. 5 Backups je Datenbank, max. 7 Tages-Ordner insgesamt."""
    try:
        from config import DB_PATH
        from datetime import date as _date, timedelta as _td
        db_dir = os.path.dirname(DB_PATH)
        base_backup = os.path.join(db_dir, "Backup Data", "db_backups")
        jetzt = datetime.now()
        tag_ordner = os.path.join(base_backup, jetzt.strftime("%Y-%m-%d"))
        os.makedirs(tag_ordner, exist_ok=True)
        zeitstempel = jetzt.strftime("%H%M%S")

        # Alle .db-Dateien direkt im database SQL-Ordner sichern (keine Unterordner)
        for db_path in glob.glob(os.path.join(db_dir, "*.db")):
            name = os.path.splitext(os.path.basename(db_path))[0]
            backup_path = os.path.join(tag_ordner, f"{name}_{zeitstempel}.db")
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(backup_path)
            src.backup(dst)
            dst.close()
            src.close()
            # Pro Tag nur die letzten 5 Backups je Datenbank behalten
            tages_backups = sorted(glob.glob(os.path.join(tag_ordner, f"{name}_*.db")))
            for alt in tages_backups[:-5]:
                try:
                    os.remove(alt)
                except Exception:
                    pass
            print(f"[OK] DB-Backup: {jetzt.strftime('%Y-%m-%d')}/{os.path.basename(backup_path)}")

        # Nur die letzten 7 Tages-Ordner behalten
        alle_tage = sorted([
            d for d in os.listdir(base_backup)
            if os.path.isdir(os.path.join(base_backup, d)) and len(d) == 10 and d.count("-") == 2
        ])
        for alter_tag in alle_tage[:-7]:
            try:
                shutil.rmtree(os.path.join(base_backup, alter_tag))
                print(f"[DEL] Alter Tages-Ordner gelöscht: {alter_tag}")
            except Exception:
                pass
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
    # GLOBAL STYLESHEET
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

    # App-Icon setzen
    _icon_path = os.path.join(BASE_DIR, "Daten", "Logo", "nesk3.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    # ── Splash Screen ──────────────────────────────────────────────────────
    from config import APP_VERSION
    splash = SplashScreen(version=APP_VERSION)
    splash.show()
    QApplication.processEvents()

    # ── DB-Backup ──────────────────────────────────────────────────────────
    splash.set_status("Datenbank-Backup wird erstellt …")
    _db_startup_backup()

    # ── Migrationen ────────────────────────────────────────────────────────
    splash.set_status("Datenbanktabellen werden geprüft …")
    try:
        from database.migrations import run_migrations
        run_migrations()
    except Exception as e:
        print(f"[WARNUNG] Datenbankinitialisierung fehlgeschlagen: {e}")
        print("[INFO] Bitte Datenbankverbindung in config.py konfigurieren.")

    # ── Mitarbeiter-DB ─────────────────────────────────────────────────────
    try:
        from database.connection import init_mitarbeiter_db
        init_mitarbeiter_db()
    except Exception as e:
        print(f"[WARNUNG] Mitarbeiter-DB Initialisierung fehlgeschlagen: {e}")

    # ── Turso-Sync ─────────────────────────────────────────────────────────
    # AUSNAHME: Falls ein Backup-Restore ausstehend ist, zuerst lokal → Turso pushen
    # (verhindert dass pull_all() die wiederhergestellten Daten überschreibt).
    try:
        from database.turso_sync import (
            ensure_turso_schema, pull_all, start_background_sync,
            push_all_local_to_turso, init_sync_ts,
        )
        from backup.backup_manager import is_restore_pending, clear_restore_pending
        splash.set_status("Turso-Schema wird geprüft …")
        ensure_turso_schema()
        if is_restore_pending():
            splash.set_status("Wiederhergestellte Daten werden nach Turso übertragen …")
            print("[Start] Backup-Restore ausstehend: sende wiederhergestellte Daten nach Turso...")
            push_all_local_to_turso()
            clear_restore_pending()
            print("[Start] Turso wurde mit wiederhergestellten Daten aktualisiert.")
        else:
            splash.set_status("Daten werden mit Turso synchronisiert …")
            pull_all()
        # Timestamp setzen – Hintergrundthread startet danach ohne Doppelpull
        init_sync_ts()
        start_background_sync()
    except Exception as e:
        print(f"[WARNUNG] Turso-Sync konnte nicht gestartet werden: {e}")
        print("[INFO] App läuft weiter mit lokalen Datenbanken.")

    # ── Hauptfenster ───────────────────────────────────────────────────────
    splash.set_status("Oberfläche wird geladen …")
    window = MainWindow()
    splash.finish(window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
