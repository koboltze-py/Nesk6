"""
Checklisten-Widget
Zeigt Drucksachen aus Daten/Drucksachen und ermoeglicht Einzel- und Gesamtdruck
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy,
    QMessageBox
)
from PySide6.QtCore import (
    Qt, Signal, QVariantAnimation, QEasingCurve, QPointF
)
from PySide6.QtGui import (
    QFont, QColor, QCursor, QPainter, QPainterPath,
    QLinearGradient, QPen, QBrush
)

from config import FIORI_BLUE, FIORI_TEXT, FIORI_WHITE, FIORI_LIGHT_BLUE

# ── Pfad ─────────────────────────────────────────────────────────────────────
try:
    from config import BASE_DIR
    DRUCKSACHEN_DIR = os.path.join(BASE_DIR, "Daten", "Drucksachen")
except Exception:
    DRUCKSACHEN_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Daten", "Drucksachen"
    )

# ── Dateityp-Konfiguration ────────────────────────────────────────────────────
EXT_INFO = {
    ".pdf":  ("📄", "#e53935"),
    ".docx": ("📝", "#1565c0"),
    ".doc":  ("📝", "#1565c0"),
    ".xlsx": ("📊", "#2e7d32"),
    ".xls":  ("📊", "#2e7d32"),
    ".pptx": ("📋", "#f57c00"),
    ".ppt":  ("📋", "#f57c00"),
    ".png":  ("🖼️",  "#6a1b9a"),
    ".jpg":  ("🖼️",  "#6a1b9a"),
    ".jpeg": ("🖼️",  "#6a1b9a"),
    ".txt":  ("📃", "#546e7a"),
}

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _ext_icon(ext: str) -> str:
    return EXT_INFO.get(ext.lower(), ("📁", "#546e7a"))[0]


def _ext_color(ext: str) -> str:
    return EXT_INFO.get(ext.lower(), ("📁", "#546e7a"))[1]


def _file_size_str(path: str) -> str:
    try:
        size = os.path.getsize(path)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size // 1024} KB"
        else:
            return f"{size / (1024*1024):.1f} MB"
    except Exception:
        return "?"


def _print_file(path: str) -> bool:
    """Sendet Datei an den Windows-Standarddrucker."""
    try:
        os.startfile(path, "print")
        return True
    except Exception:
        # Fallback: oeffnen (Benutzer druckt manuell)
        try:
            os.startfile(path)
            return True
        except Exception:
            return False


def _open_file(path: str) -> bool:
    """Oeffnet Datei mit Standardprogramm."""
    try:
        os.startfile(path)
        return True
    except Exception:
        return False


# ── Datei-Karte ───────────────────────────────────────────────────────────────

class FileCard(QFrame):
    """Moderne Karte fuer eine einzelne Drucksachen-Datei."""

    print_requested = Signal(str)   # filepath
    open_requested  = Signal(str)   # filepath

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self._filename = os.path.basename(filepath)
        self._ext = os.path.splitext(self._filename)[1]
        self._icon  = _ext_icon(self._ext)
        self._color = _ext_color(self._ext)
        self._build()
        self.setMouseTracking(True)

    @property
    def filepath(self) -> str:
        return self._filepath

    def _build(self):
        self.setFixedWidth(220)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self._apply_style(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(6)

        # --- Icon + Dateityp ---
        top = QHBoxLayout()
        icon_lbl = QLabel(self._icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 30))
        icon_lbl.setStyleSheet("border:none; background:transparent;")
        top.addWidget(icon_lbl)
        top.addStretch()

        ext_badge = QLabel(self._ext.upper().lstrip("."))
        ext_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        ext_badge.setStyleSheet(
            f"background:{self._color}; color:white; border-radius:4px;"
            f"padding: 2px 6px; border:none;"
        )
        ext_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(ext_badge)
        layout.addLayout(top)

        # --- Dateiname (max 2 Zeilen) ---
        name_lbl = QLabel(os.path.splitext(self._filename)[0])
        name_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {FIORI_TEXT}; border:none; background:transparent;")
        name_lbl.setWordWrap(True)
        name_lbl.setMaximumHeight(48)
        layout.addWidget(name_lbl)

        # --- Groesse ---
        size_lbl = QLabel(_file_size_str(self._filepath))
        size_lbl.setFont(QFont("Segoe UI", 9))
        size_lbl.setStyleSheet("color:#999; border:none; background:transparent;")
        layout.addWidget(size_lbl)

        layout.addStretch()

        # --- Buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_open = QPushButton("Öffnen")
        btn_open.setFont(QFont("Segoe UI", 9))
        btn_open.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {FIORI_BLUE};
                border: 1px solid {FIORI_BLUE};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background: {FIORI_BLUE};
                color: white;
            }}
        """)
        btn_open.clicked.connect(lambda: self.open_requested.emit(self._filepath))

        btn_print = QPushButton("🖨 Drucken")
        btn_print.setFont(QFont("Segoe UI", 9))
        btn_print.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_print.setStyleSheet(f"""
            QPushButton {{
                background: {FIORI_BLUE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background: #0056b3;
            }}
        """)
        btn_print.clicked.connect(lambda: self.print_requested.emit(self._filepath))

        btn_row.addWidget(btn_open)
        btn_row.addWidget(btn_print)
        layout.addLayout(btn_row)

    def _apply_style(self, hover: bool):
        shadow = "rgba(0,0,0,0.12)" if hover else "rgba(0,0,0,0.06)"
        border = f"2px solid {self._color}" if hover else "1px solid #e0e4ea"
        self.setStyleSheet(f"""
            FileCard {{
                background: white;
                border-radius: 10px;
                border: {border};
            }}
        """)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)


