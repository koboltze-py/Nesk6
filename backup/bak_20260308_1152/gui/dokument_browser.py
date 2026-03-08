"""
Dokument-Browser Widget
Zeigt Ordnerinhalte an und erlaubt das Öffnen / Drucken von Dokumenten
"""
import os
import subprocess
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Dateiendung → lesbares Label + Icon
_EXT_META = {
    ".pdf":  ("📄", "#e74c3c"),
    ".docx": ("📝", "#2980b9"),
    ".doc":  ("📝", "#2980b9"),
    ".xlsx": ("📊", "#27ae60"),
    ".xls":  ("📊", "#27ae60"),
    ".pptx": ("📊", "#e67e22"),
    ".ppt":  ("📊", "#e67e22"),
    ".png":  ("🖼", "#8e44ad"),
    ".jpg":  ("🖼", "#8e44ad"),
    ".jpeg": ("🖼", "#8e44ad"),
    ".txt":  ("📃", "#7f8c8d"),
    ".odt":  ("📝", "#27ae60"),
    ".ods":  ("📊", "#27ae60"),
}

_FOLDER_ICON = "📁"
_DEFAULT_ICON = ("📄", "#95a5a6")


def _icon_for(name: str):
    ext = os.path.splitext(name)[-1].lower()
    return _EXT_META.get(ext, _DEFAULT_ICON)


