"""
Call Transcription – Anrufprotokoll-Modul
Aufzeichnung und Verwaltung von Anrufinformationen mit Textbausteinen.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSplitter, QTextEdit, QLineEdit,
    QComboBox, QFormLayout, QMessageBox, QSizePolicy,
    QCheckBox, QListWidget, QListWidgetItem, QDialog,
    QDialogButtonBox, QApplication,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor

from config import FIORI_BLUE, FIORI_TEXT, FIORI_BORDER, FIORI_SIDEBAR_BG

from functions.call_transcription_db import (
    init_db,
    speichern,
    alle_laden,
    laden_by_id,
    loeschen,
    textbausteine_laden,
    textbaustein_speichern,
    textbaustein_loeschen,
)

# ──────────────────────────────────────────────────────────────────────────────
#  Konstanten
# ──────────────────────────────────────────────────────────────────────────────

_KATEGORIEN = [
    "",
    "PRM Anmeldung",
    "PRM Rückfrage",
    "PRM Stornierung",
    "Rollstuhlservice",
    "Boarding-Hilfe",
    "Ambulift",
    "Sehbehinderung",
    "Hörbehinderung",
    "Kognitive Einschränkung",
    "Sonstiges",
]

_RICHTUNGEN = ["Eingehend", "Ausgehend"]

# IATA-PRM-Hilfearten
_HILFE_ARTEN = [
    "",
    "WCHR – Rollstuhl (kann gehen, keine Treppen)",
    "WCHS – Rollstuhl (keine Treppen)",
    "WCHC – Vollständig immobil (Ambulift)",
    "BLND – Sehbehinderung",
    "DEAF – Hörbehinderung",
    "DPNA – Kognitive / mentale Einschränkung",
    "MAAS – Allgemeine Unterstützung erforderlich",
    "STRC – Krankentrage erforderlich",
    "AMBU – Ambulanter Patient",
    "LANG – Sprachbarriere",
    "Sonstiges",
]

# ── Flugdaten CGN (Stand 11.03.2026, Quelle: Flightradar24) ──────────────────
# Abflüge von Köln/Bonn (passagierrelevant)
_FLUEGE_ABFLUG: list[tuple[str, str]] = [
    ("EW4",    "Berlin BER · Eurowings"),
    ("EW6",    "Berlin BER · Eurowings"),
    ("EW80",   "München MUC · Eurowings"),
    ("EW242",  "Fuerteventura FUE · Eurowings"),
    ("EW252",  "Teneriffa TFS · Eurowings"),
    ("EW460",  "London Heathrow LHR · Eurowings"),
    ("EW520",  "Barcelona BCN · Eurowings"),
    ("EW534",  "Málaga AGP · Eurowings"),
    ("EW582",  "Palma de Mallorca PMI · Eurowings"),
    ("EW584",  "Palma de Mallorca PMI · Eurowings"),
    ("EW610",  "Funchal FNC · Eurowings"),
    ("EW646",  "Faro FAO · Eurowings"),
    ("EW752",  "Wien VIE · Eurowings"),
    ("EW754",  "Wien VIE · Eurowings"),
    ("EW762",  "Zürich ZRH · Eurowings"),
    ("EW962",  "Split SPU · Eurowings"),
    ("EW1063", "Kairo CAI · Eurowings"),
    ("EW1156", "Kairo CAI / Dschidda JED · Eurowings"),
    ("EW6900", "Düsseldorf DUS · Eurowings"),
    ("EW8051", "Berlin BER · Eurowings"),
    ("FR302",  "Gran Canaria LPA · Ryanair"),
    ("FR1355", "Alicante ALC · Ryanair"),
    ("FR2257", "Valencia VLC · Ryanair"),
    ("FR2353", "London Stansted STN · Ryanair"),
    ("FR2508", "Barcelona BCN · Ryanair"),
    ("FR4450", "Paphos PFO · Ryanair"),
    ("FR4452", "Sofia SOF · Ryanair"),
    ("FR5205", "Malta MLA · Ryanair"),
    ("FR5520", "Palma de Mallorca PMI · Ryanair"),
    ("FR5532", "Mailand Bergamo BGY · Ryanair"),
    ("FR8648", "Teneriffa TFS · Ryanair"),
    ("FR9326", "Porto OPO · Ryanair"),
    ("FR9481", "Wien VIE · Ryanair"),
    ("FR9840", "Lissabon LIS · Ryanair"),
    ("LH1979", "München MUC · Lufthansa"),
    ("MB601",  "Istanbul Atatrk IST · Chrono Jet"),
    ("OS246",  "Wien VIE · Austrian Airlines"),
    ("PC1012", "Istanbul Sabiha Gökçen SAW · Pegasus"),
    ("PC1014", "Istanbul Sabiha Gökçen SAW · Pegasus"),
    ("PC1682", "Ankara ESB · Pegasus"),
    ("PC5014", "Antalya AYT · Pegasus"),
    ("SM2919", "Hurghada HRG · Air Cairo"),
    ("TK1672", "Istanbul IST · Turkish Airlines"),
    ("VF92",   "Istanbul Sabiha Gökçen SAW · AJet"),
    ("VL1973", "München MUC · Lufthansa City"),
    ("XQ115",  "Antalya AYT · SunExpress"),
    ("XR521",  "Fuerteventura FUE · Corendon"),
]

# Ankünfte in Köln/Bonn (passagierrelevant)
_FLUEGE_ANKUNFT: list[tuple[str, str]] = [
    ("EW15",   "Berlin BER · Eurowings"),
    ("EW81",   "München MUC · Eurowings"),
    ("EW253",  "Teneriffa TFS · Eurowings"),
    ("EW461",  "London Heathrow LHR · Eurowings"),
    ("EW469",  "London Heathrow LHR · Eurowings"),
    ("EW535",  "Málaga AGP · Eurowings"),
    ("EW583",  "Palma de Mallorca PMI · Eurowings"),
    ("EW647",  "Faro FAO · Eurowings"),
    ("EW753",  "Wien VIE · Eurowings"),
    ("EW763",  "Zürich ZRH · Eurowings"),
    ("EW963",  "Split SPU · Eurowings"),
    ("EW1066", "Kairo CAI · Eurowings"),
    ("EW8050", "Berlin BER · Eurowings"),
    ("FR1034", "Teneriffa TFS · Ryanair"),
    ("FR1356", "Alicante ALC · Ryanair"),
    ("FR2256", "Valencia VLC · Ryanair"),
    ("FR2352", "London Stansted STN · Ryanair"),
    ("FR2507", "Barcelona BCN · Ryanair"),
    ("FR4453", "Sofia SOF · Ryanair"),
    ("FR5206", "Malta MLA · Ryanair"),
    ("FR5519", "Palma de Mallorca PMI · Ryanair"),
    ("FR5531", "Mailand Bergamo BGY · Ryanair"),
    ("FR7211", "Palma de Mallorca PMI · Ryanair"),
    ("FR9325", "Porto OPO · Ryanair"),
    ("FR9480", "Wien VIE · Ryanair"),
    ("LH1978", "München MUC · Lufthansa"),
    ("MB600",  "Istanbul Atatrk IST · Chrono Jet"),
    ("OS245",  "Wien VIE · Austrian Airlines"),
    ("PC1011", "Istanbul Sabiha Gökçen SAW · Pegasus"),
    ("PC1013", "Istanbul Sabiha Gökçen SAW · Pegasus"),
    ("PC1681", "Ankara ESB · Pegasus"),
    ("PC5013", "Antalya AYT · Pegasus"),
    ("SM601",  "Kairo CAI · Air Cairo"),
    ("SM2916", "Marsa Alam RMF · Air Cairo"),
    ("SM2918", "Hurghada HRG · Air Cairo"),
    ("TK1671", "Istanbul IST · Turkish Airlines"),
    ("VF91",   "Istanbul Sabiha Gökçen SAW · AJet"),
    ("VL1972", "München MUC · Lufthansa City"),
    ("XQ114",  "Antalya AYT · SunExpress"),
]

_FIELD_STYLE = (
    "QLineEdit, QTextEdit, QComboBox {"
    "border:1px solid #ccc; border-radius:4px; padding:4px; font-size:12px;"
    "background:white;}"
    "QLineEdit:focus, QTextEdit:focus, QComboBox:focus {"
    "border-color:#0a6ed1;}"
)


def _btn(text: str, color: str = FIORI_BLUE, hover: str = "#0057b8",
         min_w: int = 0) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(32)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    style = (
        f"QPushButton{{background:{color};color:white;border:none;"
        f"border-radius:4px;padding:4px 14px;font-size:12px;}}"
        f"QPushButton:hover{{background:{hover};}}"
        f"QPushButton:disabled{{background:#bbb;color:#888;}}"
    )
    b.setStyleSheet(style)
    if min_w:
        b.setMinimumWidth(min_w)
    return b


def _btn_light(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(32)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        "QPushButton{background:#eee;color:#333;border:none;"
        "border-radius:4px;padding:4px 14px;font-size:12px;}"
        "QPushButton:hover{background:#ddd;}"
    )
    return b


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    lbl.setStyleSheet(f"color:{FIORI_BLUE}; padding:2px 0;")
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{FIORI_BORDER};")
    return f


# ──────────────────────────────────────────────────────────────────────────────
#  Textbaustein-Verwaltungs-Dialog
# ──────────────────────────────────────────────────────────────────────────────

class _TextbausteinVerwaltungDialog(QDialog):
    """Ermöglicht das Hinzufügen und Löschen eigener Textbausteine."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Textbausteine verwalten")
        self.setMinimumSize(520, 420)
        self.setStyleSheet("background:white;")

        vlay = QVBoxLayout(self)
        vlay.setSpacing(10)
        vlay.setContentsMargins(16, 16, 16, 12)

        vlay.addWidget(_section_label("✏ Neuen Textbaustein anlegen"))
        form = QFormLayout()
        form.setSpacing(6)
        self._gruppe_edit = QComboBox()
        self._gruppe_edit.setEditable(True)
        self._gruppe_edit.addItems(["Allgemein", "Lage / Meldung", "Ergebnis"])
        self._gruppe_edit.setStyleSheet(_FIELD_STYLE)
        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText("Text des Bausteins …")
        self._text_edit.setStyleSheet(_FIELD_STYLE)
        form.addRow("Gruppe:", self._gruppe_edit)
        form.addRow("Text:", self._text_edit)
        vlay.addLayout(form)

        add_btn = _btn("➕ Hinzufügen")
        add_btn.clicked.connect(self._add)
        vlay.addWidget(add_btn)
        vlay.addWidget(_hline())
        vlay.addWidget(_section_label("🗑 Vorhandene Bausteine löschen"))

        self._lst = QListWidget()
        self._lst.setStyleSheet("border:1px solid #ccc; border-radius:4px; font-size:12px;")
        vlay.addWidget(self._lst, 1)

        del_btn = _btn_light("🗑 Ausgewählten löschen")
        del_btn.clicked.connect(self._delete)
        vlay.addWidget(del_btn)

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(self.reject)
        vlay.addWidget(close_btn)

        self._refresh_list()

    def _refresh_list(self):
        self._lst.clear()
        bausteine = textbausteine_laden()
        for gruppe, items in bausteine.items():
            for item in items:
                entry = QListWidgetItem(f"[{gruppe}]  {item['text']}")
                entry.setData(Qt.ItemDataRole.UserRole, item["id"])
                self._lst.addItem(entry)

    def _add(self):
        gruppe = self._gruppe_edit.currentText().strip()
        text = self._text_edit.text().strip()
        if not gruppe or not text:
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Gruppe und Text ausfüllen.")
            return
        textbaustein_speichern(gruppe, text)
        self._text_edit.clear()
        self._refresh_list()

    def _delete(self):
        item = self._lst.currentItem()
        if not item:
            return
        bid = item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(
            self, "Löschen?",
            f"Baustein wirklich löschen?\n\n{item.text()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            textbaustein_loeschen(bid)
            self._refresh_list()


# ──────────────────────────────────────────────────────────────────────────────
#  Haupt-Widget
# ──────────────────────────────────────────────────────────────────────────────

class CallTranscriptionWidget(QWidget):
    """Hauptseite: Call Transcription – Anrufprotokoll."""

    def __init__(self, parent=None):
        super().__init__(parent)
        init_db()
        self._current_id: int | None = None
        self._setup_ui()
        self._refresh_list()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Kopfzeile ──────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background:{FIORI_SIDEBAR_BG};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        title = QLabel("♿  Call Transcription – PRM-Anmeldungen CGN")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color:white;")
        hl.addWidget(title)
        hl.addStretch()

        self._lbl_count = QLabel("")
        self._lbl_count.setStyleSheet("color:#cdd5e0; font-size:11px;")
        hl.addWidget(self._lbl_count)

        root.addWidget(header)

        # ── Haupt-Splitter ─────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet("QSplitter::handle{background:#ddd;}")

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([320, 780])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

    # ── Linke Liste ────────────────────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(240)
        panel.setStyleSheet("background:#fafafa; border-right:1px solid #e0e0e0;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 12, 10, 10)
        lay.setSpacing(6)

        lay.addWidget(_section_label("♿ PRM-Anmeldungen"))

        # Suchfeld
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Suchen …")
        self._search.setStyleSheet(_FIELD_STYLE)
        self._search.textChanged.connect(self._refresh_list)
        lay.addWidget(self._search)

        # Filter: Kategorie
        self._filter_kat = QComboBox()
        self._filter_kat.addItem("Alle Kategorien", "")
        for k in _KATEGORIEN[1:]:
            self._filter_kat.addItem(k, k)
        self._filter_kat.setStyleSheet(_FIELD_STYLE)
        self._filter_kat.currentIndexChanged.connect(self._refresh_list)
        lay.addWidget(self._filter_kat)

        # Nur offene
        self._chk_offen = QCheckBox("Nur offene anzeigen")
        self._chk_offen.setStyleSheet("font-size:11px; color:#555;")
        self._chk_offen.toggled.connect(self._refresh_list)
        lay.addWidget(self._chk_offen)

        # Liste
        self._list_widget = QListWidget()
        self._list_widget.setStyleSheet(
            "QListWidget{border:1px solid #ccc; border-radius:4px; font-size:11px;}"
            "QListWidget::item:selected{background:#0a6ed1; color:white;}"
            "QListWidget::item:hover{background:#eef4fa;}"
        )
        self._list_widget.currentItemChanged.connect(self._on_list_selection)
        lay.addWidget(self._list_widget, 1)

        new_btn = _btn("➕ Neue Anmeldung")
        new_btn.clicked.connect(self._new_entry)
        lay.addWidget(new_btn)

        return panel

    # ── Rechtes Formular ───────────────────────────────────────────────────────

    def _build_right_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:white; border:none;")

        container = QWidget()
        container.setStyleSheet("background:white;")
        vlay = QVBoxLayout(container)
        vlay.setContentsMargins(24, 20, 24, 20)
        vlay.setSpacing(14)

        # ── Panel-Titel ────────────────────────────────────────────────────────
        self._form_title = QLabel("Neue PRM-Anmeldung")
        self._form_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self._form_title.setStyleSheet(f"color:{FIORI_BLUE};")
        vlay.addWidget(self._form_title)
        vlay.addWidget(_hline())

        # ── Datum / Uhrzeit / Anruf ────────────────────────────────────────────
        meta_lay = QHBoxLayout()
        meta_lay.setSpacing(12)

        # Datum
        d_lay = QVBoxLayout()
        d_lay.addWidget(QLabel("Datum *"))
        self._f_datum = QLineEdit(datetime.now().strftime("%d.%m.%Y"))
        self._f_datum.setStyleSheet(_FIELD_STYLE)
        self._f_datum.setFixedWidth(110)
        d_lay.addWidget(self._f_datum)
        meta_lay.addLayout(d_lay)

        # Uhrzeit
        t_lay = QVBoxLayout()
        t_lay.addWidget(QLabel("Uhrzeit *"))
        self._f_uhrzeit = QLineEdit(datetime.now().strftime("%H:%M"))
        self._f_uhrzeit.setStyleSheet(_FIELD_STYLE)
        self._f_uhrzeit.setFixedWidth(80)
        t_lay.addWidget(self._f_uhrzeit)
        meta_lay.addLayout(t_lay)

        # Anruf-Richtung
        r_lay = QVBoxLayout()
        r_lay.addWidget(QLabel("Anruf"))
        self._f_richtung = QComboBox()
        self._f_richtung.addItems(_RICHTUNGEN)
        self._f_richtung.setStyleSheet(_FIELD_STYLE)
        self._f_richtung.setFixedWidth(120)
        r_lay.addWidget(self._f_richtung)
        meta_lay.addLayout(r_lay)

        # Kategorie
        k_lay = QVBoxLayout()
        k_lay.addWidget(QLabel("Kategorie"))
        self._f_kategorie = QComboBox()
        self._f_kategorie.addItems(_KATEGORIEN)
        self._f_kategorie.setStyleSheet(_FIELD_STYLE)
        self._f_kategorie.setMinimumWidth(180)
        k_lay.addWidget(self._f_kategorie)
        meta_lay.addLayout(k_lay)

        meta_lay.addStretch()
        vlay.addLayout(meta_lay)

        # ── Flugdaten ──────────────────────────────────────────────────────────
        flug_lay = QHBoxLayout()
        flug_lay.setSpacing(12)

        fr_lay = QVBoxLayout()
        fr_lay.addWidget(QLabel("Flug-Richtung"))
        self._f_flug_richtung = QComboBox()
        self._f_flug_richtung.addItem("– bitte wählen –", "")
        self._f_flug_richtung.addItem("✈  Abflug (ab CGN)", "Abflug")
        self._f_flug_richtung.addItem("🛬  Ankunft (nach CGN)", "Ankunft")
        self._f_flug_richtung.setStyleSheet(_FIELD_STYLE)
        self._f_flug_richtung.setMinimumWidth(200)
        fr_lay.addWidget(self._f_flug_richtung)
        flug_lay.addLayout(fr_lay)

        fn_lay = QVBoxLayout()
        fn_lay.addWidget(QLabel("Flugnummer"))
        self._f_flugnummer = QComboBox()
        self._f_flugnummer.setEditable(True)
        self._f_flugnummer.setMinimumWidth(300)
        self._f_flugnummer.setStyleSheet(_FIELD_STYLE)
        self._f_flugnummer.lineEdit().setPlaceholderText(
            "Zuerst Flug-Richtung wählen …"
        )
        fn_lay.addWidget(self._f_flugnummer)
        flug_lay.addLayout(fn_lay, 1)

        zh_lay = QVBoxLayout()
        zh_lay.addWidget(QLabel("Ziel / Herkunft"))
        self._f_ziel_herkunft = QLineEdit()
        self._f_ziel_herkunft.setReadOnly(True)
        self._f_ziel_herkunft.setStyleSheet(
            "QLineEdit{border:1px solid #ccc; border-radius:4px; padding:4px;"
            "font-size:12px; background:#f5f5f5; color:#555;}"
        )
        self._f_ziel_herkunft.setMinimumWidth(220)
        zh_lay.addWidget(self._f_ziel_herkunft)
        flug_lay.addLayout(zh_lay, 1)

        vlay.addLayout(flug_lay)

        # ── Passagier ──────────────────────────────────────────────────────────
        pass_lay = QHBoxLayout()
        pass_lay.setSpacing(12)

        pn_lay = QVBoxLayout()
        pn_lay.addWidget(QLabel("Passagier-Name *"))
        self._f_passagier_name = QLineEdit()
        self._f_passagier_name.setPlaceholderText("Nachname, Vorname …")
        self._f_passagier_name.setStyleSheet(_FIELD_STYLE)
        pn_lay.addWidget(self._f_passagier_name)
        pass_lay.addLayout(pn_lay, 2)

        ha_lay = QVBoxLayout()
        ha_lay.addWidget(QLabel("Hilfeart (PRM-Code)"))
        self._f_hilfeart = QComboBox()
        self._f_hilfeart.addItems(_HILFE_ARTEN)
        self._f_hilfeart.setStyleSheet(_FIELD_STYLE)
        self._f_hilfeart.setMinimumWidth(270)
        ha_lay.addWidget(self._f_hilfeart)
        pass_lay.addLayout(ha_lay, 2)

        vlay.addLayout(pass_lay)

        # ── Anrufer / Kontakt ──────────────────────────────────────────────────
        caller_lay = QHBoxLayout()
        caller_lay.setSpacing(12)

        a_lay = QVBoxLayout()
        a_lay.addWidget(QLabel("Anrufer / Kontakt"))
        self._f_anrufer = QLineEdit()
        self._f_anrufer.setPlaceholderText("Name, Stelle oder Telefon-Durchsteller …")
        self._f_anrufer.setStyleSheet(_FIELD_STYLE)
        a_lay.addWidget(self._f_anrufer)
        caller_lay.addLayout(a_lay, 2)

        tel_lay = QVBoxLayout()
        tel_lay.addWidget(QLabel("Rückruf-Nummer"))
        self._f_telefon = QLineEdit()
        self._f_telefon.setPlaceholderText("+49 …")
        self._f_telefon.setStyleSheet(_FIELD_STYLE)
        tel_lay.addWidget(self._f_telefon)
        caller_lay.addLayout(tel_lay, 1)

        vlay.addLayout(caller_lay)

        # ── Betreff ────────────────────────────────────────────────────────────
        vlay.addWidget(QLabel("Betreff / Kurzbeschreibung"))
        self._f_betreff = QLineEdit()
        self._f_betreff.setPlaceholderText("Kurze Zusammenfassung …")
        self._f_betreff.setStyleSheet(_FIELD_STYLE)
        vlay.addWidget(self._f_betreff)

        vlay.addWidget(_hline())

        # ── Textbausteine ──────────────────────────────────────────────────────
        tb_header_lay = QHBoxLayout()
        tb_header_lay.addWidget(_section_label("⚡ Textbausteine – schnell einfügen"))
        tb_header_lay.addStretch()
        tb_verw_btn = _btn_light("✏ Verwalten")
        tb_verw_btn.setFixedHeight(26)
        tb_verw_btn.clicked.connect(self._open_textbaustein_verwaltung)
        tb_header_lay.addWidget(tb_verw_btn)
        vlay.addLayout(tb_header_lay)

        hint = QLabel("Klick auf einen Baustein fügt den Text an der Cursor-Position in die Notizen ein.")
        hint.setStyleSheet("color:#888; font-size:10px; font-style:italic;")
        vlay.addWidget(hint)

        self._tb_container = QWidget()
        self._tb_layout = QVBoxLayout(self._tb_container)
        self._tb_layout.setContentsMargins(0, 0, 0, 0)
        self._tb_layout.setSpacing(4)
        vlay.addWidget(self._tb_container)

        vlay.addWidget(_hline())

        # ── Notizen ────────────────────────────────────────────────────────────
        vlay.addWidget(_section_label("📝 Gesprächsnotiz"))
        self._f_notiz = QTextEdit()
        self._f_notiz.setMinimumHeight(160)
        self._f_notiz.setPlaceholderText(
            "Gesprächsinhalt, Maßnahmen und Ergebnis hier festhalten …"
        )
        self._f_notiz.setStyleSheet(
            "QTextEdit{border:1px solid #ccc; border-radius:4px; "
            "padding:6px; font-size:12px; background:white;}"
            "QTextEdit:focus{border-color:#0a6ed1;}"
        )
        vlay.addWidget(self._f_notiz)

        # ── Erledigt ───────────────────────────────────────────────────────────
        self._chk_erledigt = QCheckBox("  ✅  Als erledigt markieren")
        self._chk_erledigt.setStyleSheet("font-size:12px; color:#333;")
        vlay.addWidget(self._chk_erledigt)

        # ── Aktionszeile ───────────────────────────────────────────────────────
        vlay.addWidget(_hline())
        action_lay = QHBoxLayout()
        action_lay.setSpacing(8)

        self._btn_save = _btn("💾  Speichern", min_w=130)
        self._btn_save.clicked.connect(self._save)

        self._btn_copy = _btn_light("📋  Kopieren")
        self._btn_copy.setToolTip("Gesamten Protokolleintrag in Zwischenablage kopieren")
        self._btn_copy.clicked.connect(self._copy_to_clipboard)

        self._btn_delete = _btn("🗑  Löschen", color="#d32f2f", hover="#b71c1c")
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._delete_entry)

        action_lay.addWidget(self._btn_save)
        action_lay.addWidget(self._btn_copy)
        action_lay.addStretch()
        action_lay.addWidget(self._btn_delete)
        vlay.addLayout(action_lay)

        vlay.addStretch()

        # ── Signal-Verbindungen ──────────────────────────────────────────
        self._f_flug_richtung.currentIndexChanged.connect(self._on_flug_richtung_changed)
        self._f_flugnummer.activated.connect(self._on_flugnummer_activated)

        scroll.setWidget(container)
        return scroll

    # ── Textbausteine UI aufbauen ──────────────────────────────────────────────

    def _build_textbausteine(self):
        """Baut die Textbaustein-Buttons neu auf."""
        # Alles entfernen
        while self._tb_layout.count():
            item = self._tb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        bausteine = textbausteine_laden()
        for gruppe, items in bausteine.items():
            grp_lbl = QLabel(gruppe)
            grp_lbl.setStyleSheet("color:#555; font-size:10px; font-weight:bold; margin-top:2px;")
            self._tb_layout.addWidget(grp_lbl)

            row_w = QWidget()
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(4)

            for item in items:
                text = item["text"]
                short = text if len(text) <= 40 else text[:38] + "…"
                b = QPushButton(short)
                b.setToolTip(text)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setFixedHeight(26)
                b.setStyleSheet(
                    f"QPushButton{{background:#eef4fa;color:{FIORI_BLUE};"
                    "border:1px solid #c0d8f0; border-radius:4px; "
                    "padding:2px 8px; font-size:10px;}}"
                    f"QPushButton:hover{{background:{FIORI_BLUE};color:white;}}"
                )
                b.clicked.connect(lambda checked, t=text: self._insert_baustein(t))
                row_lay.addWidget(b)

            row_lay.addStretch()
            self._tb_layout.addWidget(row_w)

    def _insert_baustein(self, text: str):
        """Fügt Textbaustein an Cursor-Position in die Notiz ein."""
        cursor = self._f_notiz.textCursor()
        cursor.insertText(text + " ")
        self._f_notiz.setTextCursor(cursor)
        self._f_notiz.setFocus()

    def _on_flug_richtung_changed(self, idx: int):
        """Befüllt die Flugnummer-Auswahl passend zur gewählten Flug-Richtung."""
        richtung = self._f_flug_richtung.currentData()
        self._f_flugnummer.blockSignals(True)
        self._f_flugnummer.clear()
        self._f_flugnummer.addItem("", "")
        if richtung == "Abflug":
            for num, dest in _FLUEGE_ABFLUG:
                self._f_flugnummer.addItem(f"{num}  –  {dest}", dest)
        elif richtung == "Ankunft":
            for num, dest in _FLUEGE_ANKUNFT:
                self._f_flugnummer.addItem(f"{num}  –  {dest}", dest)
        self._f_flugnummer.blockSignals(False)
        self._f_flugnummer.lineEdit().setPlaceholderText(
            "Flugnummer wählen oder eingeben …"
        )
        self._f_ziel_herkunft.clear()

    def _on_flugnummer_activated(self, idx: int):
        """Setzt nur das Flugnummern-Kürzel im Feld und füllt Ziel/Herkunft."""
        dest = self._f_flugnummer.itemData(idx)
        display = self._f_flugnummer.itemText(idx)
        if display and "  –  " in display:
            num = display.split("  –  ")[0].strip()
            self._f_flugnummer.lineEdit().setText(num)
            self._f_ziel_herkunft.setText(dest or "")
        else:
            self._f_ziel_herkunft.clear()

    def _open_textbaustein_verwaltung(self):
        dlg = _TextbausteinVerwaltungDialog(self)
        dlg.exec()
        self._build_textbausteine()

    # ── Daten laden / speichern ────────────────────────────────────────────────

    def _refresh_list(self):
        """Liste links neu aufbauen."""
        filter_text = self._search.text().strip()
        kat = self._filter_kat.currentData() or ""
        nur_offen = self._chk_offen.isChecked()

        records = alle_laden(filter_text=filter_text, kategorie=kat, nur_offen=nur_offen)
        self._list_widget.blockSignals(True)
        self._list_widget.clear()

        for r in records:
            erledigt_icon = "✅" if r.get("erledigt") else "🔵"
            fr = r.get("flug_richtung", "")
            flug_icon = "✈" if fr == "Abflug" else ("🛬" if fr == "Ankunft" else "📞")
            passagier = r.get("passagier_name") or r.get("anrufer") or "–"
            flugnummer = r.get("flugnummer") or ""
            hilfeart = r.get("hilfeart") or ""
            datum = r.get("datum", "")
            uhrzeit = r.get("uhrzeit", "")
            line1 = f"{erledigt_icon} {datum}  {uhrzeit}  {flug_icon} {flugnummer}"
            line2 = f"   {passagier}"
            if hilfeart:
                short_ha = hilfeart.split("–")[0].strip() if "–" in hilfeart else hilfeart
                line2 += f"  ·  {short_ha}"
            item = QListWidgetItem(f"{line1}\n{line2}")
            item.setData(Qt.ItemDataRole.UserRole, r["id"])
            if not r.get("erledigt"):
                item.setForeground(QColor("#005a9e"))
            self._list_widget.addItem(item)

        self._list_widget.blockSignals(False)
        total = len(records)
        self._lbl_count.setText(f"{total} Einträge")

    def _on_list_selection(self, current: QListWidgetItem | None, _prev):
        if current is None:
            return
        record_id = current.data(Qt.ItemDataRole.UserRole)
        record = laden_by_id(record_id)
        if record:
            self._load_record(record)

    def _load_record(self, record: dict):
        self._current_id = record["id"]
        passagier = record.get("passagier_name") or ""
        flugnr = record.get("flugnummer") or ""
        self._form_title.setText(
            f"PRM #{record['id']}  –  {passagier}  {flugnr}  {record.get('datum', '')}"
        )
        self._f_datum.setText(record.get("datum", ""))
        self._f_uhrzeit.setText(record.get("uhrzeit", ""))
        idx = _RICHTUNGEN.index(record.get("richtung", "Eingehend")) if record.get("richtung", "") in _RICHTUNGEN else 0
        self._f_richtung.setCurrentIndex(idx)
        kat = record.get("kategorie", "")
        idx_k = _KATEGORIEN.index(kat) if kat in _KATEGORIEN else 0
        self._f_kategorie.setCurrentIndex(idx_k)
        # Flugdaten laden
        fr = record.get("flug_richtung", "")
        fr_idx = next(
            (i for i in range(self._f_flug_richtung.count())
             if self._f_flug_richtung.itemData(i) == fr), 0
        )
        self._f_flug_richtung.blockSignals(True)
        self._f_flug_richtung.setCurrentIndex(fr_idx)
        self._f_flug_richtung.blockSignals(False)
        if fr:
            self._on_flug_richtung_changed(fr_idx)
        self._f_flugnummer.setCurrentText(record.get("flugnummer", ""))
        self._f_ziel_herkunft.setText(record.get("ziel_herkunft", ""))
        self._f_passagier_name.setText(record.get("passagier_name", ""))
        ha = record.get("hilfeart", "")
        ha_idx = _HILFE_ARTEN.index(ha) if ha in _HILFE_ARTEN else 0
        self._f_hilfeart.setCurrentIndex(ha_idx)
        self._f_anrufer.setText(record.get("anrufer", ""))
        self._f_telefon.setText(record.get("telefon", ""))
        self._f_betreff.setText(record.get("betreff", ""))
        self._f_notiz.setPlainText(record.get("notiz", ""))
        self._chk_erledigt.setChecked(bool(record.get("erledigt")))
        self._btn_delete.setEnabled(True)

    def _new_entry(self):
        self._current_id = None
        self._form_title.setText("Neue PRM-Anmeldung")
        self._f_datum.setText(datetime.now().strftime("%d.%m.%Y"))
        self._f_uhrzeit.setText(datetime.now().strftime("%H:%M"))
        self._f_richtung.setCurrentIndex(0)
        self._f_kategorie.setCurrentIndex(0)
        self._f_flug_richtung.setCurrentIndex(0)
        self._f_flugnummer.clear()
        self._f_flugnummer.lineEdit().clear()
        self._f_ziel_herkunft.clear()
        self._f_passagier_name.clear()
        self._f_hilfeart.setCurrentIndex(0)
        self._f_anrufer.clear()
        self._f_telefon.clear()
        self._f_betreff.clear()
        self._f_notiz.clear()
        self._chk_erledigt.setChecked(False)
        self._btn_delete.setEnabled(False)
        self._list_widget.clearSelection()
        self._f_passagier_name.setFocus()

    def _save(self):
        datum = self._f_datum.text().strip()
        uhrzeit = self._f_uhrzeit.text().strip()
        if not datum or not uhrzeit:
            QMessageBox.warning(self, "Pflichtfeld", "Datum und Uhrzeit sind Pflichtfelder.")
            return

        # Flugnummer: bei Dropdown-Auswahl steht ggf. "EW4  –  Berlin …" im Text
        fn_text = self._f_flugnummer.currentText().strip()
        if "  –  " in fn_text:
            fn_text = fn_text.split("  –  ")[0].strip()

        daten = {
            "id": self._current_id,
            "datum": datum,
            "uhrzeit": uhrzeit,
            "flug_richtung": self._f_flug_richtung.currentData() or "",
            "flugnummer": fn_text,
            "ziel_herkunft": self._f_ziel_herkunft.text().strip(),
            "passagier_name": self._f_passagier_name.text().strip(),
            "hilfeart": self._f_hilfeart.currentText(),
            "anrufer": self._f_anrufer.text().strip(),
            "telefon": self._f_telefon.text().strip(),
            "richtung": self._f_richtung.currentText(),
            "kategorie": self._f_kategorie.currentText(),
            "betreff": self._f_betreff.text().strip(),
            "notiz": self._f_notiz.toPlainText().strip(),
            "erledigt": self._chk_erledigt.isChecked(),
        }
        new_id = speichern(daten)
        self._current_id = new_id
        passagier = daten["passagier_name"]
        self._form_title.setText(f"PRM #{new_id}  –  {passagier}  {fn_text}  {datum}")
        self._btn_delete.setEnabled(True)
        self._refresh_list()

        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == new_id:
                self._list_widget.blockSignals(True)
                self._list_widget.setCurrentItem(item)
                self._list_widget.blockSignals(False)
                break

    def _delete_entry(self):
        if not self._current_id:
            return
        if QMessageBox.question(
            self, "Eintrag löschen",
            "Diesen Anruf-Eintrag wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            loeschen(self._current_id)
            self._new_entry()
            self._refresh_list()

    def _copy_to_clipboard(self):
        """Formatiert den aktuellen PRM-Eintrag und kopiert ihn in die Zwischenablage."""
        richtung = self._f_richtung.currentText()
        anruf_icon = "📥 Eingehend" if richtung == "Eingehend" else "📤 Ausgehend"
        fr = self._f_flug_richtung.currentData() or ""
        flug_icon = "✈ Abflug" if fr == "Abflug" else ("🛬 Ankunft" if fr == "Ankunft" else "–")
        fn_text = self._f_flugnummer.currentText().strip()
        if "  –  " in fn_text:
            fn_text = fn_text.split("  –  ")[0].strip()
        lines = [
            f"♿ PRM-ANMELDUNG – CGN",
            f"─────────────────────────────────────",
            f"Datum / Uhrzeit : {self._f_datum.text()}  {self._f_uhrzeit.text()}",
            f"Anruf           : {anruf_icon}",
            f"─────────────────────────────────────",
            f"Flug            : {flug_icon}",
            f"Flugnummer      : {fn_text or '–'}",
            f"Ziel / Herkunft : {self._f_ziel_herkunft.text() or '–'}",
            f"─────────────────────────────────────",
            f"Passagier       : {self._f_passagier_name.text() or '–'}",
            f"Hilfeart        : {self._f_hilfeart.currentText() or '–'}",
            f"─────────────────────────────────────",
            f"Anrufer/Kontakt : {self._f_anrufer.text() or '–'}",
            f"Telefon         : {self._f_telefon.text() or '–'}",
            f"Kategorie       : {self._f_kategorie.currentText() or '–'}",
            f"Betreff         : {self._f_betreff.text() or '–'}",
            f"─────────────────────────────────────",
            "",
            self._f_notiz.toPlainText(),
            "",
            f"Status          : {'✅ Erledigt' if self._chk_erledigt.isChecked() else '🔵 Offen'}",
        ]
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Kopiert", "PRM-Eintrag wurde in die Zwischenablage kopiert.")

    # ── Refresh (aufgerufen beim Tab-Wechsel) ──────────────────────────────────

    def refresh(self):
        self._build_textbausteine()
        self._refresh_list()
