"""
Übergabe-Widget
Erstellt und verwaltet Tagdienst- und Nachtdienst-Übergabeprotokolle
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSplitter, QTextEdit, QLineEdit,
    QSpinBox, QComboBox, QFormLayout, QMessageBox, QSizePolicy,
    QDateEdit, QDialog, QDialogButtonBox, QListWidget, QFileDialog,
    QTimeEdit
)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QFont, QColor

from config import (
    FIORI_BLUE, FIORI_TEXT, FIORI_WHITE, FIORI_BORDER,
    FIORI_SUCCESS, FIORI_ERROR, FIORI_SIDEBAR_BG
)
from functions.uebergabe_functions import (
    erstelle_protokoll, aktualisiere_protokoll,
    lade_protokolle, lade_protokoll_by_id, loesche_protokoll,
    schliesse_protokoll_ab,
    speichere_fahrzeug_notizen, lade_fahrzeug_notizen,
    speichere_handy_eintraege, lade_handy_eintraege,
    speichere_verspaetungen, lade_verspaetungen,
)
from functions.fahrzeug_functions import (
    lade_alle_fahrzeuge,
    lade_termine as lade_fahrzeug_termine,
    aktueller_status as aktueller_fahrzeug_status,
    lade_schaeden_letzte_tage,
    markiere_schaden_gesendet,
)
from functions.verspaetung_db import lade_verspaetungen_fuer_datum as lade_vsp_aus_db
from functions.verspaetung_db import lade_verspaetungen_letzter_zeitraum as lade_vsp_7_tage
from functions.verspaetung_db import verspaetung_speichern as vsp_db_speichern
from functions.mitarbeiter_functions import lade_mitarbeiter_namen

# ── Farben ──────────────────────────────────────────────────────────────────
_TAG_COLOR    = "#e67e22"   # Orange für Tagdienst
_NACHT_COLOR  = "#2c3e50"   # Dunkelblau für Nachtdienst
_OFFEN_BG     = "#fff8e1"
_ABGES_BG     = "#e8f5e9"


class _ProtokolListItem(QFrame):
    """Kompaktes Listenelement für ein Protokoll in der Seitenleiste."""

    def __init__(self, protokoll: dict, parent=None):
        super().__init__(parent)
        self._id = protokoll["id"]
        self._setup(protokoll)

    def _setup(self, p: dict):
        typ     = p.get("schicht_typ", "tagdienst")
        datum   = p.get("datum", "")
        status  = p.get("status", "offen")
        erstell = p.get("ersteller", "–")

        # Datum lesbar formatieren
        try:
            d = datetime.strptime(datum, "%Y-%m-%d")
            datum_str = d.strftime("%d.%m.%Y")
        except Exception:
            datum_str = datum

        self._farbe  = _TAG_COLOR if typ == "tagdienst" else _NACHT_COLOR
        farbe  = self._farbe
        symbol = "☀" if typ == "tagdienst" else "🌙"
        label  = "Tagdienst" if typ == "tagdienst" else "Nachtdienst"
        self._bg_base = _OFFEN_BG if status == "offen" else _ABGES_BG

        self._apply_style(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(62)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        top = QHBoxLayout()
        typ_lbl = QLabel(f"{symbol} {label}")
        typ_lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        typ_lbl.setStyleSheet(f"color: {farbe}; border: none;")

        stat_lbl = QLabel("✓ abgeschlossen" if status == "abgeschlossen" else "· offen")
        stat_lbl.setFont(QFont("Arial", 9))
        stat_lbl.setStyleSheet(
            f"color: {FIORI_SUCCESS}; border: none;"
            if status == "abgeschlossen"
            else "color: #999; border: none;"
        )
        top.addWidget(typ_lbl)
        top.addStretch()
        top.addWidget(stat_lbl)

        datum_lbl = QLabel(f"📅 {datum_str}  |  👤 {erstell}")
        datum_lbl.setFont(QFont("Arial", 9))
        datum_lbl.setStyleSheet("color: #555; border: none;")

        layout.addLayout(top)
        layout.addWidget(datum_lbl)

        # Suchtext für Filterung
        self._search_text = f"{datum_str} {datum} {erstell} {label} {typ} {status}"

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #cfe0f5;
                    border: 2px solid {self._farbe};
                    border-left: 6px solid {self._farbe};
                    border-radius: 4px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {self._bg_base};
                    border: 1px solid #ddd;
                    border-left: 4px solid {self._farbe};
                    border-radius: 4px;
                }}
            """)

    def set_active(self, active: bool):
        self._apply_style(active)

    @property
    def protokoll_id(self) -> int:
        return self._id


