"""
Dienstliches Widget
Dienstliche Protokolle: Einsätze nach Einsatzstatistik-Vorlage FKB
"""
import os
import sys
import sqlite3
from contextlib import contextmanager
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QDateEdit, QTimeEdit, QSpinBox, QRadioButton,
    QButtonGroup, QMessageBox, QSizePolicy, QScrollArea, QGroupBox,
    QCheckBox
)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QFont, QColor

from config import FIORI_BLUE, FIORI_TEXT, BASE_DIR, FIORI_BORDER


# ──────────────────────────────────────────────────────────────────────────────
#  Datenbank
# ──────────────────────────────────────────────────────────────────────────────

_EINSATZ_DB_DIR  = os.path.join(BASE_DIR, "database SQL")
_EINSATZ_DB_PFAD = os.path.join(_EINSATZ_DB_DIR, "einsaetze.db")
_EINSATZ_PROTO_DIR = os.path.join(BASE_DIR, "Daten", "Einsatz")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS einsaetze (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    erstellt_am      TEXT    NOT NULL,
    datum            TEXT    NOT NULL,          -- dd.MM.yyyy
    uhrzeit          TEXT    NOT NULL,          -- HH:mm (Alarmierungszeit)
    einsatzdauer     INTEGER DEFAULT 0,         -- Minuten
    einsatzstichwort TEXT    DEFAULT '',
    einsatzort       TEXT    DEFAULT '',
    einsatznr_drk    TEXT    DEFAULT '',
    drk_ma1          TEXT    DEFAULT '',
    drk_ma2          TEXT    DEFAULT '',
    angenommen       INTEGER DEFAULT 1,         -- 1=Ja, 0=Nein
    grund_abgelehnt  TEXT    DEFAULT '',        -- warum nicht angenommen
    bemerkung        TEXT    DEFAULT ''
);
"""


def _ensured_db() -> str:
    os.makedirs(_EINSATZ_DB_DIR, exist_ok=True)
    con = sqlite3.connect(_EINSATZ_DB_PFAD, timeout=5)
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous  = NORMAL")
    con.execute("PRAGMA busy_timeout  = 5000")
    con.execute(_CREATE_SQL)
    con.commit()
    con.close()
    return _EINSATZ_DB_PFAD


@contextmanager
def _db():
    _ensured_db()
    con = sqlite3.connect(_EINSATZ_DB_PFAD, timeout=5)
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous  = NORMAL")
    con.execute("PRAGMA busy_timeout  = 5000")
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def einsatz_speichern(daten: dict) -> int:
    with _db() as con:
        cur = con.execute(
            """
            INSERT INTO einsaetze (
                erstellt_am, datum, uhrzeit, einsatzdauer,
                einsatzstichwort, einsatzort, einsatznr_drk,
                drk_ma1, drk_ma2, angenommen, grund_abgelehnt, bemerkung
            ) VALUES (
                :erstellt_am, :datum, :uhrzeit, :einsatzdauer,
                :einsatzstichwort, :einsatzort, :einsatznr_drk,
                :drk_ma1, :drk_ma2, :angenommen, :grund_abgelehnt, :bemerkung
            )
            """,
            {
                "erstellt_am":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "datum":            daten.get("datum", ""),
                "uhrzeit":          daten.get("uhrzeit", ""),
                "einsatzdauer":     daten.get("einsatzdauer", 0),
                "einsatzstichwort": daten.get("einsatzstichwort", ""),
                "einsatzort":       daten.get("einsatzort", ""),
                "einsatznr_drk":    daten.get("einsatznr_drk", ""),
                "drk_ma1":          daten.get("drk_ma1", ""),
                "drk_ma2":          daten.get("drk_ma2", ""),
                "angenommen":       1 if daten.get("angenommen", True) else 0,
                "grund_abgelehnt":  daten.get("grund_abgelehnt", ""),
                "bemerkung":        daten.get("bemerkung", ""),
            },
        )
        return cur.lastrowid


def einsatz_aktualisieren(row_id: int, daten: dict) -> None:
    with _db() as con:
        con.execute(
            """
            UPDATE einsaetze SET
                datum=:datum, uhrzeit=:uhrzeit, einsatzdauer=:einsatzdauer,
                einsatzstichwort=:einsatzstichwort, einsatzort=:einsatzort,
                einsatznr_drk=:einsatznr_drk, drk_ma1=:drk_ma1, drk_ma2=:drk_ma2,
                angenommen=:angenommen, grund_abgelehnt=:grund_abgelehnt, bemerkung=:bemerkung
            WHERE id=:id
            """,
            {
                "id":               row_id,
                "datum":            daten.get("datum", ""),
                "uhrzeit":          daten.get("uhrzeit", ""),
                "einsatzdauer":     daten.get("einsatzdauer", 0),
                "einsatzstichwort": daten.get("einsatzstichwort", ""),
                "einsatzort":       daten.get("einsatzort", ""),
                "einsatznr_drk":    daten.get("einsatznr_drk", ""),
                "drk_ma1":          daten.get("drk_ma1", ""),
                "drk_ma2":          daten.get("drk_ma2", ""),
                "angenommen":       1 if daten.get("angenommen", True) else 0,
                "grund_abgelehnt":  daten.get("grund_abgelehnt", ""),
                "bemerkung":        daten.get("bemerkung", ""),
            },
        )


def einsatz_loeschen(row_id: int) -> None:
    with _db() as con:
        con.execute("DELETE FROM einsaetze WHERE id=?", (row_id,))


def lade_einsaetze(
    *,
    monat: int | None = None,
    jahr: int | None = None,
    suchtext: str | None = None,
) -> list[dict]:
    where_parts: list[str] = []
    params: list = []
    if monat is not None:
        where_parts.append("substr(datum,4,2)=?")
        params.append(f"{monat:02d}")
    if jahr is not None:
        where_parts.append("substr(datum,7,4)=?")
        params.append(str(jahr))
    if suchtext:
        t = f"%{suchtext}%"
        where_parts.append(
            "(einsatzstichwort LIKE ? OR einsatzort LIKE ? OR drk_ma1 LIKE ?"
            " OR drk_ma2 LIKE ? OR einsatznr_drk LIKE ?)"
        )
        params.extend([t, t, t, t, t])

    sql = "SELECT * FROM einsaetze"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    sql += " ORDER BY substr(datum,7,4)||substr(datum,4,2)||substr(datum,1,2) DESC, id DESC"

    with _db() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def verfuegbare_jahre_einsaetze() -> list[int]:
    with _db() as con:
        rows = con.execute(
            "SELECT DISTINCT substr(datum,7,4) AS j FROM einsaetze"
            " WHERE length(datum)=10 ORDER BY j DESC"
        ).fetchall()
    result = []
    for r in rows:
        try:
            result.append(int(r["j"]))
        except (ValueError, TypeError):
            pass
    return result


# ──────────────────────────────────────────────────────────────────────────────
#  Excel-Export
# ──────────────────────────────────────────────────────────────────────────────

_PROTOKOLL_DIR = os.path.join(_EINSATZ_PROTO_DIR, "Protokolle")


def export_einsaetze_excel(
    eintraege: list[dict],
    ziel_pfad: str | None = None,
    titel_zeitraum: str = "",
) -> str:
    """
    Exportiert eine Liste von Einsätzen als Excel-Datei.
    Gibt den tatsächlichen Speicherpfad zurück.
    ziel_pfad: vollständiger Pfad inkl. Dateiname; None = Standardordner.
    """
    try:
        import openpyxl
        from openpyxl.styles import (
            Font, PatternFill, Alignment, Border, Side
        )
        from openpyxl.utils import get_column_letter
    except ImportError as e:
        raise ImportError(
            "openpyxl ist nicht installiert. Bitte 'pip install openpyxl' ausführen."
        ) from e

    os.makedirs(_PROTOKOLL_DIR, exist_ok=True)

    if not ziel_pfad:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dateiname = f"Einsatzprotokoll_{ts}.xlsx"
        ziel_pfad = os.path.join(_PROTOKOLL_DIR, dateiname)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Einsätze"

    # ── Farben / Stile ────────────────────────────────────────────────────
    rot_drk   = "C8102E"   # DRK-Rot
    hell_grau = "F2F2F2"
    gruen_bg  = "E8F5E9"
    rot_bg    = "FFE0E0"
    thin = Side(style="thin", color="AAAAAA")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    hdr_font  = Font(bold=True, color="FFFFFF", size=11)
    hdr_fill  = PatternFill("solid", fgColor=rot_drk)
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # ── Titel-Zeile ────────────────────────────────────────────────────────
    ws.merge_cells("A1:K1")
    titel_cell = ws["A1"]
    titel_text = "Einsatzstatistik – Notfalleinsätze FKB (DRK)"
    if titel_zeitraum:
        titel_text += f"  |  {titel_zeitraum}"
    titel_cell.value = titel_text
    titel_cell.font  = Font(bold=True, size=13, color="FFFFFF")
    titel_cell.fill  = PatternFill("solid", fgColor=rot_drk)
    titel_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # ── Untertitel ─────────────────────────────────────────────────────────
    ws.merge_cells("A2:K2")
    sub = ws["A2"]
    sub.value = (
        f"Erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M')}  –  "
        f"{len(eintraege)} Einsatz/ätze"
    )
    sub.font      = Font(italic=True, size=9, color="666666")
    sub.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 16

    # ── Spaltenüberschriften ───────────────────────────────────────────────
    headers = [
        "Lfd. Nr.", "Datum", "Uhrzeit", "Dauer\n(Min.)",
        "Einsatzstichwort", "Einsatzort", "Einsatznr. DRK",
        "DRK MA 1", "DRK MA 2", "Angenommen", "Grund (bei Nein) / Bemerkung"
    ]
    col_widths = [9, 13, 10, 10, 36, 22, 16, 20, 20, 13, 36]

    for col, (h, w) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = hdr_align
        cell.border    = border
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.row_dimensions[3].height = 32

    # ── Datenzeilen ────────────────────────────────────────────────────────
    ang_count = 0
    for row_idx, e in enumerate(eintraege, start=1):
        ang = bool(e.get("angenommen", 1))
        if ang:
            ang_count += 1
        row_num = row_idx + 3  # Zeile 4+
        bg_color = gruen_bg if ang else rot_bg
        row_fill = PatternFill("solid", fgColor=bg_color)

        dauer = e.get("einsatzdauer", 0) or 0
        grund_bem = e.get("grund_abgelehnt", "") or ""
        if e.get("bemerkung"):
            if grund_bem:
                grund_bem += "  |  " + e["bemerkung"]
            else:
                grund_bem = e["bemerkung"]

        values = [
            row_idx,
            e.get("datum", ""),
            e.get("uhrzeit", ""),
            dauer if dauer else "",
            e.get("einsatzstichwort", ""),
            e.get("einsatzort", ""),
            e.get("einsatznr_drk", "") or "",
            e.get("drk_ma1", ""),
            e.get("drk_ma2", "") or "",
            "Ja" if ang else "Nein",
            grund_bem,
        ]
        for col, val in enumerate(values, start=1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.fill   = row_fill
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=(col in (5, 11)))
            if col in (1, 3, 4, 10):
                cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row_num].height = 16

    # ── Statistik-Zeile ────────────────────────────────────────────────────
    stat_row = len(eintraege) + 5
    ws.merge_cells(f"A{stat_row}:K{stat_row}")
    stat_cell = ws.cell(row=stat_row, column=1)
    abgelehnt = len(eintraege) - ang_count
    stat_cell.value = (
        f"Gesamt: {len(eintraege)}   ✅ Angenommen: {ang_count}   "
        f"❌ Abgelehnt / nicht angenommen: {abgelehnt}"
    )
    stat_cell.font  = Font(bold=True, size=10)
    stat_cell.fill  = PatternFill("solid", fgColor="E3F2FD")
    stat_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[stat_row].height = 20

    # ── Zeile einfrieren ────────────────────────────────────────────────────
    ws.freeze_panes = "A4"

    wb.save(ziel_pfad)
    return ziel_pfad


# ──────────────────────────────────────────────────────────────────────────────
#  Hilfsstile
# ──────────────────────────────────────────────────────────────────────────────

def _btn(text: str, color: str = FIORI_BLUE, hover: str = "#0057b8") -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(32)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {color}; color: white; border: none;
            border-radius: 4px; padding: 4px 14px; font-size: 12px;
        }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:disabled {{ background: #bbb; color: #888; }}
    """)
    return btn


