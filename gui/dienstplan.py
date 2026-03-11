"""
Dienstplan-Widget
Schichten anzeigen, hinzufügen, bearbeiten, löschen
Excel-Import und Word-Export (Stärkemeldung)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QDateEdit, QTimeEdit, QTextEdit,
    QMessageBox, QFileDialog, QSpinBox, QFrame,
    QTreeView, QSplitter, QFileSystemModel,
    QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, QDate, QTime, Signal, QFileSystemWatcher
from PySide6.QtGui import QFont, QColor

from config import FIORI_BLUE, FIORI_TEXT, FIORI_ERROR
from database.models import Dienstplan


class DienstplanDialog(QDialog):
    """Dialog zum Erstellen/Bearbeiten einer Schicht."""
    def __init__(self, schicht: Dienstplan = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schicht" + (" bearbeiten" if schicht else " hinzufügen"))
        self.setMinimumWidth(420)
        self.result_schicht: Dienstplan | None = None
        self._s = schicht or Dienstplan()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        # Mitarbeiter-Auswahl
        self._mitarbeiter_combo = QComboBox()
        self._ma_map: dict[str, int] = {}
        try:
            from functions.mitarbeiter_functions import get_alle_mitarbeiter
            for ma in get_alle_mitarbeiter(nur_aktive=True):
                label = f"{ma.vollname} ({ma.personalnummer})"
                self._mitarbeiter_combo.addItem(label)
                self._ma_map[label] = ma.id
                if ma.id == self._s.mitarbeiter_id:
                    self._mitarbeiter_combo.setCurrentText(label)
        except Exception:
            self._mitarbeiter_combo.addItem("(Kein Mitarbeiter verfügbar)")

        self._datum = QDateEdit()
        self._datum.setCalendarPopup(True)
        self._datum.setDisplayFormat("dd.MM.yyyy")
        if self._s.datum:
            self._datum.setDate(QDate(self._s.datum.year, self._s.datum.month, self._s.datum.day))
        else:
            self._datum.setDate(QDate.currentDate())

        self._start = QTimeEdit()
        self._start.setDisplayFormat("HH:mm")
        self._start.setTime(QTime(6, 0) if not self._s.start_uhrzeit
                            else QTime(self._s.start_uhrzeit.hour, self._s.start_uhrzeit.minute))

        self._end = QTimeEdit()
        self._end.setDisplayFormat("HH:mm")
        self._end.setTime(QTime(14, 0) if not self._s.end_uhrzeit
                          else QTime(self._s.end_uhrzeit.hour, self._s.end_uhrzeit.minute))

        self._position = QComboBox()
        try:
            from functions.mitarbeiter_functions import get_positionen
            self._position.addItems(get_positionen())
        except Exception:
            self._position.addItems(["Notfallsanitäter", "Rettungssanitäter"])
        if self._s.position:
            idx = self._position.findText(self._s.position)
            if idx >= 0:
                self._position.setCurrentIndex(idx)

        self._typ = QComboBox()
        self._typ.addItems(["regulär", "nacht", "bereitschaft"])
        self._typ.setCurrentText(self._s.schicht_typ)

        self._notizen = QTextEdit(self._s.notizen)
        self._notizen.setMaximumHeight(80)

        form.addRow("Mitarbeiter *:", self._mitarbeiter_combo)
        form.addRow("Datum *:",       self._datum)
        form.addRow("Von:",           self._start)
        form.addRow("Bis:",           self._end)
        form.addRow("Position:",      self._position)
        form.addRow("Schicht-Typ:",   self._typ)
        form.addRow("Notizen:",       self._notizen)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Speichern")
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet(f"background-color: {FIORI_BLUE}; color: white; font-size: 13px; border-radius: 4px;")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        selected_label = self._mitarbeiter_combo.currentText()
        ma_id = self._ma_map.get(selected_label)
        if not ma_id:
            QMessageBox.warning(self, "Fehler", "Bitte einen Mitarbeiter auswählen.")
            return

        from datetime import date, time
        qd = self._datum.date()
        qs = self._start.time()
        qe = self._end.time()

        self._s.mitarbeiter_id  = ma_id
        self._s.datum           = date(qd.year(), qd.month(), qd.day())
        self._s.start_uhrzeit   = time(qs.hour(), qs.minute())
        self._s.end_uhrzeit     = time(qe.hour(), qe.minute())
        self._s.position        = self._position.currentText()
        self._s.schicht_typ     = self._typ.currentText()
        self._s.notizen         = self._notizen.toPlainText().strip()

        self.result_schicht = self._s
        self.accept()


# Dienste die zum Standard gehören  -  Sonderdienste werden im Dialog angezeigt
_STANDARD_DIENSTE = frozenset({'N', 'N10', 'T', 'T10', 'DT', 'DT3', 'DN', 'DN3'})

_TAG_DIENSTE   = frozenset({'T', 'T10', 'T8', 'DT', 'DT3'})
_NACHT_DIENSTE = frozenset({'N', 'N10', 'NF', 'DN', 'DN3'})


class ExportDialog(QDialog):
    """Dialog für Word-Export: Zeitraum, PAX-Zahl, Ausgabepfad, Sonderdienst-Filter."""

    _STAERKEMELDUNG_DIR = (
        r"C:\Users\DRKairport\OneDrive - Deutsches Rotes Kreuz - Kreisverband Köln e.V"
        r"\Dateien von Erste-Hilfe-Station-Flughafen - DRK Köln e.V_ - !Gemeinsam.26"
        r"\06_Stärkemeldung"
    )

    def __init__(self, parsed_data: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Word-Export  -  Stärkemeldung")
        self.setMinimumWidth(500)
        self.setMinimumHeight(460)
        self._parsed_data = parsed_data or {}
        self.result: dict | None = None
        self._checkboxen: list[tuple] = []   # (QCheckBox, vollname_lower)
        self._pfad_auto   = True             # True = Pfad noch auto-generiert
        self._ausgabe_pfad = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setSpacing(10)

        today = QDate.currentDate()

        self._von = QDateEdit(today)
        self._von.setCalendarPopup(True)
        self._von.setDisplayFormat("dd.MM.yyyy")
        self._von.dateChanged.connect(self._update_default_pfad)

        self._bis = QDateEdit(today)
        self._bis.setCalendarPopup(True)
        self._bis.setDisplayFormat("dd.MM.yyyy")
        self._bis.dateChanged.connect(self._update_default_pfad)

        self._pax = QSpinBox()
        self._pax.setRange(0, 99999)
        self._pax.setValue(0)

        self._pfad_lbl = QLabel()
        self._pfad_lbl.setWordWrap(True)
        pfad_btn = QPushButton("Speicherort wählen ...")
        pfad_btn.clicked.connect(self._choose_path)

        # Standardpfad gleich setzen
        self._update_default_pfad()

        form.addRow("Von:",       self._von)
        form.addRow("Bis:",       self._bis)
        form.addRow("PAX-Zahl:", self._pax)
        form.addRow("Datei:",    pfad_btn)
        form.addRow("",          self._pfad_lbl)
        layout.addLayout(form)

        # -- Sonderdienst-Abschnitt -------------------------------------
        sonder_personen = []
        for listen_key in ('betreuer', 'dispo'):
            for p in self._parsed_data.get(listen_key, []):
                dk = (p.get('dienst_kategorie') or '').upper()
                if dk not in _STANDARD_DIENSTE:
                    sonder_personen.append(p)

        if sonder_personen:
            sep1 = QFrame()
            sep1.setFrameShape(QFrame.Shape.HLine)
            sep1.setStyleSheet("color: #ddd;")
            layout.addWidget(sep1)

            sonder_lbl = QLabel(
                " Mitarbeiter mit Sonderdiensten:\n"
                "   Haken setzen = vom Export ausschließen"
            )
            sonder_lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            sonder_lbl.setStyleSheet("color: #555; padding: 2px 0;")
            layout.addWidget(sonder_lbl)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(160)
            scroll.setStyleSheet(
                "QScrollArea { border: 1px solid #dce8f5; border-radius: 4px; }"
            )
            inner        = QWidget()
            inner_layout = QVBoxLayout(inner)
            inner_layout.setSpacing(3)
            inner_layout.setContentsMargins(8, 6, 8, 6)

            try:
                from functions.settings_functions import get_ausgeschlossene_namen
                settings_ausgeschlossen = set(get_ausgeschlossene_namen())
            except Exception:
                settings_ausgeschlossen = set()

            for p in sonder_personen:
                vollname_lower = p.get('vollname', '').lower()
                dienst         = p.get('dienst_kategorie', '') or '?'
                anzeige        = p.get('anzeigename', p.get('vollname', ''))
                cb = QCheckBox(f"  {anzeige}  [{dienst}]")
                cb.setFont(QFont("Arial", 10))
                # vorbelegen: ausschließen wenn bereits in Einstellungen
                cb.setChecked(vollname_lower in settings_ausgeschlossen)
                inner_layout.addWidget(cb)
                self._checkboxen.append((cb, vollname_lower))

            inner_layout.addStretch()
            scroll.setWidget(inner)
            layout.addWidget(scroll)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #ddd;")
        layout.addWidget(sep2)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Exportieren")
        export_btn.setMinimumHeight(40)
        export_btn.setStyleSheet(
            f"background-color: {FIORI_BLUE}; color: white; font-size: 13px; border-radius: 4px;"
        )
        export_btn.clicked.connect(self._export)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(export_btn)
        layout.addLayout(btn_row)

    def _make_default_pfad(self) -> str:
        """Erstellt Standardpfad mit Von-Bis-Datum im Ordner 06_Stärkemeldung."""
        ziel_dir = self._STAERKEMELDUNG_DIR
        if not os.path.isdir(ziel_dir):
            ziel_dir = os.path.expanduser("~")
        qv = self._von.date()
        qb = self._bis.date()
        von_str = f"{qv.day():02d}.{qv.month():02d}.{qv.year()}"
        bis_str = f"{qb.day():02d}.{qb.month():02d}.{qb.year()}"
        if qv == qb:
            name = f"Stärkemeldung {von_str}.docx"
        else:
            name = f"Stärkemeldung {von_str} - {bis_str}.docx"
        return os.path.join(ziel_dir, name)

    def _update_default_pfad(self):
        """Pfad nur aktualisieren wenn noch auto-generiert (kein manueller Pfad)."""
        if self._pfad_auto:
            self._ausgabe_pfad = self._make_default_pfad()
            self._pfad_lbl.setText(self._ausgabe_pfad)
            self._pfad_lbl.setStyleSheet("color: #333;")

    def _choose_path(self):
        default = self._ausgabe_pfad or self._make_default_pfad()
        path, _ = QFileDialog.getSaveFileName(
            self, "Ausgabedatei wählen", default,
            "Word-Dokument (*.docx)"
        )
        if path:
            self._ausgabe_pfad = path
            self._pfad_auto    = False
            self._pfad_lbl.setText(path)
            self._pfad_lbl.setStyleSheet("color: #333;")

    def _export(self):
        if not self._ausgabe_pfad:
            QMessageBox.warning(self, "Kein Pfad", "Bitte zuerst einen Speicherort wählen.")
            return

        # PAX-Zahl = 0 → Nutzer darauf aufmerksam machen
        if self._pax.value() == 0:
            ret = QMessageBox.warning(
                self, "PAX-Zahl ist 0",
                "Die PAX-Zahl ist aktuell 0.\n\n"
                "Bitte tragen Sie die Anzahl der Passagiere ein,\n"
                "oder klicken Sie auf 'Trotzdem exportieren'.",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Ignore,
                QMessageBox.StandardButton.Ok,
            )
            if ret != QMessageBox.StandardButton.Ignore:
                self._pax.setFocus()
                self._pax.selectAll()
                return

        qv = self._von.date()
        qb = self._bis.date()
        ausgeschlossene = {vn for cb, vn in self._checkboxen if cb.isChecked()}
        self.result = {
            'von_datum':               datetime(qv.year(), qv.month(), qv.day()),
            'bis_datum':               datetime(qb.year(), qb.month(), qb.day()),
            'pax_zahl':                self._pax.value(),
            'ausgabe_pfad':            self._ausgabe_pfad,
            'ausgeschlossene_vollnamen': ausgeschlossene,
        }
        self.accept()


_ALLE_DIENST_TYPEN = [
    'T', 'T10', 'N', 'N10', 'NF',
    'DT', 'DT3', 'DN', 'DN3', 'D',
    'FB', 'FB1', 'FB2',
    'R', 'B1', 'B2',
    'KRANK',
]
_ALLE_ZEITEN = ['%02d:%02d' % (h, m) for h in range(24) for m in (0, 15, 30, 45)]


class EditDienstDialog(QDialog):
    """Dialog zum Bearbeiten von Dienst, Von- und Bis-Zeit einer Zeile."""

    def __init__(self, person: dict, parent=None, hinweis: str = ''):
        super().__init__(parent)
        self.setWindowTitle('Dienst bearbeiten')
        self.setMinimumWidth(340)
        self.result_data: dict | None = None
        self._person = person
        self._hinweis = hinweis
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        name_lbl = QLabel(self._person.get('vollname', ''))
        name_lbl.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f'color: {FIORI_TEXT};')
        layout.addWidget(name_lbl)

        if self._hinweis:
            hint_lbl = QLabel(f'ℹ  {self._hinweis}')
            hint_lbl.setWordWrap(True)
            hint_lbl.setFont(QFont('Arial', 9))
            hint_lbl.setStyleSheet(
                'background:#fff8e1; border:1px solid #f0c040; border-radius:4px;'
                'color:#7a5000; padding:5px 8px;'
            )
            layout.addWidget(hint_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        self._dienst_cb = QComboBox()
        self._dienst_cb.setEditable(True)
        self._dienst_cb.addItems(_ALLE_DIENST_TYPEN)
        current = (self._person.get('dienst_kategorie') or '').upper()
        idx = self._dienst_cb.findText(current)
        if idx >= 0:
            self._dienst_cb.setCurrentIndex(idx)
        else:
            self._dienst_cb.setCurrentText(current)

        self._von_cb = QComboBox()
        self._von_cb.setEditable(True)
        self._von_cb.addItems(_ALLE_ZEITEN)
        self._von_cb.setCurrentText(self._person.get('start_zeit', '') or '')

        self._bis_cb = QComboBox()
        self._bis_cb.setEditable(True)
        self._bis_cb.addItems(_ALLE_ZEITEN)
        self._bis_cb.setCurrentText(self._person.get('end_zeit', '') or '')

        form.addRow('Dienst:', self._dienst_cb)
        form.addRow('Von:', self._von_cb)
        form.addRow('Bis:', self._bis_cb)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        save_btn = QPushButton('\U0001f4be Speichern')
        save_btn.setMinimumHeight(38)
        save_btn.setStyleSheet(
            f'background-color: {FIORI_BLUE}; color: white; '
            f'font-size: 13px; border-radius: 4px;'
        )
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton('Abbrechen')
        cancel_btn.setMinimumHeight(38)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _save(self):
        dienst = self._dienst_cb.currentText().strip().upper()
        von    = self._von_cb.currentText().strip()
        bis    = self._bis_cb.currentText().strip()
        self.result_data = {'dienst': dienst, 'von': von, 'bis': bis}
        self.accept()


class _DispoZeitenVorschauDialog(QDialog):
    """
    Zeigt alle Dispo- und Betreuer-Eintraege des Dienstplans vor dem Export zur
    Kontrolle an. Zeiten koennen per Doppelklick oder 'Bearbeiten'-Knopf
    angepasst werden; die Aenderungen fliessen in den Word-Export ein.
    """

    def __init__(self, parsed_data: dict, parent=None, raw_data: dict | None = None):
        super().__init__(parent)
        import copy
        self.setWindowTitle("Dispo-Zeiten – Vorschau & Bearbeitung")
        self.setMinimumWidth(720)
        self.setMinimumHeight(440)
        self._data = copy.deepcopy(parsed_data)
        # Originale Excel-Zeiten vor dem Runden sichern (für Vergleichsspalten)
        # Bevorzugt aus raw_data (Parser ohne Rundung), sonst Fallback auf parsed_data
        src = raw_data if raw_data else parsed_data
        self._orig_zeiten: dict[tuple, tuple] = {}
        for i, p in enumerate(src.get('dispo', [])):
            self._orig_zeiten[('dispo', i)] = (
                p.get('start_zeit') or '–', p.get('end_zeit') or '–'
            )
        for i, p in enumerate(src.get('betreuer', [])):
            self._orig_zeiten[('betreuer', i)] = (
                p.get('start_zeit') or '–', p.get('end_zeit') or '–'
            )
        # Dispo-Zeiten vorab auf volle Stunden runden (so wie der Word-Exporter es tut)
        for p in self._data.get('dispo', []):
            for key in ('start_zeit', 'end_zeit'):
                t = p.get(key) or ''
                if t and ':' in t:
                    p[key] = f"{int(t.split(':')[0]):02d}:00"
        self._row_to_person: list[tuple[str, int]] = []
        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        title = QLabel("✏  Dispo-Zeiten prüfen und anpassen")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {FIORI_TEXT};")
        layout.addWidget(title)

        hint = QLabel(
            "Doppelklick auf eine Zeile oder «Bearbeiten»-Knopf, um Dienst / Von / Bis "
            "zu ändern. Geänderte Werte werden im Word-Export übernommen."
        )
        hint.setWordWrap(True)
        hint.setFont(QFont("Arial", 9))
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Name (Kategorie)", "Dienst",
            "Von (Excel)", "Bis (Excel)",
            "Von (Export)", "Bis (Export)"
        ])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for col in (1, 2, 3, 4, 5):
            self._table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents
            )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget{border:1px solid #ddd; font-size:12px;}"
        )
        self._table.verticalHeader().setVisible(False)
        self._table.itemDoubleClicked.connect(lambda item: self._edit_row(item.row()))
        layout.addWidget(self._table, 1)

        self._rebuild_table()

        # ── Buttons ──────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#ddd; margin:2px 0;")
        layout.addWidget(sep)

        btn_row = QHBoxLayout()

        btn_edit = QPushButton("✏  Bearbeiten")
        btn_edit.setFixedHeight(36)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setToolTip("Markierte Zeile bearbeiten (Dienst, Von, Bis)")
        btn_edit.setStyleSheet(
            f"QPushButton{{background:{FIORI_BLUE};color:white;border:none;"
            f"border-radius:4px;padding:4px 14px;font-size:12px;}}"
            f"QPushButton:hover{{background:#0855a9;}}"
        )
        btn_edit.clicked.connect(self._edit_selected)
        btn_row.addWidget(btn_edit)
        btn_row.addStretch()

        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_weiter = QPushButton("Weiter  →")
        btn_weiter.setFixedHeight(36)
        btn_weiter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_weiter.setToolTip("Zeiten übernehmen und zum Export-Dialog weitergehend")
        btn_weiter.setStyleSheet(
            "QPushButton{background:#107e3e;color:white;border:none;"
            "border-radius:4px;padding:4px 18px;font-size:12px;}"
            "QPushButton:hover{background:#0d6131;}"
        )
        btn_weiter.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(6)
        btn_row.addWidget(btn_weiter)
        layout.addLayout(btn_row)

    # ── Tabellenlogik ────────────────────────────────────────────────────────

    def _rebuild_table(self):
        self._row_to_person.clear()
        rows: list[tuple[str, int, dict]] = []
        for kat_key in ('dispo', 'betreuer'):
            for idx, p in enumerate(self._data.get(kat_key, [])):
                rows.append((kat_key, idx, p))

        self._table.setRowCount(len(rows))
        for row, (kat_key, idx, p) in enumerate(rows):
            self._row_to_person.append((kat_key, idx))
            kat_lbl = "Dispo" if kat_key == "dispo" else "Betreuer"
            anzeige = p.get("anzeigename") or p.get("vollname") or "–"
            name_item = QTableWidgetItem(f"[{kat_lbl}]  {anzeige}")
            name_item.setForeground(
                QColor("#0a5ba4") if kat_key == "dispo" else QColor(FIORI_TEXT)
            )
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, QTableWidgetItem(p.get("dienst_kategorie", "") or "–"))

            orig_von, orig_bis = self._orig_zeiten.get((kat_key, idx), ('–', '–'))
            exp_von = p.get("start_zeit", "") or "–"
            exp_bis = p.get("end_zeit", "") or "–"

            self._table.setItem(row, 2, QTableWidgetItem(orig_von))
            self._table.setItem(row, 3, QTableWidgetItem(orig_bis))

            it_von = QTableWidgetItem(exp_von)
            it_bis = QTableWidgetItem(exp_bis)
            # Exportzeit blau hervorheben wenn sie von der Excel-Zeit abweicht
            if exp_von != orig_von:
                it_von.setForeground(QColor("#0a6ed1"))
                it_von.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            if exp_bis != orig_bis:
                it_bis.setForeground(QColor("#0a6ed1"))
                it_bis.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            self._table.setItem(row, 4, it_von)
            self._table.setItem(row, 5, it_bis)

    def _edit_selected(self):
        self._edit_row(self._table.currentRow())

    def _edit_row(self, row: int):
        if row < 0 or row >= len(self._row_to_person):
            return
        kat_key, idx = self._row_to_person[row]
        person = self._data[kat_key][idx]
        hinweis = (
            'Dispo-Zeiten werden im Word-Export auf volle Stunden gerundet '
            '(z. B. 07:30 → 07:00).'
            if kat_key == 'dispo' else ''
        )
        dlg = EditDienstDialog(person, parent=self, hinweis=hinweis)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
            d = dlg.result_data
            person["dienst_kategorie"] = d["dienst"]
            person["start_zeit"] = d["von"]
            person["end_zeit"] = d["bis"]
            person["manuell_geaendert"] = True
            self._rebuild_table()
            self._table.selectRow(row)

    # ── Ergebnis ─────────────────────────────────────────────────────────────

    @property
    def modified_data(self) -> dict:
        """Gibt die (ggf. bearbeiteten) Dienstplan-Daten zurück."""
        return self._data


class _DienstplanPane(QWidget):
    """Einzelne Tabellen-Ansicht fuer einen geoeffneten Dienstplan."""

    # Signal: dieser Pane wurde als Export-Quelle aktiviert (sendet eigenen Index)
    export_selected = Signal(int)

    def __init__(self, pane_index: int = 0, parent=None):
        super().__init__(parent)
        self._pane_index: int           = pane_index
        self._parsed_data: dict | None  = None
        self._display_data: dict | None = None
        self._table_row_data: list      = []
        self._excel_path: str           = ''
        self._is_export_active: bool    = False
        self._build_ui()

    # ---------- Eigenschaften ----------

    @property
    def excel_path(self) -> str:
        return self._excel_path

    @property
    def parsed_data(self) -> dict | None:
        return self._parsed_data

    @property
    def is_empty(self) -> bool:
        return not bool(self._excel_path)

    def set_export_active(self, active: bool):
        """Markiert diese Pane visuell als Export-Quelle."""
        self._is_export_active = active
        self._update_header_style()
        self._export_btn.setEnabled(not active)
        self._export_btn.setText(
            '✓  Für Wordexport gewählt' if active
            else 'Hier klicken um Datei als Wordexport auszuwählen'
        )

    def _update_header_style(self):
        if self._is_export_active:
            self._header_bar.setStyleSheet(
                'background: #0a5ba4; border-radius: 4px 4px 0 0; padding: 2px 4px;'
            )
            self._title_lbl.setStyleSheet('color: white; font-weight: bold; font-size: 11px;')
        else:
            self._header_bar.setStyleSheet(
                'background: #f0f4f8; border: 1px solid #dce8f5; '
                'border-radius: 4px 4px 0 0; padding: 2px 4px;'
            )
            self._title_lbl.setStyleSheet(f'color: {FIORI_TEXT}; font-size: 11px;')

    def clear(self):
        self._parsed_data    = None
        self._display_data   = None
        self._table_row_data = []
        self._excel_path     = ''
        self._table.clearContents()
        self._table.setRowCount(0)
        self._datum_lbl.setVisible(False)
        self._status_lbl.setText('Doppelklick auf eine Datei im Baum, um sie zu laden.')
        self._status_lbl.setStyleSheet('color: #888; padding: 2px 0;')
        self._row_count_lbl.setText('0 Eintraege')
        self._title_lbl.setText(f'Dienstplan {self._pane_index + 1}')

    # ---------- UI ----------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Header-Zeile: Titel + Export-Button + Schliessen
        self._header_bar = QWidget()
        header_layout = QHBoxLayout(self._header_bar)
        header_layout.setContentsMargins(6, 3, 4, 3)
        header_layout.setSpacing(4)

        self._title_lbl = QLabel(f'Dienstplan {self._pane_index + 1}')
        self._title_lbl.setFont(QFont('Arial', 11))
        header_layout.addWidget(self._title_lbl)
        header_layout.addStretch()

        self._export_btn = QPushButton('Fuer Export auswaehlen')
        self._export_btn.setFixedHeight(22)
        self._export_btn.setToolTip('Diesen Dienstplan-Tab für den Stundenlisten-Export auswählen')
        self._export_btn.setStyleSheet(
            'font-size: 10px; padding: 0 6px; border-radius: 3px; '
            f'background: {FIORI_BLUE}; color: white; border: none;'
        )
        self._export_btn.clicked.connect(lambda: self.export_selected.emit(self._pane_index))
        header_layout.addWidget(self._export_btn)

        self._excel_open_btn = QPushButton('📊 In Excel öffnen')
        self._excel_open_btn.setFixedHeight(22)
        self._excel_open_btn.setEnabled(False)
        self._excel_open_btn.setToolTip('Dienstplan-Excel-Datei in Excel öffnen')
        self._excel_open_btn.setStyleSheet(
            'font-size: 10px; padding: 0 6px; border-radius: 3px; '
            'background: #107e3e; color: white; border: none;'
        )
        self._excel_open_btn.clicked.connect(self._open_in_excel)
        header_layout.addWidget(self._excel_open_btn)

        self._close_btn = QPushButton('X')
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.setStyleSheet(
            'font-size: 10px; font-weight: bold; padding: 0; border-radius: 3px; '
            'background: #c0392b; color: white; border: none;'
        )
        self._close_btn.setToolTip('Dienstplan schliessen')
        self._close_btn.clicked.connect(self._on_close_clicked)
        header_layout.addWidget(self._close_btn)

        self._update_header_style()
        layout.addWidget(self._header_bar)

        # Hauptinhalt
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 2, 4, 4)
        content_layout.setSpacing(3)
        layout.addWidget(content, 1)

        # Ersetzt layout durch content_layout fuer den Rest der UI
        layout = content_layout

        self._datum_lbl = QLabel('')
        self._datum_lbl.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        self._datum_lbl.setStyleSheet(f'color: {FIORI_TEXT}; padding: 2px 0;')
        self._datum_lbl.setVisible(False)
        layout.addWidget(self._datum_lbl)

        self._status_lbl = QLabel('Doppelklick auf eine Datei im Baum, um sie zu laden.')
        self._status_lbl.setFont(QFont('Arial', 9))
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet('color: #888; padding: 1px 0;')
        layout.addWidget(self._status_lbl)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            'Kategorie', 'Name', 'Dienst', 'Von', 'Bis'
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setMinimumSectionSize(40)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(18)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.itemDoubleClicked.connect(self._on_table_double_click)
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                gridline-color: #e8ecf0;
            }
            QTableWidget::item { padding: 0px 4px; }
            QHeaderView::section {
                background-color: #f0f4f8;
                border: none;
                border-bottom: 1px solid #c8d4e0;
                padding: 2px 4px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self._table, 1)

        self._row_count_lbl = QLabel('0 Eintraege')
        self._row_count_lbl.setFont(QFont('Arial', 9))
        self._row_count_lbl.setWordWrap(True)
        self._row_count_lbl.setStyleSheet('color: #888;')
        layout.addWidget(self._row_count_lbl)

    def _on_close_clicked(self):
        """Pane leeren und ausblenden (ausser Pane 0 - wird nur geleert)."""
        self.clear()
        if self._pane_index > 0:
            self.setVisible(False)

    # ---------- Laden ----------

    def _open_in_excel(self):
        """Geladene Dienstplan-Excel-Datei direkt in Excel öffnen."""
        if not self._excel_path or not os.path.isfile(self._excel_path):
            QMessageBox.warning(self, 'Nicht verfügbar', 'Datei nicht gefunden.')
            return
        try:
            os.startfile(self._excel_path)
        except Exception as exc:
            QMessageBox.critical(self, 'Fehler', f'Datei konnte nicht geöffnet werden:\n{exc}')

    def load(self, path: str) -> bool:
        """Excel-Datei einlesen und Tabelle befüllen. Gibt True bei Erfolg zurück."""
        self._status_lbl.setText(' Datei wird eingelesen ...')
        self._status_lbl.setStyleSheet('color: #555; padding: 2px 0;')
        self._status_lbl.repaint()

        try:
            from functions.dienstplan_parser import DienstplanParser

            display_result = DienstplanParser(path, alle_anzeigen=True).parse()
            export_result  = DienstplanParser(path, alle_anzeigen=False).parse()

            if not display_result['success']:
                QMessageBox.critical(
                    self, 'Fehler beim Einlesen',
                    f"Die Datei konnte nicht geparst werden:\n\n{display_result['error']}"
                )
                self._status_lbl.setText('Fehler: Fehler beim Einlesen.')
                self._status_lbl.setStyleSheet('color: #bb0000; padding: 2px 0;')
                return False

            self._excel_path   = path
            self._display_data = display_result
            self._parsed_data  = export_result
            self._excel_open_btn.setEnabled(True)

            # Dateiname im Header anzeigen
            dateiname = os.path.basename(path)
            self._title_lbl.setText(dateiname)

            datum = display_result.get('datum')
            if datum:
                self._datum_lbl.setText(f'Datum: {datum}')
                self._datum_lbl.setVisible(True)
            else:
                self._datum_lbl.setVisible(False)

            self._render_table_parsed(display_result)

            unbekannte = display_result.get('unbekannte_dienste', [])
            if unbekannte:
                QMessageBox.warning(
                    self, 'Unbekannte Dienst-Kürzel',
                    'Folgende Dienst-Kürzel wurden nicht erkannt:\n'
                    + '\n'.join(f'  - {d}' for d in sorted(unbekannte))
                    + '\n\nSie werden trotzdem angezeigt.'
                )

            self._status_lbl.setText(f'Geladen: {dateiname}')
            self._status_lbl.setStyleSheet('color: #107e3e; padding: 2px 0;')
            return True

        except Exception as e:
            QMessageBox.critical(self, 'Fehler', f'Unerwarteter Fehler:\n{e}')
            self._status_lbl.setText(f'Fehler: {e}')
            self._status_lbl.setStyleSheet('color: #bb0000; padding: 2px 0;')
            return False

    # ---------- Tabelle rendern ----------

    def _render_table_parsed(self, data: dict):
        """Tabelleninhalt aus geparsten Excel-Daten aufbauen."""
        tag_personen   = []
        nacht_personen = []
        sonst_personen = []

        # Namen die als Stationsleitung angezeigt werden (Kleinbuchstaben)
        STATIONSLEITUNG = {'lars peters'}

        for kat, liste in (('Dispo', data.get('dispo', [])),
                           ('Betreuer', data.get('betreuer', []))):
            for p in liste:
                name_lower = p.get('vollname', '').strip().lower()
                effekt_kat = 'Stationsleitung' if name_lower in STATIONSLEITUNG else kat
                dk = (p.get('dienst_kategorie') or '').upper()
                if dk in _TAG_DIENSTE:
                    tag_personen.append((effekt_kat, p))
                elif dk in _NACHT_DIENSTE:
                    nacht_personen.append((effekt_kat, p))
                else:
                    sonst_personen.append((effekt_kat, p))

        # ── Kranke Mitarbeiter nach Schichttyp + Dispo/Betreuer gruppieren ──────────
        krank_tag_dispo    = []
        krank_tag_betr     = []
        krank_nacht_dispo  = []
        krank_nacht_betr   = []
        krank_sonder       = []

        for p in data.get('kranke', []):
            stype = p.get('krank_schicht_typ') or 'sonderdienst'
            is_d  = p.get('krank_ist_dispo', False)
            if stype == 'tagdienst':
                if is_d:
                    krank_tag_dispo.append(p)
                else:
                    krank_tag_betr.append(p)
            elif stype == 'nachtdienst':
                if is_d:
                    krank_nacht_dispo.append(p)
                else:
                    krank_nacht_betr.append(p)
            else:
                krank_sonder.append(p)

        # Krank-Abschnitte: Dispo zuerst, dann Betreuer
        krank_tag_personen   = [('KrankDispo', p) for p in krank_tag_dispo]   + \
                               [('Krank',      p) for p in krank_tag_betr]
        krank_nacht_personen = [('KrankDispo', p) for p in krank_nacht_dispo] + \
                               [('Krank',      p) for p in krank_nacht_betr]
        krank_sonder_personen = [('Krank',     p) for p in krank_sonder]

        abschnitte = []
        if tag_personen:
            abschnitte.append(('Tagdienst',         '#1565a8', '#ffffff', tag_personen))
        if nacht_personen:
            abschnitte.append(('Nachtdienst',       '#0d2b4a', '#e8eeff', nacht_personen))
        if sonst_personen:
            abschnitte.append(('Sonstige',          '#555555', '#ffffff', sonst_personen))
        if krank_tag_personen:
            abschnitte.append(('Krank – Tagdienst',  '#8b0000', '#ffe8e8', krank_tag_personen))
        if krank_nacht_personen:
            abschnitte.append(('Krank – Nachtdienst','#5a0000', '#f5d0d0', krank_nacht_personen))
        if krank_sonder_personen:
            abschnitte.append(('Krank – Sonderdienst','#6b3300', '#fdebd0', krank_sonder_personen))

        total_rows = sum(1 + len(personen) for _, _, _, personen in abschnitte)
        self._table.clearSpans()
        self._table.setRowCount(total_rows)

        farben = {
            'Dispo':           QColor('#dce8f5'),
            'Betreuer':        QColor('#ffffff'),
            'Stationsleitung': QColor('#fff8e1'),
            'Krank':           QColor('#fce8e8'),
            'KrankDispo':      QColor('#f0d0d0'),   # Dispo-Krank: etwas dunkler
        }
        text_farben = {
            'Dispo':           QColor('#0a5ba4'),
            'Betreuer':        QColor('#1a1a1a'),
            'Stationsleitung': QColor('#7a5000'),
            'Krank':           QColor('#bb0000'),
            'KrankDispo':      QColor('#7a0000'),   # dunkler Rotton für Dispo-Krank
        }

        self._table_row_data = []
        row = 0
        sep_font = QFont('Arial', 11, QFont.Weight.Bold)
        for label_text, hdr_bg, hdr_fg, personen in abschnitte:
            self._table_row_data.append(None)
            self._table.setSpan(row, 0, 1, 5)
            sep_item = QTableWidgetItem(label_text)
            sep_item.setBackground(QColor(hdr_bg))
            sep_item.setForeground(QColor(hdr_fg))
            sep_item.setFont(sep_font)
            sep_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(row, 0, sep_item)
            self._table.verticalHeader().resizeSection(row, 24)
            row += 1

            for kategorie, p in personen:
                self._table_row_data.append(p)
                bg = farben.get(kategorie, QColor('#ffffff'))
                fg = text_farben.get(kategorie, QColor('#1a1a1a'))

                # Spalte 0: Kategorie-Anzeige (für Krank: Dispo/Betreuer)
                if kategorie == 'KrankDispo':
                    kat_anzeige = 'Dispo'
                elif kategorie == 'Krank':
                    kat_anzeige = 'Betreuer'
                else:
                    kat_anzeige = kategorie

                # Spalte 2: Dienst-Kürzel – bei Kranken den abgeleiteten Wert zeigen
                if p.get('ist_krank'):
                    dienst_anzeige = p.get('krank_abgeleiteter_dienst') or ''
                else:
                    dienst_anzeige = p.get('dienst_kategorie') or ''

                vals = [
                    kat_anzeige,
                    p.get('anzeigename', ''),
                    dienst_anzeige,
                    p.get('start_zeit', '') or '',
                    p.get('end_zeit',   '') or '',
                ]
                for col, val in enumerate(vals):
                    item = QTableWidgetItem(val)
                    item.setBackground(bg)
                    item.setForeground(fg)
                    self._table.setItem(row, col, item)

                if p.get('ist_bulmorfahrer'):
                    for col in range(5):
                        self._table.item(row, col).setBackground(QColor('#fff3b0'))
                row += 1

        # ── Statuszeile ───────────────────────────────────────────────────
        tag_n   = len(tag_personen)
        nacht_n = len(nacht_personen)
        sonst_n = len(sonst_personen)

        # Tagdienst: Dispo / Betreuer trennen
        tag_dispo_n  = sum(1 for kat, _ in tag_personen   if kat == 'Dispo')
        tag_betr_n   = tag_n - tag_dispo_n

        # Nachtdienst: Dispo / Betreuer trennen
        nacht_dispo_n = sum(1 for kat, _ in nacht_personen if kat == 'Dispo')
        nacht_betr_n  = nacht_n - nacht_dispo_n

        # Krank-Zählung getrennt nach Dispo / Betreuer / Sonder
        n_kd_tag   = len(krank_tag_dispo)
        n_kb_tag   = len(krank_tag_betr)
        n_kd_nacht = len(krank_nacht_dispo)
        n_kb_nacht = len(krank_nacht_betr)
        n_k_sonder = len(krank_sonder)
        krank_gesamt = n_kd_tag + n_kb_tag + n_kd_nacht + n_kb_nacht + n_k_sonder

        teile = []
        if tag_n:
            tag_sub = []
            if tag_betr_n:  tag_sub.append(f'Betreuer {tag_betr_n}')
            if tag_dispo_n: tag_sub.append(f'Dispo {tag_dispo_n}')
            teile.append(f'{tag_n} Tagdienst ({", ".join(tag_sub)})' if tag_sub else f'{tag_n} Tagdienst')
        if nacht_n:
            nacht_sub = []
            if nacht_betr_n:  nacht_sub.append(f'Betreuer {nacht_betr_n}')
            if nacht_dispo_n: nacht_sub.append(f'Dispo {nacht_dispo_n}')
            teile.append(f'{nacht_n} Nachtdienst ({", ".join(nacht_sub)})' if nacht_sub else f'{nacht_n} Nachtdienst')
        if sonst_n: teile.append(f'{sonst_n} Sonstige')

        if krank_gesamt:
            # Betreuer-Block
            betr_teile = []
            if n_kb_tag:   betr_teile.append(f'{n_kb_tag} Tag')
            if n_kb_nacht: betr_teile.append(f'{n_kb_nacht} Nacht')
            if n_k_sonder: betr_teile.append(f'{n_k_sonder} Sonder')
            betr_gesamt = n_kb_tag + n_kb_nacht + n_k_sonder

            # Dispo-Block
            dispo_teile = []
            if n_kd_tag:   dispo_teile.append(f'{n_kd_tag} Tag')
            if n_kd_nacht: dispo_teile.append(f'{n_kd_nacht} Nacht')
            dispo_gesamt = n_kd_tag + n_kd_nacht

            krank_blocks = []
            if betr_gesamt:
                krank_blocks.append(
                    f'Betreuer {betr_gesamt} ({" / ".join(betr_teile)})'
                )
            if dispo_gesamt:
                krank_blocks.append(
                    f'Dispo {dispo_gesamt} ({" / ".join(dispo_teile)})'
                )
            teile.append(f'{krank_gesamt} Krank  –  {" | ".join(krank_blocks)}')

        self._row_count_lbl.setText('  |  '.join(teile) if teile else '0 Eintraege')
        self._row_count_lbl.setStyleSheet('color: #555; font-weight: bold; padding: 2px 0;')

    # ---------- Doppelklick Tabellenzeile ----------

    def _on_table_double_click(self, item):
        """Ã–ffnet Edit-Dialog, speichert Ã„nderungen in Excel und lädt neu."""
        row = item.row()
        if row < 0 or row >= len(self._table_row_data):
            return
        person = self._table_row_data[row]
        if person is None:
            return
        if not self._display_data:
            return

        dlg = EditDienstDialog(person, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.result_data:
            return

        res = dlg.result_data
        try:
            self._save_to_excel(person, res['dienst'], res['von'], res['bis'])
        except Exception as e:
            QMessageBox.critical(
                self, 'Fehler beim Speichern',
                f'Die Excel-Datei konnte nicht gespeichert werden:\n{e}'
            )
            return

        excel_path = self._display_data.get('excel_path', '')
        if not excel_path:
            return
        try:
            from functions.dienstplan_parser import DienstplanParser
            display_result = DienstplanParser(excel_path, alle_anzeigen=True).parse()
            export_result  = DienstplanParser(excel_path, alle_anzeigen=False).parse()
            if display_result['success']:
                self._display_data = display_result
                self._parsed_data  = export_result
                datum = display_result.get('datum')
                if datum:
                    self._datum_lbl.setText(f'\U0001f4c5 Datum: {datum}')
                    self._datum_lbl.setVisible(True)
                self._render_table_parsed(display_result)
                self._status_lbl.setText(
                    f'\u2705 Gespeichert: {person.get("anzeigename", "")} -> {res["dienst"]}'
                    f'  \u26a0\ufe0f Andere Nutzer m\u00fcssen die Datei neu \u00f6ffnen, '
                    f'sonst werden die \u00c4nderungen \u00fcberschrieben!'
                )
                self._status_lbl.setStyleSheet('color: #b85c00; font-weight: bold; padding: 2px 0;')
        except Exception as e:
            QMessageBox.critical(self, 'Fehler', f'Fehler beim Neu-Laden:\n{e}')

    # ---------- Excel-Schutz ----------

    @staticmethod
    def _check_excel_locked(excel_path: str):
        """Prüft ob die Excel-Datei von einem anderen Programm geöffnet ist."""
        import os
        ordner     = os.path.dirname(excel_path)
        dateiname  = os.path.basename(excel_path)
        lock_datei = os.path.join(ordner, '~$' + dateiname)
        if os.path.exists(lock_datei):
            raise IOError(
                f'Die Excel-Datei ist zurzeit auf einem anderen PC oder in Excel '
                f'geöffnet:\n\n{dateiname}\n\n'
                f'Bitte die Datei dort schließen und dann erneut speichern.'
            )
        try:
            fh = open(excel_path, 'r+b')
            fh.close()
        except PermissionError:
            raise IOError(
                f'Die Excel-Datei ist gesperrt (kein Schreibzugriff):\n\n{dateiname}\n\n'
                f'Bitte sicherstellen, dass die Datei nicht anderweitig geöffnet ist.'
            )

    def _save_to_excel(self, person: dict, dienst: str, von: str, bis: str):
        """Schreibt Dienst/Von/Bis sicher in die Excel-Datei zurück (3-Ebenen-Schutz)."""
        import os
        import openpyxl
        from openpyxl.styles import PatternFill

        excel_path = (self._display_data or {}).get('excel_path', '')
        column_map = (self._display_data or {}).get('column_map', {})
        excel_row  = person.get('excel_row')
        if not excel_path or not column_map or not excel_row:
            raise ValueError('Excel-Pfad oder Zeilennummer nicht gefunden.')

        ordner    = os.path.dirname(excel_path)
        dateiname = os.path.basename(excel_path)
        temp_path = os.path.join(ordner, dateiname + '.nesk3tmp')
        nesk_lock = os.path.join(ordner, dateiname + '.nesk3lock')

        self._check_excel_locked(excel_path)

        if os.path.exists(nesk_lock):
            import time
            alter = time.time() - os.path.getmtime(nesk_lock)
            if alter < 30:
                raise IOError(
                    'Eine andere Nesk3-Instanz speichert gerade dieselbe Datei.\n'
                    'Bitte kurz warten und erneut versuchen.'
                )
            os.remove(nesk_lock)

        try:
            with open(nesk_lock, 'w') as lf:
                lf.write('nesk3')

            wb = openpyxl.load_workbook(excel_path)
            ws = wb.active

            dienst_cell = ws.cell(row=excel_row, column=column_map['dienst'] + 1)
            dienst_cell.value = dienst or None

            if dienst.upper() in ('KRANK', 'K'):
                dienst_cell.fill = PatternFill(patternType='solid', fgColor='FFFF0000')
            else:
                dienst_cell.fill = PatternFill(patternType='none')

            if column_map.get('beginn') is not None:
                ws.cell(row=excel_row, column=column_map['beginn'] + 1).value = \
                    self._parse_time_str(von)
            if column_map.get('ende') is not None:
                ws.cell(row=excel_row, column=column_map['ende'] + 1).value = \
                    self._parse_time_str(bis)

            wb.save(temp_path)
            wb.close()
            self._check_excel_locked(excel_path)
            os.replace(temp_path, excel_path)
            self._backup_excel_save(excel_path)

        finally:
            for f in (nesk_lock, temp_path):
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except OSError:
                    pass

    @staticmethod
    def _backup_excel_save(excel_path: str):
        """Erstellt nach jedem erfolgreichen Excel-Save eine Sicherungskopie."""
        import os, glob, shutil
        from datetime import datetime
        from config import BASE_DIR
        try:
            backup_dir = os.path.join(BASE_DIR, 'Backup Data', 'excel_saves')
            os.makedirs(backup_dir, exist_ok=True)
            name  = os.path.splitext(os.path.basename(excel_path))[0]
            datum = datetime.now().strftime('%Y%m%d_%H%M%S')
            dst   = os.path.join(backup_dir, f'{name}_{datum}.xlsx')
            shutil.copy2(excel_path, dst)
            alle = sorted(glob.glob(os.path.join(backup_dir, f'{name}_????????_??????.xlsx')))
            for alt in alle[:-20]:
                try:
                    os.remove(alt)
                except OSError:
                    pass
        except Exception:
            pass

    @staticmethod
    def _parse_time_str(s: str):
        """Wandelt 'HH:MM'-String in datetime.time um, oder gibt None zurück."""
        from datetime import time as dtime
        if not s or not s.strip():
            return None
        try:
            h, m = s.strip().split(':')
            return dtime(int(h), int(m))
        except Exception:
            return None


class DienstplanWidget(QWidget):
    MAX_PANES = 4   # bis zu 4 Dienstplaene nebeneinander

    def __init__(self, parent=None):
        super().__init__(parent)
        self._alle: list[Dienstplan]            = []
        self._fs_model: QFileSystemModel | None = None
        self._export_pane_idx: int              = 0   # Index der fuer Export aktiven Pane
        self._html_generiert:  bool             = False  # True nach erstem HTML-Export
        self._html_watcher = QFileSystemWatcher(parent=self)
        self._html_watcher.fileChanged.connect(self._on_excel_geaendert)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(8)

        # Titelzeile
        top = QHBoxLayout()
        title = QLabel("Dienstplan")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {FIORI_TEXT};")
        top.addWidget(title)
        top.addStretch()

        self._export_lbl = QLabel("")
        self._export_lbl.setFont(QFont("Arial", 10))
        self._export_lbl.setStyleSheet("color: #888;")
        top.addWidget(self._export_lbl)
        top.addSpacing(8)

        word_btn = QPushButton("Word exportieren")
        word_btn.setMinimumHeight(36)
        word_btn.setToolTip("Stärkemeldung als Word-Dokument exportieren und öffnen")
        word_btn.setStyleSheet(
            f"background-color: {FIORI_BLUE}; color: white; "
            f"border-radius: 4px; padding: 0 12px;"
        )
        word_btn.clicked.connect(self._word_exportieren)
        top.addWidget(word_btn)

        html_btn = QPushButton("🌐  Als Webseite anzeigen")
        html_btn.setMinimumHeight(36)
        html_btn.setToolTip(
            "Dienstplan als HTML-Seite generieren und im Browser öffnen.\n"
            "Die Seite wird automatisch neu erzeugt, wenn sich die Excel-Datei ändert."
        )
        html_btn.setStyleSheet(
            "background-color: #1e7e34; color: white; "
            "border-radius: 4px; padding: 0 12px;"
        )
        html_btn.clicked.connect(self._html_exportieren)
        top.addWidget(html_btn)

        reload_btn = QPushButton("Neu laden")
        reload_btn.setToolTip("Ordner-Ansicht neu laden")
        reload_btn.setMinimumHeight(36)
        reload_btn.clicked.connect(self.reload_tree)
        top.addWidget(reload_btn)

        outer.addLayout(top)

        # Info-Banner: Mehrere Dienstpläne gleichzeitig
        info_banner = QLabel(
            "ℹ️   Bis zu 4 Dienstpläne gleichzeitig öffnen: "
            "Klicken Sie im Dateibaum links auf eine Excel-Datei – "
            "jede Datei erscheint als eigene Spalte nebeneinander. "
            "Um eine Datei für den Word-Export auszuwählen, klicken Sie in der "
            "jeweiligen Spalte auf die Schaltfläche \"Hier klicken um Datei als Wordexport auszuwählen\"."
        )
        info_banner.setWordWrap(True)
        info_banner.setStyleSheet(
            "background-color: #e8f0fb; border: 1px solid #b0c8f0; "
            "border-radius: 6px; padding: 8px 14px; color: #1a4a8a; font-size: 12px;"
        )
        outer.addWidget(info_banner)

        # Splitter: Dateibaum links | Panes rechts
        outer_splitter = QSplitter(Qt.Orientation.Horizontal)
        outer_splitter.setHandleWidth(4)

        # Linke Seite: Dateibaum
        tree_panel = QWidget()
        tree_panel.setMinimumWidth(180)
        tree_panel.setMaximumWidth(340)
        tree_layout = QVBoxLayout(tree_panel)
        tree_layout.setContentsMargins(0, 0, 6, 0)
        tree_layout.setSpacing(4)

        tree_header = QLabel("Dienstplaene")
        tree_header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        tree_header.setStyleSheet(f"color: {FIORI_TEXT}; padding: 4px 0;")
        tree_layout.addWidget(tree_header)

        self._manuell_btn = QPushButton("📂  Datei öffnen ...")
        self._manuell_btn.setFixedHeight(28)
        self._manuell_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._manuell_btn.setToolTip(
            "Excel-Dienstplan manuell auswählen (ohne Ordner-Konfiguration)"
        )
        self._manuell_btn.setStyleSheet(
            f"QPushButton {{font-size:10px; padding: 2px 8px; border-radius:4px;"
            f"background:{FIORI_BLUE}; color:white; border:none;}}"
            f"QPushButton:hover {{background:#0855a9;}}"
        )
        self._manuell_btn.clicked.connect(self._manuell_datei_oeffnen)
        tree_layout.addWidget(self._manuell_btn)

        self._tree = QTreeView()
        self._tree.setStyleSheet("""
            QTreeView {
                background-color: white;
                border: 1px solid #dce8f5;
                border-radius: 6px;
                font-size: 12px;
            }
            QTreeView::item { padding: 3px 2px; }
            QTreeView::item:selected { background-color: #dce8f5; color: #0a5ba4; }
            QTreeView::item:hover    { background-color: #f0f4f8; }
        """)
        self._tree.setAnimated(True)
        self._tree.setSortingEnabled(True)
        self._tree.activated.connect(self._on_tree_activated)
        tree_layout.addWidget(self._tree, 1)

        self._ordner_lbl = QLabel("")
        self._ordner_lbl.setWordWrap(True)
        self._ordner_lbl.setStyleSheet("color: #aaa; font-size: 9px; padding: 2px;")
        tree_layout.addWidget(self._ordner_lbl)

        outer_splitter.addWidget(tree_panel)

        # Rechte Seite: horizontaler Splitter mit bis zu MAX_PANES Panes
        self._pane_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._pane_splitter.setHandleWidth(6)

        self._panes: list[_DienstplanPane] = []
        for i in range(self.MAX_PANES):
            pane = _DienstplanPane(pane_index=i)
            pane.export_selected.connect(self._set_export_pane)
            self._panes.append(pane)
            self._pane_splitter.addWidget(pane)

        # Beim Start nur 1 Pane sichtbar
        for i in range(1, self.MAX_PANES):
            self._panes[i].setVisible(False)

        outer_splitter.addWidget(self._pane_splitter)
        outer_splitter.setSizes([240, 900])
        outer.addWidget(outer_splitter, 1)

        # Export-Pane initial markieren
        self._set_export_pane(0)
        self._setup_tree()

    # ------------------------------------------------------------------
    # Dateibaum
    # ------------------------------------------------------------------

    def _setup_tree(self):
        """Dateibaum fuer den konfigurierten Ordner aufbauen."""
        try:
            from functions.settings_functions import get_setting
            ordner = get_setting('dienstplan_ordner')
        except Exception:
            ordner = ''

        if not ordner or not os.path.isdir(ordner):
            self._ordner_lbl.setText(
                "Kein gueltiger Ordner konfiguriert.\n"
                "Bitte unter Einstellungen einen Ordner festlegen."
            )
            self._ordner_lbl.setStyleSheet("color: #bb6600; font-size: 10px; padding: 4px;")
            return

        self._fs_model = QFileSystemModel(self)
        self._fs_model.setNameFilters(['*.xlsx', '*.xls'])
        self._fs_model.setNameFilterDisables(False)
        root_idx = self._fs_model.setRootPath(ordner)

        self._tree.setModel(self._fs_model)
        self._tree.setRootIndex(root_idx)

        for col in range(1, 4):
            self._tree.hideColumn(col)
        self._tree.header().setVisible(False)

        self._ordner_lbl.setText(ordner)
        self._ordner_lbl.setStyleSheet("color: #aaa; font-size: 9px; padding: 2px;")

    def reload_tree(self):
        """Ordner-Konfiguration neu lesen und Baum neu aufbauen."""
        if self._fs_model is not None:
            self._tree.setModel(None)
            self._fs_model.deleteLater()
            self._fs_model = None
        self._ordner_lbl.setText("")
        self._setup_tree()

    def _on_tree_activated(self, index):
        """Eintrag im Baum aktiviert (Enter / Doppelklick)."""
        if self._fs_model is None:
            return
        path = self._fs_model.filePath(index)
        if os.path.isfile(path) and path.lower().endswith(('.xlsx', '.xls')):
            self._open_in_next_pane(path)

    def _manuell_datei_oeffnen(self):
        """Öffnet einen Datei-Dialog und lädt die gewählte Datei in die nächste freie Pane."""
        try:
            from functions.settings_functions import get_setting
            start_dir = get_setting('dienstplan_ordner') or os.path.expanduser('~')
        except Exception:
            start_dir = os.path.expanduser('~')
        path, _ = QFileDialog.getOpenFileName(
            self, "Dienstplan-Excel öffnen", start_dir,
            "Excel-Dateien (*.xlsx *.xls)"
        )
        if path:
            self._open_in_next_pane(path)

    # ------------------------------------------------------------------
    # Pane-Verwaltung
    # ------------------------------------------------------------------

    def _set_export_pane(self, idx: int):
        """Markiert Pane idx als aktiv fuer den Word-Export."""
        self._export_pane_idx = idx
        for i, pane in enumerate(self._panes):
            pane.set_export_active(i == idx)
        # Titelzeile aktualisieren
        pane = self._panes[idx]
        if not pane.is_empty:
            name = os.path.basename(pane.excel_path)
            self._export_lbl.setText(f"Export: {name}")
            self._export_lbl.setStyleSheet(
                "color: #0a5ba4; font-weight: bold; "
                "background: #dce8f5; border-radius: 4px; padding: 2px 6px;"
            )
        else:
            self._export_lbl.setText("")

    def _export_pane(self) -> '_DienstplanPane':
        return self._panes[self._export_pane_idx]

    def _open_in_next_pane(self, path: str):
        """
        Datei in der naechsten freien Pane oeffnen.
        Bereits geoeffnet -> neu laden.
        Alle 4 voll -> erste Pane ersetzen.
        """
        # Bereits geoeffnet?
        for i, pane in enumerate(self._panes):
            if pane.excel_path == path:
                pane.load(path)
                self._set_export_pane(i)
                return

        # Naechste freie sichtbare Pane
        for i, pane in enumerate(self._panes):
            if pane.isVisible() and pane.is_empty:
                pane.load(path)
                self._set_export_pane(i)
                # Naechste Pane sichtbar machen (fuer naechsten Ladevorgang)
                next_idx = i + 1
                if next_idx < self.MAX_PANES:
                    self._panes[next_idx].setVisible(True)
                    self._pane_splitter.setSizes(
                        [1] * (next_idx + 1) + [0] * (self.MAX_PANES - next_idx - 1)
                    )
                return

        # Alle sichtbaren Panes belegt → neue Pane oeffnen wenn moeglich
        visible_count = sum(1 for p in self._panes if p.isVisible())
        if visible_count < self.MAX_PANES:
            pane = self._panes[visible_count]
            pane.setVisible(True)
            pane.load(path)
            self._set_export_pane(visible_count)
            self._pane_splitter.setSizes([1] * (visible_count + 1) + [0] * (self.MAX_PANES - visible_count - 1))
            return

        # Alle 4 Panes belegt → Export-Pane ersetzen
        pane = self._panes[self._export_pane_idx]
        pane.load(path)
        self._set_export_pane(self._export_pane_idx)

    def _watch_excel(self, path: str):
        """Fügt eine Excel-Datei dem Datei-Watcher hinzu (einmalig)."""
        if path and path not in self._html_watcher.files():
            self._html_watcher.addPath(path)

    def _on_excel_geaendert(self, path: str):
        """
        Wird aufgerufen wenn eine geladene Excel-Datei auf der Festplatte
        geändert wird. Erzeugt die HTML-Seite neu – aber nur wenn der
        Benutzer sie mindestens einmal manuell generiert hat.
        """
        if not self._html_generiert:
            return
        # Kleines Delay: Excel schreibt manchmal in mehreren Schritten
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self._html_auto_update(path))

    def _html_auto_update(self, path: str):
        """Stille automatische HTML-Aktualisierung nach Dateiänderung."""
        # Passende Pane suchen
        for pane in self._panes:
            if pane.excel_path == path and pane._display_data:
                try:
                    from functions.dienstplan_parser import DienstplanParser
                    result = DienstplanParser(path, alle_anzeigen=True).parse()
                    if not result.get('success'):
                        return
                    from functions.dienstplan_html_export import generiere_html
                    generiere_html(result)
                    # Status-Zeile aktualisieren
                    from datetime import datetime as _dt
                    pane._status_lbl.setText(
                        f'🌐 Webseite automatisch aktualisiert – {_dt.now().strftime("%H:%M:%S")}'
                    )
                    pane._status_lbl.setStyleSheet('color: #1e7e34; font-weight: bold; padding: 2px 0;')
                except Exception:
                    pass
                return

    # ------------------------------------------------------------------
    # Datenladen
    # ------------------------------------------------------------------

    def refresh(self):
        self._alle = []
        for pane in self._panes:
            pane.clear()
        self._set_export_pane(0)
        self._html_generiert = False

    # ------------------------------------------------------------------
    # HTML-Export (Webseite)
    # ------------------------------------------------------------------

    def _html_exportieren(self):
        """Generatert die HTML-Ansicht des aktiven Export-Dienstplans und öffnet sie im Browser."""
        pane = self._export_pane()
        if pane._display_data is None:
            QMessageBox.information(
                self, "Kein Dienstplan",
                "Bitte zuerst eine Excel-Datei im Dateibaum laden (Doppelklick)."
            )
            return
        try:
            from functions.dienstplan_html_export import generiere_html, html_pfad
            pfad = generiere_html(pane._display_data)
            self._html_generiert = True

            # Excel in Watcher aufnehmen für automatische Aktualisierung
            self._watch_excel(pane.excel_path)

            # Im Standard-Browser öffnen
            import webbrowser
            url = "file:///" + pfad.replace("\\", "/")
            webbrowser.open(url)

            pane._status_lbl.setText(
                f'🌐 Webseite generiert – {os.path.basename(pfad)}'
            )
            pane._status_lbl.setStyleSheet('color: #1e7e34; font-weight: bold; padding: 2px 0;')

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim HTML-Export", f"Fehler:\n{e}")

    # ------------------------------------------------------------------
    # Word-Export
    # ------------------------------------------------------------------

    def _word_exportieren(self):
        pane = self._export_pane()
        if pane.parsed_data is None:
            QMessageBox.information(
                self, "Kein Dienstplan",
                "Bitte zuerst eine Datei im Dateibaum auswaehlen (Doppelklick)."
            )
            return

        # ── Schritt 1: Dispo-Zeiten Vorschau / Bearbeitung ──────────────────
        # Roh-Zeiten aus Excel ohne jede Rundung für die Vergleichsspalten
        try:
            from functions.dienstplan_parser import DienstplanParser
            raw_result = DienstplanParser(
                pane.excel_path, alle_anzeigen=True, round_dispo=False
            ).parse()
            raw_data = raw_result if raw_result.get('success') else None
        except Exception:
            raw_data = None

        vorschau = _DispoZeitenVorschauDialog(pane.parsed_data, raw_data=raw_data, parent=self)
        if vorschau.exec() != QDialog.DialogCode.Accepted:
            return
        export_data = vorschau.modified_data

        # ── Schritt 2: Export-Einstellungen (Zeitraum, PAX, Pfad ...) ────────
        dlg = ExportDialog(parsed_data=export_data, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.result:
            return

        params = dlg.result
        try:
            from functions.staerkemeldung_export import StaerkemeldungExport
            exporter = StaerkemeldungExport(
                dienstplan_data           = export_data,
                ausgabe_pfad              = params['ausgabe_pfad'],
                von_datum                 = params['von_datum'],
                bis_datum                 = params['bis_datum'],
                pax_zahl                  = params['pax_zahl'],
                ausgeschlossene_vollnamen  = params.get('ausgeschlossene_vollnamen', set()),
            )
            pfad, warnungen = exporter.export()

            if warnungen:
                QMessageBox.warning(
                    self, "Hinweise",
                    "Export abgeschlossen mit Hinweisen:\n\n" + "\n".join(warnungen)
                )

            antwort = QMessageBox.question(
                self, "Export erfolgreich",
                f"Stärkemeldung gespeichert unter:\n{pfad}\n\nJetzt in Word öffnen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if antwort == QMessageBox.StandardButton.Yes:
                os.startfile(pfad)

            # Nochmal nach anderem Speicherort fragen (z.B. für E-Mail-Anhang)
            kopie_pfad, _ = QFileDialog.getSaveFileName(
                self,
                "Kopie speichern unter …",
                pfad,
                "Word-Dokumente (*.docx)",
            )
            if kopie_pfad:
                import shutil
                shutil.copy2(pfad, kopie_pfad)

            pane._status_lbl.setText(f"Word-Export: {os.path.basename(pfad)}")
            pane._status_lbl.setStyleSheet("color: #107e3e; padding: 2px 0;")

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Export", f"Fehler:\n{e}")

    # ------------------------------------------------------------------
    # Stubs (DB-Anbindung folgt)
    # ------------------------------------------------------------------

    def _render_table(self, schichten: list[Dienstplan]):
        pass

    def _get_selected_id(self) -> int | None:
        return None

    def _add_schicht(self):
        pass

    def _edit_schicht(self):
        pass

    def _delete_schicht(self):
        pass
