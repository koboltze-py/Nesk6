"""
Haupt-Fenster (MainWindow)
SAP Fiori-Design mit Sidebar-Navigation
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QColor, QPixmap

from config import (
    APP_NAME, APP_VERSION, BASE_DIR,
    FIORI_SIDEBAR_BG, FIORI_BLUE, FIORI_WHITE, FIORI_LIGHT_BLUE, FIORI_TEXT
)
from gui.dashboard        import DashboardWidget
from gui.aufgaben_tag     import AufgabenTagWidget
from gui.aufgaben         import AufgabenWidget
from gui.dienstplan       import DienstplanWidget
from gui.uebergabe        import UebergabeWidget
from gui.fahrzeuge        import FahrzeugeWidget
from gui.einstellungen    import EinstellungenWidget
from gui.code19           import Code19Widget
from gui.dokument_browser       import DokumentBrowserWidget
from gui.mitarbeiter            import MitarbeiterHauptWidget
from gui.hilfe_dialog           import HilfeDialog
from gui.dienstliches           import DienstlichesWidget
from gui.telefonnummern         import TelefonnummernWidget
from gui.call_transcription     import CallTranscriptionWidget


NAV_ITEMS = [
    ("🏠", "Dashboard",        0),
    ("👥", "Mitarbeiter",       1),
    ("☕️", "Dienstliches",     2),
    ("☀️", "Aufgaben Tag",     3),
    ("🌙", "Aufgaben Nacht",   4),
    ("📅", "Dienstplan",       5),
    ("📋", "Übergabe",         6),
    ("🚗", "Fahrzeuge",        7),
    ("🕐", "Code 19",          8),
    ("🖨️", "Ma. Ausdrucke",   9),
    ("🤒", "Krankmeldungen",  10),
    ("📞", "Telefonnummern",  11),
    ("♿", "Call Transcription", 12),
    ("💾", "Backup",          13),
    ("⚙️",  "Einstellungen",  14),
]

NAV_TOOLTIPS = [
    "Startseite – Statistiken und Übersicht",
    "Mitarbeiter-Übersicht (Stamm/Dispo) + Dokumente (Stellungnahmen, Word-Vorlagen)",
    "Dienstliche Protokolle: Einsätze und Berichte",
    "Tagdienst-Aufgaben, Checklisten und Code-19-Mail",
    "Nachtdienst-Aufgaben und Code-19-Mail",
    "Dienstplan laden, anzeigen und Hausverwaltung exportieren",
    "Schichtprotokoll erstellen, ausfüllen und abschließen",
    "Fahrzeugstatus, Schäden und Wartungstermine verwalten",
    "Code-19-Protokoll führen und Uhrzeigen-Animation",
    "Vordrucke öffnen und drucken (Ordner: Daten/Vordrucke)",
    "Krankmeldungsformulare öffnen (Ordner: 03_Krankmeldungen)",
    "Telefonnummern-Verzeichnis: FKB Gate-/Check-In-Nummern und DRK-Kontakte",
    "Anrufprotokoll: Anrufinhalte mit Textbausteinen schnell erfassen und verwalten",
    "Datensicherung erstellen und wiederherstellen",
    "App-Einstellungen, Pfade und E-Mobby-Fahrerliste",
]


class SidebarButton(QPushButton):
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"  {icon}  {text}", parent)
        self.setCheckable(True)
        self.setMinimumHeight(48)
        self.setFont(QFont("Arial", 12))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {FIORI_BLUE};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    text-align: left;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: #cdd5e0;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: rgba(255,255,255,0.1);
                    color: white;
                }}
            """)

    def setActive(self, active: bool):
        self._apply_style(active)
        self.setChecked(active)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        self._nav_buttons: list[SidebarButton] = []
        self._build_ui()
        self._navigate(0)

    # ── UI aufbauen ────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {FIORI_SIDEBAR_BG};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 0, 8, 16)
        layout.setSpacing(4)

        # Logo-Bereich
        logo_frame = QFrame()
        logo_frame.setFixedHeight(180)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(8, 8, 8, 8)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _logo_path = str(Path(BASE_DIR) / "Daten" / "Logo" / "unnamed (1).jpg")
        _pix = QPixmap(_logo_path)
        if not _pix.isNull():
            _pix = _pix.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
            if _pix.height() > 160:
                _pix = _pix.scaledToHeight(160, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(_pix)
        else:
            logo_lbl.setText("NESK3")
            logo_lbl.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            logo_lbl.setStyleSheet("color: white;")
        logo_layout.addWidget(logo_lbl)

        layout.addWidget(logo_frame)

        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #4a6480;")
        layout.addWidget(line)
        layout.addSpacing(8)

        # Navigations-Buttons
        for (icon, label, idx), tooltip in zip(NAV_ITEMS, NAV_TOOLTIPS):
            btn = SidebarButton(icon, label)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda _, i=idx: self._navigate(i))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Hilfe-Button
        hilfe_btn = QPushButton("❓  Hilfe")
        hilfe_btn.setMinimumHeight(36)
        hilfe_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hilfe_btn.setToolTip("Bedienungsanleitung und Übersicht aller Funktionen öffnen")
        hilfe_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.10);
                color: #cdd5e0;
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 4px;
                padding: 6px 12px;
                text-align: left;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.20);
                color: white;
            }
        """)
        hilfe_btn.clicked.connect(lambda: HilfeDialog(self).exec())
        layout.addWidget(hilfe_btn)

        # Version unten
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setStyleSheet("color: #4a6480; font-size: 10px; padding: 0 8px;")
        layout.addWidget(ver_lbl)

        return sidebar

    def _build_content(self) -> QWidget:
        frame = QWidget()
        frame.setStyleSheet(f"background-color: #f5f6f7;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()

        # Pages
        self._dashboard_page         = DashboardWidget()
        self._mitarbeiter_page       = MitarbeiterHauptWidget()
        self._dienstliches_page      = DienstlichesWidget()
        self._aufgaben_tag_page      = AufgabenTagWidget()
        self._aufgaben_page          = AufgabenWidget()
        self._dienstplan_page        = DienstplanWidget()
        self._uebergabe_page         = UebergabeWidget()
        self._fahrzeuge_page         = FahrzeugeWidget()
        self._code19_page            = Code19Widget()

        _AUSDRUCKE_PATH    = os.path.join(BASE_DIR, "Daten", "Vordrucke")
        _KRANKMELD_PATH    = os.path.join(
            os.path.dirname(os.path.dirname(BASE_DIR)), "03_Krankmeldungen"
        )
        self._ausdrucke_page     = DokumentBrowserWidget(
            "🖨 Ma. Ausdrucke – Vordrucke", _AUSDRUCKE_PATH
        )
        self._krankmeldungen_page = DokumentBrowserWidget(
            "🤒 Krankmeldungen", _KRANKMELD_PATH, allow_subfolders=True
        )

        self._telefonnummern_page = TelefonnummernWidget()

        self._call_transcription_page = CallTranscriptionWidget()
        self._backup_page        = self._placeholder_page("💾 Backup", "Backup-Verwaltung wird implementiert.")
        self._settings_page      = EinstellungenWidget()

        for page in [self._dashboard_page, self._mitarbeiter_page,
                     self._dienstliches_page,
                     self._aufgaben_tag_page, self._aufgaben_page,
                     self._dienstplan_page, self._uebergabe_page,
                     self._fahrzeuge_page, self._code19_page,
                     self._ausdrucke_page, self._krankmeldungen_page,
                     self._telefonnummern_page,
                     self._call_transcription_page,
                     self._backup_page, self._settings_page]:
            self._stack.addWidget(page)

        layout.addWidget(self._stack)
        return frame

    def _placeholder_page(self, title: str, msg: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {FIORI_TEXT};")
        lbl_msg = QLabel(msg)
        lbl_msg.setFont(QFont("Arial", 13))
        lbl_msg.setStyleSheet("color: #999;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_msg)
        return w

    # ── Navigation ─────────────────────────────────────────────────────────────
    def _navigate(self, index: int):
        for i, btn in enumerate(self._nav_buttons):
            btn.setActive(i == index)
        self._stack.setCurrentIndex(index)

        # Refresh nach dem Seitenumbruch aufrufen (UI reagiert sofort)
        page_map = {
            0: self._dashboard_page.refresh,
            1: self._mitarbeiter_page.refresh,
            2: self._dienstliches_page.refresh,
            3: self._aufgaben_tag_page.refresh,
            4: self._aufgaben_page.refresh,
            5: self._dienstplan_page.reload_tree,
            6: self._uebergabe_page.refresh,
            7: self._fahrzeuge_page.refresh,
            8: self._code19_page.refresh,
            9: self._ausdrucke_page.refresh,
            10: self._krankmeldungen_page.refresh,
            11: self._telefonnummern_page.refresh,
            12: self._call_transcription_page.refresh,
        }
        if index in page_map:
            QTimer.singleShot(0, page_map[index])

    # ── Screenshot-Erstellung ──────────────────────────────────────────────────
    def grab_all_screenshots(self, callback=None):
        """
        Erstellt PNG-Screenshots aller App-Seiten und speichert sie in
        Daten/Hilfe/screenshots/{idx:02d}.png.
        Ruft am Ende callback(list[str]) auf.
        """
        ss_dir = Path(BASE_DIR) / "Daten" / "Hilfe" / "screenshots"
        ss_dir.mkdir(parents=True, exist_ok=True)

        self._ss_paths: list[str] = []
        self._ss_idx: int = 0
        self._ss_dir = ss_dir
        self._ss_callback = callback

        def _grab_next():
            if self._ss_idx >= len(NAV_ITEMS):
                self._navigate(0)
                if self._ss_callback:
                    self._ss_callback(self._ss_paths)
                return
            _icon, _label, page_idx = NAV_ITEMS[self._ss_idx]
            self._navigate(page_idx)
            QTimer.singleShot(300, _do_grab)

        def _do_grab():
            _icon, _label, page_idx = NAV_ITEMS[self._ss_idx]
            pixmap = self._stack.grab()
            fpath = str(self._ss_dir / f"{page_idx:02d}.png")
            pixmap.save(fpath, "PNG")
            self._ss_paths.append(fpath)
            self._ss_idx += 1
            QTimer.singleShot(50, _grab_next)

        _grab_next()
