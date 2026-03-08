"""
Hilfe-Dialog
Erklärt alle Module und Funktionen der App visuell – mit Animationen.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QWidget, QTabWidget, QSizePolicy,
    QGridLayout, QGraphicsOpacityEffect, QProgressBar,
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QParallelAnimationGroup,
)
from PySide6.QtGui import QFont, QPainter, QLinearGradient, QColor

from config import FIORI_BLUE, FIORI_TEXT, APP_VERSION


# ── Farbpalette der Module ────────────────────────────────────────────────────
_COLORS = {
    "dashboard":    "#0a73c4",
    "aufgaben":     "#e67e22",
    "nacht":        "#8e44ad",
    "dienstplan":   "#27ae60",
    "uebergabe":    "#2980b9",
    "fahrzeuge":    "#c0392b",
    "code19":       "#e74c3c",
    "ausdrucke":    "#16a085",
    "krankmeldung": "#d35400",
    "backup":       "#7f8c8d",
    "einstellung":  "#2c3e50",
}


# ── Animations-Hilfsfunktion ─────────────────────────────────────────────────
def _stagger_fade_slide(widgets: list[QWidget],
                        delay_step: int = 70,
                        duration: int = 380,
                        slide_px: int = 20):
    """Lässt Widgets gestaffelt von unten einfaden + einschieben."""
    for i, w in enumerate(widgets):
        eff = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(eff)
        eff.setOpacity(0.0)

        def _animate(wid=w, effect=eff):
            op_anim = QPropertyAnimation(effect, b"opacity", wid)
            op_anim.setDuration(duration)
            op_anim.setStartValue(0.0)
            op_anim.setEndValue(1.0)
            op_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            g = wid.geometry()
            start_geo = QRect(g.x(), g.y() + slide_px, g.width(), g.height())
            geo_anim = QPropertyAnimation(wid, b"geometry", wid)
            geo_anim.setDuration(duration)
            geo_anim.setStartValue(start_geo)
            geo_anim.setEndValue(g)
            geo_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            grp = QParallelAnimationGroup(wid)
            grp.addAnimation(op_anim)
            grp.addAnimation(geo_anim)
            grp.start()
            wid._anim_grp = grp  # Referenz halten

        QTimer.singleShot(i * delay_step, _animate)


# ── Pulsierendes Icon im Header ───────────────────────────────────────────────
class _PulseLabel(QLabel):
    """Label dessen Font-Größe leicht pulsiert (Breathing-Effekt)."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._sizes = [36, 38, 40, 42, 40, 38]
        self._idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(600)

    def _tick(self):
        self._idx = (self._idx + 1) % len(self._sizes)
        self.setFont(QFont("Segoe UI Emoji", self._sizes[self._idx]))


# ── Animierter Laufbalken unter dem Header ────────────────────────────────────
class _RunningBanner(QFrame):
    """Schmaler Streifen mit wanderndem Farbverlauf."""
    def __init__(self, color: str = FIORI_BLUE, parent=None):
        super().__init__(parent)
        self._color = color
        self._pos = 0.0
        self.setFixedHeight(5)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)   # ~60 fps

    def _tick(self):
        self._pos = (self._pos + 2.5) % (self.width() + 160)
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#d0dcea"))
        grad = QLinearGradient(self._pos - 160, 0, self._pos, 0)
        grad.setColorAt(0.0, QColor(self._color + "00"))
        grad.setColorAt(0.5, QColor(self._color + "dd"))
        grad.setColorAt(1.0, QColor(self._color + "00"))
        p.fillRect(0, 0, w, h, grad)
        p.end()


# ── Modul-Karte ───────────────────────────────────────────────────────────────
class _ModuleCard(QFrame):
    def __init__(self, icon: str, title: str, color: str,
                 beschreibung: str, features: list[str], parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border-left: 5px solid {color};
                border-top: none; border-right: none; border-bottom: none;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        header = QHBoxLayout()
        ico_lbl = QLabel(icon)
        ico_lbl.setFont(QFont("Segoe UI Emoji", 22))
        ico_lbl.setStyleSheet("border: none;")
        ico_lbl.setFixedWidth(44)
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {color}; border: none;")
        header.addWidget(ico_lbl)
        header.addWidget(title_lbl)
        header.addStretch()
        lay.addLayout(header)

        desc_lbl = QLabel(beschreibung)
        desc_lbl.setWordWrap(True)
        desc_lbl.setFont(QFont("Arial", 11))
        desc_lbl.setStyleSheet("color: #444; border: none;")
        lay.addWidget(desc_lbl)

        if features:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #eee;")
            lay.addWidget(sep)
            for f in features:
                fl = QLabel(f"  ✔  {f}")
                fl.setFont(QFont("Arial", 10))
                fl.setStyleSheet("color: #555; border: none;")
                lay.addWidget(fl)


# ── Workflow-Schritt-Karte ────────────────────────────────────────────────────
class _StepCard(QFrame):
    def __init__(self, num: str, ico: str, col: str,
                 title: str, desc: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: white; border-radius: 10px; border: none; }"
        )
        rlay = QHBoxLayout(self)
        rlay.setContentsMargins(0, 0, 16, 0)
        rlay.setSpacing(0)

        badge = QLabel(num)
        badge.setFixedSize(58, 58)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {col}; color: white; border: none;
                border-top-left-radius: 10px; border-bottom-left-radius: 10px;
            }}
        """)
        rlay.addWidget(badge)

        i_lbl = QLabel(ico)
        i_lbl.setFixedSize(52, 58)
        i_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        i_lbl.setFont(QFont("Segoe UI Emoji", 20))
        i_lbl.setStyleSheet(f"background-color: {col}22; border: none;")
        rlay.addWidget(i_lbl)

        tlay = QVBoxLayout()
        tlay.setContentsMargins(14, 10, 0, 10)
        tlay.setSpacing(2)
        tit = QLabel(title)
        tit.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        tit.setStyleSheet(f"color: {col}; border: none;")
        dsc = QLabel(desc)
        dsc.setWordWrap(True)
        dsc.setFont(QFont("Arial", 10))
        dsc.setStyleSheet("color: #555; border: none;")
        tlay.addWidget(tit)
        tlay.addWidget(dsc)
        rlay.addLayout(tlay, 1)


# ── Tipp-Karte ────────────────────────────────────────────────────────────────
class _TipCard(QFrame):
    def __init__(self, icon: str, title: str, text: str,
                 color: str = "#0a73c4", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: white; border-radius: 8px;
                border-left: 4px solid {color};
            }}
        """)
        cl = QHBoxLayout(self)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(12)
        il = QLabel(icon)
        il.setFont(QFont("Segoe UI Emoji", 18))
        il.setStyleSheet("border: none;")
        il.setFixedWidth(34)
        tl = QVBoxLayout()
        tl.setSpacing(2)
        nl = QLabel(title)
        nl.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        nl.setStyleSheet(f"color: {color}; border: none;")
        dl = QLabel(text)
        dl.setWordWrap(True)
        dl.setFont(QFont("Arial", 10))
        dl.setStyleSheet("color: #555; border: none;")
        tl.addWidget(nl)
        tl.addWidget(dl)
        cl.addWidget(il)
        cl.addLayout(tl, 1)


