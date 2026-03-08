"""
Aufgaben Tag – Widget
Enthält Tabs für Tagesaufgaben, darunter E-Mail-Erstellung.
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QTabWidget, QFileDialog,
    QMessageBox, QFrame, QDateEdit, QGroupBox, QSizePolicy,
    QScrollArea, QCheckBox, QListWidget, QComboBox,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from config import BASE_DIR, FIORI_BLUE, FIORI_TEXT

# ── Pfade ─────────────────────────────────────────────────────────────────────
_LOGO_PATH = str(Path(BASE_DIR) / "Daten" / "Email" / "Logo.jpg")
_KYOSCAN   = Path("C:/KyoScan")


# ── Hilfs-Styling ─────────────────────────────────────────────────────────────
def _label(text: str, bold: bool = False, size: int = 12) -> QLabel:
    lbl = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    lbl.setFont(f)
    return lbl


def _btn(text: str, color: str = FIORI_BLUE, hover: str = "#005a9e") -> QPushButton:
    b = QPushButton(text)
    b.setFont(QFont("Segoe UI", 11))
    b.setMinimumHeight(36)
    b.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:disabled {{
            background-color: #b0b0b0;
        }}
    """)
    return b


def _line_edit(placeholder: str = "", min_width: int = 0) -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setFont(QFont("Segoe UI", 11))
    e.setMinimumHeight(32)
    if min_width:
        e.setMinimumWidth(min_width)
    e.setStyleSheet("border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px 8px;")
    return e


def _section_frame() -> QFrame:
    f = QFrame()
    f.setStyleSheet("background-color: white; border: 1px solid #e0e0e0; border-radius: 4px;")
    return f


