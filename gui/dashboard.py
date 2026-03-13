"""
Dashboard-Widget
Zeigt Statistiken, Kalender und Fahrzeug-Termine
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QMessageBox, QCalendarWidget, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QDate, QTime
from PySide6.QtGui import QFont, QPainter, QLinearGradient, QColor, QTextCharFormat

from config import FIORI_BLUE, FIORI_TEXT, FIORI_WHITE, FIORI_SUCCESS, FIORI_WARNING


class StatCard(QFrame):
    """Eine Statistik-Karte im SAP Fiori-Stil."""
    def __init__(self, title: str, value: str, icon: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
        """)
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        top = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Arial", 11))
        title_lbl.setStyleSheet("color: #666; border: none;")
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Arial", 20))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(title_lbl)
        top.addStretch()
        top.addWidget(icon_lbl)
        layout.addLayout(top)

        self._value_lbl = QLabel(value)
        self._value_lbl.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        self._value_lbl.setStyleSheet(f"color: {color}; border: none;")
        layout.addWidget(self._value_lbl)

    def set_value(self, value: str):
        self._value_lbl.setText(value)


# ---------------------------------------------------------------------------
# Animierter Himmel (internes Widget für FlugzeugWidget)
# ---------------------------------------------------------------------------
class _SkyWidget(QWidget):
    """Himmel-Strip mit animiertem Flugzeug via QPainter + QTimer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._x: float = -60.0
        self._speed: float = 1.8          # Pixel pro Frame (~30 fps)
        self.setFixedHeight(72)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step)
        self._anim_timer.start(30)        # ~33 FPS

    def _step(self):
        self._x += self._speed
        if self._x > self.width() + 60:
            self._x = -60.0
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Himmel-Verlauf
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#5BA3D0"))
        grad.setColorAt(1.0, QColor("#A8D8F0"))
        p.fillRect(self.rect(), grad)

        # Wolken (links)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 190))
        p.drawEllipse(18,  6, 54, 26)
        p.drawEllipse(10, 15, 44, 20)
        p.drawEllipse(52,  8, 38, 22)

        # Wolken (rechts)
        w = self.width()
        p.drawEllipse(w - 130, 10, 58, 24)
        p.drawEllipse(w - 140, 18, 46, 18)
        p.drawEllipse(w - 100,  6, 42, 22)

        # Rollbahn unten
        p.setBrush(QColor(130, 130, 130, 120))
        p.drawRect(0, self.height() - 13, w, 13)
        p.setBrush(QColor(255, 255, 255, 210))
        for i in range(0, w, 32):
            p.drawRect(i + 4, self.height() - 9, 16, 4)

        # Flugzeug-Emoji
        font = QFont("Segoe UI Emoji", 22)
        p.setFont(font)
        p.setPen(QColor(30, 30, 30))
        p.drawText(int(self._x), 50, "✈")

        p.end()


# ---------------------------------------------------------------------------
# Flugzeug-Karte (klickbar)
# ---------------------------------------------------------------------------
class FlugzeugWidget(QFrame):
    """Animiertes Flugzeug mit Verspätungs-Uhr. Klickbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._delay_min = 0
        self._delay_sec = 0
        self._build()

    def _build(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border-left: 4px solid {FIORI_BLUE};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 10)
        layout.setSpacing(8)

        # Header-Zeile
        header = QHBoxLayout()
        title = QLabel("✈  Flughafen Köln/Bonn  –  Live Ansicht")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #333; border: none;")
        hint = QLabel("zum Klicken")
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet("color: #aaa; border: none;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(hint)
        layout.addLayout(header)

        # Animierter Himmel
        self._sky = _SkyWidget(self)
        layout.addWidget(self._sky)

        # Verspätungs-Anzeige
        bottom = QHBoxLayout()
        clock_icon = QLabel("🕐")
        clock_icon.setFont(QFont("Segoe UI Emoji", 16))
        clock_icon.setStyleSheet("border: none;")
        versp_lbl = QLabel("Aktuelle Verspätung:")
        versp_lbl.setFont(QFont("Segoe UI", 10))
        versp_lbl.setStyleSheet("color: #555; border: none;")
        self._delay_lbl = QLabel("00:00 min")
        self._delay_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._delay_lbl.setStyleSheet("color: #bb0000; border: none;")
        bottom.addWidget(clock_icon)
        bottom.addSpacing(4)
        bottom.addWidget(versp_lbl)
        bottom.addStretch()
        bottom.addWidget(self._delay_lbl)
        layout.addLayout(bottom)

        # Uhr-Timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(1000)

    def _tick(self):
        self._delay_sec += 1
        if self._delay_sec >= 60:
            self._delay_sec = 0
            self._delay_min += 1
        self._delay_lbl.setText(f"{self._delay_min:02d}:{self._delay_sec:02d} min")

    def mousePressEvent(self, event):  # noqa: N802
        QMessageBox.information(
            self,
            "✈  Reisebüro Nesk3",
            f"Willkommen am Flughafen Köln/Bonn! ✈\n\n"
            f"Aktuelle Verspätung: {self._delay_min:02d}:{self._delay_sec:02d} min\n\n"
            f"Keine Sorge – das Flugzeug landet bestimmt irgendwann! 😄",
        )
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._termine: list[dict] = []
        self._build_ui()
        # Uhr-Timer
        self._uhr_timer = QTimer(self)
        self._uhr_timer.timeout.connect(self._uhr_tick)
        self._uhr_timer.start(1000)
        self._uhr_tick()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(20)

        # ── Linke Seite: Kalender + Termine ───────────────────────────────
        linke = QVBoxLayout()
        linke.setSpacing(12)

        titel = QLabel("🏠  Dashboard")
        titel.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        titel.setStyleSheet(f"color: {FIORI_TEXT};")
        linke.addWidget(titel)

        sub = QLabel("Willkommen bei Nesk3 – DRK Flughafen Köln")
        sub.setFont(QFont("Arial", 11))
        sub.setStyleSheet("color: #888;")
        linke.addWidget(sub)

        # Kalender
        self._kalender = QCalendarWidget()
        self._kalender.setGridVisible(True)
        self._kalender.setNavigationBarVisible(True)
        self._kalender.setMinimumHeight(280)
        self._kalender.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._kalender.setStyleSheet("""
            QCalendarWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #C8102E;
                border-radius: 8px 8px 0 0;
            }
            QCalendarWidget QToolButton {
                color: white;
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QCalendarWidget QToolButton:hover {
                background: rgba(255,255,255,0.20);
                border-radius: 4px;
            }
            QCalendarWidget QSpinBox {
                color: white;
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }
            QCalendarWidget QAbstractItemView {
                background-color: white;
                color: #333;
                selection-background-color: #0078D4;
                selection-color: white;
                font-size: 12px;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #bbb;
            }
        """)
        linke.addWidget(self._kalender)

        # Termin-Liste
        termin_hdr = QLabel("📌  Bevorstehende Fahrzeug-Termine")
        termin_hdr.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        termin_hdr.setStyleSheet(f"color: {FIORI_TEXT};")
        linke.addWidget(termin_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumHeight(140)
        scroll.setMaximumHeight(260)
        scroll.setStyleSheet("background: transparent;")
        self._termin_container = QWidget()
        self._termin_container.setStyleSheet("background: transparent;")
        self._termin_layout = QVBoxLayout(self._termin_container)
        self._termin_layout.setSpacing(5)
        self._termin_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._termin_container)
        linke.addWidget(scroll)

        linke.addStretch()
        outer.addLayout(linke, 6)

        # ── Rechte Seite: Uhr + Statistiken + DB-Status ───────────────────
        rechte = QVBoxLayout()
        rechte.setSpacing(12)

        # Digitaluhr
        uhr_frame = QFrame()
        uhr_frame.setStyleSheet("""
            QFrame {
                background: #354a5e;
                border-radius: 10px;
            }
        """)
        uhr_vlayout = QVBoxLayout(uhr_frame)
        uhr_vlayout.setContentsMargins(16, 14, 16, 14)
        uhr_vlayout.setSpacing(2)
        self._uhr_lbl = QLabel("00:00:00")
        self._uhr_lbl.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self._uhr_lbl.setStyleSheet("color: white; border: none;")
        self._uhr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uhr_vlayout.addWidget(self._uhr_lbl)
        self._datum_lbl = QLabel()
        self._datum_lbl.setFont(QFont("Arial", 11))
        self._datum_lbl.setStyleSheet("color: #a0b4c8; border: none;")
        self._datum_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uhr_vlayout.addWidget(self._datum_lbl)
        rechte.addWidget(uhr_frame)

        # Statistik-Karten
        self._card_aktive = StatCard("Aktive Mitarbeiter",     "–", "👥", FIORI_BLUE)
        self._card_gesamt = StatCard("Mitarbeiter gesamt",     "–", "🗂️",  "#555")
        self._card_heute  = StatCard("Schichten heute",        "–", "📅", FIORI_SUCCESS)
        self._card_monat  = StatCard("Schichten diesen Monat", "–", "📊", FIORI_WARNING)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.addWidget(self._card_aktive, 0, 0)
        grid.addWidget(self._card_gesamt, 0, 1)
        grid.addWidget(self._card_heute,  1, 0)
        grid.addWidget(self._card_monat,  1, 1)
        rechte.addLayout(grid)

        # Animiertes Flugzeug-Widget (Easter Egg)
        self._flugzeug = FlugzeugWidget()
        self._flugzeug.setToolTip("Klicken für eine wichtige Durchsage vom Flughafen Köln/Bonn ✈")
        rechte.addWidget(self._flugzeug)

        # DB-Statusanzeige
        self._db_status_lbl = QLabel("🔄 Datenbankverbindung wird geprüft...")
        self._db_status_lbl.setFont(QFont("Arial", 10))
        self._db_status_lbl.setStyleSheet(
            "background-color: white; border-radius: 6px; padding: 8px 12px;"
        )
        rechte.addWidget(self._db_status_lbl)

        rechte.addStretch()
        outer.addLayout(rechte, 4)

    # ── Uhr ───────────────────────────────────────────────────────────────

    def _uhr_tick(self):
        now = QTime.currentTime()
        self._uhr_lbl.setText(now.toString("HH:mm:ss"))
        today = QDate.currentDate()
        _WOCHENTAGE = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
        _MONATE = ["","Januar","Februar","März","April","Mai","Juni",
                   "Juli","August","September","Oktober","November","Dezember"]
        wd = _WOCHENTAGE[today.dayOfWeek() - 1]
        mo = _MONATE[today.month()]
        self._datum_lbl.setText(f"{wd}, {today.day()}. {mo} {today.year()}")

    # ── Fahrzeug-Termine laden ────────────────────────────────────────────

    def _lade_fahrzeug_termine(self) -> list[dict]:
        try:
            from database.connection import db_cursor
            with db_cursor() as cur:
                cur.execute("""
                    SELECT ft.id, ft.datum, ft.uhrzeit, ft.typ, ft.titel,
                           ft.beschreibung, f.kennzeichen, f.typ AS fzg_typ
                    FROM fahrzeug_termine ft
                    JOIN fahrzeuge f ON f.id = ft.fahrzeug_id
                    WHERE ft.datum >= date('now') AND ft.erledigt = 0
                    ORDER BY ft.datum, ft.uhrzeit
                    LIMIT 30
                """)
                return cur.fetchall()
        except Exception:
            return []

    def _lade_statistics(self):
        try:
            from database.connection import db_cursor
            with db_cursor() as cur:
                cur.execute("SELECT COUNT(*) AS n FROM mitarbeiter WHERE status='aktiv'")
                row = cur.fetchone()
                self._card_aktive.set_value(str(row["n"] if row else "–"))
            with db_cursor() as cur:
                cur.execute("SELECT COUNT(*) AS n FROM mitarbeiter")
                row = cur.fetchone()
                self._card_gesamt.set_value(str(row["n"] if row else "–"))
            with db_cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS n FROM dienstplan WHERE datum = date('now')"
                )
                row = cur.fetchone()
                self._card_heute.set_value(str(row["n"] if row else "–"))
            with db_cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS n FROM dienstplan "
                    "WHERE strftime('%Y-%m', datum) = strftime('%Y-%m', 'now')"
                )
                row = cur.fetchone()
                self._card_monat.set_value(str(row["n"] if row else "–"))
        except Exception:
            pass

    # ── Kalender-Markierungen ─────────────────────────────────────────────

    def _markiere_termine(self):
        # Alle alten Markierungen zurücksetzen (letzter Monat ± 6 Monate)
        today = QDate.currentDate()
        leer = QTextCharFormat()
        for offset in range(-6 * 30, 6 * 30):
            d = today.addDays(offset)
            self._kalender.setDateTextFormat(d, leer)

        # Termine markieren
        termin_fmt = QTextCharFormat()
        termin_fmt.setBackground(QColor("#ffb74d"))
        termin_fmt.setForeground(QColor("#7f3f00"))
        termin_fmt.setFontWeight(700)

        heute_fmt = QTextCharFormat()
        heute_fmt.setBackground(QColor("#C8102E"))
        heute_fmt.setForeground(QColor("white"))
        heute_fmt.setFontWeight(700)

        morgen_fmt = QTextCharFormat()
        morgen_fmt.setBackground(QColor("#e53935"))
        morgen_fmt.setForeground(QColor("white"))
        morgen_fmt.setFontWeight(700)

        morgen = today.addDays(1)

        for t in self._termine:
            datum_str = t.get("datum", "")
            if not datum_str:
                continue
            parts = datum_str.split("-")
            if len(parts) != 3:
                continue
            d = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
            if d == today:
                self._kalender.setDateTextFormat(d, heute_fmt)
            elif d == morgen:
                self._kalender.setDateTextFormat(d, morgen_fmt)
            else:
                self._kalender.setDateTextFormat(d, termin_fmt)

    # ── Termin-Liste aktualisieren ────────────────────────────────────────

    def _zeige_termine_liste(self):
        # Alte Einträge entfernen
        while self._termin_layout.count():
            item = self._termin_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = QDate.currentDate()
        morgen = today.addDays(1)

        if not self._termine:
            leer = QLabel("✅  Keine bevorstehenden Fahrzeug-Termine")
            leer.setStyleSheet("color: #888; font-size: 11px; padding: 4px 0;")
            self._termin_layout.addWidget(leer)
            return

        for t in self._termine[:10]:
            datum_str = t.get("datum", "")
            if datum_str:
                parts = datum_str.split("-")
                if len(parts) == 3:
                    d = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
                    datum_de = f"{d.day():02d}.{d.month():02d}.{d.year()}"
                else:
                    datum_de = datum_str
            else:
                datum_de = ""

            kz = t.get("kennzeichen", "?")
            titel = t.get("titel", "") or t.get("typ", "")
            uhrzeit = t.get("uhrzeit", "") or ""

            if datum_str:
                parts = datum_str.split("-")
                if len(parts) == 3:
                    d_check = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
                    if d_check == today:
                        farbe = "#C8102E"
                        badge = " 🔴 HEUTE"
                    elif d_check == morgen:
                        farbe = "#e53935"
                        badge = " 🟠 Morgen"
                    else:
                        farbe = "#1565a8"
                        badge = ""
                else:
                    farbe = "#555"
                    badge = ""
            else:
                farbe = "#555"
                badge = ""

            uhr_txt = f"  {uhrzeit}" if uhrzeit else ""
            text = f"{datum_de}{uhr_txt}  [{kz}]  {titel}{badge}"

            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"background: white; color: {farbe}; border-left: 3px solid {farbe};"
                "border-radius: 4px; padding: 5px 8px; font-size: 12px;"
            )
            self._termin_layout.addWidget(lbl)

        if len(self._termine) > 10:
            mehr = QLabel(f"… und {len(self._termine) - 10} weitere Termine")
            mehr.setStyleSheet("color: #888; font-size: 11px; padding: 2px 4px;")
            self._termin_layout.addWidget(mehr)

    # ── Refresh ───────────────────────────────────────────────────────────

    def refresh(self):
        """Aktualisiert alle Dashboard-Daten."""
        # DB-Verbindung testen
        try:
            from database.connection import test_connection
            ok, info = test_connection()
            if ok:
                self._db_status_lbl.setText(f"✅ Datenbank verbunden  |  {info[:60]}")
                self._db_status_lbl.setStyleSheet(
                    "background-color: #e8f5e8; border-radius: 6px; "
                    "border-left: 4px solid #107e3e; padding: 8px 12px; color: #107e3e;"
                )
            else:
                self._db_status_lbl.setText(f"❌ Keine Datenbankverbindung: {info[:80]}")
                self._db_status_lbl.setStyleSheet(
                    "background-color: #fce8e8; border-radius: 6px; "
                    "border-left: 4px solid #bb0000; padding: 8px 12px; color: #bb0000;"
                )
        except Exception as e:
            self._db_status_lbl.setText(f"❌ Fehler: {e}")

        # Statistiken laden
        self._lade_statistics()

        # Fahrzeug-Termine laden
        self._termine = self._lade_fahrzeug_termine()
        self._markiere_termine()
        self._zeige_termine_liste()

    def get_termine(self) -> list[dict]:
        """Gibt die zuletzt geladenen Fahrzeug-Termine zurück (für badge/popup)."""
        return self._termine
