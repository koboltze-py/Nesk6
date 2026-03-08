"""
Dashboard-Widget
Zeigt Statistiken und Übersichten
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QFont, QPainter, QLinearGradient, QColor

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
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Titel
        title = QLabel("🏠 Dashboard")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {FIORI_TEXT};")
        layout.addWidget(title)

        subtitle = QLabel("Willkommen bei Nesk3 – DRK Flughafen Köln")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        # Statistik-Karten
        self._card_aktive  = StatCard("Aktive Mitarbeiter",     "–", "👥", FIORI_BLUE)
        self._card_aktive.setToolTip("Anzahl der Mitarbeiter mit Status 'aktiv' in der Datenbank")
        self._card_gesamt  = StatCard("Mitarbeiter gesamt",     "–", "🗂️",  "#555")
        self._card_gesamt.setToolTip("Gesamtanzahl aller Mitarbeiter (aktiv + inaktiv)")
        self._card_heute   = StatCard("Schichten heute",        "–", "📅", FIORI_SUCCESS)
        self._card_heute.setToolTip("Anzahl der Schichten, die für den heutigen Tag eingetragen sind")
        self._card_monat   = StatCard("Schichten diesen Monat", "–", "📊", FIORI_WARNING)
        self._card_monat.setToolTip("Anzahl aller Schichten im aktuellen Kalendermonat")

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self._card_aktive, 0, 0)
        grid.addWidget(self._card_gesamt, 0, 1)
        grid.addWidget(self._card_heute,  1, 0)
        grid.addWidget(self._card_monat,  1, 1)
        layout.addLayout(grid)

        # Animiertes Flugzeug-Widget
        self._flugzeug = FlugzeugWidget()
        self._flugzeug.setToolTip("Klicken für eine wichtige Durchsage vom Flughafen Köln/Bonn ✈")
        layout.addWidget(self._flugzeug)

        # DB-Statusanzeige
        self._db_status_lbl = QLabel("🔄 Datenbankverbindung wird geprüft...")
        self._db_status_lbl.setFont(QFont("Arial", 11))
        self._db_status_lbl.setStyleSheet(
            "background-color: white; border-radius: 6px; padding: 10px 14px;"
        )
        layout.addWidget(self._db_status_lbl)

        layout.addStretch()

    def refresh(self):
        """Aktualisiert alle Dashboard-Daten."""
        # Datenbankverbindung testen
        try:
            from database.connection import test_connection
            ok, info = test_connection()
            if ok:
                self._db_status_lbl.setText(f"✅ Datenbank verbunden  |  {info[:60]}")
                self._db_status_lbl.setStyleSheet(
                    "background-color: #e8f5e8; border-radius: 6px; "
                    "border-left: 4px solid #107e3e; padding: 10px 14px; color: #107e3e;"
                )
            else:
                self._db_status_lbl.setText(f"❌ Keine Datenbankverbindung: {info[:80]}")
                self._db_status_lbl.setStyleSheet(
                    "background-color: #fce8e8; border-radius: 6px; "
                    "border-left: 4px solid #bb0000; padding: 10px 14px; color: #bb0000;"
                )
        except Exception as e:
            self._db_status_lbl.setText(f"❌ Fehler: {e}")

        # TODO: Statistiken laden (Implementierung folgt)