# ─────────────────────────────────────────────────────────────────────────────
#  Tab 1 – Freier E-Mail-Entwurf
# ─────────────────────────────────────────────────────────────────────────────
class _FreieMailTab(QWidget):
    """Freier E-Mail-Entwurf – adaptiert von Nesk2 scan_email_dialog.py"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._selected_file: Path | None = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Scroll-Bereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── Empfänger ─────────────────────────────────────────────────────────
        sec_recv = _section_frame()
        sec_recv_lay = QVBoxLayout(sec_recv)
        sec_recv_lay.setContentsMargins(12, 10, 12, 10)
        sec_recv_lay.addWidget(_label("📬 Empfänger", bold=True))
        self._to_edit = _line_edit("An: email@beispiel.de")
        self._to_edit.setText("leitung.fb2@drk-koeln.de")
        self._cc_edit = _line_edit("CC: optional")
        self._subj_edit = _line_edit("Betreff")
        sec_recv_lay.addWidget(_label("An:"))
        sec_recv_lay.addWidget(self._to_edit)
        sec_recv_lay.addWidget(_label("CC:"))
        sec_recv_lay.addWidget(self._cc_edit)
        sec_recv_lay.addWidget(_label("Betreff:"))
        sec_recv_lay.addWidget(self._subj_edit)
        layout.addWidget(sec_recv)

        # ── Text ───────────────────────────────────────────────────────────────
        sec_text = _section_frame()
        sec_text_lay = QVBoxLayout(sec_text)
        sec_text_lay.setContentsMargins(12, 10, 12, 10)
        sec_text_lay.addWidget(_label("✉️ E-Mail-Text", bold=True))
        self._text_edit = QTextEdit()
        self._text_edit.setFont(QFont("Segoe UI", 11))
        self._text_edit.setMinimumHeight(140)
        self._text_edit.setStyleSheet(
            "border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px;"
        )
        sec_text_lay.addWidget(self._text_edit)

        # Datum für Betreff / Template
        date_row = QHBoxLayout()
        date_row.setSpacing(8)
        date_row.addWidget(_label("Datum für Betreff / Template:"))
        self._tpl_date = QDateEdit()
        self._tpl_date.setCalendarPopup(True)
        self._tpl_date.setDate(QDate.currentDate())
        self._tpl_date.setDisplayFormat("dd.MM.yyyy")
        self._tpl_date.setFont(QFont("Segoe UI", 11))
        self._tpl_date.setMinimumHeight(32)
        self._tpl_date.setFixedWidth(150)
        self._tpl_date.setStyleSheet("border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px;")
        date_row.addWidget(self._tpl_date)
        date_row.addStretch()
        sec_text_lay.addLayout(date_row)

        # Template-Buttons
        tpl_row = QHBoxLayout()
        tpl_row.setSpacing(8)
        btn_chk = _btn("📅 Checklisten-Template", "#17a2b8", "#138496")
        btn_chk.clicked.connect(lambda: self._apply_template("Checklisten"))
        btn_chk.setToolTip("Füllt Betreff + Text für Checklisten-Versand")
        tpl_row.addWidget(btn_chk)
        btn_checks = _btn("📅 Checks-Template", "#17a2b8", "#138496")
        btn_checks.clicked.connect(lambda: self._apply_template("Checks"))
        btn_checks.setToolTip("Füllt Betreff + Text für Tages-Checks")
        tpl_row.addWidget(btn_checks)
        tpl_row.addStretch()
        sec_text_lay.addLayout(tpl_row)

        tpl_info = QLabel(
            "ℹ️  <b>Checklisten-Template</b>: Füllt Betreff und Mailtext automatisch "
            "mit \"Checklisten vom TT.MM.JJJJ\" – ⵡ <b>Checks-Template</b>: gleich, aber mit \"Checks vom TT.MM.JJJJ\". "
            "Das Datum kann links mit dem Datumsfeld frei gewählt werden. "
            "Anschließend Anhang hinzufügen und ‘Outlook-Entwurf erstellen’ klicken."
        )
        tpl_info.setWordWrap(True)
        tpl_info.setTextFormat(Qt.TextFormat.RichText)
        tpl_info.setStyleSheet(
            "background: #e8f4fb; border: 1px solid #b0d8f0; border-radius: 5px; "
            "padding: 7px 12px; color: #1a4a6b; font-size: 11px;"
        )
        sec_text_lay.addWidget(tpl_info)
        layout.addWidget(sec_text)

        # ── Anhang ─────────────────────────────────────────────────────────────
        sec_att = _section_frame()
        sec_att_lay = QVBoxLayout(sec_att)
        sec_att_lay.setContentsMargins(12, 10, 12, 10)
        sec_att_lay.addWidget(_label("📎 Anhang", bold=True))

        att_row = QHBoxLayout()
        att_row.setSpacing(8)
        self._file_lbl = _label("Keine Datei gewählt")
        self._file_lbl.setStyleSheet("color: #888;")
        att_row.addWidget(self._file_lbl, 1)
        btn_file = _btn("📁 Datei wählen", "#6c757d", "#5a6268")
        btn_file.setFixedWidth(150)
        btn_file.setToolTip("Datei als E-Mail-Anhang auswählen (wird optional umbenannt)")
        btn_file.clicked.connect(self._pick_file)
        att_row.addWidget(btn_file)
        btn_clear = _btn("✕", "#dc3545", "#c82333")
        btn_clear.setFixedWidth(40)
        btn_clear.setToolTip("Gewählte Anhang-Datei entfernen")
        btn_clear.clicked.connect(self._clear_file)
        att_row.addWidget(btn_clear)
        sec_att_lay.addLayout(att_row)

        # Datei umbenennen (Datum-Picker)
        rename_row = QHBoxLayout()
        rename_row.setSpacing(8)
        self._rename_chk = QCheckBox("Umbenennen zu Datum:")
        self._rename_chk.setFont(QFont("Segoe UI", 11))
        rename_row.addWidget(self._rename_chk)
        self._rename_date = QDateEdit()
        self._rename_date.setCalendarPopup(True)
        self._rename_date.setDate(QDate.currentDate())
        self._rename_date.setDisplayFormat("dd.MM.yyyy")
        self._rename_date.setFont(QFont("Segoe UI", 11))
        self._rename_date.setMinimumHeight(32)
        self._rename_date.setFixedWidth(140)
        self._rename_date.setStyleSheet("border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px;")
        rename_row.addWidget(self._rename_date)
        self._rename_preview_lbl = _label("")
        self._rename_preview_lbl.setStyleSheet("color: #555; font-style: italic;")
        rename_row.addWidget(self._rename_preview_lbl, 1)
        sec_att_lay.addLayout(rename_row)

        rename_info = QLabel(
            "ℹ️  <b>Umbenennen zu Datum</b>: Wenn aktiviert, wird die gewählte Anhang-Datei "
            "beim Versand automatisch in das Format <b>JJJJ_MM_TT</b> umbenannt "
            "(z. B. \"2026_02_26.pdf\"). "
            "Die Originaldatei bleibt unverändert – es wird eine umbenannte Kopie als Anhang an Outlook übergeben. "
            "Nützlich, wenn Checklisten oder Checks-Berichte tagesaktuell archiviert werden sollen."
        )
        rename_info.setWordWrap(True)
        rename_info.setTextFormat(Qt.TextFormat.RichText)
        rename_info.setStyleSheet(
            "background: #fff8e8; border: 1px solid #f0d080; border-radius: 5px; "
            "padding: 7px 12px; color: #5a3e00; font-size: 11px;"
        )
        sec_att_lay.addWidget(rename_info)
        self._rename_chk.toggled.connect(self._update_rename_preview)
        self._rename_date.dateChanged.connect(self._update_rename_preview)
        layout.addWidget(sec_att)

        # ── Senden ─────────────────────────────────────────────────────────────
        send_row = QHBoxLayout()
        send_row.setSpacing(12)
        send_row.addStretch()
        btn_send = _btn("📧 Outlook-Entwurf erstellen")
        btn_send.setMinimumWidth(240)
        btn_send.setMinimumHeight(42)
        btn_send.setToolTip("Erstellt einen Outlook-Entwurf mit Betreff, Text und gewähltem Anhang")
        btn_send.clicked.connect(self._send)
        send_row.addWidget(btn_send)
        layout.addLayout(send_row)
        layout.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ── Slots ─────────────────────────────────────────────────────────────────
    def _pick_file(self):
        initial = str(_KYOSCAN) if _KYOSCAN.exists() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Datei auswählen", initial,
            "Alle Dateien (*.*);;PDF (*.pdf);;Word (*.docx *.doc);;Excel (*.xlsx *.xls);;Bilder (*.jpg *.png)"
        )
        if path:
            self._selected_file = Path(path)
            self._file_lbl.setText(self._selected_file.name)
            self._file_lbl.setStyleSheet("color: #333;")
            self._update_rename_preview()

    def _clear_file(self):
        self._selected_file = None
        self._file_lbl.setText("Keine Datei gewählt")
        self._file_lbl.setStyleSheet("color: #888;")
        self._update_rename_preview()

    def _update_rename_preview(self):
        if self._rename_chk.isChecked() and self._selected_file:
            d = self._rename_date.date().toPython()
            suffix = self._selected_file.suffix
            self._rename_preview_lbl.setText(f"→ {d.strftime('%Y_%m_%d')}{suffix}")
        else:
            self._rename_preview_lbl.setText("")

    def _apply_template(self, doc_type: str):
        d = self._tpl_date.date().toPython()
        d_fmt = d.strftime("%d.%m.%Y")
        self._subj_edit.setText(f"{doc_type} vom {d_fmt}")
        self._text_edit.setPlainText(
            f"Hallo Herr Burghammer,\n\nanbei die {doc_type} vom {d_fmt}.\n\n\nMit freundlichen Grüßen"
        )

    def _send(self):
        to = self._to_edit.text().strip()
        cc = self._cc_edit.text().strip()
        subj = self._subj_edit.text().strip()
        body = self._text_edit.toPlainText().strip()

        if not to:
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Empfänger (An) eingeben.")
            return
        if not subj:
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Betreff eingeben.")
            return
        if not body:
            QMessageBox.warning(self, "Pflichtfeld", "Bitte E-Mail-Text eingeben.")
            return

        # Datei ggf. umbenennen (Datum-Format YYYY_MM_DD)
        attachment: str | None = None
        if self._selected_file:
            if self._rename_chk.isChecked():
                d = self._rename_date.date().toPython()
                new_name = d.strftime("%Y_%m_%d") + self._selected_file.suffix
                new_path = self._selected_file.parent / new_name
                try:
                    shutil.copy2(str(self._selected_file), str(new_path))
                    attachment = str(new_path)
                except Exception as exc:
                    QMessageBox.critical(self, "Fehler", f"Umbenennen fehlgeschlagen:\n{exc}")
                    return
            else:
                attachment = str(self._selected_file)

        try:
            import win32com.client
            try:
                outlook = win32com.client.GetActiveObject("Outlook.Application")
            except Exception:
                outlook = win32com.client.Dispatch("Outlook.Application")

            mail = outlook.CreateItem(0)
            mail.Display()          # lädt Signatur
            signature = mail.HTMLBody

            mail.To      = to
            mail.CC      = cc
            mail.Subject = subj

            # Body als HTML – zeilenumbrüche bewahren
            body_escaped = (
                body.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\n", "<br>")
            )
            body_html = (
                "<html><head><meta http-equiv='Content-Type' "
                "content='text/html; charset=utf-8'></head>"
                "<body style='font-family:Calibri,Arial,sans-serif;font-size:11pt;color:#000;'>"
                f"{body_escaped}"
                "</body></html>"
            )
            mail.HTMLBody = body_html + signature

            if attachment:
                att_path = Path(attachment)
                if att_path.exists():
                    mail.Attachments.Add(str(att_path))
                else:
                    QMessageBox.warning(
                        self, "Anhang fehlt",
                        f"Datei nicht gefunden:\n{att_path}\nMail wird ohne Anhang geöffnet."
                    )

            QMessageBox.information(self, "Erfolg", "Outlook wurde geöffnet mit Ihrer Signatur!\nBitte prüfen und absenden.")
        except ImportError:
            QMessageBox.critical(self, "Fehler", "pywin32 nicht installiert.\nBitte: pip install pywin32")
        except Exception as exc:
            QMessageBox.critical(
                self, "Fehler",
                f"Outlook-Entwurf konnte nicht erstellt werden:\n{exc}\n\n"
                "Stellen Sie sicher, dass Outlook installiert ist."
            )


# ─────────────────────────────────────────────────────────────────────────────
#  Tab 2 – Code 19 Mail
# ─────────────────────────────────────────────────────────────────────────────
class _Code19MailTab(QWidget):
    """Code-19-Mail mit Von/Bis-Datumsauswahl – adaptiert von Nesk2 code19_mail.py"""

    _TO  = "hildegard.eichler@koeln-bonn-airport.de"
    _CC  = "erste-hilfe-station-flughafen@drk-koeln.de; flughafen@drk-koeln.de"
    _EXCEL_DEFAULT = str(
        Path(BASE_DIR).parent.parent / "00_CODE 19" / "Code 19.xlsx"
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._excel_path: Path | None = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Info ──────────────────────────────────────────────────────────────
        info = _section_frame()
        info_lay = QVBoxLayout(info)
        info_lay.setContentsMargins(12, 10, 12, 10)
        info_lay.addWidget(_label("📋 Code 19 – E-Mail erstellen", bold=True, size=13))
        info_lay.addWidget(_label(f"An: {self._TO}"))
        info_lay.addWidget(_label(f"CC: {self._CC}"))
        root.addWidget(info)

        # ── Datumbereich ──────────────────────────────────────────────────────
        date_sec = _section_frame()
        date_lay = QVBoxLayout(date_sec)
        date_lay.setContentsMargins(12, 10, 12, 10)
        date_lay.addWidget(_label("📅 Zeitraum", bold=True))

        date_row = QHBoxLayout()
        date_row.setSpacing(24)

        von_grp = QVBoxLayout()
        von_grp.addWidget(_label("Von:"))
        self._von_date = QDateEdit()
        self._von_date.setCalendarPopup(True)
        self._von_date.setDate(QDate.currentDate().addDays(-7))
        self._von_date.setDisplayFormat("dd.MM.yyyy")
        self._von_date.setFont(QFont("Segoe UI", 11))
        self._von_date.setMinimumHeight(32)
        self._von_date.setStyleSheet("border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px;")
        von_grp.addWidget(self._von_date)

        bis_grp = QVBoxLayout()
        bis_grp.addWidget(_label("Bis:"))
        self._bis_date = QDateEdit()
        self._bis_date.setCalendarPopup(True)
        self._bis_date.setDate(QDate.currentDate())
        self._bis_date.setDisplayFormat("dd.MM.yyyy")
        self._bis_date.setFont(QFont("Segoe UI", 11))
        self._bis_date.setMinimumHeight(32)
        self._bis_date.setStyleSheet("border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px;")
        bis_grp.addWidget(self._bis_date)

        date_row.addLayout(von_grp)
        date_row.addLayout(bis_grp)
        date_row.addStretch()
        date_lay.addLayout(date_row)

        zeitraum_info = QLabel(
            "ℹ️  <b>Zeitraum</b>: Legt fest, welche Dienstplaneinträge aus der "
            "Code 19 Excel-Datei in die E-Mail übernommen werden. "
            "Es werden alle Zeilen berücksichtigt, deren Datum in diesem "
            "Bereich liegt. Standard: letzte 7 Tage bis heute."
        )
        zeitraum_info.setWordWrap(True)
        zeitraum_info.setTextFormat(Qt.TextFormat.RichText)
        zeitraum_info.setStyleSheet(
            "background: #e8f4fb; border: 1px solid #b0d8f0; border-radius: 5px; "
            "padding: 7px 12px; color: #1a4a6b; font-size: 11px;"
        )
        date_lay.addWidget(zeitraum_info)
        root.addWidget(date_sec)

        # ── Excel-Anhang ─────────────────────────────────────────────────────
        xl_sec = _section_frame()
        xl_lay = QVBoxLayout(xl_sec)
        xl_lay.setContentsMargins(12, 10, 12, 10)
        xl_lay.addWidget(_label("📎 Code 19 Excel-Datei", bold=True))

        xl_row = QHBoxLayout()
        xl_row.setSpacing(8)
        self._xl_lbl = _label(self._EXCEL_DEFAULT)
        self._xl_lbl.setStyleSheet("color: #555;")
        xl_row.addWidget(self._xl_lbl, 1)
        btn_xl = _btn("📁 Andere Datei", "#6c757d", "#5a6268")
        btn_xl.setFixedWidth(150)
        btn_xl.setToolTip("Andere Excel-Datei als Dienstplan-Basis auswählen")
        btn_xl.clicked.connect(self._pick_excel)
        xl_row.addWidget(btn_xl)
        xl_lay.addLayout(xl_row)

        # Datei-Status
        self._xl_status_lbl = _label("")
        self._update_excel_status(Path(self._EXCEL_DEFAULT))
        xl_lay.addWidget(self._xl_status_lbl)
        root.addWidget(xl_sec)

        # ── Senden ────────────────────────────────────────────────────────────
        send_row = QHBoxLayout()
        send_row.addStretch()

        btn_send = _btn("📧 Entwurf (ohne Signatur)", "#6c757d", "#5a6268")
        btn_send.setMinimumWidth(220)
        btn_send.setMinimumHeight(42)
        btn_send.setToolTip("Erstellt einen Outlook-Entwurf ohne Ihre persönliche Signatur")
        btn_send.clicked.connect(self._send)
        send_row.addWidget(btn_send)

        send_row.addSpacing(12)

        btn_sig = _btn("📧 Mail mit Signatur senden")
        btn_sig.setMinimumWidth(240)
        btn_sig.setMinimumHeight(42)
        btn_sig.setToolTip("Öffnet die Mail in Outlook mit Ihrer persönlichen Signatur (wie VBS-Script)")
        btn_sig.clicked.connect(self._send_with_signature)
        send_row.addWidget(btn_sig)

        root.addLayout(send_row)
        root.addStretch()

    # ── Slots ─────────────────────────────────────────────────────────────────
    def _pick_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excel-Datei wählen", "",
            "Excel (*.xlsx *.xls *.xlsm);;Alle Dateien (*.*)"
        )
        if path:
            self._excel_path = Path(path)
            self._xl_lbl.setText(str(self._excel_path))
            self._update_excel_status(self._excel_path)

    def _update_excel_status(self, path: Path):
        if path.exists():
            self._xl_status_lbl.setText("✅ Datei gefunden")
            self._xl_status_lbl.setStyleSheet("color: green;")
        else:
            self._xl_status_lbl.setText("⚠️ Datei nicht gefunden")
            self._xl_status_lbl.setStyleSheet("color: #e67e22;")

    def _send(self):
        von = self._von_date.date().toPython()
        bis = self._bis_date.date().toPython()

        if von > bis:
            QMessageBox.warning(self, "Datum-Fehler", "Von-Datum darf nicht nach Bis-Datum liegen.")
            return

        excel = self._excel_path or Path(self._EXCEL_DEFAULT)
        if not excel.exists():
            QMessageBox.critical(
                self, "Datei fehlt",
                f"Code 19 Excel-Datei nicht gefunden:\n{excel}\n\n"
                "Bitte wählen Sie eine andere Datei."
            )
            return

        von_str = von.strftime("%d.%m.%Y")
        bis_str = bis.strftime("%d.%m.%Y")
        subject = f"Code 19-Liste vom {von_str} bis {bis_str}"
        body = (
            f"Sehr geehrte Frau Eichler,\n\n"
            f"anbei die Code 19-Liste vom {von_str} bis {bis_str}.\n\n"
            f"Mit freundlichen Grüßen\n"
            f"Ihr Team vom PRM-Service"
        )

        try:
            from functions.mail_functions import create_outlook_draft
            create_outlook_draft(
                to=self._TO,
                subject=subject,
                body_text=body,
                cc=self._CC,
                attachment_path=str(excel),
                logo_path=_LOGO_PATH,
            )
            QMessageBox.information(self, "Erfolg", "Outlook-Entwurf wurde erstellt!\nBitte prüfen und absenden.")
        except Exception as exc:
            QMessageBox.critical(
                self, "Fehler",
                f"Mail konnte nicht erstellt werden:\n{exc}\n\n"
                "Stellen Sie sicher, dass Outlook installiert ist und pywin32 verfügbar ist."
            )

    def _send_with_signature(self):
        """Erstellt Code-19-Mail mit Outlook-Signatur (analog zum VBS-Script)."""
        von = self._von_date.date().toPython()
        bis = self._bis_date.date().toPython()

        if von > bis:
            QMessageBox.warning(self, "Datum-Fehler", "Von-Datum darf nicht nach Bis-Datum liegen.")
            return

        excel = self._excel_path or Path(self._EXCEL_DEFAULT)

        von_str = von.strftime("%d.%m.%Y")
        bis_str = bis.strftime("%d.%m.%Y")
        subject = f"Code 19-Liste vom {von_str} bis {bis_str}"

        try:
            from functions.mail_functions import create_code19_mail_with_signature
            create_code19_mail_with_signature(
                to=self._TO,
                cc=self._CC,
                subject=subject,
                von_str=von_str,
                bis_str=bis_str,
                attachment_path=str(excel) if excel.exists() else None,
            )
            if not excel.exists():
                QMessageBox.warning(
                    self, "Anhang fehlt",
                    f"Mail wurde geöffnet, aber die Excel-Datei wurde nicht gefunden:\n{excel}"
                )
            else:
                QMessageBox.information(self, "Erfolg", "Outlook wurde geöffnet mit Ihrer Signatur!\nBitte prüfen und absenden.")
        except Exception as exc:
            QMessageBox.critical(
                self, "Fehler",
                f"Mail konnte nicht erstellt werden:\n{exc}\n\n"
                "Stellen Sie sicher, dass Outlook installiert ist und pywin32 verfügbar ist."
            )


# ─────────────────────────────────────────────────────────────────────────────
#  Tab 3 – Stärkemeldung Mail
# ─────────────────────────────────────────────────────────────────────────────
class _StaerkemeldungTab(QWidget):
    """Stärkemeldung-E-Mail mit Outlook-Signatur erstellen."""

    _TO = "hildegard.eichler@koeln-bonn-airport.de; erste-hilfe-station-flughafen@drk-koeln.de"
    _CC = "leitung.fb2@drk-koeln.de; verwaltung.fb2@drk-koeln.de; loahrs@gmx.de"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._attachment_path: Path | None = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ── Info ─────────────────────────────────────────────────────────
        info_sec = _section_frame()
        info_lay = QVBoxLayout(info_sec)
        info_lay.setContentsMargins(12, 10, 12, 10)
        info_lay.addWidget(_label("📄 Stärkemeldung – E-Mail erstellen", bold=True, size=13))
        info_lay.addWidget(_label(f"An: {self._TO}"))
        info_lay.addWidget(_label(f"CC: {self._CC}"))
        layout.addWidget(info_sec)

        # ── Zeitraum ─────────────────────────────────────────────────────
        date_sec = _section_frame()
        date_lay = QVBoxLayout(date_sec)
        date_lay.setContentsMargins(12, 10, 12, 10)
        date_lay.addWidget(_label("📅 Zeitraum (für Betreff)", bold=True))

        date_row = QHBoxLayout()
        date_row.setSpacing(24)

        von_grp = QVBoxLayout()
        von_grp.addWidget(_label("Von:"))
        self._s_von = QDateEdit()
        self._s_von.setCalendarPopup(True)
        self._s_von.setDate(QDate.currentDate())
        self._s_von.setDisplayFormat("dd.MM.yyyy")
        self._s_von.setFont(QFont("Segoe UI", 11))
        self._s_von.setMinimumHeight(32)
        self._s_von.setStyleSheet("border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px;")
        von_grp.addWidget(self._s_von)
        date_row.addLayout(von_grp)

        bis_grp = QVBoxLayout()
        bis_grp.addWidget(_label("Bis:"))
        self._s_bis = QDateEdit()
        self._s_bis.setCalendarPopup(True)
        self._s_bis.setDate(QDate.currentDate())
        self._s_bis.setDisplayFormat("dd.MM.yyyy")
        self._s_bis.setFont(QFont("Segoe UI", 11))
        self._s_bis.setMinimumHeight(32)
        self._s_bis.setStyleSheet("border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px;")
        bis_grp.addWidget(self._s_bis)
        date_row.addLayout(bis_grp)
        date_row.addStretch()
        date_lay.addLayout(date_row)
        layout.addWidget(date_sec)

        # ── Anhang ────────────────────────────────────────────────────────
        att_sec = _section_frame()
        att_lay = QVBoxLayout(att_sec)
        att_lay.setContentsMargins(12, 10, 12, 10)
        att_lay.addWidget(_label("📎 Stärkemeldungs-Datei (Anhang)", bold=True))

        att_row = QHBoxLayout()
        att_row.setSpacing(8)
        self._att_lbl = _label("Keine Datei gewählt")
        self._att_lbl.setStyleSheet("color: #888;")
        att_row.addWidget(self._att_lbl, 1)
        btn_att = _btn("📁 Datei wählen", "#6c757d", "#5a6268")
        btn_att.setFixedWidth(150)
        btn_att.setToolTip("Anhang für die Code-19-Mail wählen")
        btn_att.clicked.connect(self._pick_file)
        att_row.addWidget(btn_att)
        btn_clr = _btn("✕", "#dc3545", "#c82333")
        btn_clr.setFixedWidth(40)
        btn_clr.setToolTip("Gewählten Anhang entfernen")
        btn_clr.clicked.connect(self._clear_file)
        att_row.addWidget(btn_clr)
        att_lay.addLayout(att_row)
        layout.addWidget(att_sec)

        # ── Senden ────────────────────────────────────────────────────────
        send_row = QHBoxLayout()
        send_row.addStretch()
        btn_send = _btn("📧 Mail mit Signatur erstellen")
        btn_send.setMinimumWidth(260)
        btn_send.setMinimumHeight(44)
        btn_send.setToolTip("Erstellt eine Code-19-Mail mit Ihrer Outlook-Signatur")
        btn_send.clicked.connect(self._send)
        send_row.addWidget(btn_send)
        layout.addLayout(send_row)
        layout.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll)

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Stärkemeldung wählen", "",
            "Alle Dateien (*.*);;Word (*.docx *.doc);;PDF (*.pdf);;Excel (*.xlsx)"
        )
        if path:
            self._attachment_path = Path(path)
            self._att_lbl.setText(self._attachment_path.name)
            self._att_lbl.setStyleSheet("color: #333;")

    def _clear_file(self):
        self._attachment_path = None
        self._att_lbl.setText("Keine Datei gewählt")
        self._att_lbl.setStyleSheet("color: #888;")

    def _send(self):
        von = self._s_von.date().toPython()
        bis = self._s_bis.date().toPython()

        if von > bis:
            QMessageBox.warning(self, "Datum-Fehler", "Von-Datum darf nicht nach Bis-Datum liegen.")
            return

        von_str = von.strftime("%d.%m.%Y")
        bis_str = bis.strftime("%d.%m.%Y")

        if von == bis:
            datum_text = von_str
            subject = f"Stärkemeldung {von_str}"
        else:
            datum_text = f"{von_str} bis {bis_str}"
            subject = f"Stärkemeldung {von_str} bis {bis_str}"

        try:
            import win32com.client
            try:
                outlook = win32com.client.GetActiveObject("Outlook.Application")
            except Exception:
                outlook = win32com.client.Dispatch("Outlook.Application")

            mail = outlook.CreateItem(0)
            mail.Display()  # lädt Signatur
            signature = mail.HTMLBody

            mail.To = self._TO
            mail.CC = self._CC
            mail.Subject = subject

            body_html = (
                "<html><head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'></head>"
                "<body style='font-family:Calibri,Arial,sans-serif;font-size:11pt;color:#000;'>"
                "<p>Sehr geehrte Frau Eichler,</p>"
                f"<p>im Anhang die Stärkemeldung für den {datum_text}</p>"
                "<p>mit freundlichen Grü&szlig;en</p>"
                "</body></html>"
            )
            mail.HTMLBody = body_html + signature

            if self._attachment_path and self._attachment_path.exists():
                mail.Attachments.Add(str(self._attachment_path))
            elif self._attachment_path:
                QMessageBox.warning(
                    self, "Anhang fehlt",
                    f"Datei nicht gefunden:\n{self._attachment_path}\n\nMail wird ohne Anhang geöffnet."
                )

            QMessageBox.information(self, "Erfolg", "Outlook wurde geöffnet mit Ihrer Signatur!\nBitte prüfen und absenden.")
        except ImportError:
            QMessageBox.critical(self, "Fehler", "pywin32 nicht installiert.\nBitte: pip install pywin32")
        except Exception as exc:
            QMessageBox.critical(
                self, "Fehler",
                f"Mail konnte nicht erstellt werden:\n{exc}\n\n"
                "Stellen Sie sicher, dass Outlook installiert ist."
            )


# ─────────────────────────────────────────────────────────────────────────────
#  Haupt-Widget
# ─────────────────────────────────────────────────────────────────────────────
class AufgabenTagWidget(QWidget):
    """Hauptwidget für Aufgaben Tag – Tab-basiert"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Seiten-Titel
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e0;")
        title_bar.setFixedHeight(52)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)
        lbl = QLabel("☀️ Aufgaben Tag")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {FIORI_TEXT};")
        title_layout.addWidget(lbl)
        title_layout.addStretch()
        layout.addWidget(title_bar)

        # Tabs
        tabs = QTabWidget()
        tabs.setFont(QFont("Segoe UI", 11))
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #f5f6f7;
            }
            QTabBar::tab {
                padding: 8px 20px;
                background-color: #e8edf2;
                border: none;
                border-radius: 3px 3px 0 0;
                margin-right: 2px;
                font-size: 11pt;
            }
            QTabBar::tab:selected {
                background-color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #d0dae4;
            }
        """)
        tabs.addTab(_FreieMailTab(), "📋 Checklisten Mail")
        tabs.addTab(_Code19MailTab(), "📋 Code 19 Mail")
        tabs.addTab(_StaerkemeldungTab(), "📄 Stärkemeldung")
        layout.addWidget(tabs)

    def refresh(self):
        """Wird von MainWindow aufgerufen wenn Tab aktiviert wird."""
        pass