# ── Abschnitts-Header ─────────────────────────────────────────────────────────

class SectionHeader(QWidget):
    def __init__(self, title: str, count: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 4)

        lbl = QLabel(f"  {title}  ")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {FIORI_BLUE}; border:none; background:transparent;")

        cnt = QLabel(f"{count} Datei{'en' if count != 1 else ''}")
        cnt.setFont(QFont("Segoe UI", 9))
        cnt.setStyleSheet("color: #999; border:none; background:transparent;")

        line_r = QFrame()
        line_r.setFrameShape(QFrame.Shape.HLine)
        line_r.setFixedHeight(1)
        line_r.setStyleSheet("border:none; background:#d0d8e4;")
        line_r.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(lbl)
        layout.addWidget(cnt)
        layout.addSpacing(8)
        layout.addWidget(line_r)


# ── Haupt-Widget ──────────────────────────────────────────────────────────────

class ChecklistenWidget(QWidget):
    """Hauptseite fuer Checklisten / Drucksachen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[FileCard] = []
        self._build_ui()
        self.refresh()

    # ── Baue UI ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Topbar ────────────────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet("background: white; border-bottom: 1px solid #e0e4ea;")
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(28, 0, 28, 0)

        title_lbl = QLabel("📋  Checklisten & Drucksachen")
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {FIORI_TEXT}; border:none;")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont("Segoe UI", 9))
        self._status_lbl.setStyleSheet("color:#999; border:none;")
        tb_layout.addWidget(self._status_lbl)
        tb_layout.addSpacing(16)

        btn_refresh = QPushButton("🔄 Aktualisieren")
        btn_refresh.setFont(QFont("Segoe UI", 10))
        btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {FIORI_BLUE};
                border: 1px solid {FIORI_BLUE};
                border-radius: 5px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{ background: {FIORI_LIGHT_BLUE}; }}
        """)
        btn_refresh.clicked.connect(self.refresh)
        tb_layout.addWidget(btn_refresh)
        tb_layout.addSpacing(10)

        self._btn_all_print = QPushButton("🖨  Alle drucken")
        self._btn_all_print.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._btn_all_print.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_all_print.setStyleSheet(f"""
            QPushButton {{
                background: {FIORI_BLUE};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 6px 18px;
            }}
            QPushButton:hover {{ background: #0056b3; }}
            QPushButton:disabled {{ background: #bcc; color: #999; }}
        """)
        self._btn_all_print.clicked.connect(self._print_all)
        tb_layout.addWidget(self._btn_all_print)

        root.addWidget(topbar)

        # ── Scrollbereich ─────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f5f6f7; }")

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: #f5f6f7;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(28, 20, 28, 32)
        self._content_layout.setSpacing(0)

        scroll.setWidget(self._content_widget)
        root.addWidget(scroll, 1)

    # ── Dateien laden ─────────────────────────────────────────────────────────

    def refresh(self):
        """Laedt alle Dateien aus dem Drucksachen-Ordner neu."""
        self._cards.clear()
        self._clear_content()

        if not os.path.isdir(DRUCKSACHEN_DIR):
            self._show_empty(
                "📂  Ordner nicht gefunden",
                f"Der Ordner\n{DRUCKSACHEN_DIR}\nexistiert nicht."
            )
            self._btn_all_print.setEnabled(False)
            self._status_lbl.setText("")
            return

        # Sammle Dateien: Wurzel + Unterordner
        sections: list[tuple[str, list[str]]] = []

        # Wurzel-Dateien
        root_files = self._list_files(DRUCKSACHEN_DIR)
        if root_files:
            sections.append(("Drucksachen", root_files))

        # Unterordner
        try:
            for entry in sorted(os.scandir(DRUCKSACHEN_DIR), key=lambda e: e.name.lower()):
                if entry.is_dir():
                    sub_files = self._list_files(entry.path)
                    if sub_files:
                        sections.append((entry.name, sub_files))
        except Exception:
            pass

        if not sections:
            self._show_empty(
                "📂  Keine Dateien",
                f"Im Ordner wurden keine Dateien gefunden.\n{DRUCKSACHEN_DIR}"
            )
            self._btn_all_print.setEnabled(False)
            self._status_lbl.setText("Keine Dateien")
            return

        total = 0
        for section_name, files in sections:
            self._add_section(section_name, files)
            total += len(files)

        self._content_layout.addStretch()
        self._btn_all_print.setEnabled(True)
        self._status_lbl.setText(f"{total} Datei{'en' if total != 1 else ''}")

    def _list_files(self, folder: str) -> list[str]:
        """Gibt sortierte Liste aller (nicht-versteckten) Dateien zurueck."""
        result = []
        try:
            for entry in sorted(os.scandir(folder), key=lambda e: e.name.lower()):
                if entry.is_file() and not entry.name.startswith("."):
                    result.append(entry.path)
        except Exception:
            pass
        return result

    def _add_section(self, name: str, files: list[str]):
        self._content_layout.addWidget(SectionHeader(name, len(files)))
        self._content_layout.addSpacing(12)

        grid = CardGrid()
        for fp in files:
            card = FileCard(fp)
            card.print_requested.connect(self._print_single)
            card.open_requested.connect(self._open_single)
            grid.add_card(card)
            self._cards.append(card)

        self._content_layout.addWidget(grid)
        self._content_layout.addSpacing(24)

    def _clear_content(self):
        """Entfernt alle Widgets aus dem Content-Layout."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_empty(self, title: str, msg: str):
        container = QWidget()
        cl = QVBoxLayout(container)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.setContentsMargins(0, 80, 0, 0)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        t.setStyleSheet("color: #555; border:none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(t)

        m = QLabel(msg)
        m.setFont(QFont("Segoe UI", 11))
        m.setStyleSheet("color: #999; border:none;")
        m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(m)

        self._content_layout.addWidget(container)

    # ── Druck-Aktionen ─────────────────────────────────────────────────────────

    def _print_single(self, filepath: str):
        filename = os.path.basename(filepath)
        if not os.path.isfile(filepath):
            QMessageBox.warning(self, "Datei nicht gefunden",
                                f"Die Datei wurde nicht gefunden:\n{filepath}")
            return
        ok = _print_file(filepath)
        if not ok:
            QMessageBox.warning(self, "Drucken fehlgeschlagen",
                                f"Die Datei konnte nicht gedruckt werden:\n{filename}")

    def _open_single(self, filepath: str):
        if not os.path.isfile(filepath):
            QMessageBox.warning(self, "Datei nicht gefunden",
                                f"Die Datei wurde nicht gefunden:\n{filepath}")
            return
        ok = _open_file(filepath)
        if not ok:
            QMessageBox.warning(self, "Öffnen fehlgeschlagen",
                                f"Die Datei konnte nicht geöffnet werden:\n{os.path.basename(filepath)}")

    def _print_all(self):
        if not self._cards:
            return

        filepaths = [c.filepath for c in self._cards if os.path.isfile(c.filepath)]
        if not filepaths:
            QMessageBox.warning(self, "Keine Dateien", "Es wurden keine druckbaren Dateien gefunden.")
            return

        reply = QMessageBox.question(
            self,
            "Alle drucken",
            f"Sollen alle {len(filepaths)} Dateien gedruckt werden?\n\n"
            "Jede Datei wird an den Standarddrucker gesendet.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        failed = []
        for fp in filepaths:
            ok = _print_file(fp)
            if not ok:
                failed.append(os.path.basename(fp))

        if failed:
            QMessageBox.warning(
                self,
                "Teilerfolg",
                f"{len(filepaths)-len(failed)} von {len(filepaths)} Dateien gesendet.\n\n"
                f"Fehlgeschlagen:\n" + "\n".join(f"  • {f}" for f in failed)
            )
        else:
            QMessageBox.information(
                self,
                "Drucken",
                f"Alle {len(filepaths)} Dateien wurden an den Drucker gesendet."
            )


# ── Karten-Grid (QGridLayout, 4 Spalten) ─────────────────────────────────────

class CardGrid(QWidget):
    """Zeigt FileCards in einem QGridLayout mit 4 festen Spalten."""

    COLS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self)
        self._grid.setSpacing(16)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._row = 0
        self._col = 0

    def add_card(self, card: FileCard):
        self._grid.addWidget(card, self._row, self._col,
                             Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._col += 1
        if self._col >= self.COLS:
            self._col = 0
            self._row += 1
