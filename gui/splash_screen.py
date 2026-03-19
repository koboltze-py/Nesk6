"""
Ladebildschirm (Splash Screen)
Wird beim App-Start angezeigt während Backup, Migration und Turso-Sync laufen.
"""
import os
import sys

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QPixmap, QIcon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# DRK-Farben
_DRK_RED   = "#C8102E"
_DRK_DARK  = "#1A1A2E"
_DRK_CARD  = "#16213E"
_DRK_BLUE  = "#0F3460"
_WHITE     = "#FFFFFF"
_GRAY      = "#B0B8C8"


class SplashScreen(QWidget):
    """
    Frameless Ladebildschirm – zentriert, immer im Vordergrund.
    Aufruf:
        splash = SplashScreen()
        splash.show()
        QApplication.processEvents()
        splash.set_status("Schritt 1 ...")
        ...
        splash.finish(main_window)  # schließt Splash, übergibt Fokus
    """

    def __init__(self, version: str = ""):
        super().__init__()
        self._version = version
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(520, 320)
        self._center()
        self._build_ui()

    def _center(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2,
            )

    def _build_ui(self):
        self.setStyleSheet(f"background-color: {_DRK_DARK};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 28)
        layout.setSpacing(0)

        # ── Rotes Trennband oben ──────────────────────────────────────────
        band = QWidget()
        band.setFixedHeight(5)
        band.setStyleSheet(f"background-color: {_DRK_RED}; border-radius: 2px;")
        layout.addWidget(band)

        layout.addSpacing(24)

        # ── Logo-Bereich (Kreuz-Symbol) ───────────────────────────────────
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_px = self._draw_red_cross(64)
        logo_label.setPixmap(logo_px)
        layout.addWidget(logo_label)

        layout.addSpacing(16)

        # ── App-Titel ─────────────────────────────────────────────────────
        title = QLabel("NESK 3")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {_WHITE}; font-size: 28pt; font-weight: bold; letter-spacing: 4px;")
        layout.addWidget(title)

        # ── Untertitel ────────────────────────────────────────────────────
        sub = QLabel("DRK Flughafen Köln/Bonn")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {_GRAY}; font-size: 11pt;")
        layout.addWidget(sub)

        layout.addSpacing(6)

        # ── Version ───────────────────────────────────────────────────────
        if self._version:
            ver = QLabel(f"Version {self._version}")
            ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ver.setStyleSheet(f"color: {_GRAY}; font-size: 9pt; opacity: 0.7;")
            layout.addWidget(ver)

        layout.addStretch()

        # ── Status-Zeile ──────────────────────────────────────────────────
        self._status = QLabel("Wird gestartet …")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"color: {_GRAY}; font-size: 9pt;")
        layout.addWidget(self._status)

        layout.addSpacing(8)

        # ── Rotes Trennband unten ─────────────────────────────────────────
        band2 = QWidget()
        band2.setFixedHeight(3)
        band2.setStyleSheet(f"background-color: {_DRK_RED}; border-radius: 1px;")
        layout.addWidget(band2)

    def _draw_red_cross(self, size: int) -> QPixmap:
        """Zeichnet ein stilisiertes rotes Kreuz als Pixmap."""
        # Prüfen ob icon-Datei vorhanden
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Daten", "Logo", "nesk3.ico"
        )
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            px = icon.pixmap(size, size)
            if not px.isNull():
                return px

        # Fallback: Kreuz zeichnen
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        red = QColor(_DRK_RED)
        painter.setBrush(QBrush(red))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        arm = size // 3
        cx = size // 2
        # Waagerechter Balken
        painter.drawRect(0, cx - arm // 2, size, arm)
        # Senkrechter Balken
        painter.drawRect(cx - arm // 2, 0, arm, size)
        painter.end()
        return px

    def set_status(self, message: str):
        """Aktualisiert die Status-Zeile und verarbeitet Events sofort."""
        self._status.setText(message)
        QApplication.processEvents()

    def finish(self, main_window=None):
        """Schließt den Splash Screen. Optional: Fokus an main_window übergeben."""
        self.close()