class UebergabeWidget(QWidget):
    """Haupt-Widget für Tagdienst- und Nachtdienst-Übergabeprotokolle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._aktives_protokoll_id: int | None = None
        self._ist_neu = False
        self._aktueller_typ = "tagdienst"
        self._list_items: dict[int, "_ProtokolListItem"] = {}
        _today = date.today()
        self._nav_jahr  = _today.year
        self._nav_monat = _today.month
        self._fahrzeug_notiz_widgets: dict = {}
        self._handy_eintraege_widgets: list = []  # list of (nr_edit, notiz_edit)
        self._verspaetungen_widgets: list = []   # list of (name_edit, soll_edit, ist_edit)
        self._verspaetungen_db_entries: list = []  # auto-geladene DB-Einträge (verspaetungen.db)
        self._build_ui()
        self.refresh()

    # ── UI-Aufbau ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        root.addWidget(self._build_header())

        # Hauptbereich: Liste | Formular
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        splitter.addWidget(self._build_liste())
        splitter.addWidget(self._build_formular())
        splitter.setSizes([300, 700])

        root.addWidget(splitter, 1)

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setStyleSheet(f"background-color: {FIORI_SIDEBAR_BG};")
        header.setFixedHeight(64)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(12)

        title = QLabel("📋 Übergabeprotokolle")
        title.setFont(QFont("Arial", 17, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        layout.addStretch()

        # Aktualisieren
        btn_refresh = QPushButton("🔄 Aktualisieren")
        btn_refresh.setFont(QFont("Arial", 10))
        btn_refresh.setFixedHeight(36)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(
            "QPushButton{background:#fff;color:#333;border:1px solid #ccc;"
            "border-radius:4px;padding:2px 14px;font-weight:bold;}"
            "QPushButton:hover{background:#e8eaf0;}"
        )
        btn_refresh.setToolTip("Liste der Protokolle neu laden")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

        # Neues Tagdienst-Protokoll
        btn_tag = QPushButton("☀  Neues Tagdienst-Protokoll")
        btn_tag.setFont(QFont("Arial", 11))
        btn_tag.setFixedHeight(40)
        btn_tag.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tag.setStyleSheet(f"""
            QPushButton {{
                background-color: {_TAG_COLOR};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #e08010; }}
        """)
        btn_tag.setToolTip("Neues Tagdienst-Protokoll erstellen (07:00 – 19:00)")
        btn_tag.clicked.connect(lambda: self._neues_protokoll("tagdienst"))

        # Neues Nachtdienst-Protokoll
        btn_nacht = QPushButton("🌙  Neues Nachtdienst-Protokoll")
        btn_nacht.setFont(QFont("Arial", 11))
        btn_nacht.setFixedHeight(40)
        btn_nacht.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nacht.setStyleSheet(f"""
            QPushButton {{
                background-color: {_NACHT_COLOR};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3d566e; }}
        """)
        btn_nacht.setToolTip("Neues Nachtdienst-Protokoll erstellen (19:00 – 07:00)")
        btn_nacht.clicked.connect(lambda: self._neues_protokoll("nachtdienst"))

        layout.addWidget(btn_tag)
        layout.addWidget(btn_nacht)
        return header

    def _build_liste(self) -> QWidget:
        container = QWidget()
        container.setMinimumWidth(260)
        container.setMaximumWidth(360)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Monats-Navigation
        nav_bar = QFrame()
        nav_bar.setStyleSheet("background-color: #e8eaf0; border-bottom: 1px solid #c5c8d4;")
        nav_bar.setFixedHeight(40)
        nl = QHBoxLayout(nav_bar)
        nl.setContentsMargins(6, 4, 6, 4)
        nl.setSpacing(4)
        self._btn_nav_prev = QPushButton("◄")
        self._btn_nav_prev.setFixedSize(28, 28)
        self._btn_nav_prev.setStyleSheet(
            "QPushButton{background:#fff;border:1px solid #bbb;border-radius:4px;font-size:11px;}"
            "QPushButton:hover{background:#d0d4e8;}"
        )
        self._btn_nav_prev.setToolTip("Vorherigen Monat anzeigen")
        self._btn_nav_prev.clicked.connect(self._nav_prev_monat)
        self._lbl_nav_monat = QLabel()
        self._lbl_nav_monat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_nav_monat.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self._lbl_nav_monat.setStyleSheet("border: none; color: #333;")
        self._btn_nav_next = QPushButton("►")
        self._btn_nav_next.setFixedSize(28, 28)
        self._btn_nav_next.setStyleSheet(
            "QPushButton{background:#fff;border:1px solid #bbb;border-radius:4px;font-size:11px;}"
            "QPushButton:hover{background:#d0d4e8;}"
        )
        self._btn_nav_next.setToolTip("Nächsten Monat anzeigen")
        self._btn_nav_next.clicked.connect(self._nav_next_monat)
        nl.addWidget(self._btn_nav_prev)
        nl.addWidget(self._lbl_nav_monat, 1)
        nl.addWidget(self._btn_nav_next)
        layout.addWidget(nav_bar)

        # Filter-Leiste
        filter_bar = QFrame()
        filter_bar.setStyleSheet("background-color: #f0f2f4; border-bottom: 1px solid #ddd;")
        filter_bar.setFixedHeight(44)
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(8, 4, 8, 4)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["Alle", "Tagdienst", "Nachtdienst"])
        self._filter_combo.setStyleSheet("background: white; border: 1px solid #ccc; border-radius: 3px; padding: 2px 6px;")
        self._filter_combo.setToolTip("Protokolle nach Schichttyp filtern")
        self._filter_combo.currentIndexChanged.connect(self._lade_liste)
        fl.addWidget(QLabel("Anzeigen:"))
        fl.addWidget(self._filter_combo, 1)
        layout.addWidget(filter_bar)

        # Suchleiste
        suche_bar = QFrame()
        suche_bar.setStyleSheet("background: #f8f9fb; border-bottom: 1px solid #ddd;")
        suche_bar.setFixedHeight(40)
        sl = QHBoxLayout(suche_bar)
        sl.setContentsMargins(8, 4, 8, 4)
        sl.setSpacing(6)
        suche_icon = QLabel("🔍")
        suche_icon.setStyleSheet("border:none; font-size:13px;")
        self._ue_search = QLineEdit()
        self._ue_search.setPlaceholderText("Datum, Ersteller, Typ ...")
        self._ue_search.setStyleSheet(
            "background:white; border:1px solid #ccc; border-radius:3px;"
            "padding:3px 8px; font-size:11px;"
        )
        self._ue_search.setToolTip(
            "Protokollliste filtern \u2013 sucht in Datum, Ersteller und Schichttyp.\n"
            "Beispiel: \"12.02\" zeigt alle Protokolle vom 12. Februar."
        )
        self._ue_search.textChanged.connect(self._apply_protokoll_filter)
        sl.addWidget(suche_icon)
        sl.addWidget(self._ue_search, 1)
        layout.addWidget(suche_bar)

        # Scrollbare Liste
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self._liste_container = QWidget()
        self._liste_layout = QVBoxLayout(self._liste_container)
        self._liste_layout.setContentsMargins(8, 8, 8, 8)
        self._liste_layout.setSpacing(4)
        self._liste_layout.addStretch()

        scroll.setWidget(self._liste_container)
        layout.addWidget(scroll, 1)
        return container

    def _build_formular(self) -> QWidget:
        self._form_container = QWidget()
        self._form_container.setStyleSheet("background-color: white;")
        outer = QVBoxLayout(self._form_container)
        outer.setContentsMargins(0, 0, 0, 0)

        # Formular-Header
        self._form_header = QFrame()
        self._form_header.setFixedHeight(50)
        self._form_header.setStyleSheet(f"background-color: #eef4fa; border-bottom: 1px solid {FIORI_BORDER};")
        fhl = QHBoxLayout(self._form_header)
        fhl.setContentsMargins(20, 0, 20, 0)
        self._form_titel = QLabel("Protokoll auswählen oder neu erstellen")
        self._form_titel.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self._form_titel.setStyleSheet(f"color: {FIORI_TEXT};")
        fhl.addWidget(self._form_titel)
        fhl.addStretch()
        outer.addWidget(self._form_header)

        # Formular-Scroll-Bereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        form_widget = QWidget()
        form_widget.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(form_widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # FormLayout für Felder
        fl = QFormLayout()
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fl.setSpacing(10)

        # Datum
        self._f_datum = QDateEdit()
        self._f_datum.setCalendarPopup(True)
        self._f_datum.setDate(QDate.currentDate())
        self._f_datum.setDisplayFormat("dd.MM.yyyy")
        self._f_datum.setStyleSheet(self._field_style())
        fl.addRow("Datum:", self._f_datum)

        # Beginn
        self._f_beginn = QLineEdit()
        self._f_beginn.setPlaceholderText("z.B. 07:00")
        self._f_beginn.setStyleSheet(self._field_style())
        fl.addRow("Beginn:", self._f_beginn)

        # Ende
        self._f_ende = QLineEdit()
        self._f_ende.setPlaceholderText("z.B. 19:00")
        self._f_ende.setStyleSheet(self._field_style())
        fl.addRow("Ende:", self._f_ende)

        # Patienten
        self._f_patienten = QSpinBox()
        self._f_patienten.setRange(0, 999)
        self._f_patienten.setStyleSheet(self._field_style())
        fl.addRow("Patienten:", self._f_patienten)

        # Ersteller
        self._f_ersteller = QLineEdit()
        self._f_ersteller.setPlaceholderText("Name Protokollersteller")
        self._f_ersteller.setStyleSheet(self._field_style())
        fl.addRow("Ersteller:", self._f_ersteller)

        # Abzeichner
        self._f_abzeichner = QLineEdit()
        self._f_abzeichner.setPlaceholderText("Name Abzeichner (bei Abschluss)")
        self._f_abzeichner.setStyleSheet(self._field_style())
        fl.addRow("Abzeichner:", self._f_abzeichner)

        layout.addLayout(fl)

        # Ereignisse / Vorfälle
        layout.addWidget(self._section_label("⚠ Ereignisse / Vorfälle"))
        self._f_ereignisse = QTextEdit()
        self._f_ereignisse.setPlaceholderText("Besondere Ereignisse, Vorfälle, Einsätze ...")
        self._f_ereignisse.setFixedHeight(110)
        self._f_ereignisse.setStyleSheet(self._textarea_style())
        layout.addWidget(self._f_ereignisse)

        # Fahrzeuge
        layout.addWidget(self._section_label("🚗 Fahrzeuge"))
        self._fahrzeug_section = QFrame()
        self._fahrzeug_section.setStyleSheet("QFrame { border: none; }")
        self._fahrzeug_section_layout = QVBoxLayout(self._fahrzeug_section)
        self._fahrzeug_section_layout.setContentsMargins(0, 0, 0, 0)
        self._fahrzeug_section_layout.setSpacing(4)
        _hint = QLabel("👁 Fahrzeuge werden beim Öffnen eines Protokolls geladen")
        _hint.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
        self._fahrzeug_section_layout.addWidget(_hint)
        layout.addWidget(self._fahrzeug_section)

        # Handys
        layout.addWidget(self._section_label("📱 Handys"))
        self._handy_section = QFrame()
        self._handy_section.setStyleSheet("QFrame { border: none; }")
        self._handy_section_layout = QVBoxLayout(self._handy_section)
        self._handy_section_layout.setContentsMargins(0, 0, 0, 0)
        self._handy_section_layout.setSpacing(4)
        _handy_hint = QLabel("👁 Noch keine Geräte eingetragen")
        _handy_hint.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
        self._handy_section_layout.addWidget(_handy_hint)
        layout.addWidget(self._handy_section)
        self._btn_add_handy = QPushButton("➕ Gerät hinzufügen")
        self._btn_add_handy.setFixedHeight(28)
        self._btn_add_handy.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add_handy.setStyleSheet(
            "QPushButton{background:#eef4fa;border:1px solid #b0c8e8;"
            "border-radius:4px;padding:2px 10px;color:#0a6ed1;font-size:11px;}"
            "QPushButton:hover{background:#d0e4f5;}"
        )
        self._btn_add_handy.clicked.connect(self._add_handy_row)
        layout.addWidget(self._btn_add_handy)

        # Verspätete Mitarbeiter
        layout.addWidget(self._section_label("🕐 Verspätete Mitarbeiter"))
        self._verspaetungen_section = QFrame()
        self._verspaetungen_section.setStyleSheet("QFrame { border: none; }")
        self._verspaetungen_section_layout = QVBoxLayout(self._verspaetungen_section)
        self._verspaetungen_section_layout.setContentsMargins(0, 0, 0, 0)
        self._verspaetungen_section_layout.setSpacing(4)
        _vsp_hint = QLabel("✅ Keine Verspätungen eingetragen – ➕ hinzufügen")
        _vsp_hint.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
        self._verspaetungen_section_layout.addWidget(_vsp_hint)
        layout.addWidget(self._verspaetungen_section)
        _vsp_btn_row = QHBoxLayout()
        _vsp_btn_row.setSpacing(6)
        self._btn_add_verspaetung = QPushButton("➕ Manuell hinzufügen")
        self._btn_add_verspaetung.setFixedHeight(28)
        self._btn_add_verspaetung.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add_verspaetung.setStyleSheet(
            "QPushButton{background:#fff0e0;border:1px solid #f0c080;"
            "border-radius:4px;padding:2px 10px;color:#b06000;font-size:11px;}"
            "QPushButton:hover{background:#ffe0b0;}"
        )
        self._btn_add_verspaetung.clicked.connect(self._manuell_verspaetung_erfassen)
        self._btn_add_verspaetung_db_picker = QPushButton("👤 Aus DB wählen")
        self._btn_add_verspaetung_db_picker.setFixedHeight(28)
        self._btn_add_verspaetung_db_picker.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_add_verspaetung_db_picker.setStyleSheet(
            "QPushButton{background:#e8f4f9;border:1px solid #90cbe0;"
            "border-radius:4px;padding:2px 10px;color:#1a5b78;font-size:11px;}"
            "QPushButton:hover{background:#cde8f5;}"
        )
        self._btn_add_verspaetung_db_picker.clicked.connect(self._pick_mitarbeiter_from_db)
        self._btn_pick_vsp_db = QPushButton("📋 Aus Verspätungen wählen")
        self._btn_pick_vsp_db.setFixedHeight(28)
        self._btn_pick_vsp_db.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_pick_vsp_db.setStyleSheet(
            "QPushButton{background:#f0e8ff;border:1px solid #b090e0;"
            "border-radius:4px;padding:2px 10px;color:#5a2d8a;font-size:11px;}"
            "QPushButton:hover{background:#e0d0ff;}"
        )
        self._btn_pick_vsp_db.clicked.connect(self._pick_from_verspaetungen_db)
        _vsp_btn_row.addWidget(self._btn_add_verspaetung)
        _vsp_btn_row.addWidget(self._btn_add_verspaetung_db_picker)
        _vsp_btn_row.addWidget(self._btn_pick_vsp_db)
        _vsp_btn_row.addStretch()
        layout.addLayout(_vsp_btn_row)

        # Übergabe-Notiz
        layout.addWidget(self._section_label("📝 Übergabe-Notiz (für die Folgeschicht)"))
        self._f_notiz = QTextEdit()
        self._f_notiz.setPlaceholderText("Wichtige Informationen für die Folgeschicht ...")
        self._f_notiz.setFixedHeight(110)
        self._f_notiz.setStyleSheet(self._textarea_style())
        layout.addWidget(self._f_notiz)

        layout.addSpacing(8)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_speichern = QPushButton("💾  Speichern")
        self._btn_speichern.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self._btn_speichern.setFixedHeight(40)
        self._btn_speichern.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_speichern.setToolTip("Protokoll zwischenspeichern – bleibt als 'offen' bearbeitbar")
        self._btn_speichern.setStyleSheet(f"""
            QPushButton {{
                background-color: {FIORI_BLUE};
                color: white; border: none;
                border-radius: 4px; padding: 4px 24px;
            }}
            QPushButton:hover {{ background-color: #0855a9; }}
            QPushButton:disabled {{ background-color: #ccc; color: #999; }}
        """)
        self._btn_speichern.clicked.connect(self._speichern)
        self._btn_speichern.setEnabled(False)

        self._btn_abschliessen = QPushButton("✓  Abschließen")
        self._btn_abschliessen.setFont(QFont("Arial", 11))
        self._btn_abschliessen.setFixedHeight(40)
        self._btn_abschliessen.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_abschliessen.setToolTip(
            "Protokoll endgültig abschließen. Danach ist keine Bearbeitung mehr möglich.\n"
            "Ein Abzeichner-Name wird benötigt. Das Protokoll erhält den Status 'abgeschlossen'."
        )
        self._btn_abschliessen.setStyleSheet(f"""
            QPushButton {{
                background-color: {FIORI_SUCCESS};
                color: white; border: none;
                border-radius: 4px; padding: 4px 24px;
            }}
            QPushButton:hover {{ background-color: #0d6831; }}
            QPushButton:disabled {{ background-color: #ccc; color: #999; }}
        """)
        self._btn_abschliessen.clicked.connect(self._abschliessen)
        self._btn_abschliessen.setEnabled(False)

        self._btn_email = QPushButton("📧  E-Mail")
        self._btn_email.setFont(QFont("Arial", 11))
        self._btn_email.setFixedHeight(40)
        self._btn_email.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_email.setToolTip("Erstellt einen Outlook-Entwurf mit den Protokolldaten als E-Mail-Text")
        self._btn_email.setStyleSheet("""
            QPushButton {
                background-color: #0078a8;
                color: white; border: none;
                border-radius: 4px; padding: 4px 20px;
            }
            QPushButton:hover { background-color: #005f8a; }
            QPushButton:disabled { background-color: #ccc; color: #999; }
        """)
        self._btn_email.clicked.connect(self._email_erstellen)
        self._btn_email.setEnabled(False)

        self._btn_loeschen = QPushButton("🗑  Löschen")
        self._btn_loeschen.setFont(QFont("Arial", 11))
        self._btn_loeschen.setFixedHeight(40)
        self._btn_loeschen.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_loeschen.setToolTip("Dieses Protokoll dauerhaft aus der Datenbank löschen (nicht wiederherstellbar)")
        self._btn_loeschen.setStyleSheet(f"""
            QPushButton {{
                background-color: #e0e0e0;
                color: #555; border: none;
                border-radius: 4px; padding: 4px 18px;
            }}
            QPushButton:hover {{ background-color: #ffcccc; color: #a00; }}
            QPushButton:disabled {{ background-color: #eee; color: #bbb; }}
        """)
        self._btn_loeschen.clicked.connect(self._loeschen)
        self._btn_loeschen.setEnabled(False)

        btn_row.addWidget(self._btn_speichern)
        btn_row.addWidget(self._btn_abschliessen)
        btn_row.addWidget(self._btn_email)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_loeschen)
        layout.addLayout(btn_row)

        abschluss_info = QLabel(
            "ℹ️  <b>Speichern</b> = Entwurf, jederzeit bearbeitbar.  "
            "<b>Abschließen</b> = endgültig abschließen (kein Bearbeiten mehr möglich) – "
            "Abzeichner-Name wird benötigt.  "
            "<b>E-Mail</b> = Outlook-Entwurf mit Protokollinhalt erstellen."
        )
        abschluss_info.setWordWrap(True)
        abschluss_info.setTextFormat(Qt.TextFormat.RichText)
        abschluss_info.setStyleSheet(
            "background: #e8f4fb; border: 1px solid #b0d8f0; border-radius: 5px; "
            "padding: 7px 12px; color: #1a4a6b; font-size: 11px;"
        )
        layout.addWidget(abschluss_info)
        layout.addStretch()

        scroll.setWidget(form_widget)
        outer.addWidget(scroll, 1)
        return self._form_container

    # ── Hilfsmethoden ──────────────────────────────────────────────────────────

    def _field_style(self) -> str:
        return (
            "border: 1px solid #ccc; border-radius: 3px; "
            "padding: 4px 8px; background: white; min-width: 240px;"
        )

    def _textarea_style(self) -> str:
        return (
            "border: 1px solid #ccc; border-radius: 3px; "
            "padding: 6px; background: white; font-size: 12px;"
        )

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        lbl.setStyleSheet(
            f"color: {FIORI_TEXT}; border-bottom: 1px solid #e0e0e0; "
            f"padding-bottom: 4px; margin-top: 6px;"
        )
        return lbl

    # ── Liste laden ────────────────────────────────────────────────────────────

    def _lade_liste(self):
        # Alte Einträge entfernen (ohne den Stretch am Ende)
        while self._liste_layout.count() > 1:
            item = self._liste_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._update_nav_label()
        filter_idx = self._filter_combo.currentIndex()
        typ_filter = {0: None, 1: "tagdienst", 2: "nachtdienst"}.get(filter_idx)

        monat_str = f"{self._nav_jahr}-{self._nav_monat:02d}"
        protokolle = lade_protokolle(schicht_typ=typ_filter, monat=monat_str)

        self._list_items.clear()

        if not protokolle:
            lbl = QLabel("Keine Protokolle vorhanden")
            lbl.setStyleSheet("color: #999; padding: 16px; font-size: 12px; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._liste_layout.insertWidget(0, lbl)
            return

        for p in protokolle:
            item = _ProtokolListItem(p)
            pid = p["id"]
            self._list_items[pid] = item
            item.mousePressEvent = lambda e, i=pid: self._item_clicked(i)
            # Bereits aktives Item sofort hervorheben
            if pid == self._aktives_protokoll_id:
                item.set_active(True)
            self._liste_layout.insertWidget(
                self._liste_layout.count() - 1,  # vor dem Stretch
                item
            )
        self._apply_protokoll_filter()

    def _apply_protokoll_filter(self):
        """Filtert die Protokollliste nach dem eingegebenen Suchtext."""
        text = self._ue_search.text().strip().lower()
        for pid, item in self._list_items.items():
            if not text:
                item.setVisible(True)
            else:
                item.setVisible(text in getattr(item, "_search_text", "").lower())

    # ── Item-Auswahl ────────────────────────────────────────────────────────────
    def _nav_prev_monat(self):
        if self._nav_monat == 1:
            self._nav_monat = 12
            self._nav_jahr -= 1
        else:
            self._nav_monat -= 1
        self._lade_liste()

    def _nav_next_monat(self):
        if self._nav_monat == 12:
            self._nav_monat = 1
            self._nav_jahr += 1
        else:
            self._nav_monat += 1
        self._lade_liste()

    def _update_nav_label(self):
        _MONATE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
                   "Juli", "August", "September", "Oktober", "November", "Dezember"]
        self._lbl_nav_monat.setText(
            f"{_MONATE[self._nav_monat]} {self._nav_jahr}"
        )
    def _item_clicked(self, protokoll_id: int):
        """Item in der Liste anklicken: altes deaktivieren, neues aktivieren."""
        for pid, itm in self._list_items.items():
            itm.set_active(pid == protokoll_id)
        self._lade_protokoll_in_form(protokoll_id)

    # ── Formular befüllen ──────────────────────────────────────────────────────

    def _lade_protokoll_in_form(self, protokoll_id: int):
        p = lade_protokoll_by_id(protokoll_id)
        if not p:
            return

        self._aktives_protokoll_id = protokoll_id
        # Hervorhebung synchron halten
        for pid, itm in self._list_items.items():
            itm.set_active(pid == protokoll_id)
        self._ist_neu = False
        self._aktueller_typ = p.get("schicht_typ", "tagdienst")

        typ_label = "☀ Tagdienst" if self._aktueller_typ == "tagdienst" else "🌙 Nachtdienst"
        status = p.get("status", "offen")
        self._form_titel.setText(
            f"{typ_label}-Protokoll  –  ID #{protokoll_id}"
            + ("  [abgeschlossen]" if status == "abgeschlossen" else "")
        )
        farbe = _TAG_COLOR if self._aktueller_typ == "tagdienst" else _NACHT_COLOR
        self._form_header.setStyleSheet(
            f"background-color: {farbe}22; border-bottom: 1px solid {farbe};"
        )
        self._form_titel.setStyleSheet(f"color: {farbe};")

        # Felder setzen
        try:
            qd = QDate.fromString(p.get("datum", ""), "yyyy-MM-dd")
            if qd.isValid():
                self._f_datum.setDate(qd)
        except Exception:
            pass
        self._f_beginn.setText(p.get("beginn_zeit", ""))
        self._f_ende.setText(p.get("ende_zeit", ""))
        self._f_patienten.setValue(int(p.get("patienten_anzahl") or 0))
        self._f_ersteller.setText(p.get("ersteller", ""))
        self._f_abzeichner.setText(p.get("abzeichner", ""))
        self._f_ereignisse.setPlainText(p.get("ereignisse", ""))
        self._f_notiz.setPlainText(p.get("uebergabe_notiz", ""))
        self._rebuild_fahrzeug_section(protokoll_id)
        self._rebuild_handy_section(protokoll_id)
        self._rebuild_verspaetungen_section(protokoll_id)

        abges = (status == "abgeschlossen")
        self._btn_speichern.setEnabled(not abges)
        self._btn_abschliessen.setEnabled(not abges)
        self._btn_loeschen.setEnabled(True)
        self._btn_email.setEnabled(True)

        for w in [self._f_datum, self._f_beginn, self._f_ende,
                  self._f_patienten, self._f_ersteller, self._f_abzeichner,
                  self._f_ereignisse, self._f_notiz, self._btn_add_handy,
                  self._btn_add_verspaetung]:
            w.setEnabled(not abges)
        for w in self._fahrzeug_notiz_widgets.values():
            w.setEnabled(not abges)
        for nr, notiz in self._handy_eintraege_widgets:
            nr.setEnabled(not abges)
            notiz.setEnabled(not abges)
        for n, s, i in self._verspaetungen_widgets:
            n.setEnabled(not abges)
            s.setEnabled(not abges)
            i.setEnabled(not abges)

    def _neues_protokoll(self, typ: str):
        """Öffnet ein leeres Formular für ein neues Protokoll."""
        self._aktives_protokoll_id = None
        self._ist_neu = True
        self._aktueller_typ = typ

        farbe = _TAG_COLOR if typ == "tagdienst" else _NACHT_COLOR
        typ_label = "☀ Tagdienst" if typ == "tagdienst" else "🌙 Nachtdienst"
        self._form_titel.setText(f"Neues {typ_label}-Protokoll")
        self._form_header.setStyleSheet(
            f"background-color: {farbe}22; border-bottom: 1px solid {farbe};"
        )
        self._form_titel.setStyleSheet(f"color: {farbe};")

        # Felder leeren + Zeiten je nach Diensttyp vorbelegen
        self._f_datum.setDate(QDate.currentDate())
        if typ == "tagdienst":
            self._f_beginn.setText("07:00")
            self._f_ende.setText("19:00")
        else:
            self._f_beginn.setText("19:00")
            self._f_ende.setText("07:00")
        self._f_patienten.setValue(0)
        self._f_ersteller.setText("")
        self._f_abzeichner.setText("")
        self._f_ereignisse.clear()
        self._f_notiz.clear()
        self._rebuild_fahrzeug_section(None)
        self._rebuild_handy_section(None)
        self._rebuild_verspaetungen_section(None)

        for w in [self._f_datum, self._f_beginn, self._f_ende,
                  self._f_patienten, self._f_ersteller, self._f_abzeichner,
                  self._f_ereignisse, self._f_notiz, self._btn_add_handy,
                  self._btn_add_verspaetung]:
            w.setEnabled(True)
        for w in self._fahrzeug_notiz_widgets.values():
            w.setEnabled(True)

        self._btn_speichern.setEnabled(True)
        self._btn_abschliessen.setEnabled(False)
        self._btn_loeschen.setEnabled(False)
        self._btn_email.setEnabled(False)

    # ── Aktionen ───────────────────────────────────────────────────────────────

    def _speichern(self):
        datum_str = self._f_datum.date().toString("yyyy-MM-dd")

        kwargs = dict(
            beginn_zeit      = self._f_beginn.text().strip(),
            ende_zeit        = self._f_ende.text().strip(),
            patienten_anzahl = self._f_patienten.value(),
            ereignisse       = self._f_ereignisse.toPlainText().strip(),
            uebergabe_notiz  = self._f_notiz.toPlainText().strip(),
            ersteller        = self._f_ersteller.text().strip(),
        )

        try:
            if self._ist_neu:
                new_id = erstelle_protokoll(
                    datum=datum_str,
                    schicht_typ=self._aktueller_typ,
                    **kwargs
                )
                self._aktives_protokoll_id = new_id
                self._ist_neu = False
                self._btn_abschliessen.setEnabled(True)
                self._btn_loeschen.setEnabled(True)
                self._btn_email.setEnabled(True)
                QMessageBox.information(
                    self, "Gespeichert",
                    f"Protokoll #{new_id} wurde erfolgreich gespeichert."
                )
            else:
                aktualisiere_protokoll(
                    protokoll_id=self._aktives_protokoll_id,
                    abzeichner=self._f_abzeichner.text().strip(),
                    status="offen",
                    **kwargs
                )
                QMessageBox.information(
                    self, "Gespeichert",
                    f"Protokoll #{self._aktives_protokoll_id} wurde aktualisiert."
                )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{e}")
            return

        self._lade_liste()
        # Notizen + Handy-Einträge speichern
        if self._aktives_protokoll_id:
            notizen_fz = {
                fid: w.text().strip()
                for fid, w in self._fahrzeug_notiz_widgets.items()
            }
            speichere_fahrzeug_notizen(self._aktives_protokoll_id, notizen_fz)
            eintraege_handy = [
                (nr.text().strip(), notiz.text().strip())
                for nr, notiz in self._handy_eintraege_widgets
                if nr.text().strip()
            ]
            speichere_handy_eintraege(self._aktives_protokoll_id, eintraege_handy)
            # Manuell hinzugefügte Einträge
            eintraege_vsp = [
                (n.text().strip(), s.text().strip(), i.text().strip())
                for n, s, i in self._verspaetungen_widgets
                if n.text().strip()
            ]
            # Auch auto-geladene DB-Einträge (blaue Zeilen) persistieren,
            # sofern nicht schon als manuelle Zeile vorhanden
            existing_keys = {(name, soll) for name, soll, _ in eintraege_vsp}
            for db_e in self._verspaetungen_db_entries:
                ma   = db_e.get("mitarbeiter", "")
                soll = db_e.get("dienstbeginn", "")
                ist  = db_e.get("dienstantritt", "")
                if ma and (ma, soll) not in existing_keys:
                    eintraege_vsp.append((ma, soll, ist))
                    existing_keys.add((ma, soll))  # sofort aktualisieren → keine Dopplung
            speichere_verspaetungen(self._aktives_protokoll_id, eintraege_vsp)

    def _abschliessen(self):
        if self._aktives_protokoll_id is None:
            return
        abzeichner = self._f_abzeichner.text().strip()
        if not abzeichner:
            QMessageBox.warning(self, "Kein Abzeichner",
                                "Bitte trage einen Abzeichner ein, bevor du das Protokoll abschließt.")
            return

        antwort = QMessageBox.question(
            self, "Protokoll abschließen",
            f"Protokoll #{self._aktives_protokoll_id} als abgeschlossen markieren?\n\n"
            f"Abzeichner: {abzeichner}\n\nDanach ist das Protokoll schreibgeschützt.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return

        # Zuerst aktuelle Änderungen speichern
        self._speichern()

        schliesse_protokoll_ab(self._aktives_protokoll_id, abzeichner)
        self._lade_protokoll_in_form(self._aktives_protokoll_id)
        self._lade_liste()

    def _loeschen(self):
        if self._aktives_protokoll_id is None:
            return
        antwort = QMessageBox.question(
            self, "Protokoll löschen",
            f"Protokoll #{self._aktives_protokoll_id} dauerhaft löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return
        loesche_protokoll(self._aktives_protokoll_id)
        self._aktives_protokoll_id = None
        self._ist_neu = False
        self._form_titel.setText("Protokoll auswählen oder neu erstellen")
        self._form_header.setStyleSheet(
            f"background-color: #eef4fa; border-bottom: 1px solid {FIORI_BORDER};"
        )
        self._form_titel.setStyleSheet(f"color: {FIORI_TEXT};")
        self._btn_speichern.setEnabled(False)
        self._btn_abschliessen.setEnabled(False)
        self._btn_loeschen.setEnabled(False)
        self._lade_liste()

    # ── Verspätungen-Sektion dynamisch aufbauen ──────────────────────────────────

    def _rebuild_verspaetungen_section(self, protokoll_id):
        """Baut die Verspätungs-Liste im Formular neu auf."""
        while self._verspaetungen_section_layout.count():
            item = self._verspaetungen_section_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._verspaetungen_widgets.clear()

        # Read-only: Tagdienst=heute, Nachtdienst=heute (kein Vortag)
        db_eintraege: list = []
        try:
            datum_iso = self._f_datum.date().toString("yyyy-MM-dd")
            raw = lade_vsp_aus_db(datum_iso)
            # Deduplizieren nach (mitarbeiter, dienstbeginn) – neuesten Eintrag behalten
            _seen_db: set = set()
            for _e in raw:
                _k = (_e.get("mitarbeiter", ""), _e.get("dienstbeginn", ""))
                if _k not in _seen_db:
                    db_eintraege.append(_e)
                    _seen_db.add(_k)
        except Exception as _exc:
            print(f"[VSP] Fehler beim Laden: {_exc}")
        self._verspaetungen_db_entries = list(db_eintraege)

        # Blaue Einträge aus verspaetungen.db IMMER anzeigen (auch nach Speichern)
        blue_keys = {(e.get("mitarbeiter", ""), e.get("dienstbeginn", "")) for e in db_eintraege}
        if db_eintraege:
            hdr = QLabel("📋 Aus Mitarbeiter-Dokumente (schreibgeschützt):")
            hdr.setStyleSheet(
                "color:#1a6b8a;font-size:10px;font-weight:bold;border:none;"
            )
            self._verspaetungen_section_layout.addWidget(hdr)
            for e in db_eintraege:
                self._add_verspaetung_db_row(e)

        # Legacy-Einträge aus uebergabe_verspaetungen: nur anzeigen wenn sie NICHT in verspaetungen.db
        eintraege = lade_verspaetungen(protokoll_id) if protokoll_id else []
        legacy = [
            e for e in eintraege
            if (e["mitarbeiter"] if isinstance(e, dict) else e[0],
                e["soll_zeit"]   if isinstance(e, dict) else e[1]) not in blue_keys
        ]
        if legacy:
            if db_eintraege:
                legacy_hdr = QLabel("🗂 Ältere gespeicherte Einträge:")
                legacy_hdr.setStyleSheet("color:#888;font-size:10px;font-weight:bold;border:none;")
                self._verspaetungen_section_layout.addWidget(legacy_hdr)
            for e in legacy:
                name = e["mitarbeiter"] if isinstance(e, dict) else e[0]
                soll = e["soll_zeit"]   if isinstance(e, dict) else e[1]
                ist  = e["ist_zeit"]    if isinstance(e, dict) else e[2]
                self._add_verspaetung_row(name=name, soll_zeit=soll, ist_zeit=ist,
                                          _skip_hint_remove=True)

        if not db_eintraege and not legacy:
            hint = QLabel("✅ Keine Verspätungen eingetragen – ➕ hinzufügen")
            hint.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
            self._verspaetungen_section_layout.addWidget(hint)

    def _pick_mitarbeiter_from_db(self):
        """Öffnet einen Dialog zur Auswahl eines Mitarbeiters aus der DB."""
        try:
            namen = lade_mitarbeiter_namen(nur_aktive=True)
        except Exception:
            namen = []

        dlg = QDialog(self)
        dlg.setWindowTitle("Mitarbeiter aus Datenbank wählen")
        dlg.setMinimumWidth(340)
        dlg.setMinimumHeight(380)
        dlg.setStyleSheet("background: white;")

        vlay = QVBoxLayout(dlg)
        vlay.setSpacing(8)
        vlay.setContentsMargins(12, 12, 12, 12)

        hint = QLabel("Mitarbeiter auswählen (Doppelklick oder OK):")
        hint.setStyleSheet("color: #333; font-size: 11px;")
        vlay.addWidget(hint)

        search = QLineEdit()
        search.setPlaceholderText("🔍 Suchen …")
        search.setStyleSheet(
            "border: 1px solid #ccc; border-radius: 3px; padding: 4px 8px; font-size: 11px;"
        )
        vlay.addWidget(search)

        lst = QListWidget()
        lst.setStyleSheet(
            "border: 1px solid #ccc; border-radius: 3px; font-size: 12px;"
        )
        lst.addItems(namen)
        vlay.addWidget(lst)

        def _filter(text):
            for i in range(lst.count()):
                item = lst.item(i)
                item.setHidden(text.lower() not in item.text().lower())

        search.textChanged.connect(_filter)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lst.itemDoubleClicked.connect(lambda _: dlg.accept())
        vlay.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            sel = lst.currentItem()
            if sel:
                self._add_verspaetung_row(name=sel.text())

    def _manuell_verspaetung_erfassen(self):
        """Neuen Eintrag per Dialog erfassen, in verspaetungen.db speichern und blau anzeigen."""
        result = self._versp_erfassungs_dialog()
        if result is None:
            return
        try:
            vsp_db_speichern(result)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Eintrag konnte nicht gespeichert werden:\n{e}")
            return
        self._rebuild_verspaetungen_section(self._aktives_protokoll_id)

    def _versp_erfassungs_dialog(self) -> dict | None:
        """
        Öffnet einen vollständigen Erfassungsdialog für eine Verspätung.
        Gibt ein dict für verspaetung_speichern() zurück oder None bei Abbruch.
        """
        _DIENST_ITEMS = [
            ("T – Tagdienst (06:00)",     "T",   "06:00"),
            ("T10 – Tagdienst (09:00)",   "T10", "09:00"),
            ("N – Nachtdienst (18:00)",   "N",   "18:00"),
            ("N10 – Nachtdienst (21:00)", "N10", "21:00"),
        ]

        dlg = QDialog(self)
        dlg.setWindowTitle("⏰ Verspätung erfassen")
        dlg.setMinimumWidth(480)
        dlg.setStyleSheet("background:white;")

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 14)

        title = QLabel("Meldung über unpünktlichen Dienstantritt")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{FIORI_BLUE};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Datum des Zu-spät-Kommens
        datum_edit = QDateEdit(self._f_datum.date())
        datum_edit.setDisplayFormat("dd.MM.yyyy")
        datum_edit.setCalendarPopup(True)
        datum_edit.setMinimumWidth(130)
        form.addRow("Datum (Tag des Vorfalls) *:", datum_edit)

        # Mitarbeiter
        ma_combo = QComboBox()
        ma_combo.setEditable(True)
        ma_combo.setMinimumWidth(240)
        ma_combo.lineEdit().setPlaceholderText("Name eingeben …")
        try:
            for n in lade_mitarbeiter_namen(nur_aktive=True):
                ma_combo.addItem(n)
        except Exception:
            pass
        form.addRow("Mitarbeiter *:", ma_combo)

        # Dienstart
        dienst_combo = QComboBox()
        for label, code, _ in _DIENST_ITEMS:
            dienst_combo.addItem(label, code)
        form.addRow("Dienstart *:", dienst_combo)

        # Dienstbeginn (Soll) – editierbar mit Warnung
        beginn_edit = QTimeEdit(QTime(6, 0))
        beginn_edit.setDisplayFormat("HH:mm")
        beginn_hint = QLabel("⚠️ Sollzeit manuell geändert – überprüfen!")
        beginn_hint.setStyleSheet(
            "color:#b35900;font-size:10px;font-weight:bold;border:none;"
        )
        beginn_hint.setVisible(False)
        form.addRow("Dienstbeginn (Soll):", beginn_edit)
        form.addRow("", beginn_hint)
        _dienst_soll_map: dict[int, str] = {
            i: t[2] for i, t in enumerate(_DIENST_ITEMS)
        }
        _soll_manuell_geaendert = [False]

        # Tatsächlicher Antritt
        antritt_edit = QTimeEdit(QTime(6, 0))
        antritt_edit.setDisplayFormat("HH:mm")
        form.addRow("Tatsächlicher Antritt:", antritt_edit)

        # Schnellauswahl +N Minuten
        schnell_w = QWidget()
        schnell_lay = QHBoxLayout(schnell_w)
        schnell_lay.setContentsMargins(0, 0, 0, 0)
        schnell_lay.setSpacing(4)
        for _m in [10, 20, 30, 40, 50, 60]:
            _b = QPushButton(f"+{_m}")
            _b.setFixedWidth(42)
            _b.clicked.connect(lambda checked, n=_m: antritt_edit.setTime(
                QTime((antritt_edit.time().hour() * 60 + antritt_edit.time().minute() + n) // 60 % 24,
                      (antritt_edit.time().hour() * 60 + antritt_edit.time().minute() + n) % 60)
            ))
            schnell_lay.addWidget(_b)
        schnell_lay.addStretch()
        form.addRow("+ Minuten:", schnell_w)

        # Verspätungsanzeige
        versp_lbl = QLabel("0 Minuten")
        versp_lbl.setStyleSheet("font-weight:bold;color:#c00;font-size:12px;")
        form.addRow("Verspätung:", versp_lbl)

        layout.addLayout(form)

        def _update_versp():
            b = beginn_edit.time()
            a = antritt_edit.time()
            diff = (a.hour() * 60 + a.minute()) - (b.hour() * 60 + b.minute())
            if diff > 0:
                versp_lbl.setText(f"⚠ {diff} Minuten zu spät")
                versp_lbl.setStyleSheet("font-weight:bold;color:#c00;font-size:12px;")
            elif diff < 0:
                versp_lbl.setText(f"✅ {abs(diff)} Minuten zu früh")
                versp_lbl.setStyleSheet("font-weight:bold;color:#2d6a2d;font-size:12px;")
            else:
                versp_lbl.setText("✅ Pünktlich")
                versp_lbl.setStyleSheet("font-weight:bold;color:#2d6a2d;font-size:12px;")

        beginn_edit.timeChanged.connect(_update_versp)
        antritt_edit.timeChanged.connect(_update_versp)

        def _on_dienst_changed(idx):
            _, code, beginn = _DIENST_ITEMS[idx]
            h, m = map(int, beginn.split(":"))
            _soll_manuell_geaendert[0] = False
            beginn_hint.setVisible(False)
            beginn_edit.setStyleSheet("")
            beginn_edit.setTime(QTime(h, m))
            antritt_edit.setTime(QTime(h, m))
            _update_versp()

        def _on_soll_manuell(t):
            expected = _dienst_soll_map.get(dienst_combo.currentIndex(), "")
            h, m = (int(x) for x in expected.split(":")) if expected else (0, 0)
            if t != QTime(h, m):
                _soll_manuell_geaendert[0] = True
                beginn_hint.setVisible(True)
                beginn_edit.setStyleSheet(
                    "border:1px solid #b35900;border-radius:3px;background:#fff8ee;"
                )
            else:
                _soll_manuell_geaendert[0] = False
                beginn_hint.setVisible(False)
                beginn_edit.setStyleSheet("")
            _update_versp()

        beginn_edit.timeChanged.connect(_on_soll_manuell)

        dienst_combo.currentIndexChanged.connect(_on_dienst_changed)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("✔  Hinzufügen")
        btn_ok.setStyleSheet(
            f"QPushButton{{background:{FIORI_BLUE};color:white;border:none;"
            "border-radius:4px;padding:5px 16px;font-size:12px;}}"
            f"QPushButton:hover{{background:#005a9e;}}"
        )
        btn_ab = QPushButton("Abbrechen")
        btn_ab.setStyleSheet(
            "QPushButton{background:#eee;color:#333;border:none;"
            "border-radius:4px;padding:5px 14px;font-size:12px;}"
            "QPushButton:hover{background:#ddd;}"
        )
        btn_ok.clicked.connect(dlg.accept)
        btn_ab.clicked.connect(dlg.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_ab)
        layout.addLayout(btn_row)

        _update_versp()

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None

        ma = ma_combo.currentText().strip()
        if not ma:
            return None
        b = beginn_edit.time()
        a = antritt_edit.time()
        soll = f"{b.hour():02d}:{b.minute():02d}"
        ist  = f"{a.hour():02d}:{a.minute():02d}"
        diff_min = (a.hour() * 60 + a.minute()) - (b.hour() * 60 + b.minute())
        verspaetung_min = diff_min if diff_min > 0 else 0
        qd = datum_edit.date()
        datum_str = f"{qd.day():02d}.{qd.month():02d}.{qd.year()}"
        idx = dienst_combo.currentIndex()
        dienst_code = _DIENST_ITEMS[idx][1]
        return {
            "mitarbeiter":    ma,
            "datum":          datum_str,
            "dienst":         dienst_code,
            "dienstbeginn":   soll,
            "dienstantritt":  ist,
            "verspaetung_min": verspaetung_min,
            "begruendung":    "",
            "aufgenommen_von": "",
            "dokument_pfad":  "",
        }

    def _pick_from_verspaetungen_db(self):
        """Auswahl aus allen Verspätungen der letzten 7 Tage."""
        try:
            eintraege = lade_vsp_7_tage(7)
        except Exception:
            eintraege = []

        if not eintraege:
            QMessageBox.information(
                self, "Keine Verspätungen",
                "In den letzten 7 Tagen wurden keine Verspätungen in der "
                "Mitarbeiter-Dokumentation erfasst."
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Verspätung auswählen")
        dlg.setMinimumWidth(420)
        dlg.setMinimumHeight(300)
        dlg.setStyleSheet("background:white;")
        vlay = QVBoxLayout(dlg)
        vlay.setSpacing(8)
        vlay.setContentsMargins(12, 12, 12, 12)

        vlay.addWidget(QLabel("Verspätung auswählen (Doppelklick oder OK):"))

        lst = QListWidget()
        lst.setStyleSheet("border:1px solid #ccc;border-radius:3px;font-size:12px;")
        for e in eintraege:
            ma       = e.get("mitarbeiter", "?")
            soll     = e.get("dienstbeginn", "")
            ist      = e.get("dienstantritt", "")
            diff     = e.get("verspaetung_min", "")
            e_datum  = e.get("datum", "")   # Format dd.MM.yyyy aus der DB
            # Datum immer anzeigen (letzte 7 Tage können verschiedene Tage haben)
            label = f"[{e_datum}]  {ma}   Soll: {soll}  Ist: {ist}  ({diff} Min.)"
            lst.addItem(label)
            lst.item(lst.count() - 1).setData(Qt.ItemDataRole.UserRole, e)
        vlay.addWidget(lst)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lst.itemDoubleClicked.connect(lambda _: dlg.accept())
        vlay.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        sel = lst.currentItem()
        if not sel:
            return
        e = sel.data(Qt.ItemDataRole.UserRole)
        self._add_verspaetung_row(
            name=e.get("mitarbeiter", ""),
            soll_zeit=e.get("dienstbeginn", ""),
            ist_zeit=e.get("dienstantritt", ""),
        )

    def _add_verspaetung_row(self, name: str = "", soll_zeit: str = "", ist_zeit: str = "",
                              _skip_hint_remove: bool = False):
        """Fügt eine Legacy-Verspätungs-Zeile (orange) hinzu (für DB-Picker / Altdaten)."""
        if not name:
            return  # Immer mit Name aufrufen – manueller Add: _manuell_verspaetung_erfassen()

        if not _skip_hint_remove and self._verspaetungen_section_layout.count() > 0:
            first = self._verspaetungen_section_layout.itemAt(0)
            if first and first.widget() and isinstance(first.widget(), QLabel):
                w = self._verspaetungen_section_layout.takeAt(0).widget()
                w.deleteLater()

        row_frame = QFrame()
        row_frame.setStyleSheet(
            "QFrame{background:#fff8f0;border:1px solid #f0c080;border-radius:4px;}"
        )
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(6, 4, 6, 4)
        row_layout.setSpacing(6)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Name Mitarbeiter")
        name_edit.setText(str(name))
        name_edit.setStyleSheet(
            "border:1px solid #ccc;border-radius:3px;padding:2px 6px;"
            "font-size:11px;background:white;"
        )
        soll_lbl = QLabel("Soll:")
        soll_lbl.setStyleSheet("border:none;color:#555;font-size:10px;")
        soll_edit = QLineEdit()
        soll_edit.setPlaceholderText("07:00")
        soll_edit.setText(str(soll_zeit))
        soll_edit.setFixedWidth(58)
        soll_edit.setStyleSheet(
            "border:1px solid #ccc;border-radius:3px;padding:2px 4px;"
            "font-size:11px;background:white;"
        )
        ist_lbl = QLabel("Ist:")
        ist_lbl.setStyleSheet("border:none;color:#c0392b;font-size:10px;")
        ist_edit = QLineEdit()
        ist_edit.setPlaceholderText("07:45")
        ist_edit.setText(str(ist_zeit))
        ist_edit.setFixedWidth(58)
        ist_edit.setStyleSheet(
            "border:1px solid #f0a080;border-radius:3px;padding:2px 4px;"
            "font-size:11px;background:white;"
        )
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet(
            "QPushButton{background:#eee;border:none;border-radius:3px;"
            "color:#a00;font-weight:bold;font-size:11px;}"
            "QPushButton:hover{background:#ffcccc;}"
        )
        row_layout.addWidget(name_edit, 1)
        row_layout.addWidget(soll_lbl)
        row_layout.addWidget(soll_edit)
        row_layout.addWidget(ist_lbl)
        row_layout.addWidget(ist_edit)
        row_layout.addWidget(del_btn)

        entry = (name_edit, soll_edit, ist_edit)
        self._verspaetungen_widgets.append(entry)

        def _remove():
            if entry in self._verspaetungen_widgets:
                self._verspaetungen_widgets.remove(entry)
            row_frame.setParent(None)
            row_frame.deleteLater()
            if self._verspaetungen_section_layout.count() == 0:
                hint = QLabel("✅ Keine Verspätungen eingetragen – ➕ hinzufügen")
                hint.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
                self._verspaetungen_section_layout.addWidget(hint)

        del_btn.clicked.connect(_remove)
        self._verspaetungen_section_layout.addWidget(row_frame)

    def _add_verspaetung_db_row(self, e: dict):
        """Zeigt eine Verspätung aus der MA-Doku als schreibgeschützte Zeile an."""
        row_frame = QFrame()
        row_frame.setStyleSheet(
            "QFrame{background:#e8f4f9;border:1px solid #90cbe0;border-radius:4px;}"
        )
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(6, 4, 6, 4)
        row_layout.setSpacing(8)

        name     = e.get("mitarbeiter", "")
        soll     = e.get("dienstbeginn", "")
        ist      = e.get("dienstantritt", "")
        min_vsp  = e.get("verspaetung_min", "")
        dienst   = e.get("dienst", "")
        datum    = e.get("datum", "")

        name_lbl = QLabel(f"👤 {name}")
        name_lbl.setStyleSheet("border:none;font-size:11px;font-weight:bold;")
        diff_txt  = f"  (+{min_vsp} Min.)" if min_vsp else ""
        datum_txt = f"  📅 {datum}" if datum else ""
        info_lbl  = QLabel(f"Dienst: {dienst}  Soll: {soll}  Ist: {ist}{diff_txt}{datum_txt}")
        info_lbl.setStyleSheet("border:none;font-size:10px;color:#1a5b78;")
        src_lbl   = QLabel("📋 MA-Doku")
        src_lbl.setStyleSheet(
            "border:none;font-size:9px;color:#fff;background:#1a8ab5;"
            "border-radius:3px;padding:1px 5px;"
        )

        hide_btn = QPushButton("✕")
        hide_btn.setFixedSize(22, 22)
        hide_btn.setToolTip("Aus dieser Ansicht entfernen (Eintrag bleibt in der MA-Doku erhalten)")
        hide_btn.setStyleSheet(
            "QPushButton{background:#eee;border:none;border-radius:3px;"
            "color:#a00;font-weight:bold;font-size:11px;}"
            "QPushButton:hover{background:#ffcccc;}"
        )
        hide_btn.clicked.connect(lambda: (row_frame.setParent(None), row_frame.deleteLater()))
        row_layout.addWidget(name_lbl)
        row_layout.addWidget(info_lbl)
        row_layout.addStretch()
        row_layout.addWidget(src_lbl)
        row_layout.addWidget(hide_btn)
        self._verspaetungen_section_layout.addWidget(row_frame)

    # ── Fahrzeug-Sektion dynamisch aufbauen ────────────────────────────────────

    def _rebuild_fahrzeug_section(self, protokoll_id):
        """Baut die Fahrzeug-Liste im Formular neu auf."""
        # Alte Widgets entfernen
        while self._fahrzeug_section_layout.count():
            item = self._fahrzeug_section_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._fahrzeug_notiz_widgets.clear()

        fahrzeuge = lade_alle_fahrzeuge(nur_aktive=True)
        if not fahrzeuge:
            lbl = QLabel("Keine aktiven Fahrzeuge vorhanden")
            lbl.setStyleSheet("color:#aaa;font-size:10px;border:none;")
            self._fahrzeug_section_layout.addWidget(lbl)
            return

        existing = lade_fahrzeug_notizen(protokoll_id) if protokoll_id else {}

        _STAT_LABELS = {
            "fahrbereit":   "✅ Fahrbereit",
            "defekt":        "❌ Defekt",
            "werkstatt":     "🔧 Werkstatt",
            "ausser_dienst": "⛔ Außer Dienst",
            "sonstiges":     "ℹ Sonstiges",
        }
        _STAT_COLORS = {
            "fahrbereit":   "#2e7d32",
            "defekt":        "#c62828",
            "werkstatt":     "#e65100",
            "ausser_dienst": "#616161",
            "sonstiges":     "#1565c0",
        }

        for f in fahrzeuge:
            fid  = f["id"]
            kz   = f.get("kennzeichen", "?")
            typ  = f.get("typ", "")

            stat     = aktueller_fahrzeug_status(fid)
            stat_key = (stat.get("status", "fahrbereit") if stat else "fahrbereit")
            stat_lbl = _STAT_LABELS.get(stat_key, stat_key)
            stat_col = _STAT_COLORS.get(stat_key, "#555")

            termine       = lade_fahrzeug_termine(fid)
            offene_termin = [t for t in termine if not t.get("erledigt")]

            frame = QFrame()
            frame.setStyleSheet(
                "QFrame{background:#fafafa;border:1px solid #e0e0e0;border-radius:4px;}"
            )
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(8, 6, 8, 6)
            fl.setSpacing(3)

            # Zeile 1: Kennzeichen | Typ | Status
            top = QHBoxLayout()
            kz_w = QLabel(f"<b>{kz}</b>")
            kz_w.setStyleSheet("border:none;color:#333;")
            typ_w = QLabel(typ)
            typ_w.setStyleSheet("border:none;color:#777;font-size:10px;")
            st_w = QLabel(stat_lbl)
            st_w.setStyleSheet(
                f"border:none;color:{stat_col};font-size:10px;font-weight:bold;"
            )
            top.addWidget(kz_w)
            top.addSpacing(6)
            top.addWidget(typ_w)
            top.addStretch()
            top.addWidget(st_w)
            fl.addLayout(top)

            # Zeile 2: nächster offener Termin
            if offene_termin:
                t = offene_termin[0]
                t_lbl = QLabel(
                    f"📅 {t.get('datum','')}  {t.get('titel','')}"
                )
                t_lbl.setStyleSheet(
                    "border:none;color:#e65100;font-size:10px;"
                )
                fl.addWidget(t_lbl)

            # Zeile 3: Notiz-Eingabe
            nr = QHBoxLayout()
            nl = QLabel("Notiz:")
            nl.setStyleSheet("border:none;color:#555;font-size:10px;")
            nl.setFixedWidth(42)
            ne = QLineEdit()
            ne.setPlaceholderText(f"Notiz zu {kz} ...")
            ne.setStyleSheet(
                "border:1px solid #ccc;border-radius:3px;"
                "padding:2px 6px;font-size:11px;background:white;"
            )
            ne.setText(existing.get(fid, ""))
            nr.addWidget(nl)
            nr.addWidget(ne)
            fl.addLayout(nr)

            self._fahrzeug_notiz_widgets[fid] = ne
            self._fahrzeug_section_layout.addWidget(frame)

    # ── E-Mail Dialog ──────────────────────────────────────────────────────────

    def _email_erstellen(self):
        """Öffnet einen Dialog zum Erstellen einer Übergabe-E-Mail in Outlook."""
        from PySide6.QtWidgets import QCheckBox, QScrollArea as _QSA

        # ── Protokoll-Daten ───────────────────────────────────────────────────
        typ_label  = "Tagdienst ☀" if self._aktueller_typ == "tagdienst" else "Nachtdienst 🌙"
        datum      = self._f_datum.date().toString("dd.MM.yyyy")
        beginn     = self._f_beginn.text().strip()
        ende       = self._f_ende.text().strip()
        ersteller  = self._f_ersteller.text().strip()
        abzeichner = self._f_abzeichner.text().strip()
        patienten  = self._f_patienten.value()
        ereignisse = self._f_ereignisse.toPlainText().strip()
        ue_notiz   = self._f_notiz.toPlainText().strip()
        pid        = self._aktives_protokoll_id

        betreff = (
            f"Übergabeprotokoll #{pid} – {typ_label} – {datum}"
            if pid else
            f"Übergabeprotokoll – {typ_label} – {datum}"
        )

        # ── Fahrzeugstatus ────────────────────────────────────────────────────
        _STAT_LABELS = {
            "fahrbereit":    "✅ Fahrbereit",
            "defekt":        "❌ Defekt",
            "werkstatt":     "🔧 Werkstatt",
            "ausser_dienst": "⛔ Außer Dienst",
            "sonstiges":     "ℹ Sonstiges",
        }
        try:
            alle_fz = lade_alle_fahrzeuge(nur_aktive=True)
            fz_map  = {f["id"]: f for f in lade_alle_fahrzeuge()}
        except Exception:
            alle_fz = []
            fz_map  = {}

        nicht_fb: list[tuple] = []
        for fz in alle_fz:
            fid  = fz["id"]
            stat = aktueller_fahrzeug_status(fid)
            sk   = stat.get("status", "fahrbereit") if stat else "fahrbereit"
            if sk != "fahrbereit":
                nicht_fb.append((fz.get("kennzeichen", "?"), sk,
                                  stat.get("grund", "") if stat else ""))

        # ── Schäden letzte 7 Tage ─────────────────────────────────────────────
        try:
            all_schaeden = lade_schaeden_letzte_tage(7)
        except Exception:
            all_schaeden = []

        offene_schaeden  = [s for s in all_schaeden if not s.get("gesendet")]
        bereits_gesendet = [s for s in all_schaeden if s.get("gesendet")]

        # ── E-Mail Body aufbauen ──────────────────────────────────────────────
        lines: list[str] = [
            f"Übergabeprotokoll – {typ_label}",
            "=" * 45,
            f"Datum:      {datum}",
            f"Schicht:    {beginn} – {ende}",
            f"Ersteller:  {ersteller}" + (f"   |   Abzeichner: {abzeichner}" if abzeichner else ""),
            f"Patienten:  {patienten}",
            "",
        ]
        if ereignisse:
            lines += ["Ereignisse / Vorfälle:", ereignisse, ""]

        if alle_fz:
            lines.append("Fahrzeuge:")
            for fz in alle_fz:
                fid   = fz["id"]
                kz    = fz.get("kennzeichen", "?")
                stat  = aktueller_fahrzeug_status(fid)
                sk    = stat.get("status", "fahrbereit") if stat else "fahrbereit"
                slbl  = _STAT_LABELS.get(sk, sk)
                ne    = self._fahrzeug_notiz_widgets.get(fid)
                notiz = ne.text().strip() if ne else ""
                hint  = f" [{slbl}]" if sk != "fahrbereit" else ""
                grund = f" – {stat['grund']}" if (sk != "fahrbereit" and stat and stat.get("grund")) else ""
                lines.append(f"  • {kz}{hint}{grund}" + (f": {notiz}" if notiz else ""))
            if nicht_fb:
                lines.append("")
                lines.append("⚠ ACHTUNG – Nicht fahrbereite Fahrzeuge:")
                for kz, sk, grund in nicht_fb:
                    lines.append(f"  • {kz}: {_STAT_LABELS.get(sk, sk)}"
                                  + (f" ({grund})" if grund else ""))
            lines.append("")

        handy_rows = [
            (nr.text().strip(), nt.text().strip())
            for nr, nt in self._handy_eintraege_widgets
            if nr.text().strip()
        ]
        if handy_rows:
            lines.append("Handys / Geräte:")
            for nr_t, nt_t in handy_rows:
                lines.append(f"  • Gerät {nr_t}" + (f": {nt_t}" if nt_t else ""))
            lines.append("")

        if ue_notiz:
            lines += ["Übergabe-Notiz für die Folgeschicht:", ue_notiz, ""]

        body_pre = "\n".join(lines)

        # ── Dialog ────────────────────────────────────────────────────────────
        dlg = QDialog(self)
        dlg.setWindowTitle("📧 E-Mail erstellen – Übergabeprotokoll")
        dlg.setMinimumWidth(660)
        dlg.setMinimumHeight(680)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setSpacing(10)
        dlg_layout.setContentsMargins(16, 14, 16, 14)

        # Adressfelder
        addr_form = QFormLayout()
        addr_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        addr_form.setSpacing(8)
        an_edit = QLineEdit()
        an_edit.setPlaceholderText("E-Mail-Adresse(n), kommagetrennt")
        addr_form.addRow("An:", an_edit)
        cc_edit = QLineEdit()
        cc_edit.setPlaceholderText("CC – optional, kommagetrennt")
        addr_form.addRow("CC:", cc_edit)
        subj_edit = QLineEdit()
        subj_edit.setText(betreff)
        addr_form.addRow("Betreff:", subj_edit)
        dlg_layout.addLayout(addr_form)

        # ── Fahrzeugschäden-Sektion ───────────────────────────────────────────
        schaden_frame = QFrame()
        schaden_frame.setStyleSheet(
            "QFrame{border:1px solid #e0a060;border-radius:5px;background:#fffdf8;}"
        )
        schaden_vl = QVBoxLayout(schaden_frame)
        schaden_vl.setContentsMargins(10, 8, 10, 8)
        schaden_vl.setSpacing(4)

        anz_offen = len(offene_schaeden)
        anz_ges   = len(bereits_gesendet)
        sch_lbl   = QLabel(
            f"🔧 Fahrzeugschäden letzte 7 Tage  —  "
            f"{anz_offen} offen / ungesendet    {anz_ges} bereits gesendet"
        )
        sch_lbl.setStyleSheet("font-weight:bold;font-size:11px;border:none;")
        schaden_vl.addWidget(sch_lbl)

        sch_scroll = _QSA()
        sch_scroll.setWidgetResizable(True)
        sch_scroll.setMaximumHeight(130)
        sch_scroll.setStyleSheet("QScrollArea{border:none;}")
        sch_inner = QWidget()
        sch_inner.setStyleSheet("background:transparent;")
        sch_inner_vl = QVBoxLayout(sch_inner)
        sch_inner_vl.setContentsMargins(0, 0, 0, 0)
        sch_inner_vl.setSpacing(2)

        _SCHWERE_ICON = {"gering": "🟡", "mittel": "🟠", "schwer": "🔴"}
        _schaden_checkboxes: list[tuple[QCheckBox, dict]] = []

        for s in offene_schaeden:
            icon = _SCHWERE_ICON.get(s.get("schwere", "gering"), "🟡")
            cb = QCheckBox(
                f"{icon} {s.get('kennzeichen','?')}  |  {s.get('datum','')}  |  "
                f"{s.get('beschreibung','')}"
            )
            cb.setChecked(True)
            cb.setStyleSheet("font-size:10px;")
            sch_inner_vl.addWidget(cb)
            _schaden_checkboxes.append((cb, s))

        for s in bereits_gesendet:
            cb = QCheckBox(
                f"✅ {s.get('kennzeichen','?')}  |  {s.get('datum','')}  |  "
                f"{s.get('beschreibung','')}  [bereits gesendet]"
            )
            cb.setChecked(False)
            cb.setEnabled(False)
            cb.setStyleSheet("font-size:10px;color:#aaa;")
            sch_inner_vl.addWidget(cb)

        if not all_schaeden:
            no_lbl = QLabel("Keine Schäden in den letzten 7 Tagen erfasst.")
            no_lbl.setStyleSheet("color:#aaa;font-size:10px;border:none;padding:4px;")
            sch_inner_vl.addWidget(no_lbl)

        sch_scroll.setWidget(sch_inner)
        schaden_vl.addWidget(sch_scroll)
        dlg_layout.addWidget(schaden_frame)

        # ── Einsätze des Tages ────────────────────────────────────────────────
        try:
            from gui.dienstliches import lade_einsaetze as _lade_einsaetze
            _datum_dd = self._f_datum.date().toString("dd.MM.yyyy")
            _einsatz_parts = _datum_dd.split(".")
            alle_einsaetze = [
                e for e in _lade_einsaetze()
                if e.get("datum", "") == _datum_dd
            ]
        except Exception:
            alle_einsaetze = []

        einsatz_frame = QFrame()
        einsatz_frame.setStyleSheet(
            "QFrame{border:1px solid #5a9060;border-radius:5px;background:#f0faf2;}"
        )
        einsatz_vl = QVBoxLayout(einsatz_frame)
        einsatz_vl.setContentsMargins(10, 8, 10, 8)
        einsatz_vl.setSpacing(4)

        einz_lbl = QLabel(
            f"🚑 Einsätze des Tages ({_datum_dd})  —  {len(alle_einsaetze)} Einsatz/Einsätze"
        )
        einz_lbl.setStyleSheet("font-weight:bold;font-size:11px;border:none;")
        einsatz_vl.addWidget(einz_lbl)

        einz_scroll = _QSA()
        einz_scroll.setWidgetResizable(True)
        einz_scroll.setMaximumHeight(120)
        einz_scroll.setStyleSheet("QScrollArea{border:none;}")
        einz_inner = QWidget()
        einz_inner.setStyleSheet("background:transparent;")
        einz_inner_vl = QVBoxLayout(einz_inner)
        einz_inner_vl.setContentsMargins(0, 0, 0, 0)
        einz_inner_vl.setSpacing(2)

        _einsatz_checkboxes: list[tuple] = []

        for _e in alle_einsaetze:
            _ang = "✅" if _e.get("angenommen") else "❌"
            _stw = _e.get("einsatzstichwort", "") or "—"
            _ort = _e.get("einsatzort", "") or "—"
            _uhr = _e.get("uhrzeit", "") or "—"
            _ma1 = _e.get("drk_ma1", "") or ""
            _ma2 = _e.get("drk_ma2", "") or ""
            _ma_txt = f"  MA: {', '.join(filter(None, [_ma1, _ma2]))}" if (_ma1 or _ma2) else ""
            _ecb = QCheckBox(
                f"{_ang} {_uhr}  |  {_stw}  |  {_ort}{_ma_txt}"
            )
            _ecb.setChecked(True)
            _ecb.setStyleSheet("font-size:10px;")
            einz_inner_vl.addWidget(_ecb)
            _einsatz_checkboxes.append((_ecb, _e))

        if not alle_einsaetze:
            _no_e = QLabel("Keine Einsätze für diesen Tag erfasst.")
            _no_e.setStyleSheet("color:#aaa;font-size:10px;border:none;padding:4px;")
            einz_inner_vl.addWidget(_no_e)

        einz_scroll.setWidget(einz_inner)
        einsatz_vl.addWidget(einz_scroll)
        dlg_layout.addWidget(einsatz_frame)

        # ── PSA-Verstöße des Tages ────────────────────────────────────────────
        try:
            from functions.psa_db import lade_psa_fuer_datum as _lade_psa
            alle_psa = _lade_psa(_datum_dd)
        except Exception:
            alle_psa = []

        offene_psa   = [p for p in alle_psa if not p.get("gesendet")]
        gesendet_psa = [p for p in alle_psa if p.get("gesendet")]

        psa_frame = QFrame()
        psa_frame.setStyleSheet(
            "QFrame{border:1px solid #a06030;border-radius:5px;background:#fff8f0;}"
        )
        psa_vl = QVBoxLayout(psa_frame)
        psa_vl.setContentsMargins(10, 8, 10, 8)
        psa_vl.setSpacing(4)

        _anz_psa_offen = len(offene_psa)
        _anz_psa_ges   = len(gesendet_psa)
        psa_lbl = QLabel(
            f"🦺 PSA-Verstöße ({_datum_dd})  —  "
            f"{_anz_psa_offen} offen / ungesendet    {_anz_psa_ges} bereits gesendet"
        )
        psa_lbl.setStyleSheet("font-weight:bold;font-size:11px;border:none;")
        psa_vl.addWidget(psa_lbl)

        psa_scroll = _QSA()
        psa_scroll.setWidgetResizable(True)
        psa_scroll.setMaximumHeight(120)
        psa_scroll.setStyleSheet("QScrollArea{border:none;}")
        psa_inner = QWidget()
        psa_inner.setStyleSheet("background:transparent;")
        psa_inner_vl = QVBoxLayout(psa_inner)
        psa_inner_vl.setContentsMargins(0, 0, 0, 0)
        psa_inner_vl.setSpacing(2)

        _psa_checkboxes: list[tuple] = []

        for _p in offene_psa:
            _psa_cb = QCheckBox(
                f"🦺 {_p.get('mitarbeiter','?')}  |  {_p.get('psa_typ','?')}  |  "
                f"{_p.get('bemerkung','') or '—'}  (aufgen.: {_p.get('aufgenommen_von','') or '—'})"
            )
            _psa_cb.setChecked(True)
            _psa_cb.setStyleSheet("font-size:10px;")
            psa_inner_vl.addWidget(_psa_cb)
            _psa_checkboxes.append((_psa_cb, _p))

        for _p in gesendet_psa:
            _psa_cb2 = QCheckBox(
                f"✅ {_p.get('mitarbeiter','?')}  |  {_p.get('psa_typ','?')}  |  "
                f"{_p.get('bemerkung','') or '—'}  [bereits gesendet]"
            )
            _psa_cb2.setChecked(False)
            _psa_cb2.setEnabled(False)
            _psa_cb2.setStyleSheet("font-size:10px;color:#aaa;")
            psa_inner_vl.addWidget(_psa_cb2)

        if not alle_psa:
            _no_psa = QLabel("Keine PSA-Verstöße für diesen Tag erfasst.")
            _no_psa.setStyleSheet("color:#aaa;font-size:10px;border:none;padding:4px;")
            psa_inner_vl.addWidget(_no_psa)

        psa_scroll.setWidget(psa_inner)
        psa_vl.addWidget(psa_scroll)
        dlg_layout.addWidget(psa_frame)

        # ── Verspätete Mitarbeiter – Zeitraumfilter ───────────────────────────
        try:
            _legacy_vsp = lade_verspaetungen(pid) if pid else []
        except Exception:
            _legacy_vsp = []
        # DB-Einträge bevorzugen (haben Datum) – legacy nur wenn kein DB-Eintrag vorhanden
        try:
            _datum_iso = self._f_datum.date().toString("yyyy-MM-dd")
            _db_vsp_heute = lade_vsp_aus_db(_datum_iso)
            # Schlüsselmenge der DB-Einträge (mitarbeiter, dienstbeginn)
            _db_keys = {
                (_e.get("mitarbeiter", ""), _e.get("dienstbeginn", ""))
                for _e in _db_vsp_heute
            }
            # Legacy-Einträge nur behalten wenn KEIN DB-Eintrag diese Person/Zeit abdeckt
            _legacy_only = [
                _sv for _sv in _legacy_vsp
                if ((_sv.get("mitarbeiter", "") if isinstance(_sv, dict) else _sv[0]),
                    (_sv.get("soll_zeit", "")   if isinstance(_sv, dict) else _sv[1]))
                   not in _db_keys
            ]
            alle_vsp = _db_vsp_heute + _legacy_only
        except Exception:
            alle_vsp = _legacy_vsp

        def _vsp_label(e):
            _name = e["mitarbeiter"] if isinstance(e, dict) else e[0]
            if isinstance(e, dict) and "dienstbeginn" in e:
                # Eintrag aus verspaetungen.db (MA-Doku)
                _soll = e.get("dienstbeginn", "")
                _ist  = e.get("dienstantritt", "")
                _min_v = e.get("verspaetung_min")
                _diff = f"  (+{_min_v} Min.)" if _min_v else ""
            else:
                _soll = e["soll_zeit"] if isinstance(e, dict) else e[1]
                _ist  = e["ist_zeit"]  if isinstance(e, dict) else e[2]
                _diff = ""
                try:
                    from datetime import datetime as _dt
                    _delta = int((_dt.strptime(_ist, "%H:%M") - _dt.strptime(_soll, "%H:%M")).total_seconds() // 60)
                    if _delta > 0:
                        _diff = f"  (+{_delta} Min.)"
                except Exception:
                    pass
            return _name, _soll, _ist, _diff

        vsp_frame = QFrame()
        vsp_frame.setStyleSheet(
            "QFrame{border:1px solid #f0c080;border-radius:5px;background:#fff8f0;}"
        )
        vsp_vl = QVBoxLayout(vsp_frame)
        vsp_vl.setContentsMargins(10, 8, 10, 8)
        vsp_vl.setSpacing(6)

        vsp_hdr_row = QHBoxLayout()
        vsp_hdr_lbl = QLabel("🕐 Verspätete Mitarbeiter – Datum / Zeitraum filtern")
        vsp_hdr_lbl.setStyleSheet("font-weight:bold;font-size:11px;border:none;")

        # Datum-Filter: immer aktueller Tag (kein Vortag)
        _datum_qdate = self._f_datum.date()
        _default_von_datum = _datum_qdate

        _datum_von_lbl = QLabel("Datum von:")
        _datum_von_lbl.setStyleSheet("border:none;font-size:10px;")
        vsp_datum_von_edit = QDateEdit(_default_von_datum)
        vsp_datum_von_edit.setDisplayFormat("dd.MM.yyyy")
        vsp_datum_von_edit.setCalendarPopup(True)
        vsp_datum_von_edit.setFixedWidth(100)

        _datum_bis_lbl = QLabel("bis:")
        _datum_bis_lbl.setStyleSheet("border:none;font-size:10px;")
        vsp_datum_bis_edit = QDateEdit(_datum_qdate)
        vsp_datum_bis_edit.setDisplayFormat("dd.MM.yyyy")
        vsp_datum_bis_edit.setCalendarPopup(True)
        vsp_datum_bis_edit.setFixedWidth(100)

        _von_lbl = QLabel("Zeit von:")
        _von_lbl.setStyleSheet("border:none;font-size:10px;")
        vsp_von_edit = QLineEdit()
        vsp_von_edit.setPlaceholderText("00:00")
        vsp_von_edit.setText(beginn if beginn else "00:00")
        vsp_von_edit.setFixedWidth(52)
        _bis_lbl = QLabel("bis:")
        _bis_lbl.setStyleSheet("border:none;font-size:10px;")
        vsp_bis_edit = QLineEdit()
        vsp_bis_edit.setPlaceholderText("23:59")
        vsp_bis_edit.setText(ende if ende else "23:59")
        vsp_bis_edit.setFixedWidth(52)

        vsp_hdr_row.addWidget(vsp_hdr_lbl)
        vsp_hdr_row.addStretch()
        vsp_hdr_row.addWidget(_datum_von_lbl)
        vsp_hdr_row.addWidget(vsp_datum_von_edit)
        vsp_hdr_row.addWidget(_datum_bis_lbl)
        vsp_hdr_row.addWidget(vsp_datum_bis_edit)
        vsp_hdr_row.addSpacing(8)
        vsp_hdr_row.addWidget(_von_lbl)
        vsp_hdr_row.addWidget(vsp_von_edit)
        vsp_hdr_row.addWidget(_bis_lbl)
        vsp_hdr_row.addWidget(vsp_bis_edit)
        vsp_vl.addLayout(vsp_hdr_row)

        vsp_scroll = _QSA()
        vsp_scroll.setWidgetResizable(True)
        vsp_scroll.setMaximumHeight(120)
        vsp_scroll.setStyleSheet("QScrollArea{border:none;}")
        vsp_inner = QWidget()
        vsp_inner.setStyleSheet("background:transparent;")
        vsp_inner_vl = QVBoxLayout(vsp_inner)
        vsp_inner_vl.setContentsMargins(0, 0, 0, 0)
        vsp_inner_vl.setSpacing(2)
        vsp_scroll.setWidget(vsp_inner)
        vsp_vl.addWidget(vsp_scroll)

        _vsp_checkboxes: list = []  # list of (QCheckBox, entry)

        def _rebuild_vsp_liste():
            while vsp_inner_vl.count():
                _it = vsp_inner_vl.takeAt(0)
                if _it.widget():
                    _it.widget().deleteLater()
            _vsp_checkboxes.clear()
            if not alle_vsp:
                _nl = QLabel("Keine Verspätungen erfasst.")
                _nl.setStyleSheet("color:#aaa;font-size:10px;border:none;padding:4px;")
                vsp_inner_vl.addWidget(_nl)
                return
            from datetime import datetime as _dt2, date as _ddate3
            def _pt(s):
                try: return _dt2.strptime(s.strip(), "%H:%M")
                except: return None
            def _pd(s):
                # Parst dd.MM.yyyy aus DB-Feld "datum"
                try: return _ddate3.strptime(s.strip(), "%d.%m.%Y")
                except: return None
            t_von = _pt(vsp_von_edit.text())
            t_bis = _pt(vsp_bis_edit.text())
            _overnight = (t_von and t_bis and t_von > t_bis)
            d_von = vsp_datum_von_edit.date().toPython()
            d_bis = vsp_datum_bis_edit.date().toPython()
            shown = 0
            for _e in alle_vsp:
                _n, _s, _i, _d = _vsp_label(_e)
                # Datumsfilter (nur für MA-Doku-Einträge mit "datum"-Feld)
                _e_datum_str = _e.get("datum", "") if isinstance(_e, dict) else ""
                if _e_datum_str:
                    _e_date = _pd(_e_datum_str)
                    if _e_date and not (d_von <= _e_date <= d_bis):
                        continue
                # Zeitfilter
                t_ist_v = _pt(_i)
                if t_von and t_bis and t_ist_v:
                    if _overnight:
                        if not (t_ist_v >= t_von or t_ist_v <= t_bis):
                            continue
                    else:
                        if not (t_von <= t_ist_v <= t_bis):
                            continue
                from PySide6.QtWidgets import QCheckBox as _QCB
                _src_tag = "  📋" if (isinstance(_e, dict) and "dienstbeginn" in _e) else ""
                _datum_tag = f"  [{_e_datum_str}]" if _e_datum_str else ""
                _cb = _QCB(f"🕐 {_n}  –  Gefordert: {_s}  Tatsächlich: {_i}{_d}{_datum_tag}{_src_tag}")
                _cb.setChecked(True)
                _cb.setStyleSheet("font-size:10px;")
                vsp_inner_vl.addWidget(_cb)
                _vsp_checkboxes.append((_cb, _e))
                shown += 1
            if shown == 0:
                _nl2 = QLabel(f"Keine Verspätungen im gewählten Zeitraum.")
                _nl2.setStyleSheet("color:#aaa;font-size:10px;border:none;padding:4px;")
                vsp_inner_vl.addWidget(_nl2)

        vsp_von_edit.textChanged.connect(lambda _: _rebuild_vsp_liste())
        vsp_bis_edit.textChanged.connect(lambda _: _rebuild_vsp_liste())
        vsp_datum_von_edit.dateChanged.connect(lambda _: _rebuild_vsp_liste())
        vsp_datum_bis_edit.dateChanged.connect(lambda _: _rebuild_vsp_liste())
        _rebuild_vsp_liste()
        dlg_layout.addWidget(vsp_frame)

        # E-Mail-Body
        body_lbl = QLabel("Nachricht:")
        body_lbl.setStyleSheet("font-weight:bold;")
        dlg_layout.addWidget(body_lbl)
        body_edit = QTextEdit()
        body_edit.setPlainText(body_pre)
        body_edit.setMinimumHeight(170)
        dlg_layout.addWidget(body_edit)

        # Anhänge
        att_lbl = QLabel("Anhänge:")
        att_lbl.setStyleSheet("font-weight:bold;")
        dlg_layout.addWidget(att_lbl)
        att_list = QListWidget()
        att_list.setMaximumHeight(70)
        att_list.setStyleSheet(
            "QListWidget{border:1px solid #ccc;border-radius:3px;font-size:10px;}"
        )
        dlg_layout.addWidget(att_list)

        att_row = QHBoxLayout()
        att_add_btn = QPushButton("➕ Datei hinzufügen")
        att_add_btn.setFixedHeight(26)
        att_add_btn.setStyleSheet(
            "QPushButton{background:#eef4fa;border:1px solid #b0c8e8;"
            "border-radius:4px;padding:2px 10px;color:#0a6ed1;font-size:11px;}"
            "QPushButton:hover{background:#d0e4f5;}"
        )
        att_remove_btn = QPushButton("✕ Entfernen")
        att_remove_btn.setFixedHeight(26)
        att_remove_btn.setStyleSheet(
            "QPushButton{background:#eee;border:1px solid #ccc;"
            "border-radius:4px;padding:2px 10px;font-size:11px;}"
            "QPushButton:hover{background:#ffcccc;color:#a00;}"
        )
        att_row.addWidget(att_add_btn)
        att_row.addWidget(att_remove_btn)
        att_row.addStretch()
        dlg_layout.addLayout(att_row)

        # ── Stellungnahmen-Link Sektion ───────────────────────────────────────
        from PySide6.QtWidgets import QComboBox as _QComboBox
        stell_outer = QFrame()
        stell_outer.setStyleSheet(
            "QFrame{border:1px solid #6a4cc0;border-radius:5px;background:#f5f0ff;}"
        )
        stell_outer_vl = QVBoxLayout(stell_outer)
        stell_outer_vl.setContentsMargins(10, 8, 10, 8)
        stell_outer_vl.setSpacing(6)

        cb_stell_link = QCheckBox("📋  Stellungnahmen-Link in E-Mail anhängen")
        cb_stell_link.setStyleSheet("font-weight:bold;font-size:11px;border:none;")
        stell_outer_vl.addWidget(cb_stell_link)

        stell_detail = QFrame()
        stell_detail.setStyleSheet("QFrame{border:none;background:transparent;}")
        stell_detail.setVisible(False)
        stell_detail_vl = QVBoxLayout(stell_detail)
        stell_detail_vl.setContentsMargins(0, 0, 0, 0)
        stell_detail_vl.setSpacing(4)

        stell_hint = QLabel("ℹ️  Allgemeiner Link oder spezifischen Fall auswählen:")
        stell_hint.setStyleSheet("font-size:10px;color:#555;border:none;")
        stell_detail_vl.addWidget(stell_hint)

        combo_stell_fall = _QComboBox()
        combo_stell_fall.setStyleSheet("font-size:11px;")
        combo_stell_fall.addItem("— Allgemeiner Link (kein spezifischer Fall) —", None)
        try:
            from functions.stellungnahmen_db import lade_alle as _stell_alle, _ART_LABEL as _ALBL
            for _e in _stell_alle()[:30]:
                _lbl = f"#{_e['id']} – {_e.get('mitarbeiter','')} – {_e.get('datum_vorfall','')} – {_ALBL.get(_e.get('art',''),'')}"
                combo_stell_fall.addItem(_lbl, _e["id"])
        except Exception:
            pass
        stell_detail_vl.addWidget(combo_stell_fall)

        cb_stell_anhang = QCheckBox("📎  Word-Dokument des ausgewählten Falls anhängen")
        cb_stell_anhang.setStyleSheet("font-size:10px;border:none;")
        cb_stell_anhang.setEnabled(False)  # erst aktiv wenn ein Fall gewählt
        stell_detail_vl.addWidget(cb_stell_anhang)

        def _on_fall_changed():
            hat_fall = combo_stell_fall.currentData() is not None
            cb_stell_anhang.setEnabled(hat_fall)
            if not hat_fall:
                cb_stell_anhang.setChecked(False)
        combo_stell_fall.currentIndexChanged.connect(_on_fall_changed)

        stell_outer_vl.addWidget(stell_detail)

        cb_stell_link.toggled.connect(stell_detail.setVisible)
        dlg_layout.addWidget(stell_outer)

        def _add_att():
            paths, _ = QFileDialog.getOpenFileNames(dlg, "Datei(en) auswählen")
            for p in paths:
                if p:
                    att_list.addItem(p)

        def _remove_att():
            for it in att_list.selectedItems():
                att_list.takeItem(att_list.row(it))

        att_add_btn.clicked.connect(_add_att)
        att_remove_btn.clicked.connect(_remove_att)

        # Buttons
        btn_box = QDialogButtonBox()
        send_btn   = btn_box.addButton("📧 In Outlook öffnen", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = btn_box.addButton("Abbrechen",            QDialogButtonBox.ButtonRole.RejectRole)  # noqa
        btn_box.rejected.connect(dlg.reject)
        send_btn.setStyleSheet(
            "QPushButton{background:#0078a8;color:white;border:none;border-radius:4px;"
            "padding:6px 18px;font-weight:bold;}"
            "QPushButton:hover{background:#005f8a;}"
        )
        dlg_layout.addWidget(btn_box)

        def _senden():
            from functions.mail_functions import create_outlook_draft

            checked   = [(cb, s) for cb, s in _schaden_checkboxes if cb.isChecked()]
            unchecked = [(cb, s) for cb, s in _schaden_checkboxes if not cb.isChecked()]

            # Warnung wenn offene Schäden NICHT mitgesendet werden
            if unchecked:
                answer = QMessageBox.warning(
                    dlg,
                    "Offene Schäden nicht mitgesendet",
                    f"Es gibt {len(unchecked)} offene Schäden, die du NICHT in die E-Mail aufnimmst.\n\n"
                    "Trotzdem senden?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return

            body_text = body_edit.toPlainText().strip()

            # Ausgewählte Schäden in den Body einbauen
            if checked:
                sch_lines = ["", "─" * 38, "🔧 Gemeldete Fahrzeugschäden:", "─" * 38]
                for _, s in checked:
                    icon = _SCHWERE_ICON.get(s.get("schwere", "gering"), "🟡")
                    behoben_txt = " [behoben]" if s.get("behoben") else " [⚠ offen]"
                    sch_lines.append(
                        f"  {icon} {s.get('kennzeichen','?')}  |  {s.get('datum','')}  |  "
                        f"{s.get('beschreibung','')}{behoben_txt}"
                        + (f"\n       Kommentar: {s['kommentar']}" if s.get("kommentar") else "")
                    )
                body_text += "\n" + "\n".join(sch_lines)

            # Stellungnahmen-Link einfügen
            if cb_stell_link.isChecked():
                try:
                    from functions.stellungnahmen_html_export import html_pfad as _html_pfad
                    _html_url = "file:///" + _html_pfad().replace("\\", "/")
                    _fall_id = combo_stell_fall.currentData()
                    _full_url = f"{_html_url}#id-{_fall_id}" if _fall_id else _html_url
                    _link_text = "Stellungnahmen-Datenbank öffnen" if not _fall_id else f"Stellungnahme #{_fall_id} öffnen"
                    _ref_line = f"<br><small style='color:#555'>Referenz: {combo_stell_fall.currentText()}</small>" if _fall_id else ""
                    body_text += (
                        "<br><hr style='border:none;border-top:1px solid #ccc;margin:12px 0'>"
                        "<b>📋 Stellungnahmen-Datenbank:</b><br>"
                        f"<a href='{_full_url}' style='color:#0563C1;text-decoration:underline;'>{_link_text}</a>"
                        f"{_ref_line}"
                    )
                except Exception:
                    pass

            # Verspätete Mitarbeiter in Body einbauen
            _checked_vsp = [(_cb, _e) for _cb, _e in _vsp_checkboxes if _cb.isChecked()]
            if _checked_vsp:
                _vsp_lines = ["", "─" * 38, "🕐 Verspätete Mitarbeiter:", "─" * 38]
                for _, _e in _checked_vsp:
                    _n, _s, _i, _d = _vsp_label(_e)
                    _datum_str = _e.get("datum", "") if isinstance(_e, dict) else ""
                    _datum_txt = f"  📅 {_datum_str}" if _datum_str else ""
                    _vsp_lines.append(f"  • {_n}{_datum_txt}  –  Gefordert: {_s}  Tatsächlich: {_i}{_d}")
                body_text += "\n" + "\n".join(_vsp_lines)

            # Einsätze in Body einbauen
            _checked_einz = [(_cb, _e) for _cb, _e in _einsatz_checkboxes if _cb.isChecked()]
            if _checked_einz:
                _einz_lines = ["", "─" * 38, "🚑 Einsätze:", "─" * 38]
                for _, _e in _checked_einz:
                    _ang = "✅ angenommen" if _e.get("angenommen") else "❌ abgelehnt"
                    _stw = _e.get("einsatzstichwort", "") or "—"
                    _ort = _e.get("einsatzort", "") or "—"
                    _uhr = _e.get("uhrzeit", "") or "—"
                    _dur = _e.get("einsatzdauer", 0) or 0
                    _ma1 = _e.get("drk_ma1", "") or ""
                    _ma2 = _e.get("drk_ma2", "") or ""
                    _ma_txt = f"  MA: {', '.join(filter(None, [_ma1, _ma2]))}" if (_ma1 or _ma2) else ""
                    _nr = _e.get("einsatznr_drk", "") or ""
                    _nr_txt = f"  Nr.: {_nr}" if _nr else ""
                    _dur_txt = f"  Dauer: {_dur} Min." if _dur else ""
                    _einz_lines.append(
                        f"  • {_uhr}  |  {_stw}  |  {_ort}  |  {_ang}{_nr_txt}{_ma_txt}{_dur_txt}"
                    )
                    if _e.get("bemerkung"):
                        _einz_lines.append(f"       Bemerkung: {_e['bemerkung']}")
                body_text += "\n" + "\n".join(_einz_lines)

            # PSA-Verstöße in Body einbauen
            _checked_psa = [(_cb, _p) for _cb, _p in _psa_checkboxes if _cb.isChecked()]
            if _checked_psa:
                _psa_lines = ["", "─" * 38, "🦺 PSA-Verstöße:", "─" * 38]
                for _, _p in _checked_psa:
                    _psa_lines.append(
                        f"  • {_p.get('mitarbeiter','?')}  |  {_p.get('psa_typ','?')}  |  "
                        f"{_p.get('bemerkung','') or '—'}  (aufgen.: {_p.get('aufgenommen_von','') or '—'})"
                    )
                body_text += "\n" + "\n".join(_psa_lines)

            to_val = an_edit.text().strip()
            cc_val = cc_edit.text().strip()
            subj   = subj_edit.text().strip()
            atts   = [att_list.item(i).text() for i in range(att_list.count())]

            # Word-Dokument der ausgewählten Stellungnahme anhängen
            if cb_stell_link.isChecked() and cb_stell_anhang.isChecked():
                _fall_id_att = combo_stell_fall.currentData()
                if _fall_id_att:
                    try:
                        from functions.stellungnahmen_db import get_eintrag as _get_sn
                        _sn = _get_sn(_fall_id_att)
                        if _sn:
                            import os as _os
                            _doc_pfad = _sn.get("pfad_intern") or _sn.get("pfad_extern") or ""
                            if _doc_pfad and _os.path.isfile(_doc_pfad):
                                atts.append(_doc_pfad)
                            elif _sn.get("pfad_extern") and _os.path.isfile(_sn["pfad_extern"]):
                                atts.append(_sn["pfad_extern"])
                    except Exception:
                        pass
            try:
                create_outlook_draft(
                    to=to_val,
                    subject=subj,
                    body_text=body_text,
                    cc=cc_val,
                    attachments=atts if atts else None,
                )
                # Als gesendet markieren
                for _, s in checked:
                    try:
                        markiere_schaden_gesendet(s["id"])
                    except Exception:
                        pass
                for _, _e in _checked_einz:
                    try:
                        from gui.dienstliches import markiere_einsatz_gesendet as _mark_einz
                        _mark_einz(_e["id"])
                    except Exception:
                        pass
                for _, _p in _checked_psa:
                    try:
                        from functions.psa_db import markiere_psa_gesendet as _mark_psa
                        _mark_psa(_p["id"])
                    except Exception:
                        pass
                dlg.accept()
            except Exception as e:
                QMessageBox.critical(
                    dlg, "Fehler",
                    f"E-Mail konnte nicht erstellt werden:\n{e}\n\n"
                    "Bitte sicherstellen, dass Outlook geöffnet ist."
                )

        send_btn.clicked.connect(_senden)
        dlg.exec()

    # ── Handy-Sektion dynamisch aufbauen ──────────────────────────────────────

    def _rebuild_handy_section(self, protokoll_id):
        """Baut die Handy-Eintragsliste neu auf."""
        while self._handy_section_layout.count():
            item = self._handy_section_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._handy_eintraege_widgets.clear()

        eintraege = lade_handy_eintraege(protokoll_id) if protokoll_id else []
        if eintraege:
            for e in eintraege:
                self._add_handy_row(
                    geraet_nr=e["geraet_nr"] if isinstance(e, dict) else e[0],
                    notiz=e["notiz"] if isinstance(e, dict) else e[1],
                    _skip_hint_remove=True
                )
        else:
            hint = QLabel("🤙 Noch keine Geräte eingetragen – ➕ hinzufügen")
            hint.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
            self._handy_section_layout.addWidget(hint)

    def _add_handy_row(self, geraet_nr: str = "", notiz: str = "",
                       _skip_hint_remove: bool = False):
        """Fügt eine neue Zeile (Geräte-Nr + Notiz) zur Handy-Sektion hinzu."""
        if not _skip_hint_remove and self._handy_section_layout.count() > 0:
            first = self._handy_section_layout.itemAt(0)
            if first and first.widget() and isinstance(first.widget(), QLabel):
                w = self._handy_section_layout.takeAt(0).widget()
                w.deleteLater()

        row_frame = QFrame()
        row_frame.setStyleSheet(
            "QFrame{background:#fafafa;border:1px solid #e8e8e8;border-radius:4px;}"
        )
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(6, 4, 6, 4)
        row_layout.setSpacing(6)

        nr_lbl = QLabel("Gerät:")
        nr_lbl.setStyleSheet("border:none;color:#555;font-size:10px;")
        nr_lbl.setFixedWidth(40)
        nr_edit = QLineEdit()
        nr_edit.setPlaceholderText("z.B. 7 oder Handy-3")
        nr_edit.setText(str(geraet_nr))
        nr_edit.setFixedWidth(100)
        nr_edit.setStyleSheet(
            "border:1px solid #ccc;border-radius:3px;padding:2px 4px;"
            "font-size:11px;background:white;"
        )

        notiz_edit = QLineEdit()
        notiz_edit.setPlaceholderText("Notiz zu diesem Gerät ...")
        notiz_edit.setText(str(notiz))
        notiz_edit.setStyleSheet(
            "border:1px solid #ccc;border-radius:3px;padding:2px 4px;"
            "font-size:11px;background:white;"
        )

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet(
            "QPushButton{background:#eee;border:none;border-radius:3px;"
            "color:#a00;font-weight:bold;font-size:11px;}"
            "QPushButton:hover{background:#ffcccc;}"
        )

        row_layout.addWidget(nr_lbl)
        row_layout.addWidget(nr_edit)
        row_layout.addWidget(notiz_edit, 1)
        row_layout.addWidget(del_btn)

        entry = (nr_edit, notiz_edit)
        self._handy_eintraege_widgets.append(entry)

        def _remove():
            if entry in self._handy_eintraege_widgets:
                self._handy_eintraege_widgets.remove(entry)
            row_frame.setParent(None)
            row_frame.deleteLater()
            if self._handy_section_layout.count() == 0:
                hint = QLabel("🤙 Noch keine Geräte eingetragen – ➕ hinzufügen")
                hint.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
                self._handy_section_layout.addWidget(hint)

        del_btn.clicked.connect(_remove)
        self._handy_section_layout.addWidget(row_frame)

    # ── Refresh (von main_window aufgerufen) ───────────────────────────────────

    def refresh(self):
        self._lade_liste()
        # Verspätungssektion neu aufbauen, damit neue MA-Doku-Einträge
        # sichtbar werden wenn man von einem anderen Tab zurückkommt
        if self._aktives_protokoll_id is not None:
            self._rebuild_verspaetungen_section(self._aktives_protokoll_id)
        elif self._ist_neu:
            self._rebuild_verspaetungen_section(None)