# ── Haupt-Dialog ─────────────────────────────────────────────────────────────
class HilfeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("❓ Hilfe – Nesk3 Bedienungsanleitung")
        self.resize(900, 700)
        self.setMinimumSize(720, 520)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint
        )
        self._tabs_animated: set[int] = set()
        self._tab_widgets: dict[int, list[QWidget]] = {}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        self._banner = _RunningBanner(FIORI_BLUE)
        root.addWidget(self._banner)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #f5f6f7; }
            QTabBar::tab {
                padding: 10px 22px; font-size: 12px; font-family: Arial;
                background: #e8ecf0; color: #555;
                border-bottom: 3px solid transparent;
            }
            QTabBar::tab:selected {
                background: #f5f6f7; color: #0a73c4;
                border-bottom: 3px solid #0a73c4; font-weight: bold;
            }
            QTabBar::tab:hover { background: #dde3ea; }
        """)

        self._tabs.addTab(self._tab_uebersicht(),   "🏠  Übersicht")
        self._tabs.addTab(self._tab_module(),        "📦  Module")
        self._tabs.addTab(self._tab_workflow(),      "🔄  Workflow")
        self._tabs.addTab(self._tab_tipps(),         "💡  Tipps & FAQ")
        self._tabs.addTab(self._tab_anleitungen(),   "📖  Anleitungen")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 10, 16, 14)
        btn_row.addStretch()
        close_btn = QPushButton("✕  Schließen")
        close_btn.setMinimumHeight(36)
        close_btn.setMinimumWidth(130)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {FIORI_BLUE}; color: white;
                border: none; border-radius: 4px;
                padding: 6px 20px; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #0855a9; }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    # ── Header mit Puls-Icon ──────────────────────────────────────────────────
    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(90)
        header.setStyleSheet(f"background-color: {FIORI_BLUE};")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(28, 0, 28, 0)

        left = QVBoxLayout()
        t1 = QLabel("❓ Hilfe & Bedienungsanleitung")
        t1.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        t1.setStyleSheet("color: white; border: none;")
        t2 = QLabel(
            f"Nesk3  ·  Version {APP_VERSION}  ·  "
            "DRK Erste-Hilfe-Station Flughafen Köln/Bonn"
        )
        t2.setFont(QFont("Arial", 10))
        t2.setStyleSheet("color: rgba(255,255,255,0.75); border: none;")
        left.addStretch()
        left.addWidget(t1)
        left.addWidget(t2)
        left.addStretch()

        self._pulse_icon = _PulseLabel("🏥")
        self._pulse_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pulse_icon.setStyleSheet("border: none; color: rgba(255,255,255,0.30);")

        lay.addLayout(left, 1)
        lay.addWidget(self._pulse_icon)
        return header

    # ── Tab 0: Übersicht ──────────────────────────────────────────────────────
    def _tab_uebersicht(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        intro = QLabel(
            "Nesk3 ist die digitale Verwaltungsapp der DRK Erste-Hilfe-Station "
            "am Flughafen Köln/Bonn.\n"
            "Sie fasst alle wichtigen Funktionen des Stationsbetriebs an einem Ort zusammen."
        )
        intro.setWordWrap(True)
        intro.setFont(QFont("Arial", 12))
        intro.setStyleSheet("color: #333;")
        root.addWidget(intro)
        root.addWidget(self._section_label("📌  Was kann die App?"))

        grid = QGridLayout()
        grid.setSpacing(12)
        items = [
            ("🏠", "Dashboard",       _COLORS["dashboard"],
             "Mitarbeiter, Schichten, DB-Status auf einen Blick."),
            ("☀️🌙", "Aufgaben",      _COLORS["aufgaben"],
             "Tages- & Nachtdienst-Aufgaben, Checklisten, Code-19-E-Mails."),
            ("📅", "Dienstplan",       _COLORS["dienstplan"],
             "Excel-Dienstpläne laden und als Word-Stärkemeldung exportieren."),
            ("📋", "Übergabe",          _COLORS["uebergabe"],
             "Schichtprotokolle anlegen, ausfüllen, per E-Mail weiterleiten."),
            ("🚗", "Fahrzeuge",         _COLORS["fahrzeuge"],
             "Status, Schäden, Reparaturaufträge, Wartungstermine."),
            ("🕐", "Code 19",           _COLORS["code19"],
             "Code-19-Protokoll führen, animierte Uhrzeigen-Anzeige."),
            ("🖨️", "Ma. Ausdrucke",    _COLORS["ausdrucke"],
             "Vordrucke öffnen oder drucken."),
            ("🤒", "Krankmeldungen",    _COLORS["krankmeldung"],
             "Krankmeldungsformulare je Mitarbeiter öffnen."),
            ("💾", "Backup",            _COLORS["backup"],
             "Datensicherung erstellen und wiederherstellen."),
            ("⚙️", "Einstellungen",     _COLORS["einstellung"],
             "Pfade, E-Mobby-Fahrer, Protokolle archivieren."),
        ]
        animatables: list[QWidget] = [intro]
        for i, (ico, name, col, desc) in enumerate(items):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: white; border-radius: 8px;
                    border-left: 4px solid {col};
                }}
            """)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.setSpacing(10)
            il = QLabel(ico)
            il.setFont(QFont("Segoe UI Emoji", 16))
            il.setStyleSheet("border: none;")
            il.setFixedWidth(32)
            tl = QVBoxLayout()
            QLabel_name = QLabel(name)
            QLabel_name.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            QLabel_name.setStyleSheet(f"color: {col}; border: none;")
            QLabel_desc = QLabel(desc)
            QLabel_desc.setWordWrap(True)
            QLabel_desc.setFont(QFont("Arial", 10))
            QLabel_desc.setStyleSheet("color: #555; border: none;")
            tl.addWidget(QLabel_name)
            tl.addWidget(QLabel_desc)
            cl.addWidget(il)
            cl.addLayout(tl, 1)
            grid.addWidget(card, i // 2, i % 2)
            animatables.append(card)

        root.addLayout(grid)
        root.addStretch()
        self._tab_widgets[0] = animatables
        return self._scroll_wrap(w)

    # ── Tab 1: Module im Detail ───────────────────────────────────────────────
    def _tab_module(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addWidget(self._section_label("📦  Alle Module im Detail"))

        module_data: list[tuple] = [
            ("🏠", "Dashboard", _COLORS["dashboard"],
             "Die Startseite von Nesk3. Wird beim Programmstart automatisch angezeigt "
             "und zeigt die wichtigsten Betriebskennzahlen auf einen Blick. "
             "Ein Klick auf das Flugzeug-Widget startet eine kleine Animation. 😄",
             [
                 "Karte: Aktive Mitarbeiter – Anzahl der aktuell aktiven MA sowie Gesamtanzahl",
                 "Karte: Schichten heute – wie viele Schichten sind für heute eingetragen",
                 "Karte: Schichten diesen Monat – Gesamtzahl im laufenden Monat",
                 "Karte: Datenbankstatus – zeigt 'Verbunden' oder den Fehlerpfad",
                 "Alle Karten werden beim Öffnen automatisch aus der Datenbank geladen",
                 "Oben rechts: App-Version und Stationsname sichtbar",
             ]),
            ("☀️", "Aufgaben Tag", _COLORS["aufgaben"],
             "Enthält alle wiederkehrenden Aufgaben des Tagdienstes. "
             "Über die integrierten Mail-Funktionen können Berichte und Meldungen "
             "direkt an Outlook übergeben werden, inklusive Dateianhänge und Signatur.",
             [
                 "Schaltfläche 'Mail erstellen' → öffnet den freien E-Mail-Dialog",
                 "Im Mail-Dialog: Empfänger, Betreff, Freitext, Anhang-Auswahl",
                 "Anhang umbenennen: Datei auswählen → neuen Namen eingeben → wird beim Senden umbenannt",
                 "Template 'Checklisten-Mail': lädt vordefinierten Betreff + Empfänger",
                 "Template 'Checks-Mail': lädt vordefinierten Betreff + Empfänger",
                 "Code-19-Button: Monat auswählen → Excel wird geladen → Outlook-Entwurf öffnet sich",
                 "Signatur-Button: startet VBS-Skript, das Outlook mit Ihrer persönlichen Signatur öffnet",
                 "Alle Outlook-Aktionen öffnen nur einen Entwurf – Senden geschieht manuell in Outlook",
             ]),
            ("🌙", "Aufgaben Nacht", _COLORS["nacht"],
             "Spiegelseite des Tagdienst-Moduls, optimiert für den Nachtdienst. "
             "Enthält dieselben E-Mail-Funktionen sowie zusätzliche Nacht-spezifische Aktionen.",
             [
                 "Gleiche Mail-Funktionen wie im Tagdienst (freier Entwurf, Templates, Signatur)",
                 "Schaltfläche 'AOCC Lagebericht öffnen' → öffnet die hinterlegte Datei direkt",
                 "Eigene Code-19-Berichtsfunktion für den Nachtdienst",
                 "Alle Felder sind separat von den Tagdienst-Feldern – keine gegenseitige Überschreibung",
             ]),
            ("📅", "Dienstplan", _COLORS["dienstplan"],
             "Öffnet und zeigt Excel-Dienstpläne an. Mehrere Pläne können gleichzeitig "
             "nebeneinander angezeigt werden. Über den Export-Mechanismus wird eine "
             "Word-Stärkemeldung erzeugt.",
             [
                 "Dateibaum links: zeigt den konfigurierten Dienstplan-Ordner",
                 "Datei öffnen: Klick auf eine Excel-Datei im Dateibaum → erscheint als neue Spalte",
                 "Bis zu 4 Dienstpläne gleichzeitig nebeneinander anzeigen",
                 "Jede Spalte zeigt: Dateiname, Dienstplaninhalt, Export-Taste",
                 "Export-Taste: 'Hier klicken um Datei als Wordexport auszuwählen' → Spalte wird blau markiert",
                 "Word-Export-Button oben: öffnet Dialog zur Zeitraum- und Speicherort-Auswahl",
                 "Im Export-Dialog: Datum 'von' und 'bis' wählen, dann Speicherort festlegen",
                 "Ergebnis: Word-Datei 'Stärkemeldung [Datum].docx' wird gespeichert",
                 "E-Mobby-Fahrer werden im Plan automatisch farblich hervorgehoben",
             ]),
            ("📋", "Übergabe", _COLORS["uebergabe"],
             "Erstellt, verwaltet und verschickt Schichtprotokolle. "
             "Protokolle werden in der lokalen Datenbank gespeichert und können "
             "monatsweise durchgeblättert werden.",
             [
                 "Tab-Auswahl: '☀ Tagdienst' oder '🌙 Nachtdienst' für getrennte Protokolllisten",
                 "Schaltfläche 'Neues Protokoll': legt Protokoll mit aktuellem Datum und Schichttyp an",
                 "Protokoll ausfüllen: Mitarbeitername, Anmerkungen, Ereignisse, Schäden",
                 "Monatliche Navigation: Vor/Zurück-Buttons wechseln den angezeigten Monat",
                 "Suchfeld: Protokolle nach Datum, Mitarbeiter oder Inhalt filtern",
                 "Schaltfläche 'E-Mail erstellen': öffnet Outlook-Entwurf mit Protokollinhalt",
                 "Im E-Mail-Dialog: Schadenmeldungen per Checkbox anhaken – werden automatisch in den Mailtext übernommen",
                 "Archivierte Protokolle sind über 'Archiv anzeigen' einsehbar",
                 "Löschen und Archivieren sind passwortgeschützt (Passwort bei Stationsleitung erfragen)",
             ]),
            ("🚗", "Fahrzeuge", _COLORS["fahrzeuge"],
             "Vollständige Fahrzeugverwaltung mit Status, Schadensdokumentation, "
             "Reparaturaufträgen und Wartungsterminen. Alle Daten werden in der "
             "lokalen Datenbank gespeichert.",
             [
                 "Tab 'Fahrzeuge': Liste aller Fahrzeuge mit aktuellem Status",
                 "Fahrzeug hinzufügen: '+ Fahrzeug' → Name, Kennzeichen, Typ eingeben",
                 "Status ändern: Fahrzeug auswählen → Status-Dropdown → Grund + Datum eingeben",
                 "Status-Optionen: Einsatzbereit, In Reparatur, Außer Dienst, TÜV fällig",
                 "Tab 'Schäden': Schäden pro Fahrzeug dokumentieren",
                 "Schaden melden: 'Neuer Schaden' → Beschreibung, Schweregrad, Datum",
                 "Schaden beheben: Behoben-Datum setzen → Schaden wird archiviert",
                 "Unfallbogen-Schaltfläche: öffnet PDF-Unfallbogen im Standard-Betrachter",
                 "Reparaturauftrag: PDF wird automatisch mit Fahrzeug- und Schadensdaten befüllt",
                 "Tab 'Wartung': TÜV-Termin, Ölwechsel, letzte Wartung eintragen",
                 "Globale Suche oben: durchsucht alle Felder (Status, Kennzeichen, Schäden, Termine)",
             ]),
            ("🕐", "Code 19", _COLORS["code19"],
             "Dient der Protokollierung von Code-19-Ereignissen während der Schicht. "
             "Enthält eine animierte Analoguhr zur schnellen Zeiterfassung.",
             [
                 "Ereignis erfassen: Uhrzeit (aus Uhr übernehmen oder manuell) + Freitextbeschreibung",
                 "Animierte Analoguhr: zeigt aktuelle Uhrzeit, Klick übernimmt Uhrzeit ins Feld",
                 "Liste aller Einträge im aktuellen Protokoll",
                 "Eintrag löschen: Zeile markieren → 'Löschen'",
                 "Export: vollständiges Protokoll als Outlook-E-Mail-Entwurf",
                 "Verknüpft mit Code-19-Excel-Datei für den monatlichen Bericht (s. Aufgaben)",
             ]),
            ("🖨️", "Ma. Ausdrucke", _COLORS["ausdrucke"],
             "Zeigt alle im Ordner 'Daten/Vordrucke' abgelegten Dateien an. "
             "Jede Datei kann geöffnet oder direkt an den Drucker gesendet werden.",
             [
                 "Automatische Erkennung aller Dateien im konfigurierten Vordrucke-Ordner",
                 "Schaltfläche 'Öffnen': startet das zum Dateityp gehörende Programm (Word, PDF, ...)",
                 "Schaltfläche 'Drucken': sendet die Datei direkt an den Windows-Standarddrucker",
                 "Liste wird beim Öffnen des Tabs automatisch aktualisiert",
                 "Pfad zum Vordrucke-Ordner ist in den Einstellungen konfigurierbar",
             ]),
            ("🤒", "Krankmeldungen", _COLORS["krankmeldung"],
             "Bietet schnellen Zugriff auf die Krankmeldungsformulare der einzelnen Mitarbeiter. "
             "Formulare liegen meistens als Excel- oder Word-Dateien in Unterordnern vor.",
             [
                 "Automatische Erkennung von Mitarbeiter-Unterordnern im konfigurierten Pfad",
                 "Suchfeld: Mitarbeiternamen eingeben → Liste filtert in Echtzeit",
                 "Schaltfläche 'Öffnen': startet die Datei im Standard-Editor",
                 "Schaltfläche 'Drucken': sendet die Datei direkt an den Drucker",
                 "Pfad zum Krankmeldungs-Ordner ist in den Einstellungen festlegbar",
             ]),
            ("💾", "Backup", _COLORS["backup"],
             "Erstellt und stellt Sicherungen der lokalen Datenbank her. "
             "Sichert alle Protokoll-, Fahrzeug- und Mitarbeiterdaten.",
             [
                 "Schaltfläche 'Backup erstellen': kopiert die aktuelle Datenbank in den Backup-Ordner",
                 "Dateiname enthält automatisch Datum und Uhrzeit",
                 "Schaltfläche 'Backup wiederherstellen': wählt eine Sicherungsdatei aus und stellt sie wieder her",
                 "Warnung vor dem Wiederherstellen: aktuelle Daten werden überschrieben",
                 "Backup-Ordner ist in den Einstellungen konfigurierbar",
             ]),
            ("⚙️", "Einstellungen", _COLORS["einstellung"],
             "Zentrale Konfigurationsseite. Hier werden alle Ordnerpfade, Benutzerdaten "
             "und Verwaltungsoptionen festgelegt. Einige Aktionen sind passwortgeschützt.",
             [
                 "Pfad: Dienstplan-Ordner – wo liegen die Excel-Dienstpläne?",
                 "Pfad: Vordrucke-Ordner – welcher Ordner enthält die Ausdrucke?",
                 "Pfad: Krankmeldungs-Ordner – Unterordner pro Mitarbeiter",
                 "Pfad: Backup-Ordner – Speicherort für Datensicherungen",
                 "E-Mobby-Fahrerliste: Namen hinzufügen/entfernen (werden im Dienstplan hervorgehoben)",
                 "Protokolle archivieren: verschiebt ältere Übergabeprotokolle in die Archiv-DB",
                 "Protokolle löschen: löscht Protokolle dauerhaft (passwortgeschützt!)",
                 "Archiv-Datenbank verwalten: Archiv einsehen oder zurückspielen",
                 "Alle Pfadänderungen sind sofort wirksam – kein Neustart nötig",
             ]),
        ]
        cards: list[QWidget] = []
        for data in module_data:
            c = _ModuleCard(*data)
            root.addWidget(c)
            cards.append(c)
        root.addStretch()
        self._tab_widgets[1] = cards
        return self._scroll_wrap(w)

    # ── Tab 2: Workflow ───────────────────────────────────────────────────────
    def _tab_workflow(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        root.addWidget(self._section_label("🔄  Typischer Schichtablauf – Schritt für Schritt"))

        intro = QLabel(
            "Der folgende Ablauf beschreibt einen typischen Tagesablauf an der EHS. "
            "Nicht alle Schritte sind bei jeder Schicht zwingend notwendig – passen Sie "
            "die Reihenfolge an die aktuelle Lage an."
        )
        intro.setWordWrap(True)
        intro.setFont(QFont("Arial", 11))
        intro.setStyleSheet("color: #555;")
        root.addWidget(intro)

        # Fortschrittsbalken – wird animiert wenn Tab aufgerufen
        self._wf_bar = QProgressBar()
        self._wf_bar.setRange(0, 100)
        self._wf_bar.setValue(0)
        self._wf_bar.setFixedHeight(8)
        self._wf_bar.setTextVisible(False)
        self._wf_bar.setStyleSheet(f"""
            QProgressBar {{
                background: #dde4ed; border-radius: 4px; border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {FIORI_BLUE}, stop:1 #27ae60
                );
                border-radius: 4px;
            }}
        """)
        root.addWidget(self._wf_bar)

        steps = [
            ("1", "🏠", "#0a73c4", "App starten → Dashboard prüfen",
             "Programm starten. Das Dashboard öffnet sich automatisch. "
             "DB-Status (grün = verbunden), Mitarbeiterzahl und heutige Schichten prüfen. "
             "Blinkt der Status rot → Datenbankpfad in den Einstellungen korrekt hinterlegt?"),
            ("2", "📋", "#2980b9", "Übergabeprotokoll anlegen",
             "Tab '📋 Übergabe' öffnen → Tab '☀ Tagdienst' oder '🌙 Nachtdienst' wählen → "
             "'Neues Protokoll' klicken. Das Protokoll wird mit aktuellem Datum und Schichttyp angelegt. "
             "Namen und ersten Eintrag sofort ausfüllen, damit nichts vergessen wird."),
            ("3", "🚗", "#c0392b", "Fahrzeuge kontrollieren",
             "Tab '🚗 Fahrzeuge' öffnen. Status jedes Fahrzeugs prüfen. "
             "Neue Schäden sofort über '+ Schaden' dokumentieren – Schweregrad, Beschreibung, Datum. "
             "Bei Bedarf Reparaturauftrag als PDF erstellen und weiterleiten."),
            ("4", "☀️", "#e67e22", "Aufgaben bearbeiten",
             "Tab '☀ Aufgaben Tag' oder '🌙 Aufgaben Nacht' öffnen. "
             "Checklisten und Templates nutzen. Code-19-Meldung: Code-19-Button klicken → "
             "Monat auswählen → Outlook-Entwurf erscheint automatisch. "
             "AOCC Lagebericht (Nachtdienst): direkter Öffnen-Button verfügbar."),
            ("5", "📅", "#27ae60", "Dienstplan laden und prüfen",
             "Tab '📅 Dienstplan' öffnen. Im Dateibaum links die gewünschte Excel-Datei anklicken. "
             "Die Datei erscheint als Spalte. Für Word-Export: "
             "'Hier klicken…' Schaltfläche im Panel klicken (blaue Markierung) → "
             "dann oben 'Word exportieren' → Zeitraum und Speicherort wählen → OK."),
            ("6", "🕐", "#e74c3c", "Code-19-Ereignisse protokollieren",
             "Tab '🕐 Code 19' öffnen. Ereignis eintreten → Analoguhr klicken um Uhrzeit "
             "automatisch zu übernehmen → Beschreibung eingeben → 'Hinzufügen'. "
             "Am Ende der Schicht: 'E-Mail erstellen' → Outlook-Entwurf mit vollständigem Protokoll."),
            ("7", "📋", "#2980b9", "Protokoll abschließen und weiterleiten",
             "Zurück zu '📋 Übergabe'. Offene Felder ausfüllen – Ereignisse, Anmerkungen, Besonderheiten. "
             "'E-Mail erstellen' klicken. Im Dialog: aufgetretene Schäden per Checkbox anhaken. "
             "Outlook öffnet einen fertigen Entwurf → prüfen → manuell absenden."),
            ("8", "💾", "#7f8c8d", "Backup (empfohlen am Schichtende)",
             "Tab '💾 Backup' öffnen → 'Backup erstellen'. "
             "Die Datenbank wird mit Datums-Zeitstempel in den Backup-Ordner kopiert. "
             "Empfehlenswertes Intervall: mind. einmal täglich oder nach umfangreichen Eingaben."),
        ]
        step_cards: list[QWidget] = []
        for num, ico, col, title, desc in steps:
            card = _StepCard(num, ico, col, title, desc)
            root.addWidget(card)
            step_cards.append(card)

        root.addSpacing(8)
        root.addWidget(self._section_label("⚡  Häufige Sondersituationen"))
        sonder = [
            ("🔴", "#e74c3c", "Fahrzeug fällt aus",
             "Fahrzeuge → Status auf 'Außer Dienst' setzen, Grund eintragen. "
             "Schaden dokumentieren. Reparaturauftrag erstellen. In Übergabe vermerken."),
            ("📞", "#0a73c4", "Notfall-Sonderaufgabe",
             "Sonderaufgaben-Modul öffnen (falls vorhanden). Ereignis in Code-19 und/oder "
             "Übergabeprotokoll festhalten."),
            ("🤒", "#d35400", "Krankmeldung eines MA",
             "Krankmeldungen → Mitarbeiter suchen → Formular öffnen und ausfüllen → drucken."),
            ("📄", "#16a085", "Formular / Vordruck wird benötigt",
             "Ma. Ausdrucke → Datei suchen → 'Öffnen' zum Bearbeiten oder 'Drucken' für Direktdruck."),
        ]
        for ico, col, title, desc in sonder:
            card = _TipCard(ico, title, desc, col)
            root.addWidget(card)
            step_cards.append(card)

        root.addStretch()
        self._tab_widgets[2] = step_cards
        return self._scroll_wrap(w)

    # ── Tab 3: Tipps & Shortcuts ──────────────────────────────────────────────
    def _tab_tipps(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        root.addWidget(self._section_label("💡  Tipps, Hinweise & häufige Fragen"))

        tipps = [
            ("🖱️", "Tooltips nutzen",
             "Fahren Sie mit der Maus über jeden Button, jedes Textfeld oder jedes Symbol – "
             "ein Tooltip-Fenster erklärt die genaue Funktion. So lernen Sie die App am schnellsten kennen.",
             "#0a73c4"),
            ("🔍", "Globale Suche (Fahrzeuge & Übergabe)",
             "Sowohl im Fahrzeug-Modul als auch im Übergabe-Modul gibt es eine Suchleiste oben. "
             "Fahrzeuge: Suche nach Kennzeichen, Status, Schadensart. "
             "Übergabe: Suche nach Datum, Mitarbeitername oder Stichwort im Protokolltext.",
             "#27ae60"),
            ("📧", "Outlook-Integration",
             "Alle E-Mail-Schaltflächen erstellen einen fertigen Outlook-Entwurf – sie senden nichts "
             "automatisch ab. Sie können den Entwurf in Outlook noch bearbeiten, Empfänger ändern "
             "und erst dann manuell absenden. Keine unbeabsichtigten Mails möglich!",
             "#2980b9"),
            ("✍️", "Signatur-Button",
             "Der Signatur-Button in den Aufgaben-Modulen startet ein VBS-Skript, das Outlook mit "
             "Ihrer persönlichen Signatur öffnet. Funktioniert nur, wenn Outlook als Standard-Mailclient "
             "eingerichtet ist und die Signatur in Outlook hinterlegt ist.",
             "#8e44ad"),
            ("💾", "Datenbank-Pfad",
             "Alle Daten werden in einer lokalen SQLite-Datenbank gespeichert. Den aktuellen Pfad "
             "sehen Sie im Dashboard unter 'DB-Status'. Pfad ändern: Einstellungen → Datenbankpfad.",
             "#7f8c8d"),
            ("📦", "Archivieren statt löschen",
             "Protokolle sollten archiviert statt gelöscht werden! Archivierte Protokolle werden in "
             "eine separate Archiv-Datenbank verschoben und bleiben dauerhaft lesbar. "
             "Löschen entfernt Daten unwiederbringlich.",
             "#8e44ad"),
            ("🗂️", "Mehrere Dienstpläne nebeneinander",
             "Im Dienstplan-Tab können bis zu 4 Excel-Dateien gleichzeitig geöffnet sein. "
             "Klicken Sie einfach auf weitere Dateien im Dateibaum links – jede öffnet eine neue Spalte. "
             "Für den Word-Export: erst im gewünschten Panel 'Hier klicken…' auswählen (blau markiert), "
             "dann oben 'Word exportieren'.",
             "#27ae60"),
            ("🔒", "Passwortschutz",
             "Das Löschen und Archivieren von Protokollen ist passwortgeschützt. "
             "Das Passwort erfragen Sie bei der Stationsleitung. "
             "Bitte geben Sie das Passwort nicht an unbefugte Personen weiter.",
             "#e74c3c"),
            ("🖨️", "Direktdruck",
             "In 'Ma. Ausdrucke' und 'Krankmeldungen' können Dateien direkt an den Windows-"
             "Standarddrucker gesendet werden, ohne die Datei zuerst zu öffnen. "
             "Stellen Sie sicher, dass der richtige Drucker in Windows als Standard gesetzt ist.",
             "#16a085"),
            ("📅", "Datum-Navigation in der Übergabe",
             "Im Übergabe-Modul können Sie über die Vor/Zurück-Pfeile monatsweise durch alle "
             "Protokolle blättern. So finden Sie auch ältere Einträge schnell wieder. "
             "Das Suchfeld filtert alle sichtbaren Einträge in Echtzeit.",
             "#2980b9"),
            ("🚗", "Reparaturauftrag erstellen",
             "Im Fahrzeug-Modul einen Schaden markieren → 'Reparaturauftrag' → es wird ein PDF "
             "mit allen relevanten Fahrzeug- und Schadensdaten automatisch befüllt. "
             "Das PDF kann dann geöffnet, ergänzt und ausgedruckt werden.",
             "#c0392b"),
            ("⚙️", "Einstellungen direkt erreichbar",
             "Die Einstellungen sind jederzeit über den Tab '⚙ Einstellungen' oben erreichbar. "
             "Dort können alle Pfade nachträglich angepasst werden. "
             "Pfadänderungen wirken sofort ohne Neustart.",
             "#2c3e50"),
            ("🔄", "App neu laden",
             "Falls Daten nicht aktuell erscheinen: zwischen Tabs hin- und herwechseln aktualisiert die Ansicht. "
             "Ein vollständiger Neustart der App stellt immer den konsistenten Datenbankzustand her.",
             "#0a73c4"),
            ("📁", "Pfade konfigurieren",
             "Alle wichtigen Ordnerpfade (Dienstpläne, Vordrucke, Krankmeldungen, Backup) werden in den "
             "Einstellungen festgelegt. Wenn eine Schaltfläche nicht reagiert oder eine Fehlermeldung "
             "erscheint, zuerst den entsprechenden Pfad in den Einstellungen prüfen.",
             "#e67e22"),
        ]
        cards: list[QWidget] = []
        for ico, title, text, col in tipps:
            card = _TipCard(ico, title, text, col)
            root.addWidget(card)
            cards.append(card)

        root.addSpacing(8)
        root.addWidget(self._section_label("❓  Häufig gestellte Fragen"))

        faq = [
            ("❓", "Warum öffnet sich kein Outlook-Fenster?",
             "Outlook muss als Standard-E-Mail-Programm in Windows eingerichtet sein. "
             "Prüfen: Windows-Einstellungen → Standard-Apps → E-Mail → Outlook auswählen.",
             "#e74c3c"),
            ("❓", "Der Dateibaum im Dienstplan ist leer – was tun?",
             "Den Dienstplan-Pfad in den Einstellungen (⚙) überprüfen. "
             "Der Pfad muss auf den Ordner zeigen, in dem die Excel-Dateien liegen.",
             "#27ae60"),
            ("❓", "Wie exportiere ich eine Stärkemeldung als Word?",
             "Dienstplan öffnen → im Panel 'Hier klicken um Datei als Wordexport auszuwählen' klicken "
             "(Panel wird blau) → oben 'Word exportieren' klicken → Zeitraum und Speicherort wählen → OK.",
             "#27ae60"),
            ("❓", "Die Datenbank zeigt einen Fehler – was tun?",
             "Einstellungen öffnen → Datenbankpfad prüfen und ggf. korrigieren. "
             "Alternativ: Backup wiederherstellen, falls Daten verloren gegangen sind.",
             "#e74c3c"),
            ("❓", "Wie füge ich einen neuen E-Mobby-Fahrer hinzu?",
             "Einstellungen → Abschnitt 'E-Mobby-Fahrer' → Namen eingeben → 'Hinzufügen'. "
             "Der Name erscheint ab sofort im Dienstplan farblich hervorgehoben.",
             "#0a73c4"),
        ]
        for ico, title, text, col in faq:
            card = _TipCard(ico, title, text, col)
            root.addWidget(card)
            cards.append(card)

        root.addSpacing(8)
        ver_frm = QFrame()
        ver_frm.setStyleSheet(
            "QFrame { background: #e8ecf1; border-radius: 8px; border: none; }"
        )
        vl = QHBoxLayout(ver_frm)
        vl.setContentsMargins(16, 10, 16, 10)
        vc = QLabel("ℹ️")
        vc.setFont(QFont("Segoe UI Emoji", 14))
        vc.setStyleSheet("border: none;")
        vl.addWidget(vc)
        ver_txt = QLabel(
            f"<b>Nesk3 v{APP_VERSION}</b> · DRK Erste-Hilfe-Station Flughafen Köln/Bonn · "
            "Entwickelt mit Python 3.13 + PySide6"
        )
        ver_txt.setFont(QFont("Arial", 10))
        ver_txt.setStyleSheet("color: #555; border: none;")
        ver_txt.setWordWrap(True)
        vl.addWidget(ver_txt, 1)
        root.addWidget(ver_frm)
        cards.append(ver_frm)

        root.addStretch()
        self._tab_widgets[3] = cards
        return self._scroll_wrap(w)

    # ── Tab 4: Schritt-für-Schritt Anleitungen ────────────────────────────────
    def _tab_anleitungen(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addWidget(self._section_label("📖  Schritt-für-Schritt Anleitungen"))

        anleitungen = [
            {
                "title": "📅  Dienstplan laden und als Word exportieren",
                "color": _COLORS["dienstplan"],
                "steps": [
                    ("1", "📅", "#27ae60", "Dienstplan-Tab öffnen",
                     "Klicken Sie oben in der Navigation auf den Tab '📅 Dienstplan'."),
                    ("2", "🗂️", "#27ae60", "Dateibaum prüfen",
                     "Links sehen Sie den Dateibaum. Ist er leer → Einstellungen → Dienstplan-Pfad prüfen."),
                    ("3", "📂", "#27ae60", "Excel-Datei öffnen",
                     "Klicken Sie auf eine Excel-Datei im Dateibaum. Sie erscheint als Spalte rechts."),
                    ("4", "🖱️", "#27ae60", "Für Export markieren",
                     "Klicken Sie im Panel auf 'Hier klicken um Datei als Wordexport auszuwählen'. "
                     "Das Panel wird blau umrandet – ✓ Für Wordexport gewählt erscheint auf der Taste."),
                    ("5", "📝", "#27ae60", "Word exportieren",
                     "Klicken Sie oben auf 'Word exportieren'. Es öffnet sich der Export-Dialog."),
                    ("6", "📆", "#27ae60", "Zeitraum und Pfad wählen",
                     "Von-Datum und Bis-Datum einstellen. Dann Speicherort-Schaltfläche klicken "
                     "und Zielordner auswählen."),
                    ("7", "✅", "#27ae60", "Export starten",
                     "Auf 'Exportieren' klicken. Die Datei 'Stärkemeldung [Datum].docx' wird gespeichert."),
                ],
            },
            {
                "title": "📋  Übergabeprotokoll erstellen und weiterleiten",
                "color": _COLORS["uebergabe"],
                "steps": [
                    ("1", "📋", "#2980b9", "Übergabe-Tab öffnen",
                     "Klicken Sie oben auf den Tab '📋 Übergabe'."),
                    ("2", "☀️", "#2980b9", "Schichttyp wählen",
                     "Wählen Sie den Sub-Tab '☀ Tagdienst' oder '🌙 Nachtdienst'."),
                    ("3", "➕", "#2980b9", "Neues Protokoll anlegen",
                     "Klicken Sie auf 'Neues Protokoll'. Das Formular öffnet sich mit aktuellem Datum."),
                    ("4", "✍️", "#2980b9", "Protokoll ausfüllen",
                     "Mitarbeitername, Schichtbesonderheiten, Ereignisse und Schadenmeldungen eintragen."),
                    ("5", "📧", "#2980b9", "E-Mail erstellen",
                     "Klicken Sie auf 'E-Mail erstellen'. Der E-Mail-Dialog erscheint."),
                    ("6", "☑️", "#2980b9", "Schäden anhaken",
                     "Im Mail-Dialog aufgetretene Schäden per Checkbox auswählen – "
                     "sie werden automatisch in den Mailtext eingefügt."),
                    ("7", "📨", "#2980b9", "Outlook-Entwurf öffnen",
                     "Auf 'E-Mail-Entwurf öffnen' klicken. Outlook öffnet sich mit fertigem Text. "
                     "Inhalt prüfen und manuell absenden."),
                ],
            },
            {
                "title": "🚗  Fahrzeugschaden melden und Reparaturauftrag erstellen",
                "color": _COLORS["fahrzeuge"],
                "steps": [
                    ("1", "🚗", "#c0392b", "Fahrzeuge-Tab öffnen",
                     "Klicken Sie oben auf den Tab '🚗 Fahrzeuge'."),
                    ("2", "🖱️", "#c0392b", "Fahrzeug auswählen",
                     "Das betroffene Fahrzeug in der Liste anklicken."),
                    ("3", "🔧", "#c0392b", "Schäden-Tab wechseln",
                     "Im Fahrzeugdetail auf den Tab 'Schäden' wechseln."),
                    ("4", "➕", "#c0392b", "Neuen Schaden erfassen",
                     "'+ Schaden hinzufügen' klicken → Beschreibung, Schweregrad (leicht/mittel/schwer), "
                     "Datum eingeben → Speichern."),
                    ("5", "🔴", "#c0392b", "Status aktualisieren",
                     "Zurück zur Fahrzeugliste → Status-Dropdown → 'In Reparatur' oder 'Außer Dienst' → "
                     "Grund und Datum eingeben → Speichern."),
                    ("6", "📄", "#c0392b", "Reparaturauftrag PDF",
                     "Im Schäden-Tab den Schaden markieren → 'Reparaturauftrag' klicken. "
                     "Das PDF öffnet sich mit Fahrzeug- und Schadensdaten vorausgefüllt."),
                    ("7", "📋", "#c0392b", "In Übergabe vermerken",
                     "Schaden im Übergabeprotokoll dokumentieren, damit die nächste Schicht informiert ist."),
                ],
            },
            {
                "title": "🕐  Code-19-Ereignis protokollieren",
                "color": _COLORS["code19"],
                "steps": [
                    ("1", "🕐", "#e74c3c", "Code-19-Tab öffnen",
                     "Klicken Sie oben auf den Tab '🕐 Code 19'."),
                    ("2", "🕰️", "#e74c3c", "Uhrzeit erfassen",
                     "Die Analoguhr zeigt die aktuelle Zeit. Klick auf die Uhr übernimmt die Uhrzeit "
                     "automatisch ins Zeitfeld. Alternativ: Uhrzeit manuell eingeben."),
                    ("3", "✍️", "#e74c3c", "Beschreibung eingeben",
                     "Im Textfeld den Vorgang beschreiben, z.B. 'Patient X, 14:23 Ankunft, ...'."),
                    ("4", "➕", "#e74c3c", "Eintrag hinzufügen",
                     "'Hinzufügen' klicken. Der Eintrag erscheint in der Liste."),
                    ("5", "🗑️", "#e74c3c", "Korrektur / Löschen",
                     "Eintrag in der Liste markieren → 'Löschen' klicken. Dann neu erfassen."),
                    ("6", "📧", "#e74c3c", "Am Schichtende: E-Mail",
                     "'E-Mail erstellen' klicken → Outlook-Entwurf mit vollständigem Protokoll erscheint. "
                     "Prüfen und manuell versenden."),
                ],
            },
            {
                "title": "⚙️  Ersteinrichtung: Pfade konfigurieren",
                "color": _COLORS["einstellung"],
                "steps": [
                    ("1", "⚙️", "#2c3e50", "Einstellungen öffnen",
                     "Klicken Sie oben auf den Tab '⚙ Einstellungen'."),
                    ("2", "📅", "#2c3e50", "Dienstplan-Pfad festlegen",
                     "Auf das Ordner-Symbol neben 'Dienstplan-Ordner' klicken → "
                     "Ordner mit den Excel-Dienstplänen auswählen → Speichern."),
                    ("3", "🖨️", "#2c3e50", "Vordrucke-Pfad festlegen",
                     "Ordner-Symbol neben 'Vordrucke-Ordner' → Ordner mit Druckvorlagen auswählen."),
                    ("4", "🤒", "#2c3e50", "Krankmeldungs-Pfad prüfen",
                     "Pfad zum Ordner mit den Mitarbeiter-Unterordnern für Krankmeldungen festlegen."),
                    ("5", "💾", "#2c3e50", "Backup-Ordner festlegen",
                     "Sicherungsordner auswählen. Empfehlung: Netzlaufwerk oder OneDrive-Ordner."),
                    ("6", "🚐", "#2c3e50", "E-Mobby-Fahrer hinzufügen",
                     "Namen in das Eingabefeld eingeben → 'Hinzufügen'. Im Dienstplan werden diese "
                     "Personen farblich hervorgehoben."),
                    ("7", "✅", "#2c3e50", "Einstellungen prüfen",
                     "Dashboard öffnen – zeigt der DB-Status 'Verbunden'? ✓ App ist einsatzbereit."),
                ],
            },
        ]

        all_cards: list[QWidget] = []
        for anl in anleitungen:
            # Abschnitts-Header
            sec_lbl = self._section_label(anl["title"])
            root.addWidget(sec_lbl)
            all_cards.append(sec_lbl)
            for step_data in anl["steps"]:
                card = _StepCard(*step_data)
                root.addWidget(card)
                all_cards.append(card)
            root.addSpacing(8)

        root.addStretch()
        self._tab_widgets[4] = all_cards
        return self._scroll_wrap(w)

    # ── Gemeinsame Helfer ─────────────────────────────────────────────────────
    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {FIORI_TEXT}; padding-bottom: 4px;")
        return lbl

    @staticmethod
    def _scroll_wrap(widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f5f6f7; }")
        scroll.setWidget(widget)
        return scroll

    # ── Progress-Animation Workflow ───────────────────────────────────────────
    def _animate_wf_bar(self):
        if not hasattr(self, "_wf_bar"):
            return
        self._wf_bar.setValue(0)
        self._wf_pval = 0

        def _tick():
            self._wf_pval = min(self._wf_pval + 2, 100)
            self._wf_bar.setValue(self._wf_pval)
            if self._wf_pval >= 100:
                self._wf_tick_timer.stop()

        self._wf_tick_timer = QTimer(self)
        self._wf_tick_timer.timeout.connect(_tick)
        self._wf_tick_timer.start(16)

    # ── Tab-Wechsel ───────────────────────────────────────────────────────────
    def _on_tab_changed(self, idx: int):
        if idx in self._tabs_animated:
            return
        self._tabs_animated.add(idx)
        widgets = self._tab_widgets.get(idx, [])
        if widgets:
            QTimer.singleShot(40, lambda: _stagger_fade_slide(widgets, delay_step=60))
        if idx == 2:
            QTimer.singleShot(220, self._animate_wf_bar)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, lambda: self._on_tab_changed(0))
