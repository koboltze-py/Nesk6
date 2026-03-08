"""
Code 19 – Widget
Öffnet die Code-19-Excel-Datei. Pfad ist in den Einstellungen konfigurierbar.
"""
import os
import sys
import math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QTime, QPointF, QRectF
from PySide6.QtGui import (
    QFont, QPainter, QPen, QBrush, QColor, QRadialGradient,
    QLinearGradient, QConicalGradient
)

from config import FIORI_BLUE, FIORI_TEXT
from functions.settings_functions import get_setting


# ---------------------------------------------------------------------------
# Alice-im-Wunderland Taschenuhr (animiert)
# ---------------------------------------------------------------------------
class _PocketWatchWidget(QWidget):
    """
    Gezeichnete Taschenuhr im Alice-im-Wunderland-Stil.
    - Goldenes Gehäuse, schwingt wie ein Pendel
    - Sekundenzeiger tickt jede Sekunde (Rucken)
    - Römische Ziffern
    """
    _ROMAN = {1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",
              7:"VII",8:"VIII",9:"IX",10:"X",11:"XI",12:"XII"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(240, 300)

        self._swing_angle = 0.0   # Pendelwinkel (Grad)
        self._swing_t     = 0.0   # Zeitvariable für Sinus
        self._blink_on    = True  # für Tick-Blink-Effekt

        # Swing-Timer (~40 FPS)
        self._swing_timer = QTimer(self)
        self._swing_timer.timeout.connect(self._swing_step)
        self._swing_timer.start(25)

        # Tik-Tok jede Sekunde (Sekundenzeiger + Blink)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(1000)

    def _swing_step(self):
        self._swing_t += 0.04
        # Pendel: ~±14° Amplitude, leicht abklingend sieht cooler aus, aber
        # für Alice lassen wir es gleichmäßig pendeln
        self._swing_angle = 14.0 * math.sin(self._swing_t)
        self.update()

    def _tick(self):
        self._blink_on = not self._blink_on
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        # Uhr-Mittelpunkt etwas unterhalb der Mitte (Platz für Kette oben)
        cy = self.height() / 2 + 20
        r  = 90.0   # äußerer Radius Gehäuse

        # ── Pendel-Transformation ────────────────────────────────────
        # Drehpunkt = oben an der Kette
        pivot_y = 10.0
        p.translate(cx, pivot_y)
        p.rotate(self._swing_angle)
        p.translate(0, -(pivot_y - cy))  # cy relativ zu pivot

        # Alles jetzt relativ zu (cx=0 nach translate, cy=cy)
        local_cx = 0.0
        local_cy = cy - pivot_y  # = cy - 10

        # ── Kette / Halterung ────────────────────────────────────────
        chain_pen = QPen(QColor("#B8860B"), 3)
        p.setPen(chain_pen)
        p.drawLine(QPointF(local_cx, 0), QPointF(local_cx, local_cy - r + 4))

        # Krönung (Crown) oben
        p.setBrush(QBrush(QColor("#DAA520")))
        p.setPen(QPen(QColor("#8B6914"), 1))
        p.drawEllipse(QPointF(local_cx, local_cy - r - 6), 7, 7)

        # ── Äußeres Gehäuse (Gold-Gradient) ─────────────────────────
        grad_outer = QRadialGradient(
            QPointF(local_cx - r * 0.3, local_cy - r * 0.3),
            r * 2.2
        )
        grad_outer.setColorAt(0.0, QColor("#FFD700"))
        grad_outer.setColorAt(0.5, QColor("#DAA520"))
        grad_outer.setColorAt(1.0, QColor("#8B6914"))
        p.setBrush(QBrush(grad_outer))
        p.setPen(QPen(QColor("#5C4000"), 2))
        p.drawEllipse(QPointF(local_cx, local_cy), r, r)

        # ── Inneres Zifferblatt ──────────────────────────────────────
        ri = r - 10
        face_grad = QRadialGradient(QPointF(local_cx, local_cy), ri * 1.4)
        face_grad.setColorAt(0.0, QColor("#FFFDE7"))
        face_grad.setColorAt(1.0, QColor("#F5E6C8"))
        p.setBrush(QBrush(face_grad))
        p.setPen(QPen(QColor("#C9A227"), 1))
        p.drawEllipse(QPointF(local_cx, local_cy), ri, ri)

        # ── Stundenstrich­e ──────────────────────────────────────────
        for h in range(1, 13):
            angle_rad = math.radians(h * 30 - 90)
            is_major = (h % 3 == 0)
            tick_len = 10 if is_major else 5
            x1 = local_cx + (ri - 4)       * math.cos(angle_rad)
            y1 = local_cy + (ri - 4)       * math.sin(angle_rad)
            x2 = local_cx + (ri - 4 - tick_len) * math.cos(angle_rad)
            y2 = local_cy + (ri - 4 - tick_len) * math.sin(angle_rad)
            tick_pen = QPen(QColor("#5C3D00"), 3 if is_major else 1)
            p.setPen(tick_pen)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── Römische Ziffern (12, 3, 6, 9) ──────────────────────────
        roman_font = QFont("Times New Roman", 9, QFont.Weight.Bold)
        p.setFont(roman_font)
        p.setPen(QPen(QColor("#3B2000")))
        for h in [12, 3, 6, 9]:
            angle_rad = math.radians(h * 30 - 90)
            rx = local_cx + (ri - 22) * math.cos(angle_rad)
            ry = local_cy + (ri - 22) * math.sin(angle_rad)
            txt = self._ROMAN[h]
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(txt)
            th = fm.ascent()
            p.drawText(QPointF(rx - tw / 2, ry + th / 2 - 1), txt)

        # ── Zeiger-Berechnung aus echter Uhrzeit ────────────────────
        now = QTime.currentTime()
        sec  = now.second()
        minn = now.minute()
        hour = now.hour() % 12

        sec_angle  = math.radians(sec  * 6   - 90)
        min_angle  = math.radians(minn * 6   + sec  * 0.1 - 90)
        hour_angle = math.radians(hour * 30  + minn * 0.5 - 90)

        # Stundenzeiger (kurz, dick, dunkel)
        p.setPen(QPen(QColor("#1A0A00"), 5, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawLine(
            QPointF(local_cx, local_cy),
            QPointF(local_cx + (ri * 0.5) * math.cos(hour_angle),
                    local_cy + (ri * 0.5) * math.sin(hour_angle))
        )
        # Minutenzeiger (lang, mittel)
        p.setPen(QPen(QColor("#1A0A00"), 3, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawLine(
            QPointF(local_cx, local_cy),
            QPointF(local_cx + (ri * 0.72) * math.cos(min_angle),
                    local_cy + (ri * 0.72) * math.sin(min_angle))
        )
        # Sekundenzeiger (dünn, rot, TICKEND – kein Smooth)
        sec_snap = math.radians(sec * 6 - 90)
        p.setPen(QPen(QColor("#CC0000"), 1, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawLine(
            QPointF(local_cx - 15 * math.cos(sec_snap),
                    local_cy - 15 * math.sin(sec_snap)),
            QPointF(local_cx + (ri * 0.82) * math.cos(sec_snap),
                    local_cy + (ri * 0.82) * math.sin(sec_snap))
        )

        # ── Mittelpivot ──────────────────────────────────────────────
        p.setPen(QPen(QColor("#5C3D00"), 1))
        p.setBrush(QBrush(QColor("#FFD700")))
        p.drawEllipse(QPointF(local_cx, local_cy), 5, 5)

        # ── Tick-Blink (kleiner roter Punkt oben rechts auf Zifferblatt)
        if self._blink_on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#CC0000")))
            bx = local_cx + ri * 0.5
            by = local_cy - ri * 0.5
            p.drawEllipse(QPointF(bx, by), 4, 4)

        p.end()


# ---------------------------------------------------------------------------
class Code19Widget(QWidget):
    """Seite zum Öffnen der Code-19-Excel-Datei."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Titel-Bar ──────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e0;")
        title_bar.setFixedHeight(52)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)
        lbl = QLabel("🕐 Code 19")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {FIORI_TEXT};")
        title_layout.addWidget(lbl)
        title_layout.addStretch()
        root.addWidget(title_bar)

        # ── Inhalt ─────────────────────────────────────────────────────
        content = QWidget()
        content.setStyleSheet("background-color: #f5f6f7;")
        layout = QVBoxLayout(content)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 30, 40, 30)

        # Animierte Uhr (Alice im Wunderland)
        self._watch = _PocketWatchWidget()
        layout.addWidget(self._watch, 0, Qt.AlignmentFlag.AlignCenter)

        # Spruch – Alice im Wunderland
        quote = QLabel('"Ich bin spät! Ich bin spät!"')
        quote.setFont(QFont("Times New Roman", 11, QFont.Weight.Normal,
                            italic=True))
        quote.setStyleSheet("color: #8B6914;")
        quote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(quote)

        self._pfad_lbl = QLabel()
        self._pfad_lbl.setStyleSheet("color: #555; font-size: 11px; font-family: Consolas, monospace;")
        self._pfad_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pfad_lbl.setWordWrap(True)
        layout.addWidget(self._pfad_lbl)

        self._status_lbl = QLabel()
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self._status_lbl)

        self._btn = QPushButton("📄  Code 19 öffnen")
        self._btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._btn.setFixedHeight(52)
        self._btn.setFixedWidth(280)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {FIORI_BLUE};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }}
            QPushButton:hover {{ background-color: #0855a9; }}
            QPushButton:disabled {{
                background-color: #b0b0b0;
                color: #e0e0e0;
            }}
        """)
        self._btn.clicked.connect(self._open)
        layout.addWidget(self._btn, 0, Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Pfad über ⚙️ Einstellungen konfigurierbar")
        hint.setStyleSheet("color: #999; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        root.addWidget(content, 1)
        self._refresh_ui()

    def refresh(self):
        self._refresh_ui()

    def _refresh_ui(self):
        pfad = get_setting('code19_datei')
        self._pfad_lbl.setText(pfad)
        if os.path.isfile(pfad):
            self._status_lbl.setText("✅ Datei gefunden")
            self._status_lbl.setStyleSheet("color: #107e3e; font-size: 11px;")
            self._btn.setEnabled(True)
        else:
            self._status_lbl.setText("⚠️ Datei nicht gefunden – Pfad in Einstellungen prüfen")
            self._status_lbl.setStyleSheet("color: #bb6600; font-size: 11px;")
            self._btn.setEnabled(False)

    def _open(self):
        pfad = get_setting('code19_datei')
        if not os.path.isfile(pfad):
            QMessageBox.warning(self, "Datei nicht gefunden",
                f"Die Datei wurde nicht gefunden:\n{pfad}\n\n"
                "Bitte den Pfad in den Einstellungen anpassen.")
            return
        try:
            os.startfile(pfad)
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Öffnen:\n{exc}")