def _btn_light(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(32)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton { background:#eee; color:#333; border:none;
            border-radius:4px; padding:4px 14px; font-size:12px; }
        QPushButton:hover { background:#ddd; }
        QPushButton:disabled { background:#f5f5f5; color:#bbb; }
    """)
    return btn


# ──────────────────────────────────────────────────────────────────────────────
#  Dialog: Einsatz erfassen / bearbeiten
# ──────────────────────────────────────────────────────────────────────────────

class _EinsatzDialog(QDialog):
    """Formular zum Anlegen oder Bearbeiten eines Notfalleinsatzes."""

    _FIELD_STYLE = (
        "QLineEdit, QTextEdit, QTimeEdit, QDateEdit, QSpinBox, QComboBox {"
        "border:1px solid #ccc; border-radius:4px; padding:4px;"
        "font-size:12px; background:white;}"
    )
    _GROUP_STYLE = (
        "QGroupBox { font-weight:bold; font-size:12px; color:#1565a8;"
        "border:1px solid #c5d8f0; border-radius:6px;"
        "margin-top:6px; padding-top:10px; background:#f8fbff;}"
        "QGroupBox::title { subcontrol-origin:margin; left:12px;"
        "padding:0 4px; background:#f8fbff;}"
    )

    # Einsatzstichwörter
    _STICHWOERTER = [
        "",
        "Intern 1",
        "Intern 2",
        "Chirurgisch 1",
        "Chirurgisch 2",
        "Sandienst",
        "Pat. Station",
    ]

    def __init__(self, daten: dict | None = None, parent=None):
        super().__init__(parent)
        self._edit_daten = daten  # None = Neu, dict = Bearbeiten
        self.setWindowTitle(
            "✏️  Einsatz bearbeiten" if daten else "🚑  Neuen Einsatz erfassen"
        )
        self.setMinimumWidth(560)
        self.setMinimumHeight(620)
        self.resize(580, 680)
        self._build_ui()
        if daten:
            self._befuellen(daten)
        self._update_visibility()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 8)
        main.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(container)
        main.addWidget(scroll, 1)

        # ── Zeitangaben ────────────────────────────────────────────────────
        grp_zeit = QGroupBox("⏱️  Zeitangaben")
        grp_zeit.setStyleSheet(self._GROUP_STYLE)
        zeit_fl = QFormLayout(grp_zeit)
        zeit_fl.setSpacing(8)

        self._datum = QDateEdit()
        self._datum.setCalendarPopup(True)
        self._datum.setDisplayFormat("dd.MM.yyyy")
        self._datum.setDate(QDate.currentDate())
        self._datum.setStyleSheet(self._FIELD_STYLE)
        zeit_fl.addRow("Datum:", self._datum)

        self._uhrzeit = QTimeEdit()
        self._uhrzeit.setDisplayFormat("HH:mm")
        self._uhrzeit.setTime(QTime.currentTime())
        self._uhrzeit.setStyleSheet(self._FIELD_STYLE)
        zeit_fl.addRow("Alarmierungszeit:", self._uhrzeit)

        self._einsatzdauer = QSpinBox()
        self._einsatzdauer.setRange(0, 999)
        self._einsatzdauer.setSuffix("  min")
        self._einsatzdauer.setValue(0)
        self._einsatzdauer.setStyleSheet(self._FIELD_STYLE)
        zeit_fl.addRow("Einsatzdauer:", self._einsatzdauer)

        layout.addWidget(grp_zeit)

        # ── Einsatz-Details ────────────────────────────────────────────────
        grp_detail = QGroupBox("🚨  Einsatz-Details")
        grp_detail.setStyleSheet(self._GROUP_STYLE)
        det_fl = QFormLayout(grp_detail)
        det_fl.setSpacing(8)

        self._stichwort = QComboBox()
        self._stichwort.setEditable(True)
        self._stichwort.addItems(self._STICHWOERTER)
        self._stichwort.setStyleSheet(self._FIELD_STYLE)
        det_fl.addRow("Einsatzstichwort:", self._stichwort)

        self._einsatzort = QLineEdit()
        self._einsatzort.setPlaceholderText("z.B. T1 Gate B11, T2 Ebene 3 ...")
        self._einsatzort.setStyleSheet(self._FIELD_STYLE)
        det_fl.addRow("Einsatzort:", self._einsatzort)

        self._einsatznr_drk = QLineEdit()
        self._einsatznr_drk.setPlaceholderText("DRK interne Einsatznummer")
        self._einsatznr_drk.setStyleSheet(self._FIELD_STYLE)
        det_fl.addRow("Einsatznr. DRK:", self._einsatznr_drk)

        layout.addWidget(grp_detail)

        # ── Alarmierung ────────────────────────────────────────────────────
        grp_alarm = QGroupBox("📻  Alarmierung – Einsatz angenommen?")
        grp_alarm.setStyleSheet(self._GROUP_STYLE)
        alarm_layout = QVBoxLayout(grp_alarm)
        alarm_layout.setSpacing(6)

        self._alarm_group = QButtonGroup(self)
        self._radio_ja   = QRadioButton("✅  Ja – Einsatz angenommen")
        self._radio_nein = QRadioButton("❌  Nein – Einsatz abgelehnt / nicht angenommen")
        self._radio_ja.setChecked(True)
        for rb in (self._radio_ja, self._radio_nein):
            self._alarm_group.addButton(rb)
            alarm_layout.addWidget(rb)

        self._radio_ja.toggled.connect(self._update_visibility)
        self._radio_nein.toggled.connect(self._update_visibility)
        layout.addWidget(grp_alarm)

        # ── Grund (wenn nicht angenommen) ─────────────────────────────────
        self._grp_grund = QGroupBox("❓  Grund der Ablehnung")
        self._grp_grund.setStyleSheet(self._GROUP_STYLE)
        grund_layout = QVBoxLayout(self._grp_grund)
        self._grund_abgelehnt = QTextEdit()
        self._grund_abgelehnt.setPlaceholderText("Warum wurde der Einsatz nicht angenommen?")
        self._grund_abgelehnt.setMaximumHeight(80)
        self._grund_abgelehnt.setStyleSheet(self._FIELD_STYLE)
        grund_layout.addWidget(self._grund_abgelehnt)
        layout.addWidget(self._grp_grund)

        # ── Einsatzkräfte ──────────────────────────────────────────────────
        grp_ma = QGroupBox("👥  Eingesetzte DRK Mitarbeiter")
        grp_ma.setStyleSheet(self._GROUP_STYLE)
        ma_fl = QFormLayout(grp_ma)
        ma_fl.setSpacing(8)

        self._drk_ma1 = QLineEdit()
        self._drk_ma1.setPlaceholderText("DRK Mitarbeiter 1")
        self._drk_ma1.setStyleSheet(self._FIELD_STYLE)
        ma_fl.addRow("DRK MA 1:", self._drk_ma1)

        self._drk_ma2 = QLineEdit()
        self._drk_ma2.setPlaceholderText("DRK Mitarbeiter 2 (optional)")
        self._drk_ma2.setStyleSheet(self._FIELD_STYLE)
        ma_fl.addRow("DRK MA 2:", self._drk_ma2)

        layout.addWidget(grp_ma)

        # ── Bemerkungen ────────────────────────────────────────────────────
        grp_bem = QGroupBox("📝  Bemerkungen (optional)")
        grp_bem.setStyleSheet(self._GROUP_STYLE)
        bem_layout = QVBoxLayout(grp_bem)
        self._bemerkung = QTextEdit()
        self._bemerkung.setPlaceholderText("Weitere Anmerkungen zum Einsatz ...")
        self._bemerkung.setMaximumHeight(80)
        self._bemerkung.setStyleSheet(self._FIELD_STYLE)
        bem_layout.addWidget(self._bemerkung)
        layout.addWidget(grp_bem)
        layout.addStretch()

        # ── Buttons ────────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        label = "✏️  Speichern" if self._edit_daten else "🚑  Einsatz erfassen"
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(label)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        main.addWidget(btns)

    def _update_visibility(self):
        self._grp_grund.setVisible(self._radio_nein.isChecked())

    def _befuellen(self, d: dict):
        """Felder mit bestehenden Daten füllen."""
        try:
            parts = d.get("datum", "").split(".")
            if len(parts) == 3:
                self._datum.setDate(QDate(int(parts[2]), int(parts[1]), int(parts[0])))
        except Exception:
            pass
        try:
            h, m = d.get("uhrzeit", "00:00").split(":")
            self._uhrzeit.setTime(QTime(int(h), int(m)))
        except Exception:
            pass
        self._einsatzdauer.setValue(d.get("einsatzdauer", 0) or 0)
        # Stichwort
        stw = d.get("einsatzstichwort", "")
        idx = self._stichwort.findText(stw)
        if idx >= 0:
            self._stichwort.setCurrentIndex(idx)
        else:
            self._stichwort.setCurrentText(stw)
        self._einsatzort.setText(d.get("einsatzort", ""))
        self._einsatznr_drk.setText(d.get("einsatznr_drk", ""))
        self._drk_ma1.setText(d.get("drk_ma1", ""))
        self._drk_ma2.setText(d.get("drk_ma2", ""))
        angenommen = bool(d.get("angenommen", 1))
        if angenommen:
            self._radio_ja.setChecked(True)
        else:
            self._radio_nein.setChecked(True)
        self._grund_abgelehnt.setPlainText(d.get("grund_abgelehnt", ""))
        self._bemerkung.setPlainText(d.get("bemerkung", ""))

    def _on_accept(self):
        if not self._einsatzort.text().strip() and not self._stichwort.currentText().strip():
            QMessageBox.warning(
                self, "Pflichtfeld",
                "Bitte mindestens Einsatzstichwort oder Einsatzort angeben."
            )
            return
        self.accept()

    def get_daten(self) -> dict:
        return dict(
            datum            = self._datum.date().toString("dd.MM.yyyy"),
            uhrzeit          = self._uhrzeit.time().toString("HH:mm"),
            einsatzdauer     = self._einsatzdauer.value(),
            einsatzstichwort = self._stichwort.currentText().strip(),
            einsatzort       = self._einsatzort.text().strip(),
            einsatznr_drk    = self._einsatznr_drk.text().strip(),
            drk_ma1          = self._drk_ma1.text().strip(),
            drk_ma2          = self._drk_ma2.text().strip(),
            angenommen       = self._radio_ja.isChecked(),
            grund_abgelehnt  = self._grund_abgelehnt.toPlainText().strip(),
            bemerkung        = self._bemerkung.toPlainText().strip(),
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Einsätze-Tab-Widget
# ──────────────────────────────────────────────────────────────────────────────

class _EinsaetzeTab(QWidget):
    """Tab 'Einsätze' – Einsatzprotokoll nach Vorlage FKB."""

    # Tabellen-Spalten
    _COLS = [
        "Lfd. Nr.", "Datum", "Uhrzeit", "Dauer\n(Min.)",
        "Einsatzstichwort", "Einsatzort", "Einsatznr.\nDRK",
        "DRK MA 1", "DRK MA 2", "Angenommen", "Grund (bei Nein)"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._eintraege: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # ── Titelzeile ────────────────────────────────────────────────────
        titel_lbl = QLabel("🚑  Einsatzstatistik – Notfalleinsätze FKB")
        titel_lbl.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        titel_lbl.setStyleSheet(f"color:{FIORI_TEXT}; padding: 4px 0;")
        layout.addWidget(titel_lbl)

        hinweis_lbl = QLabel(
            "Alarmierung über die Leitstelle per Telefon oder Digitalmelder"
        )
        hinweis_lbl.setStyleSheet("color:#666; font-size:11px; font-style:italic;")
        layout.addWidget(hinweis_lbl)

        # ── Filter-Leiste ─────────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame{background:#f8f9fa;border:1px solid #ddd;"
            "border-radius:4px;padding:4px;}"
        )
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(10)

        fl.addWidget(QLabel("Jahr:"))
        self._combo_jahr = QComboBox()
        self._combo_jahr.setFixedWidth(80)
        self._combo_jahr.addItem("Alle", None)
        self._combo_jahr.currentIndexChanged.connect(self._filter_changed)
        fl.addWidget(self._combo_jahr)

        fl.addWidget(QLabel("Monat:"))
        self._combo_monat = QComboBox()
        self._combo_monat.setFixedWidth(110)
        for i, m in enumerate([
            "Alle", "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember"
        ]):
            self._combo_monat.addItem(m, None if i == 0 else i)
        self._combo_monat.currentIndexChanged.connect(self._filter_changed)
        fl.addWidget(self._combo_monat)

        fl.addWidget(QLabel("Suche:"))
        self._suche = QLineEdit()
        self._suche.setPlaceholderText("Stichwort, Ort, Mitarbeiter …")
        self._suche.setMinimumWidth(200)
        self._suche.textChanged.connect(self._filter_changed)
        fl.addWidget(self._suche, 1)

        btn_reset = _btn_light("✖ Zurücksetzen")
        btn_reset.setFixedHeight(28)
        btn_reset.clicked.connect(self._filter_reset)
        fl.addWidget(btn_reset)

        layout.addWidget(filter_frame)

        # ── Aktions-Buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_neu = _btn("＋  Neuer Einsatz", "#107e3e", "#0a5c2e")
        self._btn_neu.setToolTip("Neuen Notfalleinsatz erfassen")
        self._btn_neu.clicked.connect(self._neu)
        btn_row.addWidget(self._btn_neu)

        self._btn_bearbeiten = _btn_light("✏  Bearbeiten")
        self._btn_bearbeiten.setEnabled(False)
        self._btn_bearbeiten.setToolTip("Ausgewählten Einsatz bearbeiten")
        self._btn_bearbeiten.clicked.connect(self._bearbeiten)
        btn_row.addWidget(self._btn_bearbeiten)

        self._btn_loeschen = _btn_light("🗑  Löschen")
        self._btn_loeschen.setEnabled(False)
        self._btn_loeschen.setStyleSheet(
            "QPushButton{background:#eee;color:#333;border:none;"
            "border-radius:4px;padding:4px 14px;font-size:12px;}"
            "QPushButton:hover{background:#ffcccc;color:#a00;}"
            "QPushButton:disabled{background:#f5f5f5;color:#bbb;}"
        )
        self._btn_loeschen.clicked.connect(self._loeschen)
        btn_row.addWidget(self._btn_loeschen)

        # Trennstrich
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#ccc;")
        btn_row.addWidget(sep)

        self._btn_excel = _btn("📈  Excel exportieren", "#1565a8", "#0d47a1")
        self._btn_excel.setToolTip(
            f"Aktuelle Ansicht als Excel speichern\n"
            f"Standard-Ordner: Daten/Einsatz/Protokolle"
        )
        self._btn_excel.clicked.connect(self._excel_exportieren)
        btn_row.addWidget(self._btn_excel)

        self._btn_excel_wo = _btn_light("📂  Speicherort wählen")
        self._btn_excel_wo.setToolTip("Excel exportieren und Speicherort manuell wählen")
        self._btn_excel_wo.clicked.connect(lambda: self._excel_exportieren(ask_path=True))
        btn_row.addWidget(self._btn_excel_wo)

        self._btn_mail = _btn("📧  Per E-Mail senden", "#6a1b9a", "#4a148c")
        self._btn_mail.setToolTip("Excel exportieren und als Outlook-Entwurf öffnen")
        self._btn_mail.clicked.connect(self._per_mail_senden)
        btn_row.addWidget(self._btn_mail)

        btn_row.addStretch()

        self._treffer_lbl = QLabel()
        self._treffer_lbl.setStyleSheet("color:#666; font-size:11px;")
        btn_row.addWidget(self._treffer_lbl)

        layout.addLayout(btn_row)

        # ── Tabelle ────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(len(self._COLS))
        self._table.setHorizontalHeaderLabels(self._COLS)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Lfd. Nr.
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Datum
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Uhrzeit
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Dauer
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)           # Stichwort
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Ort
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Einsatznr.
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # MA1
        hh.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # MA2
        hh.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Angenommen
        hh.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents) # Grund
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget{border:1px solid #ddd; font-size:12px;}"
            "QTableWidget::item:selected{background:#d0e4f8; color:#000;}"
        )
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._auswahl_geaendert)
        self._table.itemDoubleClicked.connect(lambda _: self._bearbeiten())
        layout.addWidget(self._table, 1)

        # ── Statistik-Leiste ───────────────────────────────────────────────
        self._stat_lbl = QLabel()
        self._stat_lbl.setStyleSheet(
            "background:#e8f5e9; color:#256029; border-radius:4px;"
            "padding:6px 12px; font-size:11px;"
        )
        layout.addWidget(self._stat_lbl)

    # ── Refresh / Laden ───────────────────────────────────────────────────────

    def refresh(self):
        # Jahre aktualisieren
        current_j = self._combo_jahr.currentData()
        self._combo_jahr.blockSignals(True)
        self._combo_jahr.clear()
        self._combo_jahr.addItem("Alle", None)
        for j in verfuegbare_jahre_einsaetze():
            self._combo_jahr.addItem(str(j), j)
        # Aktuelles Jahr wiederherstellen
        for i in range(self._combo_jahr.count()):
            if self._combo_jahr.itemData(i) == current_j:
                self._combo_jahr.setCurrentIndex(i)
                break
        self._combo_jahr.blockSignals(False)
        self._lade()

    def _filter_reset(self):
        self._combo_jahr.blockSignals(True)
        self._combo_monat.blockSignals(True)
        self._suche.blockSignals(True)
        self._combo_jahr.setCurrentIndex(0)
        self._combo_monat.setCurrentIndex(0)
        self._suche.clear()
        self._combo_jahr.blockSignals(False)
        self._combo_monat.blockSignals(False)
        self._suche.blockSignals(False)
        self._lade()

    def _filter_changed(self):
        self._lade()

    def _lade(self):
        jahr   = self._combo_jahr.currentData()
        monat  = self._combo_monat.currentData()
        suche  = self._suche.text().strip() or None
        try:
            eintraege = lade_einsaetze(monat=monat, jahr=jahr, suchtext=suche)
        except Exception as exc:
            QMessageBox.critical(self, "Datenbankfehler", str(exc))
            return

        self._eintraege = eintraege
        lfd_nr = 1
        self._table.setRowCount(len(eintraege))
        angenommen_count = 0
        for row, e in enumerate(eintraege):
            ang = bool(e.get("angenommen", 1))
            if ang:
                angenommen_count += 1

            def _item(text: str, center: bool = False) -> QTableWidgetItem:
                item = QTableWidgetItem(str(text) if text else "")
                if center:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return item

            self._table.setItem(row, 0, _item(str(row + 1), center=True))
            self._table.setItem(row, 1, _item(e.get("datum", "")))
            self._table.setItem(row, 2, _item(e.get("uhrzeit", ""), center=True))
            dauer = e.get("einsatzdauer", 0) or 0
            self._table.setItem(row, 3, _item(str(dauer) if dauer else "—", center=True))
            self._table.setItem(row, 4, _item(e.get("einsatzstichwort", "")))
            self._table.setItem(row, 5, _item(e.get("einsatzort", "")))
            self._table.setItem(row, 6, _item(e.get("einsatznr_drk", "") or "—"))
            self._table.setItem(row, 7, _item(e.get("drk_ma1", "")))
            self._table.setItem(row, 8, _item(e.get("drk_ma2", "") or "—"))

            ang_item = _item("✅ Ja" if ang else "❌ Nein", center=True)
            if not ang:
                ang_item.setBackground(QColor("#ffe0e0"))
            else:
                ang_item.setBackground(QColor("#e8f5e9"))
            self._table.setItem(row, 9, ang_item)

            self._table.setItem(row, 10, _item(e.get("grund_abgelehnt", "") or "—"))

        n = len(eintraege)
        abgelehnt = n - angenommen_count
        self._treffer_lbl.setText(f"{n} Einsatz{'ätze' if n != 1 else ''} gefunden")
        self._stat_lbl.setText(
            f"📊  Gesamt: {n}  |  ✅ Angenommen: {angenommen_count}  |  ❌ Abgelehnt: {abgelehnt}"
        )
        self._auswahl_geaendert()

    # ── Aktionen ──────────────────────────────────────────────────────────────

    def _auswahl_geaendert(self):
        hat = bool(self._aktuell())
        self._btn_bearbeiten.setEnabled(hat)
        self._btn_loeschen.setEnabled(hat)

    def _aktuell(self) -> dict | None:
        row = self._table.currentRow()
        if 0 <= row < len(self._eintraege):
            return self._eintraege[row]
        return None

    def _neu(self):
        dlg = _EinsatzDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            daten = dlg.get_daten()
            try:
                einsatz_speichern(daten)
                self.refresh()
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern:\n{exc}")

    def _bearbeiten(self):
        e = self._aktuell()
        if not e:
            return
        dlg = _EinsatzDialog(daten=e, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            daten = dlg.get_daten()
            try:
                einsatz_aktualisieren(e["id"], daten)
                self.refresh()
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern:\n{exc}")

    def _loeschen(self):
        e = self._aktuell()
        if not e:
            return
        antwort = QMessageBox.question(
            self, "Einsatz löschen",
            f"Einsatz wirklich löschen?\n\n"
            f"Datum:       {e.get('datum', '')}\n"
            f"Uhrzeit:     {e.get('uhrzeit', '')}\n"
            f"Stichwort:   {e.get('einsatzstichwort', '')}\n"
            f"Einsatzort:  {e.get('einsatzort', '')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            try:
                einsatz_loeschen(e["id"])
                self.refresh()
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Löschen:\n{exc}")

    # ── Export-Helfer ─────────────────────────────────────────────────────────

    def _zeitraum_label(self) -> str:
        """Gibt einen lesbaren Zeitraum-Text aus den aktuellen Filtern zurück."""
        teile = []
        j = self._combo_jahr.currentData()
        m = self._combo_monat.currentData()
        _MONATE = ["","Januar","Februar","März","April","Mai","Juni",
                   "Juli","August","September","Oktober","November","Dezember"]
        if m:
            teile.append(_MONATE[m])
        if j:
            teile.append(str(j))
        return " ".join(teile) if teile else "Alle Einträge"

    def _excel_exportieren(self, ask_path: bool = False):
        if not self._eintraege:
            QMessageBox.information(self, "Kein Inhalt", "Keine Einträge zur Ansicht vorhanden.")
            return

        # Datumszeitraum wählen
        zeitraum_dlg = _DatumsbereichDialog(self._eintraege, self)
        if zeitraum_dlg.exec() != QDialog.DialogCode.Accepted:
            return
        export_eintraege = zeitraum_dlg.get_gefilterte()
        zeitraum_lbl = zeitraum_dlg.get_zeitraum_label()

        ziel = None
        if ask_path:
            from PySide6.QtWidgets import QFileDialog
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            vorschlag = os.path.join(_PROTOKOLL_DIR, f"Einsatzprotokoll_{ts}.xlsx")
            os.makedirs(_PROTOKOLL_DIR, exist_ok=True)
            ziel, _ = QFileDialog.getSaveFileName(
                self,
                "Excel-Datei speichern",
                vorschlag,
                "Excel-Dateien (*.xlsx)",
            )
            if not ziel:
                return

        try:
            pfad = export_einsaetze_excel(
                export_eintraege,
                ziel_pfad=ziel,
                titel_zeitraum=zeitraum_lbl,
            )
        except ImportError as e:
            QMessageBox.critical(self, "Modul fehlt", str(e))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Export-Fehler", f"Fehler beim Exportieren:\n{exc}")
            return

        antwort = QMessageBox.question(
            self,
            "Excel gespeichert",
            f"Excel wurde erfolgreich gespeichert:\n\n{pfad}\n\nDatei jetzt öffnen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            import subprocess
            subprocess.Popen(["explorer", pfad], shell=False)

        return pfad

    def _per_mail_senden(self):
        if not self._eintraege:
            QMessageBox.information(self, "Kein Inhalt", "Keine Einträge zur Ansicht vorhanden.")
            return

        # Datumszeitraum wählen
        zeitraum_dlg = _DatumsbereichDialog(self._eintraege, self)
        if zeitraum_dlg.exec() != QDialog.DialogCode.Accepted:
            return
        export_eintraege = zeitraum_dlg.get_gefilterte()
        zeitraum_lbl = zeitraum_dlg.get_zeitraum_label()

        # Excel speichern
        try:
            excel_pfad = export_einsaetze_excel(
                export_eintraege,
                titel_zeitraum=zeitraum_lbl,
            )
        except ImportError as e:
            QMessageBox.critical(self, "Modul fehlt", str(e))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Export-Fehler", f"Fehler beim Erstellen der Excel:\n{exc}")
            return

        # Mail-Dialog
        dlg = _MailDialog(
            excel_pfad=excel_pfad,
            zeitraum=zeitraum_lbl,
            anzahl=len(export_eintraege),
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        empfaenger, betreff, body = dlg.get_daten()

        try:
            from functions.mail_functions import create_outlook_draft
            logo_pfad = os.path.join(BASE_DIR, "Daten", "Email", "Logo.jpg")
            create_outlook_draft(
                to=empfaenger,
                subject=betreff,
                body_text=body,
                attachment_path=excel_pfad,
                logo_path=logo_pfad if os.path.isfile(logo_pfad) else None,
            )
            QMessageBox.information(
                self, "Outlook geöffnet",
                "Der Outlook-Entwurf wurde geöffnet.\n"
                "Bitte prüfen und manuell absenden."
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "E-Mail-Fehler",
                f"Outlook-Entwurf konnte nicht erstellt werden:\n{exc}\n\n"
                f"Die Excel-Datei wurde trotzdem gespeichert:\n{excel_pfad}"
            )


# ──────────────────────────────────────────────────────────────────────────────
#  Dialog: E-Mail versenden
# ──────────────────────────────────────────────────────────────────────────────

class _DatumsbereichDialog(QDialog):
    """
    Wählt einen Von-Bis-Datumsbereich für den Export.
    Gibt die gefilterten Einträge zurück.
    """

    _FIELD_STYLE = (
        "QDateEdit { border:1px solid #ccc; border-radius:4px;"
        "padding:4px; font-size:12px; background:white;}"
    )

    def __init__(self, eintraege: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("📅  Datumszeitraum wählen")
        self.setMinimumWidth(400)
        self.setFixedHeight(230)
        self._alle = eintraege

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 10)

        info = QLabel(
            "Über welchen Zeitraum soll die Excel-Datei erstellt werden?"
        )
        info.setStyleSheet("color:#444; font-size:12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Von / Bis
        fl = QFormLayout()
        fl.setSpacing(8)

        # Defaultwerte: frühestes / spätestes Datum aus den Einträgen
        def _to_qdate(s: str) -> QDate:
            try:
                d, m, y = s.split(".")
                return QDate(int(y), int(m), int(d))
            except Exception:
                return QDate.currentDate()

        daten = [e.get("datum", "") for e in eintraege if e.get("datum")]
        if daten:
            # sortierbar machen: yyyymmdd
            def _sort_key(s):
                try:
                    d, m, y = s.split(".")
                    return y + m + d
                except Exception:
                    return ""
            daten_sorted = sorted(daten, key=_sort_key)
            von_default = _to_qdate(daten_sorted[0])
            bis_default = _to_qdate(daten_sorted[-1])
        else:
            von_default = bis_default = QDate.currentDate()

        self._von = QDateEdit()
        self._von.setCalendarPopup(True)
        self._von.setDisplayFormat("dd.MM.yyyy")
        self._von.setDate(von_default)
        self._von.setStyleSheet(self._FIELD_STYLE)
        fl.addRow("Von:", self._von)

        self._bis = QDateEdit()
        self._bis.setCalendarPopup(True)
        self._bis.setDisplayFormat("dd.MM.yyyy")
        self._bis.setDate(bis_default)
        self._bis.setStyleSheet(self._FIELD_STYLE)
        fl.addRow("Bis:", self._bis)

        layout.addLayout(fl)

        self._treffer_lbl = QLabel()
        self._treffer_lbl.setStyleSheet(
            "background:#e3f2fd; color:#154360; border-radius:4px;"
            "padding:5px 10px; font-size:11px;"
        )
        layout.addWidget(self._treffer_lbl)
        self._update_treffer()
        self._von.dateChanged.connect(self._update_treffer)
        self._bis.dateChanged.connect(self._update_treffer)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("📈  Exportieren")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _filter(self) -> list[dict]:
        """Gibt alle Einträge zurück die im gewählten Zeitraum liegen."""
        von_str = self._von.date().toString("yyyyMMdd")
        bis_str = self._bis.date().toString("yyyyMMdd")

        def _key(e) -> str:
            try:
                d, m, y = e.get("datum", "").split(".")
                return y + m + d
            except Exception:
                return ""

        return [e for e in self._alle if von_str <= _key(e) <= bis_str]

    def _update_treffer(self):
        n = len(self._filter())
        von = self._von.date().toString("dd.MM.yyyy")
        bis = self._bis.date().toString("dd.MM.yyyy")
        self._treffer_lbl.setText(
            f"📊  {n} Einsatz/ätze im Zeitraum {von} – {bis}"
        )

    def _on_accept(self):
        if not self._filter():
            QMessageBox.warning(
                self, "Keine Einträge",
                "Im gewählten Zeitraum gibt es keine Einsätze."
            )
            return
        self.accept()

    def get_gefilterte(self) -> list[dict]:
        return self._filter()

    def get_zeitraum_label(self) -> str:
        von = self._von.date().toString("dd.MM.yyyy")
        bis = self._bis.date().toString("dd.MM.yyyy")
        return f"{von} – {bis}"


class _MailDialog(QDialog):
    """Kleiner Dialog: Empfänger, Betreff und Nachrichtentext für Einsatz-Mail."""

    _FIELD_STYLE = (
        "QLineEdit, QTextEdit { border:1px solid #ccc; border-radius:4px;"
        "padding:4px; font-size:12px; background:white;}"
    )

    def __init__(
        self,
        excel_pfad: str,
        zeitraum: str,
        anzahl: int,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("📧  Einsatzprotokoll per E-Mail senden")
        self.setMinimumWidth(500)
        self.resize(540, 420)
        self._excel_pfad = excel_pfad
        layout = QVBoxLayout(self)
        fl = QFormLayout()
        fl.setSpacing(8)

        self._empfaenger = QLineEdit()
        self._empfaenger.setPlaceholderText("empfaenger@drk-koeln.de")
        self._empfaenger.setStyleSheet(self._FIELD_STYLE)
        fl.addRow("Empfänger:", self._empfaenger)

        self._betreff = QLineEdit()
        self._betreff.setText(
            f"Einsatzprotokoll FKB – {zeitraum}  ({anzahl} Einsätze)"
        )
        self._betreff.setStyleSheet(self._FIELD_STYLE)
        fl.addRow("Betreff:", self._betreff)

        layout.addLayout(fl)
        layout.addWidget(QLabel("Nachrichtentext:"))

        self._body = QTextEdit()
        self._body.setStyleSheet(self._FIELD_STYLE)
        self._body.setPlainText(
            f"Hallo,\n\n"
            f"anbei das Einsatzprotokoll für den Zeitraum {zeitraum} "
            f"({anzahl} Einsätze).\n\n"
            f"Das Protokoll ist als Excel-Datei angehängt.\n\n"
            f"Mit freundlichen Grüßen\n"
            f"DRK-Kreisverband Köln e.V."
        )
        self._body.setMinimumHeight(140)
        layout.addWidget(self._body, 1)

        anhang_lbl = QLabel(f"📎  Anhang: {os.path.basename(excel_pfad)}")
        anhang_lbl.setStyleSheet(
            "background:#e3f2fd; color:#154360; border-radius:4px;"
            "padding:6px 10px; font-size:11px;"
        )
        layout.addWidget(anhang_lbl)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("📧  Outlook-Entwurf öffnen")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        if not self._empfaenger.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte einen Empfänger angeben.")
            return
        self.accept()

    def get_daten(self) -> tuple[str, str, str]:
        return (
            self._empfaenger.text().strip(),
            self._betreff.text().strip(),
            self._body.toPlainText().strip(),
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Übersicht-Tab
# ──────────────────────────────────────────────────────────────────────────────

class _UebersichtTab(QWidget):
    """Tab 'Übersicht' – Statistiken und Kennzahlen über alle Einsätze."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # ── Titel ──────────────────────────────────────────────────────────
        titel = QLabel("📊  Übersicht Einsatzstatistik")
        titel.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        titel.setStyleSheet(f"color:{FIORI_TEXT}; padding:4px 0;")
        layout.addWidget(titel)

        # ── Filter: Jahr ───────────────────────────────────────────────────
        fff = QFrame()
        fff.setStyleSheet(
            "QFrame{background:#f8f9fa;border:1px solid #ddd;"
            "border-radius:4px;padding:4px;}"
        )
        fl = QHBoxLayout(fff)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(10)
        fl.addWidget(QLabel("Jahr:"))
        self._combo_jahr = QComboBox()
        self._combo_jahr.setFixedWidth(90)
        self._combo_jahr.addItem("Alle", None)
        self._combo_jahr.currentIndexChanged.connect(self.refresh)
        fl.addWidget(self._combo_jahr)
        fl.addStretch()
        layout.addWidget(fff)

        # ── KPI-Kacheln ────────────────────────────────────────────────────
        kpi_frame = QFrame()
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setSpacing(12)
        kpi_layout.setContentsMargins(0, 0, 0, 0)

        self._kpi_gesamt   = self._kpi_card("📥  Gesamt",      "0", "#1565a8")
        self._kpi_ja       = self._kpi_card("✅  Angenommen", "0", "#2e7d32")
        self._kpi_nein     = self._kpi_card("❌  Abgelehnt",  "0", "#c62828")
        self._kpi_dauer    = self._kpi_card("⏱  Ø-Dauer",     "0 min", "#6a1b9a")

        for card in (self._kpi_gesamt, self._kpi_ja, self._kpi_nein, self._kpi_dauer):
            kpi_layout.addWidget(card, 1)
        layout.addWidget(kpi_frame)

        # ── Splitter: linke Tabelle + rechte Stichwort-Tabelle ─────────────
        from PySide6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:#ddd; width:2px;}")

        # Monatstabelle
        monat_widget = QWidget()
        ml = QVBoxLayout(monat_widget)
        ml.setContentsMargins(0, 0, 4, 0)
        ml.addWidget(QLabel("📅  Einsätze nach Monat"))
        self._monat_table = QTableWidget()
        self._monat_table.setColumnCount(4)
        self._monat_table.setHorizontalHeaderLabels(
            ["Monat", "Gesamt", "Angenommen", "Abgelehnt"]
        )
        mh = self._monat_table.horizontalHeader()
        mh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, 4):
            mh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self._monat_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._monat_table.setAlternatingRowColors(True)
        self._monat_table.verticalHeader().setVisible(False)
        self._monat_table.setStyleSheet("font-size:12px;")
        ml.addWidget(self._monat_table, 1)
        splitter.addWidget(monat_widget)

        # Stichwort-Tabelle
        stw_widget = QWidget()
        sl = QVBoxLayout(stw_widget)
        sl.setContentsMargins(4, 0, 0, 0)
        sl.addWidget(QLabel("🚨  Häufigste Einsatzstichwörter"))
        self._stw_table = QTableWidget()
        self._stw_table.setColumnCount(2)
        self._stw_table.setHorizontalHeaderLabels(["Einsatzstichwort", "Anzahl"])
        sh = self._stw_table.horizontalHeader()
        sh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        sh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._stw_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._stw_table.setAlternatingRowColors(True)
        self._stw_table.verticalHeader().setVisible(False)
        self._stw_table.setStyleSheet("font-size:12px;")
        sl.addWidget(self._stw_table, 1)
        splitter.addWidget(stw_widget)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter, 1)

        # ── Mitarbeiter-Tabelle ────────────────────────────────────────────
        ma_lbl = QLabel("👥  Einsätze nach Mitarbeiter")
        layout.addWidget(ma_lbl)
        self._ma_table = QTableWidget()
        self._ma_table.setColumnCount(3)
        self._ma_table.setHorizontalHeaderLabels(["Mitarbeiter", "Als MA 1", "Als MA 2"])
        mah = self._ma_table.horizontalHeader()
        mah.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, 3):
            mah.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self._ma_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._ma_table.setAlternatingRowColors(True)
        self._ma_table.verticalHeader().setVisible(False)
        self._ma_table.setMaximumHeight(160)
        self._ma_table.setStyleSheet("font-size:12px;")
        layout.addWidget(self._ma_table)

    @staticmethod
    def _kpi_card(label: str, wert: str, farbe: str) -> QFrame:
        card = QFrame()
        card.setMinimumHeight(80)
        card.setStyleSheet(
            f"QFrame{{background:{farbe};border-radius:8px;padding:8px;}}"
        )
        vl = QVBoxLayout(card)
        vl.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color:rgba(255,255,255,0.8);font-size:11px;background:transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val = QLabel(wert)
        val.setObjectName("val")
        val.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        val.setStyleSheet("color:white;background:transparent;")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(lbl)
        vl.addWidget(val)
        return card

    @staticmethod
    def _set_kpi(card: QFrame, wert: str):
        val = card.findChild(QLabel, "val")
        if val:
            val.setText(wert)

    def refresh(self):
        # Jahre in Combo befüllen
        current_j = self._combo_jahr.currentData()
        self._combo_jahr.blockSignals(True)
        self._combo_jahr.clear()
        self._combo_jahr.addItem("Alle", None)
        for j in verfuegbare_jahre_einsaetze():
            self._combo_jahr.addItem(str(j), j)
        for i in range(self._combo_jahr.count()):
            if self._combo_jahr.itemData(i) == current_j:
                self._combo_jahr.setCurrentIndex(i)
                break
        self._combo_jahr.blockSignals(False)

        jahr = self._combo_jahr.currentData()
        alle = lade_einsaetze(jahr=jahr)

        # ── KPIs ───────────────────────────────────────────────────────────
        n = len(alle)
        ang = sum(1 for e in alle if e.get("angenommen", 1))
        nein = n - ang
        dauern = [e["einsatzdauer"] for e in alle if e.get("einsatzdauer")]
        avg_d = round(sum(dauern) / len(dauern)) if dauern else 0

        self._set_kpi(self._kpi_gesamt, str(n))
        self._set_kpi(self._kpi_ja,     str(ang))
        self._set_kpi(self._kpi_nein,   str(nein))
        self._set_kpi(self._kpi_dauer,  f"{avg_d} min")

        # ── Monatstabelle ──────────────────────────────────────────────────
        _MONATE = ["","Januar","Februar","März","April","Mai","Juni",
                   "Juli","August","September","Oktober","November","Dezember"]
        monat_stats: dict[int, dict] = {}
        for e in alle:
            try:
                m = int(e["datum"].split(".")[1])
            except Exception:
                continue
            if m not in monat_stats:
                monat_stats[m] = {"gesamt": 0, "ang": 0, "nein": 0}
            monat_stats[m]["gesamt"] += 1
            if e.get("angenommen", 1):
                monat_stats[m]["ang"] += 1
            else:
                monat_stats[m]["nein"] += 1

        sorted_monate = sorted(monat_stats.keys())
        self._monat_table.setRowCount(len(sorted_monate))
        for row, m in enumerate(sorted_monate):
            s = monat_stats[m]
            self._monat_table.setItem(row, 0, QTableWidgetItem(_MONATE[m]))
            for col, key in enumerate(["gesamt", "ang", "nein"], start=1):
                it = QTableWidgetItem(str(s[key]))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 2 and s[key] > 0:
                    it.setBackground(QColor("#e8f5e9"))
                elif col == 3 and s[key] > 0:
                    it.setBackground(QColor("#ffe0e0"))
                self._monat_table.setItem(row, col, it)

        # ── Stichwort-Tabelle ──────────────────────────────────────────────
        from collections import Counter
        stw_counter = Counter(
            e["einsatzstichwort"] for e in alle
            if e.get("einsatzstichwort")
        )
        top_stw = stw_counter.most_common(20)
        self._stw_table.setRowCount(len(top_stw))
        for row, (stw, cnt) in enumerate(top_stw):
            self._stw_table.setItem(row, 0, QTableWidgetItem(stw))
            it = QTableWidgetItem(str(cnt))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._stw_table.setItem(row, 1, it)

        # ── Mitarbeiter-Tabelle ────────────────────────────────────────────
        ma1_counter: dict[str, int] = {}
        ma2_counter: dict[str, int] = {}
        for e in alle:
            m1 = (e.get("drk_ma1") or "").strip()
            m2 = (e.get("drk_ma2") or "").strip()
            if m1:
                ma1_counter[m1] = ma1_counter.get(m1, 0) + 1
            if m2:
                ma2_counter[m2] = ma2_counter.get(m2, 0) + 1

        alle_ma = sorted(set(ma1_counter) | set(ma2_counter))
        self._ma_table.setRowCount(len(alle_ma))
        for row, ma in enumerate(alle_ma):
            self._ma_table.setItem(row, 0, QTableWidgetItem(ma))
            for col, counter in enumerate([ma1_counter, ma2_counter], start=1):
                it = QTableWidgetItem(str(counter.get(ma, 0)))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._ma_table.setItem(row, col, it)


