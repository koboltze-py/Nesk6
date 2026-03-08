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
    QLineEdit, QComboBox, QMessageBox, QApplication,
    QDialog, QFormLayout, QDialogButtonBox, QTextEdit, QTabWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from config import FIORI_BLUE, FIORI_TEXT, BASE_DIR

from functions.telefonnummern_db import (
    importiere_aus_excel,
    lade_telefonnummern,
    lade_kategorien,
    lade_sheets,
    letzter_import,
    ist_db_leer,
    hat_veraltete_daten,
    eintrag_speichern,
    eintrag_aktualisieren,
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
#  Eintrag-Dialog  (Neu anlegen + Bearbeiten)
# ──────────────────────────────────────────────────────────────────────────────

class _EintragDialog(QDialog):
    """Dialog zum Anlegen oder Bearbeiten eines Telefoneintrags.

    Aufruf mit ``daten=None`` → neuer Eintrag (Neuanlage).
    Aufruf mit ``daten=dict`` → Bearbeiten-Modus, Felder werden vorausgefüllt.
    """

    _FIELD_STYLE = (
        "QLineEdit, QTextEdit, QComboBox {"
        "border:1px solid #ccc; border-radius:4px; padding:4px;"
        "font-size:12px; background:white;}"
    )

    def __init__(self, daten: dict | None = None, parent=None):
        super().__init__(parent)
        self._edit_mode = daten is not None
        self._orig = daten or {}
        self.setWindowTitle("Eintrag bearbeiten" if self._edit_mode else "Neuen Eintrag anlegen")
        self.setMinimumWidth(460)
        self.setStyleSheet(self._FIELD_STYLE)
        self._build()
        if self._edit_mode:
            self._prefill()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Bereich (Sheet) ────────────────────────────────────────────────────
        sheet_row = QHBoxLayout()
        lbl_sheet = QLabel("Bereich:")
        lbl_sheet.setFixedWidth(100)
        self._f_sheet = QComboBox()
        self._f_sheet.setEditable(True)
        for s in lade_sheets():
            self._f_sheet.addItem(s, s)
        if not self._edit_mode:
            # Manuell als Standard für neue Einträge
            if self._f_sheet.findText("Manuell") < 0:
                self._f_sheet.addItem("Manuell", "Manuell")
            self._f_sheet.setCurrentText("Manuell")
        self._f_sheet.currentTextChanged.connect(self._update_kat_options)
        sheet_row.addWidget(lbl_sheet)
        sheet_row.addWidget(self._f_sheet, 1)
        layout.addLayout(sheet_row)

        # ── Kategorie ──────────────────────────────────────────────────────────
        kat_row = QHBoxLayout()
        lbl_kat = QLabel("Kategorie:")
        lbl_kat.setFixedWidth(100)
        self._f_kat = QComboBox()
        self._f_kat.setEditable(True)
        self._f_kat.setPlaceholderText("z.B. DRK, Check In B …")
        self._populate_kat("")
        kat_row.addWidget(lbl_kat)
        kat_row.addWidget(self._f_kat, 1)
        layout.addLayout(kat_row)

        # ── Restliche Felder ───────────────────────────────────────────────────
        form = QFormLayout()
        form.setSpacing(10)

        self._f_bez  = QLineEdit()
        self._f_nr   = QLineEdit()
        self._f_mail = QLineEdit()
        self._f_bem  = QTextEdit()
        self._f_bem.setFixedHeight(60)

        self._f_bez.setPlaceholderText("Name oder Bezeichnung")
        self._f_nr.setPlaceholderText("Telefonnummer")
        self._f_mail.setPlaceholderText("E-Mail (optional)")

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

    def _populate_kat(self, sheet_text: str):
        """Füllt Kategorie-Dropdown – passende Kategorien zuerst."""
        curr = self._f_kat.currentText()
        alle = lade_kategorien()
        try:
            sheet_eintraege = lade_telefonnummern(sheet=sheet_text) if sheet_text else []
            sheet_kats = sorted({e["kategorie"] for e in sheet_eintraege if e.get("kategorie")})
        except Exception:
            sheet_kats = []

        self._f_kat.blockSignals(True)
        self._f_kat.clear()
        self._f_kat.addItem("", "")
        shown: set[str] = set()
        for k in sheet_kats:
            self._f_kat.addItem(k, k)
            shown.add(k)
        if sheet_kats:
            self._f_kat.insertSeparator(self._f_kat.count())
        for k in alle:
            if k not in shown:
                self._f_kat.addItem(k, k)
        idx = self._f_kat.findText(curr)
        self._f_kat.setCurrentIndex(idx if idx >= 0 else 0)
        if idx < 0 and curr:
            self._f_kat.setCurrentText(curr)
        self._f_kat.blockSignals(False)

    def _update_kat_options(self, sheet_text: str):
        self._populate_kat(sheet_text)

    def _prefill(self):
        """Füllt Formularfelder mit bestehenden Daten."""
        sheet = self._orig.get("sheet", "")
        idx = self._f_sheet.findText(sheet)
        if idx >= 0:
            self._f_sheet.setCurrentIndex(idx)
        else:
            self._f_sheet.setCurrentText(sheet)

        # Kategorie erst nach Sheet setzen (update_kat_options läuft beim Sheet-Wechsel)
        kat = self._orig.get("kategorie", "")
        idx = self._f_kat.findText(kat)
        if idx >= 0:
            self._f_kat.setCurrentIndex(idx)
        else:
            self._f_kat.setCurrentText(kat)

        self._f_bez.setText(self._orig.get("bezeichnung", ""))
        self._f_nr.setText(self._orig.get("nummer", ""))
        self._f_mail.setText(self._orig.get("email", "") or "")
        self._f_bem.setPlainText(self._orig.get("bemerkung", "") or "")

    def _accept(self):
        if not self._f_bez.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Bezeichnung eingeben.")
            return
        self.accept()

    def get_daten(self) -> dict:
        sheet = self._f_sheet.currentText().strip() or "Manuell"
        return {
            "kategorie":   self._f_kat.currentText().strip(),
            "bezeichnung": self._f_bez.text().strip(),
            "nummer":      self._f_nr.text().strip(),
            "email":       self._f_mail.text().strip(),
            "bemerkung":   self._f_bem.toPlainText().strip(),
            "quelle":      self._orig.get("quelle", "Manuell"),
            "sheet":       sheet,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Haupt-Widget
# ──────────────────────────────────────────────────────────────────────────────

class TelefonnummernWidget(QWidget):
    """Telefonnummern-Verzeichnis aus Excel-Import, organisiert in Tabs."""

    # (Tab-Label, sheet-Filter – None = alle)
    _TABS = [
        ("🔍  Alle",            None),
        ("📋  Kontakte",        "Kontakte"),
        ("🏪  Check-In (CIC)",  "Check-In (CIC)"),
        ("🚪  Interne & Gate",  "Interne & Gate"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tab_eintraege: list[list[dict]] = [[] for _ in self._TABS]
        self._tab_tables:    list[QTableWidget] = []
        self._build_ui()
        self._auto_import_if_needed()

    # ── Automatischer Import ───────────────────────────────────────────────────

    def _auto_import_if_needed(self):
        """Importiert Excel beim ersten Start oder wenn alte Kategorienamen vorhanden sind."""
        try:
            if ist_db_leer() or hat_veraltete_daten():
                n = importiere_aus_excel(clear_first=True)
                self._status_lbl.setText(f"✅  Import: {n} Einträge geladen.")
        except Exception as exc:
            self._status_lbl.setText(f"⚠️  Import fehlgeschlagen: {exc}")
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

        # ── Aktions- und Suchzeile ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_import = _btn("📥  Excel neu einlesen", "#1565a8", "#0d47a1")
        self._btn_import.setToolTip(
            "Löscht alle Einträge und liest die Excel-Dateien\n"
            f"aus {os.path.join(BASE_DIR, 'Daten', 'Telefonnummern')} neu ein."
        )
        self._btn_import.clicked.connect(self._excel_neu_einlesen)
        btn_row.addWidget(self._btn_import)

        self._btn_neu = _btn("＋  Neu", "#107e3e", "#0a5c2e")
        self._btn_neu.setToolTip("Neuen Eintrag manuell hinzufügen")
        self._btn_neu.clicked.connect(self._manuell_hinzufuegen)
        btn_row.addWidget(self._btn_neu)

        self._btn_bearbeiten = _btn_light("✏  Bearbeiten")
        self._btn_bearbeiten.setEnabled(False)
        self._btn_bearbeiten.setToolTip("Ausgewählten Eintrag bearbeiten (auch: Doppelklick)")
        self._btn_bearbeiten.clicked.connect(self._bearbeiten)
        btn_row.addWidget(self._btn_bearbeiten)

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
        self._btn_kopieren.setToolTip("Telefonnummer in Zwischenablage kopieren")
        self._btn_kopieren.clicked.connect(self._kopieren)
        btn_row.addWidget(self._btn_kopieren)

        btn_row.addStretch()

        suche_lbl = QLabel("Suche:")
        suche_lbl.setStyleSheet("font-size:12px;")
        btn_row.addWidget(suche_lbl)

        self._suche = QLineEdit()
        self._suche.setPlaceholderText("Name, Nummer, Abteilung …")
        self._suche.setMinimumWidth(200)
        self._suche.textChanged.connect(self._lade)
        btn_row.addWidget(self._suche)

        self._treffer_lbl = QLabel()
        self._treffer_lbl.setStyleSheet("color:#666; font-size:11px; min-width:80px;")
        btn_row.addWidget(self._treffer_lbl)

        layout.addLayout(btn_row)

        # ── Tabs mit je einer Tabelle ──────────────────────────────────────────
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet(
            "QTabBar::tab { padding: 6px 18px; font-size: 12px; }"
            "QTabBar::tab:selected { font-weight: bold; color: #1565a8; }"
        )

        for label, _ in self._TABS:
            table = self._make_table()
            self._tab_tables.append(table)
            container = QWidget()
            vl = QVBoxLayout(container)
            vl.setContentsMargins(0, 4, 0, 0)
            vl.addWidget(table)
            self._tab_widget.addTab(container, label)

        self._tab_widget.currentChanged.connect(self._auswahl_geaendert)
        layout.addWidget(self._tab_widget, 1)

        # ── Status-Leiste ──────────────────────────────────────────────────────
        self._status_lbl = QLabel()
        self._status_lbl.setStyleSheet(
            "background:#e8f5e9; color:#1b5e20; border-radius:4px;"
            "padding:5px 12px; font-size:11px;"
        )
        layout.addWidget(self._status_lbl)

    def _make_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Kategorie", "Bezeichnung", "Telefonnummer", "E-Mail", "Bemerkung",
        ])
        hh = table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(
            "QTableWidget{border:1px solid #ddd; font-size:12px;}"
            "QTableWidget::item:selected{background:#d0e4f8; color:#000;}"
        )
        table.verticalHeader().setVisible(False)
        table.itemSelectionChanged.connect(self._auswahl_geaendert)
        table.itemDoubleClicked.connect(lambda _: self._bearbeiten())
        return table

    # ── Laden ──────────────────────────────────────────────────────────────────

    def _lade(self):
        suche = self._suche.text().strip() or None
        total = 0

        for idx, (_, sheet_filter) in enumerate(self._TABS):
            try:
                eintraege = lade_telefonnummern(suchtext=suche, sheet=sheet_filter)
            except Exception:
                eintraege = []

            self._tab_eintraege[idx] = eintraege
            table = self._tab_tables[idx]
            table.setRowCount(len(eintraege))

            for row, e in enumerate(eintraege):
                cols = [
                    e.get("kategorie", ""),
                    e.get("bezeichnung", ""),
                    e.get("nummer", ""),
                    e.get("email", "") or "",
                    e.get("bemerkung", "") or "",
                ]
                for col, text in enumerate(cols):
                    item = QTableWidgetItem(str(text))
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                    )
                    if e.get("quelle") == "Manuell":
                        item.setBackground(QColor("#fff8e1"))
                    table.setItem(row, col, item)

            if idx == 0:
                total = len(eintraege)

        self._treffer_lbl.setText(f"{total} Einträge")
        self._auswahl_geaendert()

    def refresh(self):
        self._lade()
        ts = letzter_import()
        if ts:
            self._status_lbl.setText(f"Letzter Excel-Import: {ts}")

    # ── Auswahl / Buttons ──────────────────────────────────────────────────────

    def _current_table(self) -> QTableWidget:
        return self._tab_tables[self._tab_widget.currentIndex()]

    def _current_eintraege(self) -> list[dict]:
        return self._tab_eintraege[self._tab_widget.currentIndex()]

    def _aktuell_eintrag(self) -> dict | None:
        row = self._current_table().currentRow()
        try:
            return self._current_eintraege()[row]
        except (IndexError, AttributeError):
            return None

    def _auswahl_geaendert(self):
        e = self._aktuell_eintrag()
        hat = e is not None
        self._btn_kopieren.setEnabled(hat)
        self._btn_bearbeiten.setEnabled(hat)
        self._btn_loeschen.setEnabled(hat)

    # ── Aktionen ───────────────────────────────────────────────────────────────

    def _kopieren(self):
        e = self._aktuell_eintrag()
        if not e:
            return
        nr = e.get("nummer", "").strip()
        if not nr:
            QMessageBox.information(self, "Keine Nummer", "Dieser Eintrag hat keine Telefonnummer.")
            return
        QApplication.clipboard().setText(nr)
        self._status_lbl.setText(f"📋  Kopiert: {e.get('bezeichnung','')}  →  {nr}")

    def _bearbeiten(self):
        e = self._aktuell_eintrag()
        if not e:
            return
        dlg = _EintragDialog(daten=dict(e), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        daten = dlg.get_daten()
        try:
            eintrag_aktualisieren(e["id"], daten)
            self._lade()
            self._status_lbl.setText(f"✅  Gespeichert: {daten['bezeichnung']}")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Speichern", str(exc))

    def _manuell_hinzufuegen(self):
        dlg = _EintragDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        daten = dlg.get_daten()
        try:
            eintrag_speichern(daten)
            self._lade()
            self._status_lbl.setText(f"✅  Hinzugefügt: {daten['bezeichnung']}")
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
                self._lade()
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", str(exc))

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

