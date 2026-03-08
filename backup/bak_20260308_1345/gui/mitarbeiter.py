"""
Mitarbeiter-Widget
Mitarbeiter anzeigen, hinzufügen, bearbeiten, löschen
und aus Dienstplan-Excel-Dateien importieren.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QComboBox, QDateEdit, QMessageBox, QFrame,
    QProgressDialog, QApplication,
)
from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtGui import QFont, QColor

from config import FIORI_BLUE, FIORI_TEXT, FIORI_ERROR
from database.models import Mitarbeiter


# ── Import-Worker ──────────────────────────────────────────────────────────────

class _ImportWorker(QThread):
    """Führt den Excel-Import im Hintergrund-Thread aus."""
    fortschritt = Signal(int, int, str)   # (aktuell, gesamt, dateiname)
    fertig      = Signal(dict)            # Ergebnis-Dict
    fehler      = Signal(str)

    def __init__(self, ordner: str, parent=None):
        super().__init__(parent)
        self._ordner = ordner

    def run(self):
        try:
            from functions.mitarbeiter_functions import importiere_aus_dienstplaenen
            result = importiere_aus_dienstplaenen(
                ordner=self._ordner,
                fortschritt_callback=lambda a, b, c: self.fortschritt.emit(a, b, c),
            )
            self.fertig.emit(result)
        except Exception as e:
            self.fehler.emit(str(e))


# ── Lade-Worker ────────────────────────────────────────────────────────────────

class _LoadWorker(QThread):
    """Lädt Mitarbeiterdaten + Ausschluss-Set im Hintergrund-Thread."""
    fertig = Signal(list, set)   # (mitarbeiter_liste, ausgeschlossene_namen_set)

    def run(self):
        try:
            from functions.mitarbeiter_functions import get_alle_mitarbeiter
            from functions.settings_functions import get_ausgeschlossene_namen
            mitarbeiter = get_alle_mitarbeiter()
            try:
                ausgeschlossen = set(get_ausgeschlossene_namen())
            except Exception:
                ausgeschlossen = set()
            self.fertig.emit(mitarbeiter, ausgeschlossen)
        except Exception:
            self.fertig.emit([], set())


# ── Mitarbeiter-Dialog ─────────────────────────────────────────────────────────

class MitarbeiterDialog(QDialog):
    """Dialog zum Erstellen/Bearbeiten eines Mitarbeiters."""
    def __init__(self, mitarbeiter: Mitarbeiter = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mitarbeiter" + (" bearbeiten" if mitarbeiter else " hinzufügen"))
        self.setMinimumWidth(440)
        self.result_ma: Mitarbeiter | None = None
        self._ma = mitarbeiter or Mitarbeiter()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(10)

        self._vorname   = QLineEdit(self._ma.vorname)
        self._nachname  = QLineEdit(self._ma.nachname)
        self._persnr    = QLineEdit(self._ma.personalnummer)
        self._email     = QLineEdit(self._ma.email)
        self._telefon   = QLineEdit(self._ma.telefon)

        self._funktion  = QComboBox()
        self._funktion.addItems(["stamm", "dispo"])
        self._funktion.setCurrentText(self._ma.funktion or "stamm")

        self._position  = QComboBox()
        self._position.setEditable(True)
        self._abteilung = QComboBox()
        self._abteilung.setEditable(True)

        self._status = QComboBox()
        self._status.addItems(["aktiv", "inaktiv", "beurlaubt"])
        self._status.setCurrentText(self._ma.status)

        self._eintrittsdatum = QDateEdit()
        self._eintrittsdatum.setCalendarPopup(True)
        self._eintrittsdatum.setDisplayFormat("dd.MM.yyyy")
        if self._ma.eintrittsdatum:
            self._eintrittsdatum.setDate(QDate(
                self._ma.eintrittsdatum.year,
                self._ma.eintrittsdatum.month,
                self._ma.eintrittsdatum.day,
            ))
        else:
            self._eintrittsdatum.setDate(QDate.currentDate())

        try:
            from functions.mitarbeiter_functions import get_positionen, get_abteilungen
            for p in get_positionen():
                self._position.addItem(p)
            for a in get_abteilungen():
                self._abteilung.addItem(a)
        except Exception:
            self._position.addItems(["Notfallsanitäter", "Rettungssanitäter", "Sanitätshelfer"])
            self._abteilung.addItems(["Erste-Hilfe-Station"])

        if self._ma.position:
            idx = self._position.findText(self._ma.position)
            if idx >= 0:
                self._position.setCurrentIndex(idx)
            else:
                self._position.setCurrentText(self._ma.position)
        if self._ma.abteilung:
            idx = self._abteilung.findText(self._ma.abteilung)
            if idx >= 0:
                self._abteilung.setCurrentIndex(idx)
            else:
                self._abteilung.setCurrentText(self._ma.abteilung)

        form.addRow("Vorname *:",       self._vorname)
        form.addRow("Nachname *:",      self._nachname)
        form.addRow("Personalnummer:",  self._persnr)
        form.addRow("Funktion:",        self._funktion)
        form.addRow("Position:",        self._position)
        form.addRow("Abteilung:",       self._abteilung)
        form.addRow("E-Mail:",          self._email)
        form.addRow("Telefon:",         self._telefon)
        form.addRow("Eintrittsdatum:",  self._eintrittsdatum)
        form.addRow("Status:",          self._status)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Speichern")
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet(
            f"background-color: {FIORI_BLUE}; color: white; "
            f"font-size: 13px; border-radius: 4px;"
        )
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        if not self._vorname.text().strip() or not self._nachname.text().strip():
            QMessageBox.warning(self, "Pflichtfelder", "Vor- und Nachname sind Pflichtfelder.")
            return

        qd = self._eintrittsdatum.date()
        from datetime import date
        eintritt = date(qd.year(), qd.month(), qd.day())

        self._ma.vorname        = self._vorname.text().strip()
        self._ma.nachname       = self._nachname.text().strip()
        self._ma.personalnummer = self._persnr.text().strip()
        self._ma.funktion       = self._funktion.currentText()
        self._ma.position       = self._position.currentText()
        self._ma.abteilung      = self._abteilung.currentText()
        self._ma.email          = self._email.text().strip()
        self._ma.telefon        = self._telefon.text().strip()
        self._ma.eintrittsdatum = eintritt
        self._ma.status         = self._status.currentText()

        self.result_ma = self._ma
        self.accept()


# ── Mitarbeiter-Widget ─────────────────────────────────────────────────────────

class MitarbeiterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._alle: list[Mitarbeiter] = []
        self._ausgeschlossen_set: set = set()
        self._load_worker: _LoadWorker | None = None
        self._gefiltert: list[Mitarbeiter] = []   # aktuell gefiltertes Gesamtergebnis
        self._angezeigt: int = 0                  # wie viele Zeilen gerade in der Tabelle
        self._PAGE_SIZE = 50
        self._build_ui()
        # refresh() wird von MitarbeiterHauptWidget.refresh() aufgerufen

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # ── Titelzeile ──
        top = QHBoxLayout()
        title = QLabel("👥 Mitarbeiter")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {FIORI_TEXT};")
        top.addWidget(title)
        top.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Suchen…")
        self._search.setMinimumWidth(200)
        self._search.setMinimumHeight(36)
        self._search.textChanged.connect(self._search_changed)
        top.addWidget(self._search)

        self._filter_funktion = QComboBox()
        self._filter_funktion.addItems(["Alle", "stamm", "dispo"])
        self._filter_funktion.setMinimumHeight(36)
        self._filter_funktion.currentTextChanged.connect(self._anwenden_filter)
        top.addWidget(self._filter_funktion)

        add_btn = QPushButton("➕ Hinzufügen")
        add_btn.setMinimumHeight(36)
        add_btn.setStyleSheet(
            f"background-color: {FIORI_BLUE}; color: white; "
            f"border-radius: 4px; padding: 0 12px;"
        )
        add_btn.clicked.connect(self._add_mitarbeiter)
        top.addWidget(add_btn)

        import_btn = QPushButton("📥 Aus Dienstplänen")
        import_btn.setMinimumHeight(36)
        import_btn.setToolTip(
            "Alle Excel-Dienstpläne aus 04_Tagesdienstpläne/ scannen\n"
            "und neue Namen in die Datenbank importieren (keine Duplikate)"
        )
        import_btn.setStyleSheet(
            "background-color: #2e7d32; color: white; "
            "border-radius: 4px; padding: 0 12px;"
        )
        import_btn.clicked.connect(self._import_aus_dienstplaenen)
        top.addWidget(import_btn)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Aktualisieren")
        refresh_btn.setMinimumHeight(36)
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)

        layout.addLayout(top)

        # ── Tabelle ──
        self._table = QTableWidget()
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels([
            "ID", "Vorname", "Nachname", "Funktion", "Personalnr.",
            "Position", "Status", "Eintritt", "Export", "Abteilung",
        ])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._edit_mitarbeiter)
        self._table.setStyleSheet("background-color: white; border-radius: 6px;")
        layout.addWidget(self._table)

        self._mehr_btn = QPushButton("▼  Nächste 50 laden")
        self._mehr_btn.setFixedHeight(32)
        self._mehr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mehr_btn.setStyleSheet(
            "QPushButton{background:#f0f4fa;border:1px solid #b0c4de;"
            "border-radius:4px;color:#1565a8;font-size:11px;}"
            "QPushButton:hover{background:#d8e8f8;}"
        )
        self._mehr_btn.setVisible(False)
        self._mehr_btn.clicked.connect(self._weitere_laden)
        layout.addWidget(self._mehr_btn)

        # ── Aktions-Buttons ──
        btn_row = QHBoxLayout()
        edit_btn = QPushButton("✏️ Bearbeiten")
        edit_btn.clicked.connect(self._edit_mitarbeiter)
        del_btn  = QPushButton("🗑️ Löschen")
        del_btn.setStyleSheet(f"color: {FIORI_ERROR};")
        del_btn.clicked.connect(self._delete_mitarbeiter)
        self._ausschluss_btn = QPushButton("🚫 Ausschließen")
        self._ausschluss_btn.setToolTip(
            "Ausgewählten Mitarbeiter vom Word-Export ausschließen / einschließen"
        )
        self._ausschluss_btn.clicked.connect(self._toggle_ausschluss)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addWidget(self._ausschluss_btn)
        btn_row.addStretch()
        self._row_count_lbl = QLabel("0 Einträge")
        self._row_count_lbl.setStyleSheet("color: #888;")
        btn_row.addWidget(self._row_count_lbl)
        layout.addLayout(btn_row)

        # ── Weitere-laden-Button (unter Tabelle) ──────────────────────────────────
        # (wird erst nach der Tabelle in layout eingefügt, Reihenfolge beachten)

        # ── Info-Box ──
        info = QLabel(
            "ℹ️  <b>Export-Spalte (✅/🚫)</b>: Zeigt, ob ein Mitarbeiter in der "
            "<b>Stärkemeldungs-Word-Datei</b> erscheint. Mit \'🚫 Ausschließen\' "
            "kann das für einzelne Personen deaktiviert werden. "
            "<b>📥 Aus Dienstplänen</b> scannt alle Excel-Dateien in "
            "<i>04_Tagesdienstpläne/</i> und legt neue Namen automatisch an "
            "(Stamm/Dispo wird erkannt, keine Duplikate)."
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setStyleSheet(
            "background: #fff8e8; border: 1px solid #f0d080; border-radius: 5px; "
            "padding: 7px 12px; color: #5a3e00; font-size: 11px;"
        )
        layout.addWidget(info)

    # ── Daten laden ────────────────────────────────────────────────────────────

    def refresh(self):
        """Startet asynchrones Laden der Mitarbeiter aus der DB."""
        # Laufenden Worker aufgeben (NICHT warten — würde Hauptthread blockieren)
        if self._load_worker and self._load_worker.isRunning():
            try:
                self._load_worker.fertig.disconnect()
            except RuntimeError:
                pass
            self._load_worker.quit()
            # kein wait() — Worker läuft still im Hintergrund zu Ende

        # Gecachte Daten sofort anzeigen (falls vorhanden)
        if self._alle:
            self._anwenden_filter()
        else:
            self._row_count_lbl.setText("⏳ Lade…")

        self._load_worker = _LoadWorker(self)
        self._load_worker.fertig.connect(self._on_data_geladen)
        self._load_worker.start()

    def _on_data_geladen(self, mitarbeiter: list, ausgeschlossen: set):
        """Callback wenn Worker fertig — läuft im Hauptthread."""
        self._alle = mitarbeiter
        self._ausgeschlossen_set = ausgeschlossen
        self._anwenden_filter()

    def _anwenden_filter(self):
        """Filtert alle Daten, zeigt erste PAGE_SIZE Zeilen."""
        funktion_filter = self._filter_funktion.currentText()
        suchtext = self._search.text().strip().lower()

        gefiltert = self._alle
        if funktion_filter != "Alle":
            gefiltert = [m for m in gefiltert if m.funktion == funktion_filter]
        if suchtext:
            gefiltert = [
                m for m in gefiltert
                if suchtext in m.vorname.lower()
                or suchtext in m.nachname.lower()
                or suchtext in (m.personalnummer or "").lower()
                or suchtext in (m.position or "").lower()
                or suchtext in (m.funktion or "").lower()
            ]
        self._gefiltert = gefiltert
        self._angezeigt = 0
        self._table.setRowCount(0)
        self._render_page()

    def _weitere_laden(self):
        """Lädt die nächsten PAGE_SIZE Zeilen nach."""
        self._render_page()

    def _render_page(self):
        """Fügt die nächsten PAGE_SIZE Einträge aus _gefiltert in die Tabelle."""
        start = self._angezeigt
        ende  = min(start + self._PAGE_SIZE, len(self._gefiltert))
        neue_zeilen = self._gefiltert[start:ende]
        if not neue_zeilen:
            self._mehr_btn.setVisible(False)
            self._update_count_label()
            return

        ausgeschlossen_set = self._ausgeschlossen_set
        self._table.setUpdatesEnabled(False)
        self._table.setRowCount(ende)  # Gesamtzeilen auf neue Tabellengröße setzen

        for row_idx, m in enumerate(neue_zeilen):
            row = start + row_idx
            vollname_low = f"{m.vorname} {m.nachname}".lower().strip()
            ist_ausgeschlossen = vollname_low in ausgeschlossen_set
            export_symbol = "🚫 Nein" if ist_ausgeschlossen else "✅ Ja"
            funktion_label = "🔰 Dispo" if m.funktion == "dispo" else "👕 Stamm"

            vals = [
                str(m.id or ""),
                m.vorname,
                m.nachname,
                funktion_label,
                m.personalnummer or "",
                m.position or "",
                m.status or "",
                str(m.eintrittsdatum or ""),
                export_symbol,
                m.abteilung or "",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, m.id)

                if m.funktion == "dispo":
                    item.setBackground(QColor("#dce8f5"))
                    item.setForeground(QColor("#0a5ba4"))
                elif col == 6 and val == "aktiv":
                    item.setForeground(QColor(Qt.GlobalColor.darkGreen))
                elif col == 6 and val == "inaktiv":
                    item.setForeground(QColor(Qt.GlobalColor.darkRed))

                if ist_ausgeschlossen:
                    item.setBackground(QColor("#fce8e8"))
                    item.setForeground(QColor("#bb0000"))

                self._table.setItem(row, col, item)

        self._table.setUpdatesEnabled(True)
        self._angezeigt = ende
        self._update_count_label()

    def _update_count_label(self):
        gesamt   = len(self._gefiltert)
        angezeigt = self._angezeigt
        rest = gesamt - angezeigt
        if rest > 0:
            self._mehr_btn.setText(f"▼  Nächste {min(rest, self._PAGE_SIZE)} laden ({rest} weitere)")
            self._mehr_btn.setVisible(True)
        else:
            self._mehr_btn.setVisible(False)
        self._row_count_lbl.setText(
            f"{angezeigt} / {gesamt} Einträge  "
            f"| Stamm: {sum(1 for m in self._gefiltert if m.funktion=='stamm')}  "
            f"| Dispo: {sum(1 for m in self._gefiltert if m.funktion=='dispo')}"
        )

    def _search_changed(self, _text: str):
        self._anwenden_filter()

    # ── Tabelle rendern ────────────────────────────────────────────────────────

    # Wird von _render_page() ersetzt (bleibt für direkte Aufrufe bei CRUD-Refresh)
    def _render_table(self, mitarbeiter: list[Mitarbeiter]):
        """Erzwingt vollständiges Neurender (z.B. nach CRUD-Aktion)."""
        self._gefiltert = mitarbeiter
        self._angezeigt = 0
        self._table.setRowCount(0)
        self._render_page()

    # ── Hilfsmethoden ──────────────────────────────────────────────────────────

    def _get_selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return int(item.text()) if item and item.text() else None

    def _get_vollname_selected(self) -> str | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        vorname  = (self._table.item(row, 1) or QTableWidgetItem("")).text()
        nachname = (self._table.item(row, 2) or QTableWidgetItem("")).text()
        return f"{vorname} {nachname}".strip() or None

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def _add_mitarbeiter(self):
        dialog = MitarbeiterDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_ma:
            try:
                from functions.mitarbeiter_functions import mitarbeiter_erstellen
                mitarbeiter_erstellen(dialog.result_ma)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Fehler beim Speichern", str(e))

    def _edit_mitarbeiter(self):
        mid = self._get_selected_id()
        if mid is None:
            QMessageBox.information(self, "Kein Mitarbeiter", "Bitte eine Zeile auswählen.")
            return
        try:
            from functions.mitarbeiter_functions import (
                get_mitarbeiter_by_id, mitarbeiter_aktualisieren,
            )
            ma = get_mitarbeiter_by_id(mid)
            if ma is None:
                return
            dialog = MitarbeiterDialog(ma, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_ma:
                mitarbeiter_aktualisieren(dialog.result_ma)
                self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def _delete_mitarbeiter(self):
        mid = self._get_selected_id()
        if mid is None:
            QMessageBox.information(self, "Kein Mitarbeiter", "Bitte eine Zeile auswählen.")
            return
        vollname = self._get_vollname_selected() or f"ID {mid}"
        antwort = QMessageBox.question(
            self, "Mitarbeiter löschen",
            f"Soll <b>{vollname}</b> wirklich gelöscht werden?<br>"
            "Diese Aktion kann nicht rückgängig gemacht werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            try:
                from functions.mitarbeiter_functions import mitarbeiter_loeschen
                mitarbeiter_loeschen(mid)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", str(e))

    def _toggle_ausschluss(self):
        vollname = self._get_vollname_selected()
        if not vollname:
            QMessageBox.information(self, "Kein Mitarbeiter", "Bitte eine Zeile auswählen.")
            return
        try:
            from functions.settings_functions import toggle_ausgeschlossener_name
            jetzt_ausgeschlossen = toggle_ausgeschlossener_name(vollname)
            status = "🚫 ausgeschlossen" if jetzt_ausgeschlossen else "✅ eingeschlossen"
            self._ausschluss_btn.setText(
                "✅ Einschließen" if jetzt_ausgeschlossen else "🚫 Ausschließen"
            )
            QMessageBox.information(
                self, "Export-Status geändert",
                f"{vollname} ist jetzt {status} vom Word-Export.",
            )
            self._anwenden_filter()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    # ── Excel-Import ───────────────────────────────────────────────────────────

    def _import_aus_dienstplaenen(self):
        """Startet den Excel-Import-Prozess im Hintergrundthread."""
        from config import BASE_DIR
        from pathlib import Path
        ordner = str(Path(BASE_DIR).parent.parent / "04_Tagesdienstpläne")

        if not Path(ordner).exists():
            QMessageBox.warning(
                self, "Ordner nicht gefunden",
                f"Dienstplan-Ordner nicht gefunden:\n{ordner}\n\n"
                "Bitte sicherstellen, dass der OneDrive-Ordner "
                "'04_Tagesdienstpläne' vorhanden ist.",
            )
            return

        antwort = QMessageBox.question(
            self, "Aus Dienstplänen importieren",
            "Alle Excel-Dateien im Ordner <b>04_Tagesdienstpläne/</b> werden "
            "durchsucht und neue Namen importiert.<br><br>"
            "Bereits vorhandene Mitarbeiter werden <b>nicht</b> doppelt angelegt.<br>"
            "Dispo-Mitarbeiter werden automatisch erkannt.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return

        # Progress-Dialog
        self._progress = QProgressDialog(
            "Dienstpläne werden gescannt…", "Abbrechen", 0, 100, self
        )
        self._progress.setWindowTitle("Import läuft…")
        self._progress.setMinimumWidth(400)
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.setValue(0)
        self._progress.show()

        # Hintergrundthread
        self._worker = _ImportWorker(ordner, parent=self)
        self._worker.fortschritt.connect(self._import_fortschritt)
        self._worker.fertig.connect(self._import_abgeschlossen)
        self._worker.fehler.connect(self._import_fehler)
        self._progress.canceled.connect(self._worker.quit)
        self._worker.start()

    def _import_fortschritt(self, aktuell: int, gesamt: int, datei: str):
        if gesamt > 0:
            self._progress.setMaximum(gesamt)
            self._progress.setValue(aktuell)
            self._progress.setLabelText(f"Scanne Datei {aktuell}/{gesamt}:\n{datei}")

    def _import_abgeschlossen(self, result: dict):
        self._progress.close()
        self.refresh()
        QMessageBox.information(
            self, "Import abgeschlossen",
            f"✅ <b>{result['neu']}</b> neue Mitarbeiter importiert\n"
            f"⏭️ {result['übersprungen']} bereits vorhanden (übersprungen)\n"
            f"⚠️ {result['fehler']} Dateien konnten nicht gelesen werden\n"
            f"📂 {result['gesamt']} Excel-Dateien gescannt",
        )

    def _import_fehler(self, msg: str):
        self._progress.close()
        QMessageBox.critical(self, "Import-Fehler", f"Fehler beim Import:\n{msg}")


# ── Kombiniertes Haupt-Widget (Tab: Übersicht + Dokumente) ─────────────────────

class MitarbeiterHauptWidget(QWidget):
    """Kombiniertes Widget: Tab 1 = Mitarbeiter-Übersicht, Tab 2 = Dokumente.
    MitarbeiterDokumenteWidget wird erst beim ersten Klick auf Tab 2 geladen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QTabWidget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 160px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #1565a8;
                font-weight: bold;
                border-bottom: 2px solid #1565a8;
            }
        """)

        self._uebersicht_tab = MitarbeiterWidget()

        # Dokumente-Tab: erst beim ersten Klick laden (Lazy Loading)
        self._dokumente_tab = None
        self._dokumente_placeholder = QWidget()  # leerer Platzhalter

        self._tabs.addTab(self._dokumente_placeholder, "📄  Dokumente")
        self._tabs.addTab(self._uebersicht_tab,       "👥  Übersicht")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tabs)

    def _on_tab_changed(self, index: int):
        """Lädt MitarbeiterDokumenteWidget beim ersten Klick auf Tab 0 (Dokumente)."""
        if index == 0 and self._dokumente_tab is None:
            from gui.mitarbeiter_dokumente import MitarbeiterDokumenteWidget
            self._dokumente_tab = MitarbeiterDokumenteWidget()
            # Platzhalter ersetzen
            self._tabs.removeTab(0)
            self._tabs.insertTab(0, self._dokumente_tab, "📄  Dokumente")
            self._tabs.setCurrentIndex(0)

    def refresh(self):
        # Beim ersten Aufruf: Dokumente-Tab sofort laden wenn er aktiv ist
        if self._dokumente_tab is None and self._tabs.currentIndex() == 0:
            self._on_tab_changed(0)
        self._uebersicht_tab.refresh()
        if self._tabs.currentIndex() == 0 and self._dokumente_tab is not None:
            self._dokumente_tab.refresh()