# ──────────────────────────────────────────────────────────────────────────────
#  Haupt-Widget: Dienstliches
# ──────────────────────────────────────────────────────────────────────────────

class DienstlichesWidget(QWidget):
    """Haupt-Widget 'Dienstliches' mit Tabs für Einsätze und weitere Protokolle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Titelleiste ────────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background:{FIORI_BLUE}; border:none;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)
        lbl = QLabel("☕  Dienstliches")
        lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        lbl.setStyleSheet("color:white; background:transparent;")
        hl.addWidget(lbl)
        hl.addStretch()

        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedSize(30, 30)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setToolTip("Ansicht aktualisieren")
        btn_refresh.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.15);color:white;"
            "border:1px solid rgba(255,255,255,0.3);border-radius:4px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.25);}"
        )
        btn_refresh.clicked.connect(self.refresh)
        hl.addWidget(btn_refresh)
        layout.addWidget(header)

        # ── Tab-Widget ─────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border:1px solid #ddd; }
            QTabBar::tab {
                padding:8px 20px; font-size:13px; min-width:120px;
                border:1px solid #ddd; border-bottom:none;
                background:#f5f5f5; color:#555;
                border-top-left-radius:4px; border-top-right-radius:4px;
            }
            QTabBar::tab:selected { background:white; color:#1565a8; font-weight:bold; }
            QTabBar::tab:hover:!selected { background:#e8f0fb; }
        """)

        self._einsaetze_tab = _EinsaetzeTab()
        self._tabs.addTab(self._einsaetze_tab, "🚑  Einsätze")

        self._uebersicht_tab = _UebersichtTab()
        self._tabs.addTab(self._uebersicht_tab, "📊  Übersicht")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs, 1)

    def _on_tab_changed(self, idx: int):
        if idx == 1:
            self._uebersicht_tab.refresh()

    def refresh(self):
        self._einsaetze_tab.refresh()
        if self._tabs.currentIndex() == 1:
            self._uebersicht_tab.refresh()