class _FileItem(QFrame):
    """Einzelne Datei-Zeile im Browser."""

    def __init__(self, path: str, name: str, parent=None):
        super().__init__(parent)
        self._path = path
        self._build(name)

    def _build(self, name: str):
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            QFrame:hover {
                border: 1px solid #b0c4de;
                background: #f5f8fc;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        icon_ch, icon_color = _icon_for(name)
        icon_lbl = QLabel(icon_ch)
        icon_lbl.setFont(QFont("Arial", 16))
        icon_lbl.setFixedWidth(26)
        icon_lbl.setStyleSheet(f"color: {icon_color}; border: none;")

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Arial", 10))
        name_lbl.setStyleSheet("color: #2c3e50; border: none;")
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        name_lbl.setToolTip(self._path)

        btn_open = QPushButton("Öffnen")
        btn_open.setFixedSize(72, 28)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setStyleSheet("""
            QPushButton {
                background: #2980b9; color: white;
                border: none; border-radius: 3px;
                font-size: 10px; font-weight: bold;
            }
            QPushButton:hover { background: #1a6fa3; }
        """)
        btn_open.clicked.connect(self._oeffnen)

        btn_print = QPushButton("🖨 Drucken")
        btn_print.setFixedSize(78, 28)
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setStyleSheet("""
            QPushButton {
                background: #27ae60; color: white;
                border: none; border-radius: 3px;
                font-size: 10px; font-weight: bold;
            }
            QPushButton:hover { background: #1e8449; }
        """)
        btn_print.clicked.connect(self._drucken)

        layout.addWidget(icon_lbl)
        layout.addWidget(name_lbl, 1)
        layout.addWidget(btn_open)
        layout.addWidget(btn_print)

    def _oeffnen(self):
        try:
            os.startfile(self._path)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Kann Datei nicht öffnen:\n{e}")

    def _drucken(self):
        try:
            if sys.platform == "win32":
                os.startfile(self._path, "print")
            else:
                subprocess.Popen(["lp", self._path])
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Drucken nicht möglich:\n{e}")


class _FolderSection(QFrame):
    """Klappt-Sektion für einen Unterordner."""

    def __init__(self, folder_path: str, folder_name: str, parent=None):
        super().__init__(parent)
        self._folder = folder_path
        self._folder_name = folder_name
        self._expanded = True
        self._items: list[_FileItem] = []
        self._build()

    def _build(self):
        self.setStyleSheet("QFrame { border: none; }")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 4)
        self._layout.setSpacing(2)

        # Kopfzeile mit Klapptaste
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: #dde3ec;
                border-radius: 4px;
                border: none;
            }
        """)
        header.setFixedHeight(34)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 4, 10, 4)

        self._toggle_btn = QPushButton("▼")
        self._toggle_btn.setFixedSize(20, 20)
        self._toggle_btn.setStyleSheet(
            "QPushButton{border:none;background:transparent;font-size:10px;color:#555;}"
        )
        self._toggle_btn.clicked.connect(self._toggle)

        lbl = QLabel(f"{_FOLDER_ICON} {self._folder_name}")
        lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #1a2942; border: none;")
        hl.addWidget(self._toggle_btn)
        hl.addWidget(lbl, 1)

        open_folder_btn = QPushButton("Ordner öffnen")
        open_folder_btn.setFixedSize(100, 22)
        open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_folder_btn.setStyleSheet(
            "QPushButton{background:#7f8c8d;color:white;border:none;border-radius:3px;font-size:9px;}"
            "QPushButton:hover{background:#5d6d7e;}"
        )
        open_folder_btn.clicked.connect(lambda: os.startfile(self._folder))
        hl.addWidget(open_folder_btn)

        self._layout.addWidget(header)

        # Datei-Container
        self._content = QWidget()
        self._content.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(self._content)
        cl.setContentsMargins(12, 2, 0, 2)
        cl.setSpacing(3)
        self._content_layout = cl

        self._load_files()
        self._layout.addWidget(self._content)

    def _load_files(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._items.clear()

        try:
            entries = sorted(os.listdir(self._folder))
        except PermissionError:
            lbl = QLabel("⚠ Kein Zugriff")
            lbl.setStyleSheet("color:#c0392b;font-size:10px;border:none;padding:4px;")
            self._content_layout.addWidget(lbl)
            return

        files = [e for e in entries
                 if os.path.isfile(os.path.join(self._folder, e))
                 and not e.startswith(".")]

        if not files:
            lbl = QLabel("(Keine Dateien)")
            lbl.setStyleSheet("color:#aaa;font-size:10px;border:none;padding:4px;")
            self._content_layout.addWidget(lbl)
            return

        for name in files:
            path = os.path.join(self._folder, name)
            fi = _FileItem(path, name)
            self._items.append(fi)
            self._content_layout.addWidget(fi)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._toggle_btn.setText("▼" if self._expanded else "►")

    def apply_search(self, text: str):
        """Zeigt nur Dateien, deren Name den Suchtext enthält."""
        text = text.lower()
        visible_count = 0
        for fi in self._items:
            show = not text or text in fi._path.lower().split(os.sep)[-1].lower()
            fi.setVisible(show)
            if show:
                visible_count += 1
        self.setVisible(True)  # Sektion immer zeigen, auch wenn leer


class DokumentBrowserWidget(QWidget):
    """
    Wiederverwendbares Dokument-Browser Widget.
    Zeigt Inhalte eines Ordners und erlaubt Öffnen/Drucken.

    Parameters
    ----------
    title:            Überschrift im Header
    folder_path:      Pfad zum anzuzeigenden Ordner
    allow_subfolders: Wenn True, werden Unterordner als klappbare Sektionen gezeigt
    """

    def __init__(self, title: str, folder_path: str,
                 allow_subfolders: bool = False, parent=None):
        super().__init__(parent)
        self._title = title
        self._folder = folder_path
        self._allow_subfolders = allow_subfolders
        self._sections: list[_FolderSection] = []
        self._flat_items: list[_FileItem] = []
        self._build_ui()
        self._load()

    # ── UI-Aufbau ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: #1b3a5c;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 8, 20, 8)

        title_lbl = QLabel(self._title)
        title_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: white; border: none;")
        hl.addWidget(title_lbl)
        hl.addStretch()

        btn_ordner = QPushButton("📂 Ordner öffnen")
        btn_ordner.setFixedHeight(36)
        btn_ordner.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ordner.setStyleSheet("""
            QPushButton {
                background: #2980b9; color: white;
                border: none; border-radius: 4px;
                padding: 4px 14px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #1a6fa3; }
        """)
        btn_ordner.clicked.connect(self._ordner_oeffnen)
        hl.addWidget(btn_ordner)

        btn_refresh = QPushButton("🔄 Aktualisieren")
        btn_refresh.setFixedHeight(36)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background: #27ae60; color: white;
                border: none; border-radius: 4px;
                padding: 4px 14px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #1e8449; }
        """)
        btn_refresh.clicked.connect(self.refresh)
        hl.addWidget(btn_refresh)

        root.addWidget(header)

        # Suchleiste
        search_bar = QFrame()
        search_bar.setFixedHeight(46)
        search_bar.setStyleSheet("background: #f0f2f4; border-bottom: 1px solid #ddd;")
        sl = QHBoxLayout(search_bar)
        sl.setContentsMargins(16, 6, 16, 6)
        sl.setSpacing(8)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("border: none; font-size: 14px;")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Dateiname suchen ...")
        self._search_input.setStyleSheet(
            "background: white; border: 1px solid #ccc; border-radius: 4px;"
            "padding: 4px 10px; font-size: 12px;"
        )
        self._search_input.textChanged.connect(self._apply_filter)

        sl.addWidget(search_icon)
        sl.addWidget(self._search_input, 1)
        root.addWidget(search_bar)

        # Pfad-Anzeige
        self._path_lbl = QLabel()
        self._path_lbl.setStyleSheet(
            "background: #fafafa; border-bottom: 1px solid #e8e8e8;"
            "color: #888; font-size: 10px; padding: 3px 16px; border-top: none;"
        )
        root.addWidget(self._path_lbl)

        # Scrollbereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f5f6f7; }")

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: #f5f6f7;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(16, 12, 16, 12)
        self._content_layout.setSpacing(4)
        self._content_layout.addStretch()

        scroll.setWidget(self._content_widget)
        root.addWidget(scroll, 1)

    # ── Laden ─────────────────────────────────────────────────────────────────

    def _load(self):
        # Vorherige Inhalte entfernen
        while self._content_layout.count() > 1:
            it = self._content_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self._sections.clear()
        self._flat_items.clear()

        # Pfad anzeigen
        self._path_lbl.setText(f"📂 {self._folder}")

        if not os.path.isdir(self._folder):
            lbl = QLabel(f"⚠ Ordner nicht gefunden:\n{self._folder}")
            lbl.setStyleSheet("color: #c0392b; font-size: 12px; padding: 20px; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.insertWidget(0, lbl)
            return

        try:
            entries = sorted(os.listdir(self._folder))
        except PermissionError:
            lbl = QLabel("⚠ Kein Zugriff auf den Ordner.")
            lbl.setStyleSheet("color: #c0392b; font-size: 12px; padding: 20px; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.insertWidget(0, lbl)
            return

        insert_pos = 0

        if self._allow_subfolders:
            for name in entries:
                full = os.path.join(self._folder, name)
                if os.path.isdir(full) and not name.startswith("."):
                    sec = _FolderSection(full, name)
                    self._sections.append(sec)
                    self._content_layout.insertWidget(insert_pos, sec)
                    insert_pos += 1

        # Direkte Dateien des Hauptordners
        files = [e for e in entries
                 if os.path.isfile(os.path.join(self._folder, e))
                 and not e.startswith(".")]

        if files:
            if self._allow_subfolders and self._sections:
                # Abschnitt für Dateien direkt im Hauptordner
                root_sec = _FolderSection(self._folder, "(Hauptordner)")
                # Wir nutzen hier _FolderSection nur als Layout-Wrapper
                self._sections.append(root_sec)
                self._content_layout.insertWidget(insert_pos, root_sec)
                insert_pos += 1
            else:
                for fname in files:
                    path = os.path.join(self._folder, fname)
                    fi = _FileItem(path, fname)
                    self._flat_items.append(fi)
                    self._content_layout.insertWidget(insert_pos, fi)
                    insert_pos += 1

        if not files and not self._sections:
            lbl = QLabel("📭 Keine Dateien vorhanden.")
            lbl.setStyleSheet("color: #aaa; font-size: 12px; padding: 20px; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.insertWidget(0, lbl)

    # ── Filter ─────────────────────────────────────────────────────────────────

    def _apply_filter(self):
        text = self._search_input.text().strip().lower()
        for sec in self._sections:
            sec.apply_search(text)
        for fi in self._flat_items:
            fname = os.path.basename(fi._path).lower()
            fi.setVisible(not text or text in fname)

    # ── Aktionen ───────────────────────────────────────────────────────────────

    def _ordner_oeffnen(self):
        try:
            os.startfile(self._folder)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Ordner konnte nicht geöffnet werden:\n{e}")

    def refresh(self):
        """Ordnerinhalt neu laden."""
        self._search_input.clear()
        self._load()
