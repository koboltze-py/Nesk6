"""
Telefonnummern-Widget
Verzeichnis aller Telefonnummern, eingelesen aus Excel-Dateien.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QMessageBox, QApplication, QSizePolicy,
    QDialog, QFormLayout, QDialogButtonBox, QTextEdit, QTabWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from config import FIORI_BLUE, FIORI_TEXT, BASE_DIR

from functions.telefonnummern_db import (
    importiere_aus_excel,
    lade_telefonnummern,
    lade_kategorien,
    lade_quellen,
    lade_sheets,
    letzter_import,
    ist_db_leer,
    hat_veraltete_daten,
    eintrag_speichern,
    eintrag_loeschen,
)


# ──────────────────────────────────────────────────────────────────────────────
#  Hilfsfunktionen
# ──────────────────────────────────────────────────────────────────────────────

def _btn(text: str, color: str = FIORI_BLUE, hover: str = "#0057b8") -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(32)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {color}; color: white; border: none;
            border-radius: 4px; padding: 4px 14px; font-size: 12px;
        }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:disabled {{ background: #bbb; color: #888; }}
    """)
    return btn


def _btn_light(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(32)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton { background:#eee; color:#333; border:none;
            border-radius:4px; padding:4px 14px; font-size:12px; }
        QPushButton:hover { background:#ddd; }
        QPushButton:disabled { background:#f5f5f5; color:#bbb; }
    """)
    return btn


# ──────────────────────────────────────────────────────────────────────────────
#  Manueller Eintrag-Dialog
# ──────────────────────────────────────────────────────────────────────────────

class _EintragDialog(QDialog):
    _FIELD_STYLE = (
        "QLineEdit, QTextEdit, QComboBox {"
        "border:1px solid #ccc; border-radius:4px; padding:4px;"
        "font-size:12px; background:white;}"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telefoneintrag hinzufügen")
        self.setMinimumWidth(420)
        self.setStyleSheet(self._FIELD_STYLE)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self._f_kat  = QLineEdit()
        self._f_bez  = QLineEdit()
        self._f_nr   = QLineEdit()
        self._f_mail = QLineEdit()
        self._f_bem  = QTextEdit()
        self._f_bem.setFixedHeight(60)

        self._f_kat.setPlaceholderText("z.B. DRK, FKB, Gates B …")
        self._f_bez.setPlaceholderText("Name oder Bezeichnung")
        self._f_nr.setPlaceholderText("Telefonnummer")
        self._f_mail.setPlaceholderText("E-Mail (optional)")

        form.addRow("Kategorie:", self._f_kat)
        form.addRow("Bezeichnung *:", self._f_bez)
        form.addRow("Nummer:", self._f_nr)
        form.addRow("E-Mail:", self._f_mail)
        form.addRow("Bemerkung:", self._f_bem)
        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _accept(self):
        if not self._f_bez.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Bezeichnung eingeben.")
            return
        self.accept()

    def get_daten(self) -> dict:
        return {
            "kategorie":   self._f_kat.text().strip(),
            "bezeichnung": self._f_bez.text().strip(),
            "nummer":      self._f_nr.text().strip(),
            "email":       self._f_mail.text().strip(),
            "bemerkung":   self._f_bem.toPlainText().strip(),
            "quelle":      "Manuell",
            "sheet":       "Manuell",
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Haupt-Widget
# ──────────────────────────────────────────────────────────────────────────────

class TelefonnummernWidget(QWidget):
    """Telefonnummern-Verzeichnis aus Excel-Import, organisiert in Tabs."""

    # (Tab-Label, sheet-Filter – None = alle)
    _TABS = [
        ("🔍  Alle",             None),
        ("📋  Kontakte",         "Kontakte"),
        ("🏪  Check-In (CIC)",   "Check-In (CIC)"),
        ("🚪  Interne & Gate",   "Interne & Gate"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tables:   dict[int, QTableWidget] = {}
        self._eintraege: dict[int, list[dict]]  = {}
        self._build_ui()
        self._auto_import_if_needed()

    def _auto_import_if_needed(self):
        """Importiert Excel beim ersten Start oder wenn alte Kategorienamen vorhanden sind."""
        try:
            if ist_db_leer() or hat_veraltete_daten():
                n = importiere_aus_excel(clear_first=True)
                self._status_lbl.setText(f"✅  Import: {n} Einträge geladen.")
        except Exception as exc:
            self._status_lbl.setText(f"⚠️  Import fehlgeschlagen: {exc}")
        self._aktualisiere_kat_filter()
        self._lade()

    # ── UI aufbauen ────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # ── Titelzeile ─────────────────────────────────────────────────────────
        titel_lbl = QLabel("📞  Telefonnummern-Verzeichnis")
        titel_lbl.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        titel_lbl.setStyleSheet(f"color:{FIORI_TEXT}; padding: 4px 0;")
        layout.addWidget(titel_lbl)

        hinweis_lbl = QLabel("Aus Excel-Dateien importierte Telefonnummern – FKB & DRK Köln")
        hinweis_lbl.setStyleSheet("color:#666; font-size:11px; font-style:italic;")
        layout.addWidget(hinweis_lbl)

        # ── Filterleiste ───────────────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame{background:#f8f9fa;border:1px solid #ddd;"
            "border-radius:4px;padding:4px;}"
        )
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(10)

        fl.addWidget(QLabel("Suche:"))
        self._suche = QLineEdit()
        self._suche.setPlaceholderText("Name, Nummer, Abteilung …")
        self._suche.setMinimumWidth(180)
        self._suche.textChanged.connect(self._filter_changed)
        fl.addWidget(self._suche, 2)

        fl.addWidget(QLabel("Kategorie:"))
        self._combo_kat = QComboBox()
        self._combo_kat.setMinimumWidth(130)
        self._combo_kat.addItem("Alle", None)
        self._combo_kat.currentIndexChanged.connect(self._filter_changed)
        fl.addWidget(self._combo_kat)

        fl.addWidget(QLabel("Bereich:"))
        self._combo_sheet = QComboBox()
        self._combo_sheet.setMinimumWidth(130)
        self._combo_sheet.addItem("Alle", None)
        self._combo_sheet.currentIndexChanged.connect(self._filter_changed)
        fl.addWidget(self._combo_sheet)

        btn_reset = _btn_light("✖ Zurücksetzen")
        btn_reset.setFixedHeight(28)
        btn_reset.clicked.connect(self._filter_reset)
        fl.addWidget(btn_reset)

        layout.addWidget(filter_frame)

        # ── Aktions-Buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_import = _btn("📥  Excel neu einlesen", "#1565a8", "#0d47a1")
        self._btn_import.setToolTip(
            "Löscht alle bestehenden Einträge und liest die Excel-Dateien\n"
            f"aus {os.path.join(BASE_DIR, 'Daten', 'Telefonnummern')} neu ein."
        )
        self._btn_import.clicked.connect(self._excel_neu_einlesen)
        btn_row.addWidget(self._btn_import)

        self._btn_neu = _btn("＋  Manuell hinzufügen", "#107e3e", "#0a5c2e")
        self._btn_neu.setToolTip("Manuellen Eintrag hinzufügen")
        self._btn_neu.clicked.connect(self._manuell_hinzufuegen)
        btn_row.addWidget(self._btn_neu)

        self._btn_loeschen = _btn_light("🗑  Löschen")
        self._btn_loeschen.setEnabled(False)
        self._btn_loeschen.setStyleSheet(
            "QPushButton{background:#eee;color:#333;border:none;"
            "border-radius:4px;padding:4px 14px;font-size:12px;}"
            "QPushButton:hover{background:#ffcccc;color:#a00;}"
            "QPushButton:disabled{background:#f5f5f5;color:#bbb;}"
        )
        self._btn_loeschen.clicked.connect(self._loeschen)
        btn_row.addWidget(self._btn_loeschen)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#ccc;")
        btn_row.addWidget(sep)

        self._btn_kopieren = _btn("📋  Nummer kopieren", "#6a1b9a", "#4a148c")
        self._btn_kopieren.setEnabled(False)
        self._btn_kopieren.setToolTip("Telefonnummer des gewählten Eintrags in die Zwischenablage kopieren")
        self._btn_kopieren.clicked.connect(self._kopieren)
        btn_row.addWidget(self._btn_kopieren)

        btn_row.addStretch()

        self._treffer_lbl = QLabel()
        self._treffer_lbl.setStyleSheet("color:#666; font-size:11px;")
        btn_row.addWidget(self._treffer_lbl)

        layout.addLayout(btn_row)

        # ── Tabelle ────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Kategorie", "Bezeichnung", "Telefonnummer", "E-Mail", "Bereich", "Bemerkung",
        ])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget{border:1px solid #ddd; font-size:12px;}"
            "QTableWidget::item:selected{background:#d0e4f8; color:#000;}"
        )
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._auswahl_geaendert)
        self._table.itemDoubleClicked.connect(lambda _: self._kopieren())
        layout.addWidget(self._table, 1)

        # ── Status-Leiste ──────────────────────────────────────────────────────
        self._status_lbl = QLabel()
        self._status_lbl.setStyleSheet(
            "background:#e8f5e9; color:#1b5e20; border-radius:4px;"
            "padding:5px 12px; font-size:11px;"
        )
        layout.addWidget(self._status_lbl)

    # ── Filter ─────────────────────────────────────────────────────────────────

    def _aktualisiere_filter(self):
        """Füllt Kategorie- und Bereich-Dropdowns."""
        curr_kat   = self._combo_kat.currentData()
        curr_sheet = self._combo_sheet.currentData()

        self._combo_kat.blockSignals(True)
        self._combo_kat.clear()
        self._combo_kat.addItem("Alle", None)
        for k in lade_kategorien():
            self._combo_kat.addItem(k, k)
        for i in range(self._combo_kat.count()):
            if self._combo_kat.itemData(i) == curr_kat:
                self._combo_kat.setCurrentIndex(i)
                break
        self._combo_kat.blockSignals(False)

        self._combo_sheet.blockSignals(True)
        self._combo_sheet.clear()
        self._combo_sheet.addItem("Alle", None)
        for s in lade_sheets():
            self._combo_sheet.addItem(s, s)
        for i in range(self._combo_sheet.count()):
            if self._combo_sheet.itemData(i) == curr_sheet:
                self._combo_sheet.setCurrentIndex(i)
                break
        self._combo_sheet.blockSignals(False)

    def _filter_changed(self):
        self._lade()

    def _filter_reset(self):
        for w in (self._combo_kat, self._combo_sheet):
            w.blockSignals(True)
            w.setCurrentIndex(0)
            w.blockSignals(False)
        self._suche.blockSignals(True)
        self._suche.clear()
        self._suche.blockSignals(False)
        self._lade()

    # ── Laden ──────────────────────────────────────────────────────────────────

    def _lade(self):
        suche  = self._suche.text().strip() or None
        kat    = self._combo_kat.currentData()
        sheet  = self._combo_sheet.currentData()

        try:
            self._eintraege = lade_telefonnummern(
                suchtext=suche, kategorie=kat, sheet=sheet
            )
        except Exception as exc:
            QMessageBox.critical(self, "Datenbankfehler", str(exc))
            return

        self._table.setRowCount(len(self._eintraege))
        for row, e in enumerate(self._eintraege):
            cols = [
                e.get("kategorie", ""),
                e.get("bezeichnung", ""),
                e.get("nummer", ""),
                e.get("email", "") or "—",
                e.get("sheet", ""),
                e.get("bemerkung", "") or "",
            ]
            for col, text in enumerate(cols):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                # Quelle "Manuell" farblich abheben
                if e.get("quelle") == "Manuell":
                    item.setBackground(QColor("#fff8e1"))
                self._table.setItem(row, col, item)

        n = len(self._eintraege)
        self._treffer_lbl.setText(f"{n} Eintrag{'e' if n != 1 else ''}")
        self._auswahl_geaendert()

    def refresh(self):
        self._aktualisiere_filter()
        self._lade()
        ts = letzter_import()
        if ts:
            self._status_lbl.setText(f"Letzter Excel-Import: {ts}")

    # ── Aktionen ───────────────────────────────────────────────────────────────

    def _auswahl_geaendert(self):
        hat = self._table.currentRow() >= 0 and bool(self._eintraege)
        self._btn_kopieren.setEnabled(hat)
        # Löschen nur für manuell eingegebene Einträge erlauben
        e = self._aktuell_eintrag()
        self._btn_loeschen.setEnabled(bool(e and e.get("quelle") == "Manuell"))

    def _aktuell_eintrag(self) -> dict | None:
        row = self._table.currentRow()
        try:
            return self._eintraege[row]
        except (IndexError, AttributeError):
            return None

    def _kopieren(self):
        """Kopiert die Telefonnummer des gewählten Eintrags in die Zwischenablage."""
        e = self._aktuell_eintrag()
        if not e:
            return
        nr = e.get("nummer", "").strip()
        if not nr:
            QMessageBox.information(self, "Keine Nummer", "Dieser Eintrag hat keine Telefonnummer.")
            return
        QApplication.clipboard().setText(nr)
        self._status_lbl.setText(f"📋  Kopiert: {e.get('bezeichnung','')}  →  {nr}")

    def _excel_neu_einlesen(self):
        antwort = QMessageBox.question(
            self, "Excel neu einlesen",
            "Alle bestehenden Einträge werden gelöscht und aus den\n"
            "Excel-Dateien im Ordner 'Daten/Telefonnummern' neu eingelesen.\n\n"
            "Manuell hinzugefügte Einträge gehen dabei verloren!\n\n"
            "Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return
        try:
            n = importiere_aus_excel(clear_first=True)
            self.refresh()
            QMessageBox.information(
                self, "Import abgeschlossen",
                f"✅  {n} Einträge erfolgreich importiert."
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Import fehlgeschlagen",
                f"Fehler beim Einlesen der Excel-Dateien:\n\n{exc}\n\n"
                "Bitte sicherstellen, dass openpyxl installiert ist\n"
                "und die Excel-Dateien nicht geöffnet sind."
            )

    def _manuell_hinzufuegen(self):
        dlg = _EintragDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        daten = dlg.get_daten()
        try:
            eintrag_speichern(daten)
            self._aktualisiere_filter()
            self._lade()
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Speichern", str(exc))

    def _loeschen(self):
        e = self._aktuell_eintrag()
        if not e:
            return
        antwort = QMessageBox.question(
            self, "Eintrag löschen",
            f"Eintrag wirklich löschen?\n\n"
            f"Bezeichnung: {e.get('bezeichnung', '')}\n"
            f"Nummer: {e.get('nummer', '')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            try:
                eintrag_loeschen(e["id"])
                self._aktualisiere_filter()
                self._lade()
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", str(exc))
