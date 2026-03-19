"""
Backup-Widget
Verwaltung von Datenbank- und Gemeinsam.26-Ordner-Backups
"""
import os
import sys
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QGroupBox, QListWidget, QListWidgetItem,
    QProgressDialog, QTreeWidget, QTreeWidgetItem, QScrollArea, QSizePolicy
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, QThread, Signal

from config import FIORI_BLUE, FIORI_TEXT, FIORI_SUCCESS, FIORI_ERROR
from backup import backup_manager


class BackupThread(QThread):
    """Thread für Backup-Erstellung (verhindert GUI-Freeze)."""
    finished = Signal(dict)
    progress = Signal(int, int, str)  # (aktuell, gesamt, dateiname)
    
    def __init__(self, backup_type='gemeinsam', inkrementell=True):
        super().__init__()
        self.backup_type = backup_type
        self.inkrementell = inkrementell
    
    def _progress_callback(self, current, total, filename):
        """Callback für Fortschrittsanzeige."""
        self.progress.emit(current, total, filename)
    
    def run(self):
        if self.backup_type == 'gemeinsam':
            result = backup_manager.create_gemeinsam_backup(
                self.inkrementell, 
                progress_callback=self._progress_callback
            )
        elif self.backup_type == 'sql_databases':
            result = backup_manager.create_sql_databases_backup(
                progress_callback=self._progress_callback
            )
        elif self.backup_type == 'nesk3':
            zip_path = backup_manager.create_zip_backup()
            result = {
                'erfolg': bool(zip_path),
                'zip_pfad': zip_path,
                'meldung': 'Nesk3 Backup erstellt.' if zip_path else 'Fehler beim Backup.'
            }
        else:
            result = {'erfolg': False, 'meldung': 'Unbekannter Backup-Typ'}
        
        self.finished.emit(result)


class BackupWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._backup_thread = None
        self._build_ui()
        self._load_backups()

    def _build_ui(self):
        # Scroll-Container damit das Widget bei vielen Sektionen scrollbar ist
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        inner = QWidget()
        scroll.setWidget(inner)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Titel ──────────────────────────────────────────────────────
        title = QLabel("💾 Backup-Verwaltung")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {FIORI_TEXT};")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ddd;")
        layout.addWidget(sep)

        # ── Gemeinsam.26 Backup Gruppe ──────────────────────────────────
        self._build_gemeinsam_group(layout)
        
        # ── SQL-Datenbanken Backup Gruppe ──────────────────────────────
        self._build_sql_databases_group(layout)

        # ── Automatische DB-Backups (Startup) ─────────────────────────
        self._build_db_backups_group(layout)

        # ── Nesk3 Code Backup Gruppe ───────────────────────────────────
        self._build_nesk3_group(layout)

    def _build_gemeinsam_group(self, parent_layout):
        """Erstellt die Gemeinsam.26 Backup Sektion."""
        grp = QGroupBox("📂 Gemeinsam.26 Ordner Backup")
        grp.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        grp.setStyleSheet("""
            QGroupBox {
                border: 1px solid #dce8f5;
                border-radius: 6px;
                margin-top: 8px;
                padding: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #0a5ba4;
            }
        """)
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(12)

        # Beschreibung
        beschreibung = QLabel(
            "Sichert alle Dateien im !Gemeinsam.26 Ordner (außer Nesk-Unterordner).\n"
            "Inkrementelles Backup: Nur geänderte Dateien werden gesichert."
        )
        beschreibung.setWordWrap(True)
        beschreibung.setStyleSheet("color: #555; font-size: 11px; font-weight: normal;")
        grp_layout.addWidget(beschreibung)

        # Statistiken
        self._gemeinsam_stats_label = QLabel("Lade Statistiken...")
        self._gemeinsam_stats_label.setStyleSheet(
            "background: #f5f5f5; padding: 8px; border-radius: 4px; font-size: 11px; font-weight: normal;"
        )
        grp_layout.addWidget(self._gemeinsam_stats_label)

        # Buttons
        btn_row = QHBoxLayout()
        
        self._gemeinsam_backup_btn = QPushButton("🔄 Backup erstellen (Inkrementell)")
        self._gemeinsam_backup_btn.setMinimumHeight(36)
        self._gemeinsam_backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {FIORI_SUCCESS};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #0e9948;
            }}
        """)
        self._gemeinsam_backup_btn.clicked.connect(self._create_gemeinsam_backup)
        btn_row.addWidget(self._gemeinsam_backup_btn)
        
        voll_backup_btn = QPushButton("📦 Vollständiges Backup")
        voll_backup_btn.setMinimumHeight(36)
        voll_backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {FIORI_BLUE};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #0854a0;
            }}
        """)
        voll_backup_btn.clicked.connect(self._create_gemeinsam_backup_full)
        btn_row.addWidget(voll_backup_btn)
        
        grp_layout.addLayout(btn_row)

        # Backup-Liste
        list_label = QLabel("Vorhandene Backups:")
        list_label.setStyleSheet("font-weight: bold; font-size: 11px; margin-top: 8px;")
        grp_layout.addWidget(list_label)

        self._gemeinsam_list = QListWidget()
        self._gemeinsam_list.setMaximumHeight(180)
        self._gemeinsam_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f5f8fa;
            }
        """)
        grp_layout.addWidget(self._gemeinsam_list)

        # Backup-Listen Buttons
        list_btn_row = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Aktualisieren")
        refresh_btn.setMaximumWidth(150)
        refresh_btn.clicked.connect(self._load_backups)
        list_btn_row.addWidget(refresh_btn)
        
        list_btn_row.addStretch()
        
        delete_btn = QPushButton("🗑️ Löschen")
        delete_btn.setMaximumWidth(120)
        delete_btn.setStyleSheet(f"color: {FIORI_ERROR};")
        delete_btn.clicked.connect(self._delete_gemeinsam_backup)
        list_btn_row.addWidget(delete_btn)
        
        grp_layout.addLayout(list_btn_row)

        parent_layout.addWidget(grp)

    def _build_sql_databases_group(self, parent_layout):
        """Erstellt die SQL-Datenbanken Backup Sektion."""
        grp = QGroupBox("🗄️ SQL-Datenbanken Backup")
        grp.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        grp.setStyleSheet("""
            QGroupBox {
                border: 1px solid #dce8f5;
                border-radius: 6px;
                margin-top: 8px;
                padding: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #0a5ba4;
            }
        """)
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(12)

        # Beschreibung
        beschreibung = QLabel(
            "Sichert alle Datenbanken (.db) aus dem 'database SQL' Ordner:\n"
            "einsaetze.db, mitarbeiter.db, nesk3.db, patienten_station.db, psa.db, usw."
        )
        beschreibung.setWordWrap(True)
        beschreibung.setStyleSheet("color: #555; font-size: 11px; font-weight: normal;")
        grp_layout.addWidget(beschreibung)

        # Button
        sql_backup_btn = QPushButton("💾 SQL-Datenbanken sichern")
        sql_backup_btn.setMinimumHeight(36)
        sql_backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {FIORI_SUCCESS};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #0e9948;
            }}
        """)
        sql_backup_btn.clicked.connect(self._create_sql_databases_backup)
        grp_layout.addWidget(sql_backup_btn)

        # Backup-Liste
        list_label = QLabel("Vorhandene SQL-Backups:")
        list_label.setStyleSheet("font-weight: bold; font-size: 11px; margin-top: 8px;")
        grp_layout.addWidget(list_label)

        self._sql_list = QListWidget()
        self._sql_list.setMaximumHeight(150)
        self._sql_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f5f8fa;
            }
        """)
        grp_layout.addWidget(self._sql_list)

        # Backup-Listen Buttons
        list_btn_row = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Aktualisieren")
        refresh_btn.setMaximumWidth(150)
        refresh_btn.clicked.connect(self._load_backups)
        list_btn_row.addWidget(refresh_btn)
        
        list_btn_row.addStretch()
        
        restore_btn = QPushButton("♻️ Wiederherstellen")
        restore_btn.setMaximumWidth(150)
        restore_btn.setStyleSheet(f"background-color: {FIORI_BLUE}; color: white; border-radius: 4px; padding: 4px 8px;")
        restore_btn.clicked.connect(self._restore_sql_backup)
        list_btn_row.addWidget(restore_btn)
        
        delete_btn = QPushButton("🗑️ Löschen")
        delete_btn.setMaximumWidth(120)
        delete_btn.setStyleSheet(f"color: {FIORI_ERROR};")
        delete_btn.clicked.connect(self._delete_sql_backup)
        list_btn_row.addWidget(delete_btn)
        
        grp_layout.addLayout(list_btn_row)

        parent_layout.addWidget(grp)

    def _build_db_backups_group(self, parent_layout):
        """Automatische Startup-DB-Backups: anzeigen und als Kopie laden."""
        grp = QGroupBox("🗄️ Automatische DB-Backups (7 Tage)")
        grp.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        grp.setStyleSheet("""
            QGroupBox {
                border: 1px solid #dce8f5;
                border-radius: 6px;
                margin-top: 8px;
                padding: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #0a5ba4;
            }
        """)
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(10)

        hinweis = QLabel(
            "Beim Start der App werden automatisch alle Datenbanken gesichert (bis zu 7 Tage, 5× pro Tag).\n"
            "Mit 'Backup-Kopie erstellen' werden die Dateien in einen geschützten Ordner kopiert –\n"
            "die Live-Datenbanken und Turso-Sync werden dabei NICHT verändert."
        )
        hinweis.setWordWrap(True)
        hinweis.setStyleSheet("color: #555; font-size: 11px; font-weight: normal;")
        grp_layout.addWidget(hinweis)

        self._db_backup_tree = QTreeWidget()
        self._db_backup_tree.setHeaderLabels(["Datum / Uhrzeit", "Datenbanken", "Größe"])
        self._db_backup_tree.setColumnWidth(0, 220)
        self._db_backup_tree.setColumnWidth(1, 100)
        self._db_backup_tree.setMaximumHeight(260)
        self._db_backup_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                font-size: 11px;
            }
            QTreeWidget::item { padding: 4px; border-bottom: 1px solid #f0f0f0; }
            QTreeWidget::item:hover { background: #f5f8fa; }
            QTreeWidget::item:selected { background: #dce8f5; color: #000; }
        """)
        grp_layout.addWidget(self._db_backup_tree)

        btn_row = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Aktualisieren")
        refresh_btn.setMaximumWidth(150)
        refresh_btn.clicked.connect(self._load_db_backups)
        btn_row.addWidget(refresh_btn)

        btn_row.addStretch()

        copy_btn = QPushButton("📋 Backup-Kopie erstellen")
        copy_btn.setMinimumHeight(32)
        copy_btn.setStyleSheet(
            f"background-color: {FIORI_BLUE}; color: white; border-radius: 4px; "
            "font-weight: bold; padding: 4px 14px;"
        )
        copy_btn.setToolTip(
            "Kopiert die Dateien des gewählten Snapshots in einen sicheren Ordner.\n"
            "Live-Datenbanken werden NICHT verändert."
        )
        copy_btn.clicked.connect(self._create_db_backup_copy)
        btn_row.addWidget(copy_btn)

        grp_layout.addLayout(btn_row)
        parent_layout.addWidget(grp)

    def _load_db_backups(self):
        """Füllt den DB-Backup-Baum."""
        self._db_backup_tree.clear()
        backups = backup_manager.list_db_backups()
        if not backups:
            item = QTreeWidgetItem(["Noch keine Backups vorhanden", "", ""])
            item.setForeground(0, QColor("#999"))
            self._db_backup_tree.addTopLevelItem(item)
            return

        for eintrag in backups:
            root = QTreeWidgetItem([
                f"📅 {eintrag['datum_anzeige']}",
                f"{eintrag['anzahl_dbs']} DB(s)",
                f"{eintrag['groesse_mb']} MB",
            ])
            root.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            root.setData(0, Qt.ItemDataRole.UserRole, {"typ": "tag", "pfad": eintrag["pfad"]})
            for snap in eintrag["snapshots"]:
                db_namen = ", ".join(s["name"] for s in snap["dateien"])
                child = QTreeWidgetItem([
                    f"  🕐 {snap['zeit']}",
                    f"{len(snap['dateien'])} DB(s)",
                    "",
                ])
                child.setToolTip(0, db_namen)
                child.setData(0, Qt.ItemDataRole.UserRole, {
                    "typ": "snapshot",
                    "pfad": eintrag["pfad"],
                    "ts":   snap["ts"],
                    "zeit": snap["zeit"],
                    "datum_anzeige": eintrag["datum_anzeige"],
                })
                root.addChild(child)
            self._db_backup_tree.addTopLevelItem(root)
        self._db_backup_tree.expandAll()

    def _create_db_backup_copy(self):
        """Erstellt eine Backup-Kopie des gewählten Snapshots."""
        item = self._db_backup_tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Keine Auswahl",
                                "Bitte wählen Sie einen Snapshot (Uhrzeit-Eintrag) oder einen Tag aus.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        pfad = data["pfad"]
        ts   = data.get("ts")          # None bei Tages-Auswahl → neuester Snapshot
        info = data.get("zeit", "neuester Snapshot")
        datum = data.get("datum_anzeige", "")

        antwort = QMessageBox.question(
            self,
            "Backup-Kopie erstellen",
            f"Backup-Kopie erstellen für:\n\n"
            f"  Datum: {datum}\n"
            f"  Snapshot: {info}\n\n"
            "Die Kopie wird in einem geschützten Ordner abgelegt.\n"
            "Die Live-Datenbanken werden NICHT verändert.\n\n"
            "Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return

        ergebnis = backup_manager.restore_db_backup_as_copy(pfad, ts)
        if ergebnis["erfolg"]:
            QMessageBox.information(self, "Backup-Kopie erstellt", ergebnis["meldung"])
        else:
            QMessageBox.critical(self, "Fehler", ergebnis["meldung"])

    def _build_nesk3_group(self, parent_layout):
        """Erstellt die Nesk3 Code Backup Sektion."""
        grp = QGroupBox("💻 Nesk3 Code Backup")
        grp.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        grp.setStyleSheet("""
            QGroupBox {
                border: 1px solid #dce8f5;
                border-radius: 6px;
                margin-top: 8px;
                padding: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #0a5ba4;
            }
        """)
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(12)

        # Beschreibung
        beschreibung = QLabel(
            "Sichert den kompletten Nesk3 Quellcode (Python, Datenbanken, Konfiguration)."
        )
        beschreibung.setWordWrap(True)
        beschreibung.setStyleSheet("color: #555; font-size: 11px; font-weight: normal;")
        grp_layout.addWidget(beschreibung)

        # Button
        nesk3_backup_btn = QPushButton("💾 Nesk3 Backup erstellen")
        nesk3_backup_btn.setMinimumHeight(36)
        nesk3_backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {FIORI_BLUE};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #0854a0;
            }}
        """)
        nesk3_backup_btn.clicked.connect(self._create_nesk3_backup)
        grp_layout.addWidget(nesk3_backup_btn)

        # Backup-Liste
        self._nesk3_list = QListWidget()
        self._nesk3_list.setMaximumHeight(150)
        self._nesk3_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f5f8fa;
            }
        """)
        grp_layout.addWidget(self._nesk3_list)

        parent_layout.addWidget(grp)

    def _load_backups(self):
        """Lädt alle Backups und aktualisiert die Listen."""
        # Gemeinsam.26 Statistiken
        stats = backup_manager.get_gemeinsam_backup_stats()
        if stats['ordner_existiert']:
            stats_text = (
                f"📊 Ordner: {stats['dateien_count']} Dateien | "
                f"{stats['groesse_mb']} MB | "
                f"Letzte Änderung: {stats['letzte_aenderung']}"
            )
        else:
            stats_text = "⚠️ Quellordner nicht gefunden"
        self._gemeinsam_stats_label.setText(stats_text)

        # Gemeinsam.26 Backups
        self._gemeinsam_list.clear()
        gemeinsam_backups = backup_manager.list_gemeinsam_backups()
        for backup in gemeinsam_backups:
            item_text = f"📦 {backup['dateiname']} | {backup['groesse_mb']} MB | {backup['erstellt']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, backup)
            self._gemeinsam_list.addItem(item)
        
        if not gemeinsam_backups:
            item = QListWidgetItem("Noch keine Backups vorhanden")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self._gemeinsam_list.addItem(item)

        # SQL-Datenbank Backups
        self._sql_list.clear()
        sql_backups = backup_manager.list_sql_backups()
        for backup in sql_backups:
            item_text = f"🗄️ {backup['datum_anzeige']} | {backup['anzahl_dbs']} DB(s) | {backup['anzahl_snapshots']} Snapshots | {backup['groesse_mb']} MB"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, backup)
            self._sql_list.addItem(item)
        
        if not sql_backups:
            item = QListWidgetItem("Noch keine Backups vorhanden")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self._sql_list.addItem(item)

        # Nesk3 Backups
        self._nesk3_list.clear()
        nesk3_backups = backup_manager.list_zip_backups()
        for backup in nesk3_backups[:10]:  # Nur letzte 10 anzeigen
            item_text = f"💻 {backup['dateiname']} | {round(backup['groesse_kb']/1024, 1)} MB | {backup['erstellt']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, backup)
            self._nesk3_list.addItem(item)
        
        if not nesk3_backups:
            item = QListWidgetItem("Noch keine Backups vorhanden")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.gray)
            self._nesk3_list.addItem(item)

        # Automatische DB-Backups
        self._load_db_backups()

    def _create_gemeinsam_backup(self):
        """Erstellt ein inkrementelles Gemeinsam.26 Backup."""
        self._start_backup('gemeinsam', inkrementell=True)

    def _create_gemeinsam_backup_full(self):
        """Erstellt ein vollständiges Gemeinsam.26 Backup."""
        reply = QMessageBox.question(
            self,
            "Vollständiges Backup",
            "Möchten Sie wirklich ein vollständiges Backup erstellen?\n"
            "Dies kann länger dauern als ein inkrementelles Backup.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_backup('gemeinsam', inkrementell=False)

    def _create_nesk3_backup(self):
        """Erstellt ein Nesk3 Code Backup."""
        self._start_backup('nesk3')

    def _start_backup(self, backup_type, inkrementell=True):
        """Startet Backup-Thread."""
        if self._backup_thread and self._backup_thread.isRunning():
            QMessageBox.warning(self, "Backup läuft", "Ein Backup läuft bereits.")
            return

        # Buttons deaktivieren
        self._gemeinsam_backup_btn.setEnabled(False)

        # Progress Dialog mit echtem Fortschritt
        self._progress = QProgressDialog("Backup wird erstellt...", None, 0, 100, self)
        self._progress.setWindowTitle("Backup")
        self._progress.setMinimumDuration(0)
        self._progress.setCancelButton(None)
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.show()

        # Thread starten
        self._backup_thread = BackupThread(backup_type, inkrementell)
        self._backup_thread.finished.connect(self._on_backup_finished)
        self._backup_thread.progress.connect(self._on_backup_progress)
        self._backup_thread.start()
    
    def _on_backup_progress(self, current: int, total: int, filename: str):
        """Aktualisiert die Fortschrittsanzeige."""
        if total > 0:
            percent = int((current / total) * 100)
            self._progress.setValue(percent)
            # Kürze Dateiname wenn zu lang
            short_name = filename if len(filename) < 60 else '...' + filename[-57:]
            self._progress.setLabelText(
                f"Backup wird erstellt...\n\n"
                f"Datei {current} von {total}\n"
                f"{short_name}"
            )
        else:
            self._progress.setLabelText(f"Backup wird erstellt...\n\n{filename}")

    def _on_backup_finished(self, result: dict):
        """Wird aufgerufen wenn Backup fertig ist."""
        self._progress.close()
        self._gemeinsam_backup_btn.setEnabled(True)

        if result['erfolg']:
            if result.get('dateien_count', 0) == 0:
                QMessageBox.information(self, "Backup", result['meldung'])
            else:
                msg = result['meldung']
                # Zeige Warnungen wenn Dateien übersprungen wurden
                if result.get('skipped_count', 0) > 0 or result.get('error_count', 0) > 0:
                    QMessageBox.warning(self, "Backup abgeschlossen mit Warnungen", msg)
                else:
                    QMessageBox.information(self, "Backup erfolgreich", msg)
            self._load_backups()
        else:
            QMessageBox.critical(self, "Backup Fehler", result['meldung'])

    def _delete_gemeinsam_backup(self):
        """Löscht das ausgewählte Gemeinsam.26 Backup."""
        selected = self._gemeinsam_list.currentItem()
        if not selected or not selected.data(Qt.ItemDataRole.UserRole):
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie ein Backup aus.")
            return

        backup = selected.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "Backup löschen",
            f"Möchten Sie das Backup '{backup['dateiname']}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(backup['pfad'])
                QMessageBox.information(self, "Gelöscht", f"Backup gelöscht: {backup['dateiname']}")
                self._load_backups()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Löschen: {str(e)}")

    def _create_sql_databases_backup(self):
        """Erstellt ein Backup aller SQL-Datenbanken."""
        self._start_backup('sql_databases')

    def _restore_sql_backup(self):
        """Stellt ein SQL-Datenbank-Backup wieder her."""
        selected = self._sql_list.currentItem()
        if not selected or not selected.data(Qt.ItemDataRole.UserRole):
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie ein Backup aus.")
            return

        backup = selected.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.warning(
            self,
            "Datenbank wiederherstellen",
            f"⚠️ WARNUNG ⚠️\n\n"
            f"Möchten Sie wirklich das Backup vom {backup['datum_anzeige']} wiederherstellen?\n\n"
            f"Dies überschreibt ALLE aktuellen Datenbanken!\n"
            f"Es wird empfohlen, vorher ein neues Backup zu erstellen.\n\n"
            f"Backup enthält {backup['anzahl_dbs']} Datenbank(en) ({backup['anzahl_snapshots']} Snapshots).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                ergebnis = backup_manager.restore_sql_backup(backup['pfad'])
                if ergebnis.get('erfolg'):
                    QMessageBox.information(
                        self,
                        "Wiederherstellung erfolgreich",
                        f"Backup vom {backup['datum_anzeige']} wurde wiederhergestellt.\n\n"
                        f"{ergebnis['meldung']}\n\n"
                        f"Bitte starten Sie die Anwendung neu, damit die Änderungen wirksam werden."
                    )
                else:
                    QMessageBox.critical(self, "Fehler", f"Wiederherstellung fehlgeschlagen:\n{ergebnis.get('meldung', 'Unbekannter Fehler')}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler bei Wiederherstellung: {str(e)}")

    def _delete_sql_backup(self):
        """Löscht das ausgewählte SQL-Datenbank-Backup."""
        selected = self._sql_list.currentItem()
        if not selected or not selected.data(Qt.ItemDataRole.UserRole):
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie ein Backup aus.")
            return

        backup = selected.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "Backup löschen",
            f"Möchten Sie das SQL-Backup vom '{backup['datum_anzeige']}' wirklich löschen?\n\n"
            f"Alle {backup['anzahl_snapshots']} Snapshot(s) dieses Tages werden gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(backup['pfad'])
                QMessageBox.information(self, "Gelöscht", f"Backup vom {backup['datum_anzeige']} wurde gelöscht.")
                self._load_backups()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Löschen: {str(e)}")
