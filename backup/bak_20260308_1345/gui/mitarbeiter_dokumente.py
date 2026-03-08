"""
Mitarbeiter-Dokumente Widget
Öffnen, Bearbeiten und Erstellen von Mitarbeiter-Dokumenten
mit einheitlicher DRK-Kopf-/Fußzeile
"""
import os
import sys
import webbrowser
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QListWidget, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
    QFormLayout, QLineEdit, QTextEdit, QComboBox, QDateEdit,
    QMessageBox, QFrame, QScrollArea, QSizePolicy, QInputDialog,
    QFileDialog, QGroupBox, QRadioButton, QButtonGroup, QCheckBox,
    QTimeEdit, QTabWidget
)
from PySide6.QtCore import Qt, QDate, QSize, QTime
from PySide6.QtGui import QFont, QColor, QIcon

from config import FIORI_BLUE, FIORI_TEXT, FIORI_WHITE, FIORI_BORDER

from functions.mitarbeiter_dokumente_functions import (
    KATEGORIEN, DOKUMENTE_BASIS, VORLAGE_PFAD, STELLUNGNAHMEN_EXTERN_PFAD,
    lade_dokumente_nach_kategorie,
    erstelle_dokument_aus_vorlage,
    erstelle_stellungnahme,
    oeffne_datei,
    loesche_dokument,
    umbenennen_dokument,
    sicherungsordner,
)
from functions.stellungnahmen_db import (
    lade_alle as db_lade_alle,
    eintrag_loeschen as db_eintrag_loeschen,
    verfuegbare_jahre as db_jahre,
    get_eintrag as db_get_eintrag,
)
from functions.verspaetung_db import (
    verspaetung_speichern,
    verspaetung_aktualisieren,
    verspaetung_loeschen as vdb_loeschen,
    lade_verspaetungen,
    verfuegbare_jahre as vdb_jahre,
)
from functions.verspaetung_functions import (
    erstelle_verspaetungs_dokument,
    oeffne_dokument as oeffne_versp_dokument,
    berechne_verspaetung_min,
)
from functions.psa_db import (
    psa_speichern,
    psa_aktualisieren,
    psa_loeschen as pdb_loeschen,
    lade_psa_eintraege,
    verfuegbare_jahre as pdb_jahre,
)


# ── Hilfsstile ────────────────────────────────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════════════════════
#  Dialog: Stellungnahme erstellen
# ══════════════════════════════════════════════════════════════════════════════

class _StellungnahmeDialog(QDialog):
    """Strukturierter Stellungnahme-Assistent mit kontextabhängigen Feldern."""

    _FIELD_STYLE = (
        "QLineEdit, QTextEdit, QTimeEdit, QComboBox {"
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝 Stellungnahme erstellen")
        self.setMinimumWidth(580)
        self.setMinimumHeight(680)
        self.resize(620, 750)
        self._build_ui()
        self._update_visibility()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 8)
        main_layout.setSpacing(6)

        # Scrollbereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        # ── 1. Allgemeine Angaben ──────────────────────────────────────────────
        grp_allg = QGroupBox("📌 Allgemeine Angaben")
        grp_allg.setStyleSheet(self._GROUP_STYLE)
        fl = QFormLayout(grp_allg)
        fl.setSpacing(8)

        self._mitarbeiter = QLineEdit()
        self._mitarbeiter.setPlaceholderText("Vor- und Nachname")
        self._mitarbeiter.setStyleSheet(self._FIELD_STYLE)
        fl.addRow("Mitarbeiter:", self._mitarbeiter)

        self._datum_vorfall = QDateEdit()
        self._datum_vorfall.setCalendarPopup(True)
        self._datum_vorfall.setDisplayFormat("dd.MM.yyyy")
        self._datum_vorfall.setDate(QDate.currentDate())
        self._datum_vorfall.setStyleSheet(self._FIELD_STYLE)
        fl.addRow("Datum des Vorfalls:", self._datum_vorfall)

        self._datum_verfasst = QDateEdit()
        self._datum_verfasst.setCalendarPopup(True)
        self._datum_verfasst.setDisplayFormat("dd.MM.yyyy")
        self._datum_verfasst.setDate(QDate.currentDate())
        self._datum_verfasst.setStyleSheet(self._FIELD_STYLE)
        fl.addRow("Verfasst am:", self._datum_verfasst)

        layout.addWidget(grp_allg)

        # ── 2. Art der Stellungnahme ───────────────────────────────────────────
        grp_art = QGroupBox("ℹ️ Art der Stellungnahme")
        grp_art.setStyleSheet(self._GROUP_STYLE)
        art_layout = QVBoxLayout(grp_art)
        art_layout.setSpacing(6)

        self._art_group = QButtonGroup(self)
        self._radio_flug   = QRadioButton("✈️  Flug-bezogener Vorfall")
        self._radio_beschwerde  = QRadioButton("🗣️  Passagierbeschwerde")
        self._radio_nm     = QRadioButton("🚶  Passagier nicht mitgeflogen (kein PRM-Dienstverspätung)")
        self._radio_flug.setChecked(True)
        for rb in (self._radio_flug, self._radio_beschwerde, self._radio_nm):
            self._art_group.addButton(rb)
            art_layout.addWidget(rb)

        self._radio_flug.toggled.connect(self._update_visibility)
        self._radio_beschwerde.toggled.connect(self._update_visibility)
        self._radio_nm.toggled.connect(self._update_visibility)
        layout.addWidget(grp_art)

        # ── 3. Flugdaten ───────────────────────────────────────────────────────
        self._grp_flug = QGroupBox("✈️ Flugdaten")
        self._grp_flug.setStyleSheet(self._GROUP_STYLE)
        flug_layout = QFormLayout(self._grp_flug)
        flug_layout.setSpacing(8)

        self._flugnummer = QLineEdit()
        self._flugnummer.setPlaceholderText("z.B. LH1234 / EW987")
        self._flugnummer.setStyleSheet(self._FIELD_STYLE)
        flug_layout.addRow("Flugnummer:", self._flugnummer)

        # Verspätung
        self._verspaetung_cb = QCheckBox("Flug hat Verspätung")
        self._verspaetung_cb.toggled.connect(self._update_visibility)
        flug_layout.addRow("Verspätung:", self._verspaetung_cb)

        self._grp_verspaetung = QGroupBox("🕒 Verspätungszeiten")
        self._grp_verspaetung.setStyleSheet(
            "QGroupBox{font-weight:bold;font-size:11px;color:#555;"
            "border:1px dashed #ccc;border-radius:4px;margin-top:4px;padding-top:8px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 3px;}"
        )
        vsp_fl = QFormLayout(self._grp_verspaetung)
        vsp_fl.setSpacing(6)
        self._onblock = QTimeEdit()
        self._onblock.setDisplayFormat("HH:mm")
        self._onblock.setStyleSheet(self._FIELD_STYLE)
        self._offblock = QTimeEdit()
        self._offblock.setDisplayFormat("HH:mm")
        self._offblock.setStyleSheet(self._FIELD_STYLE)
        vsp_fl.addRow("Onblock-Zeit (tatsächlich):", self._onblock)
        vsp_fl.addRow("Offblock-Zeit (geplant):", self._offblock)
        # _grp_verspaetung wird als separates Top-Level-Element eingefügt

        # Richtung
        richtung_lbl = QLabel("Flugrichtung:")
        richtung_lbl.setStyleSheet("font-size:12px;")
        richtung_widget = QWidget()
        rw = QHBoxLayout(richtung_widget)
        rw.setContentsMargins(0, 0, 0, 0)
        rw.setSpacing(16)
        self._richt_group = QButtonGroup(self)
        self._radio_inbound  = QRadioButton("Inbound 🛬")
        self._radio_outbound = QRadioButton("Outbound 🛫")
        self._radio_beides   = QRadioButton("Beides")
        self._radio_inbound.setChecked(True)
        for rb in (self._radio_inbound, self._radio_outbound, self._radio_beides):
            self._richt_group.addButton(rb)
            rw.addWidget(rb)
        rw.addStretch()
        self._radio_inbound.toggled.connect(self._update_visibility)
        self._radio_outbound.toggled.connect(self._update_visibility)
        self._radio_beides.toggled.connect(self._update_visibility)
        flug_layout.addRow(richtung_lbl, richtung_widget)

        layout.addWidget(self._grp_flug)
        layout.addWidget(self._grp_verspaetung)

        # ── 4. Inbound-Felder ─────────────────────────────────────────────────
        self._grp_inbound = QGroupBox("🛬 Inbound-Einsatz")
        self._grp_inbound.setStyleSheet(self._GROUP_STYLE)
        ib_fl = QFormLayout(self._grp_inbound)
        ib_fl.setSpacing(8)
        self._ankunft_lfz = QTimeEdit()
        self._ankunft_lfz.setDisplayFormat("HH:mm")
        self._ankunft_lfz.setStyleSheet(self._FIELD_STYLE)
        self._auftragsende = QTimeEdit()
        self._auftragsende.setDisplayFormat("HH:mm")
        self._auftragsende.setStyleSheet(self._FIELD_STYLE)
        ib_fl.addRow("Ankunft Luftfahrzeug:", self._ankunft_lfz)
        ib_fl.addRow("Auftragsende:", self._auftragsende)
        layout.addWidget(self._grp_inbound)

        # ── 5. Outbound-Felder ────────────────────────────────────────────────
        self._grp_outbound = QGroupBox("🛫 Outbound-Einsatz")
        self._grp_outbound.setStyleSheet(self._GROUP_STYLE)
        ob_fl = QFormLayout(self._grp_outbound)
        ob_fl.setSpacing(8)
        self._paxannahme_zeit = QTimeEdit()
        self._paxannahme_zeit.setDisplayFormat("HH:mm")
        self._paxannahme_zeit.setStyleSheet(self._FIELD_STYLE)
        ob_fl.addRow("Paxannahme-Zeit:", self._paxannahme_zeit)

        self._paxannahme_ort = QComboBox()
        self._paxannahme_ort.addItems(["C72", "Meetingpoint", "Sonstiges"])
        self._paxannahme_ort.setStyleSheet(self._FIELD_STYLE)
        self._paxannahme_ort.currentTextChanged.connect(self._update_visibility)
        ob_fl.addRow("Ort der Paxannahme:", self._paxannahme_ort)

        self._paxannahme_sonstiges = QLineEdit()
        self._paxannahme_sonstiges.setPlaceholderText("Bitte Ort angeben ...")
        self._paxannahme_sonstiges.setStyleSheet(self._FIELD_STYLE)
        ob_fl.addRow("Ort (Sonstiges):", self._paxannahme_sonstiges)
        layout.addWidget(self._grp_outbound)

        # ── 6. Sachverhalt (für Flug + Beschwerde + nicht_mitgeflogen) ────────
        self._grp_sachverhalt = QGroupBox("📝 Sachverhalt")
        self._grp_sachverhalt.setStyleSheet(self._GROUP_STYLE)
        sv_layout = QVBoxLayout(self._grp_sachverhalt)
        self._sachverhalt = QTextEdit()
        self._sachverhalt.setPlaceholderText(
            "Bitte den Sachverhalt vollständig und sachlich schildern ..."
        )
        self._sachverhalt.setMinimumHeight(120)
        self._sachverhalt.setStyleSheet(self._FIELD_STYLE)
        sv_layout.addWidget(self._sachverhalt)
        layout.addWidget(self._grp_sachverhalt)

        # ── 7. Beschwerde-Text ────────────────────────────────────────────────
        self._grp_beschwerde = QGroupBox("🗣️ Beschreibung der Beschwerde")
        self._grp_beschwerde.setStyleSheet(self._GROUP_STYLE)
        bw_layout = QVBoxLayout(self._grp_beschwerde)
        bw_fl = QFormLayout()
        bw_fl.setSpacing(8)
        self._flugnummer_beschwerde = QLineEdit()
        self._flugnummer_beschwerde.setPlaceholderText("z.B. LH1234 (optional)")
        self._flugnummer_beschwerde.setStyleSheet(self._FIELD_STYLE)
        bw_fl.addRow("Flugnummer (optional):", self._flugnummer_beschwerde)
        bw_layout.addLayout(bw_fl)
        self._beschwerde_text = QTextEdit()
        self._beschwerde_text.setPlaceholderText("Inhalt der Beschwerde schildern ...")
        self._beschwerde_text.setMinimumHeight(100)
        self._beschwerde_text.setStyleSheet(self._FIELD_STYLE)
        bw_layout.addWidget(self._beschwerde_text)
        layout.addWidget(self._grp_beschwerde)

        # ── 8. Nicht-mitgeflogen: Flugnummer ─────────────────────────────────
        self._grp_nm = QGroupBox("🚶 Passagier nicht mitgeflogen")
        self._grp_nm.setStyleSheet(self._GROUP_STYLE)
        nm_fl = QFormLayout(self._grp_nm)
        nm_fl.setSpacing(8)
        self._flugnummer_nm = QLineEdit()
        self._flugnummer_nm.setPlaceholderText("z.B. LH1234")
        self._flugnummer_nm.setStyleSheet(self._FIELD_STYLE)
        nm_fl.addRow("Flugnummer:", self._flugnummer_nm)
        layout.addWidget(self._grp_nm)

        layout.addStretch()

        # ── Speicherort-Hinweis ───────────────────────────────────────────────
        info = QLabel(
            f"💾 Wird gespeichert in:\n"
            f"  • Intern: Daten/Mitarbeiterdokumente/Stellungnahmen/\n"
            f"  • Extern: 97_Stellungnahmen/"
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background:#e8f5e9; color:#256029; border-radius:4px;"
            "padding:8px 12px; font-size:11px;"
        )
        main_layout.addWidget(info)

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("📝  Stellungnahme erstellen")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        main_layout.addWidget(btns)

    # ── Sichtbarkeit aktualisieren ────────────────────────────────────────────

    def _update_visibility(self):
        is_flug  = self._radio_flug.isChecked()
        is_beschwerde = self._radio_beschwerde.isChecked()
        is_nm    = self._radio_nm.isChecked()
        is_verspaetung = self._verspaetung_cb.isChecked()
        be_inbound  = self._radio_inbound.isChecked()  or self._radio_beides.isChecked()
        be_outbound = self._radio_outbound.isChecked() or self._radio_beides.isChecked()
        is_sonstiges = self._paxannahme_ort.currentText() == "Sonstiges"

        self._grp_flug.setVisible(is_flug)
        self._grp_verspaetung.setVisible(is_flug and is_verspaetung)
        self._grp_inbound.setVisible(is_flug and be_inbound)
        self._grp_outbound.setVisible(is_flug and be_outbound)
        self._grp_sachverhalt.setVisible(True)  # immer sichtbar
        self._grp_beschwerde.setVisible(is_beschwerde)
        self._grp_nm.setVisible(is_nm)
        # Sonstiges-Eingabefeld
        for i in range(self._grp_outbound.layout().rowCount()):
            item = self._grp_outbound.layout().itemAt(i, QFormLayout.ItemRole.FieldRole)
            if item and item.widget() == self._paxannahme_sonstiges:
                item.widget().setVisible(is_sonstiges)
            lbl_item = self._grp_outbound.layout().itemAt(i, QFormLayout.ItemRole.LabelRole)
            if lbl_item and lbl_item.widget() and \
                    "Sonstiges" in lbl_item.widget().text():
                lbl_item.widget().setVisible(is_sonstiges)

    # ── Validierung + Accept ──────────────────────────────────────────────────

    def _on_accept(self):
        if not self._mitarbeiter.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte den Mitarbeiternamen eingeben.")
            return
        if self._radio_flug.isChecked() and not self._flugnummer.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte die Flugnummer eingeben.")
            return
        if self._radio_nm.isChecked() and not self._flugnummer_nm.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte die Flugnummer eingeben.")
            return
        if not self._sachverhalt.toPlainText().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte den Sachverhalt schildern.")
            return
        self.accept()

    # ── Daten auslesen ────────────────────────────────────────────────────────

    def get_daten(self) -> dict:
        art = ("flug" if self._radio_flug.isChecked()
               else "beschwerde" if self._radio_beschwerde.isChecked()
               else "nicht_mitgeflogen")
        richtung = ("inbound" if self._radio_inbound.isChecked()
                    else "outbound" if self._radio_outbound.isChecked()
                    else "beides")
        ort = self._paxannahme_ort.currentText()
        if ort == "Sonstiges":
            ort = self._paxannahme_sonstiges.text().strip() or "Sonstiges"
        return dict(
            mitarbeiter    = self._mitarbeiter.text().strip(),
            datum          = self._datum_vorfall.date().toString("dd.MM.yyyy"),
            verfasst_am    = self._datum_verfasst.date().toString("dd.MM.yyyy"),
            art            = art,
            flugnummer     = (self._flugnummer.text().strip() if art == "flug"
                             else self._flugnummer_beschwerde.text().strip() if art == "beschwerde"
                             else self._flugnummer_nm.text().strip()),
            verspaetung    = self._verspaetung_cb.isChecked(),
            onblock        = self._onblock.time().toString("HH:mm"),
            offblock       = self._offblock.time().toString("HH:mm"),
            richtung       = richtung,
            ankunft_lfz    = self._ankunft_lfz.time().toString("HH:mm"),
            auftragsende   = self._auftragsende.time().toString("HH:mm"),
            paxannahme_zeit = self._paxannahme_zeit.time().toString("HH:mm"),
            paxannahme_ort = ort,
            sachverhalt    = self._sachverhalt.toPlainText().strip(),
            beschwerde_text = self._beschwerde_text.toPlainText().strip(),
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Dialog: Neues Dokument erstellen
# ══════════════════════════════════════════════════════════════════════════════

class _NeuesDokumentDialog(QDialog):
    """Formulardialog zum Erstellen eines neuen Mitarbeiter-Dokuments."""

    def __init__(self, vorkategorie: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues Dokument erstellen")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        layout = QVBoxLayout(self)
        fl = QFormLayout()
        fl.setSpacing(8)

        # Kategorie
        self._kategorie = QComboBox()
        for kat in KATEGORIEN:
            self._kategorie.addItem(kat)
        if vorkategorie in KATEGORIEN:
            self._kategorie.setCurrentText(vorkategorie)
        fl.addRow("Kategorie:", self._kategorie)

        # Titel
        self._titel = QLineEdit()
        self._titel.setPlaceholderText("z.B. Stellungnahme zum Diensteinsatz")
        fl.addRow("Titel des Dokuments:", self._titel)

        # Mitarbeiter
        self._mitarbeiter = QLineEdit()
        self._mitarbeiter.setPlaceholderText("Vor- und Nachname")
        fl.addRow("Mitarbeiter:", self._mitarbeiter)

        # Datum
        self._datum = QDateEdit()
        self._datum.setCalendarPopup(True)
        self._datum.setDisplayFormat("dd.MM.yyyy")
        self._datum.setDate(QDate.currentDate())
        fl.addRow("Datum:", self._datum)

        layout.addLayout(fl)

        # Inhalt
        layout.addWidget(QLabel("Inhalt / Text des Dokuments:"))
        self._inhalt = QTextEdit()
        self._inhalt.setPlaceholderText(
            "Hier den vollständigen Text eingeben...\n\n"
            "Alle Absätze werden automatisch mit der DRK-Kopf-/Fußzeile formatiert."
        )
        self._inhalt.setMinimumHeight(180)
        self._inhalt.setStyleSheet(
            "QTextEdit { border:1px solid #ccc; border-radius:4px; "
            "padding:6px; font-size:13px; }"
        )
        layout.addWidget(self._inhalt)

        # Info-Box Vorlage
        vorlage_ok = os.path.isfile(VORLAGE_PFAD)
        info = QLabel(
            "✅ Kopf-/Fußzeile aus DRK-Vorlage wird übernommen."
            if vorlage_ok else
            "⚠ Vorlage nicht gefunden! Dokument ohne DRK-Kopf-/Fußzeile erstellt.\n"
            f"Erwartet: {VORLAGE_PFAD}"
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            f"background:{'#e8f5e9' if vorlage_ok else '#fff3e0'};"
            f"color:{'#256029' if vorlage_ok else '#7f5000'};"
            "border-radius:4px; padding:6px 10px; font-size:11px;"
        )
        layout.addWidget(info)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("📄 Erstellen")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        if not self._titel.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte einen Titel eingeben.")
            return
        if not self._mitarbeiter.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte einen Mitarbeiternamen eingeben.")
            return
        self.accept()

    def get_data(self) -> dict:
        return dict(
            kategorie   = self._kategorie.currentText(),
            titel       = self._titel.text().strip(),
            mitarbeiter = self._mitarbeiter.text().strip(),
            datum       = self._datum.date().toString("dd.MM.yyyy"),
            inhalt      = self._inhalt.toPlainText(),
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Dialog: Dokument bearbeiten (Text-Popup)
# ══════════════════════════════════════════════════════════════════════════════

class _DokumentBearbeitenDialog(QDialog):
    """
    Öffnet ein bestehendes .docx/.txt als editierbares Popup.
    Bei .docx werden die Absätze ausgelesen; bei .txt der Rohtext.
    Beim Speichern wird das Dokument neu über die Vorlage erstellt.
    """

    def __init__(self, eintrag: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Bearbeiten – {eintrag['name']}")
        self.setMinimumWidth(620)
        self.setMinimumHeight(520)
        self._eintrag = eintrag
        layout = QVBoxLayout(self)

        # Originalinhalt laden
        pfad = eintrag["pfad"]
        original = ""
        try:
            if pfad.lower().endswith(".docx"):
                from docx import Document as _Doc
                doc = _Doc(pfad)
                original = "\n".join(p.text for p in doc.paragraphs)
            elif pfad.lower().endswith(".txt"):
                with open(pfad, encoding="utf-8", errors="replace") as f:
                    original = f.read()
        except Exception as e:
            original = f"[Fehler beim Laden: {e}]"

        # Meta-Zeile
        meta = QLabel(f"📄  {eintrag['name']}   |   Zuletzt geändert: {eintrag['geaendert']}")
        meta.setStyleSheet("color:#555; font-size:11px; padding:2px 0 8px 0;")
        layout.addWidget(meta)

        # Textbereich
        self._editor = QTextEdit()
        self._editor.setPlainText(original)
        self._editor.setStyleSheet(
            "QTextEdit { border:1px solid #ccc; border-radius:4px; "
            "padding:8px; font-size:13px; }"
        )
        layout.addWidget(self._editor, 1)

        # Hinweis
        hint = QLabel(
            "ℹ️  Beim Übernehmen wird das Dokument mit diesem Text und der DRK-Vorlage neu erstellt."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "background:#e3f2fd; color:#154360; border-radius:4px; "
            "padding:6px 10px; font-size:11px;"
        )
        layout.addWidget(hint)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Save).setText("💾 Übernehmen & neu erstellen")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_inhalt(self) -> str:
        return self._editor.toPlainText()


# ══════════════════════════════════════════════════════════════════════════════
#  Dialog: Verspätung erfassen
# ══════════════════════════════════════════════════════════════════════════════

class _VerspaetungDialog(QDialog):
    """Dialog zum Erfassen einer Meldung über unpünktlichen Dienstantritt."""

    _DIENST_ITEMS = [
        ("T – Tagdienst (06:00)",   "T",   "06:00"),
        ("T10 – Tagdienst 10h",     "T10", "06:00"),
        ("N – Nachtdienst (21:00)", "N",   "21:00"),
        ("N10 – Nachtdienst 10h",   "N10", "21:00"),
    ]

    def __init__(self, daten: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⏰ Verspätungsmeldung erfassen")
        self.setMinimumWidth(520)
        self.resize(560, 590)
        self._vorlage_daten = daten or {}
        self._build_ui()
        if daten:
            self._prefill(daten)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        title = QLabel("🕐 Meldung über unpünktlichen Dienstantritt")
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{FIORI_BLUE};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Mitarbeiter
        self._ma_combo = QComboBox()
        self._ma_combo.setEditable(True)
        self._ma_combo.setMinimumWidth(260)
        self._ma_combo.lineEdit().setPlaceholderText("Name eingeben …")
        try:
            from functions.mitarbeiter_functions import lade_mitarbeiter_namen
            for name in lade_mitarbeiter_namen():
                self._ma_combo.addItem(name)
        except Exception:
            try:
                from database.models import Mitarbeiter as _MA
                from database.connection import get_session
                with get_session() as s:
                    mas = s.query(_MA).filter(_MA.status == "aktiv").order_by(_MA.nachname).all()
                    for m in mas:
                        self._ma_combo.addItem(f"{m.nachname}, {m.vorname}")
            except Exception:
                pass
        form.addRow("Mitarbeiter *:", self._ma_combo)

        # Datum
        self._datum = QDateEdit(QDate.currentDate())
        self._datum.setCalendarPopup(True)
        self._datum.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Datum *:", self._datum)

        # Dienstart
        self._dienst_combo = QComboBox()
        for label, code, _ in self._DIENST_ITEMS:
            self._dienst_combo.addItem(label, code)
        self._dienst_combo.currentIndexChanged.connect(self._on_dienst_changed)
        form.addRow("Dienstart *:", self._dienst_combo)

        # Dienstbeginn
        self._beginn = QTimeEdit(QTime(6, 0))
        self._beginn.setDisplayFormat("HH:mm")
        self._beginn.timeChanged.connect(self._update_verspaetung)
        form.addRow("Dienstbeginn:", self._beginn)

        # Dienstantritt
        self._antritt = QTimeEdit(QTime(6, 0))
        self._antritt.setDisplayFormat("HH:mm")
        self._antritt.timeChanged.connect(self._update_verspaetung)
        form.addRow("Tatsächlicher Antritt *:", self._antritt)

        # Verspätung (readonly)
        self._versp_lbl = QLabel("0 Minuten")
        self._versp_lbl.setStyleSheet(
            "font-weight:bold; color:#c00; font-size:13px; padding:2px 0;"
        )
        form.addRow("Verspätung:", self._versp_lbl)

        # Begründung
        self._begruendung = QTextEdit()
        self._begruendung.setPlaceholderText("Begründung des Mitarbeiters …")
        self._begruendung.setMinimumHeight(80)
        self._begruendung.setMaximumHeight(130)
        form.addRow("Begründung:", self._begruendung)

        # Aufgenommen von
        self._aufgenommen_von = QLineEdit()
        self._aufgenommen_von.setPlaceholderText("Name Schichtleiter/in")
        form.addRow("Aufgenommen von:", self._aufgenommen_von)

        layout.addLayout(form)

        hint = QLabel(
            "ℹ️  Das Dokument wird im Ordner <b>Daten/Spät/Protokoll/</b> gespeichert "
            "und kann direkt geöffnet und gedruckt werden."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "background:#fff8e1; color:#5a3e00; border-radius:4px;"
            "padding:8px 12px; font-size:11px;"
        )
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_erstellen = _btn("📄  Dokument erstellen", FIORI_BLUE)
        btn_erstellen.clicked.connect(self._on_accept)
        btn_abbrechen = _btn_light("Abbrechen")
        btn_abbrechen.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_erstellen)
        btn_row.addWidget(btn_abbrechen)
        layout.addLayout(btn_row)

        self._update_verspaetung()

    def _on_dienst_changed(self, idx: int):
        _, code, beginn = self._DIENST_ITEMS[idx]
        h, m = map(int, beginn.split(":"))
        self._beginn.setTime(QTime(h, m))

    def _update_verspaetung(self):
        b = self._beginn.time()
        a = self._antritt.time()
        diff = (a.hour() * 60 + a.minute()) - (b.hour() * 60 + b.minute())
        if diff > 0:
            self._versp_lbl.setText(f"⚠ {diff} Minuten zu spät")
            self._versp_lbl.setStyleSheet(
                "font-weight:bold; color:#c00; font-size:13px; padding:2px 0;"
            )
        elif diff < 0:
            self._versp_lbl.setText(f"✅ {abs(diff)} Minuten zu früh")
            self._versp_lbl.setStyleSheet(
                "font-weight:bold; color:#2d6a2d; font-size:13px; padding:2px 0;"
            )
        else:
            self._versp_lbl.setText("✅ Pünktlich (0 Minuten)")
            self._versp_lbl.setStyleSheet(
                "font-weight:bold; color:#2d6a2d; font-size:13px; padding:2px 0;"
            )

    def _on_accept(self):
        ma = self._ma_combo.currentText().strip()
        if not ma:
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Mitarbeiter angeben.")
            return
        self.accept()

    def _prefill(self, daten: dict):
        if daten.get("mitarbeiter"):
            idx = self._ma_combo.findText(daten["mitarbeiter"])
            if idx >= 0:
                self._ma_combo.setCurrentIndex(idx)
            else:
                self._ma_combo.setCurrentText(daten["mitarbeiter"])
        if daten.get("datum"):
            parts = daten["datum"].split(".")
            if len(parts) == 3:
                self._datum.setDate(QDate(int(parts[2]), int(parts[1]), int(parts[0])))
        if daten.get("dienst"):
            for i, (_, code, _) in enumerate(self._DIENST_ITEMS):
                if code == daten["dienst"]:
                    self._dienst_combo.setCurrentIndex(i)
                    break
        if daten.get("dienstbeginn"):
            h, m = map(int, daten["dienstbeginn"].split(":"))
            self._beginn.setTime(QTime(h, m))
        if daten.get("dienstantritt"):
            h, m = map(int, daten["dienstantritt"].split(":"))
            self._antritt.setTime(QTime(h, m))
        if daten.get("begruendung"):
            self._begruendung.setPlainText(daten["begruendung"])
        if daten.get("aufgenommen_von"):
            self._aufgenommen_von.setText(daten["aufgenommen_von"])

    def get_daten(self) -> dict:
        b = self._beginn.time()
        a = self._antritt.time()
        beginn_str  = f"{b.hour():02d}:{b.minute():02d}"
        antritt_str = f"{a.hour():02d}:{a.minute():02d}"
        diff = (a.hour() * 60 + a.minute()) - (b.hour() * 60 + b.minute())
        idx = self._dienst_combo.currentIndex()
        dienst_code = self._dienst_combo.itemData(idx) or "T"
        return {
            "mitarbeiter":     self._ma_combo.currentText().strip(),
            "datum":           self._datum.date().toString("dd.MM.yyyy"),
            "dienst":          dienst_code,
            "dienstbeginn":    beginn_str,
            "dienstantritt":   antritt_str,
            "verspaetung_min": diff,
            "begruendung":     self._begruendung.toPlainText().strip(),
            "aufgenommen_von": self._aufgenommen_von.text().strip(),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Dialog: PSA-Verstoß erfassen
# ══════════════════════════════════════════════════════════════════════════════

class _PsaDialog(QDialog):
    """Dialog zum Erfassen eines PSA-Verstoßes (fehlende Schutzausrüstung)."""

    _PSA_TYPEN = [
        "Oberteil",
        "Hose",
        "Sicherheitsschuhe",
        "Warnweste",
    ]

    def __init__(self, daten: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🦺 PSA-Verstoß erfassen")
        self.setMinimumWidth(480)
        self.resize(520, 420)
        self._build_ui()
        if daten:
            self._prefill(daten)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        title = QLabel("🦺 PSA-Verstoß erfassen")
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{FIORI_BLUE};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._ma_combo = QComboBox()
        self._ma_combo.setEditable(True)
        self._ma_combo.setMinimumWidth(260)
        self._ma_combo.lineEdit().setPlaceholderText("Name eingeben …")
        try:
            from functions.mitarbeiter_functions import lade_mitarbeiter_namen
            for name in lade_mitarbeiter_namen():
                self._ma_combo.addItem(name)
        except Exception:
            pass
        form.addRow("Mitarbeiter *:", self._ma_combo)

        self._datum = QDateEdit(QDate.currentDate())
        self._datum.setCalendarPopup(True)
        self._datum.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Datum *:", self._datum)

        self._psa_typ = QComboBox()
        self._psa_typ.setEditable(True)
        self._psa_typ.addItems(self._PSA_TYPEN)
        self._psa_typ.lineEdit().setPlaceholderText("Auswählen oder eigenen Typ eingeben …")
        form.addRow("PSA-Typ *:", self._psa_typ)

        self._bemerkung = QTextEdit()
        self._bemerkung.setPlaceholderText("Beschreibung des Verstoßes, Beobachtung …")
        self._bemerkung.setMinimumHeight(80)
        self._bemerkung.setMaximumHeight(130)
        form.addRow("Bemerkung:", self._bemerkung)

        self._aufgenommen_von = QLineEdit()
        self._aufgenommen_von.setPlaceholderText("Name Schichtleiter/in")
        form.addRow("Aufgenommen von:", self._aufgenommen_von)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_speichern = _btn("💾  Speichern", FIORI_BLUE)
        btn_speichern.clicked.connect(self._on_accept)
        btn_abbrechen = _btn_light("Abbrechen")
        btn_abbrechen.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_speichern)
        btn_row.addWidget(btn_abbrechen)
        layout.addLayout(btn_row)

    def _on_accept(self):
        if not self._ma_combo.currentText().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Mitarbeiter angeben.")
            return
        self.accept()

    def _prefill(self, daten: dict):
        if daten.get("mitarbeiter"):
            idx = self._ma_combo.findText(daten["mitarbeiter"])
            if idx >= 0:
                self._ma_combo.setCurrentIndex(idx)
            else:
                self._ma_combo.setCurrentText(daten["mitarbeiter"])
        if daten.get("datum"):
            parts = daten["datum"].split(".")
            if len(parts) == 3:
                self._datum.setDate(QDate(int(parts[2]), int(parts[1]), int(parts[0])))
        if daten.get("psa_typ"):
            idx = self._psa_typ.findText(daten["psa_typ"])
            if idx >= 0:
                self._psa_typ.setCurrentIndex(idx)
        if daten.get("bemerkung"):
            self._bemerkung.setPlainText(daten["bemerkung"])
        if daten.get("aufgenommen_von"):
            self._aufgenommen_von.setText(daten["aufgenommen_von"])

    def get_daten(self) -> dict:
        return {
            "mitarbeiter":     self._ma_combo.currentText().strip(),
            "datum":           self._datum.date().toString("dd.MM.yyyy"),
            "psa_typ":         self._psa_typ.currentText(),
            "bemerkung":       self._bemerkung.toPlainText().strip(),
            "aufgenommen_von": self._aufgenommen_von.text().strip(),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Haupt-Widget
# ══════════════════════════════════════════════════════════════════════════════

class MitarbeiterDokumenteWidget(QWidget):
    """
    Haupt-Widget für den Mitarbeiter-Dokumente-Bereich.
    Links: Kategorieliste
    Rechts: Dateiliste der gewählten Kategorie + Aktions-Buttons
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._akt_kategorie: str = KATEGORIEN[0]
        self._dokumente: dict[str, list[dict]] = {}
        self._db_eintraege: list[dict] = []
        self._build_ui()
        self.refresh()

    # ── UI aufbauen ───────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Titelleiste ────────────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background:{FIORI_BLUE}; border:none;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)
        lbl = QLabel("👥  Mitarbeiter-Dokumente")
        lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        lbl.setStyleSheet("color:white; background:transparent;")
        hl.addWidget(lbl)
        hl.addStretch()

        btn_ordner = QPushButton("📂 Ordner öffnen")
        btn_ordner.setFixedHeight(30)
        btn_ordner.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ordner.setToolTip("Mitarbeiterdokumente-Ordner im Explorer öffnen")
        btn_ordner.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.15);color:white;"
            "border:1px solid rgba(255,255,255,0.3);border-radius:4px;padding:4px 10px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.25);}"
        )
        btn_ordner.clicked.connect(self._ordner_oeffnen)
        hl.addWidget(btn_ordner)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedSize(30, 30)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setToolTip("Dateiliste aktualisieren")
        btn_refresh.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.15);color:white;"
            "border:1px solid rgba(255,255,255,0.3);border-radius:4px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.25);}"
        )
        btn_refresh.clicked.connect(self.refresh)
        hl.addWidget(btn_refresh)
        layout.addWidget(header)

        # ── Splitter (Links + Rechts) ──────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background:#ddd; width:1px; }")
        layout.addWidget(splitter, 1)

        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_hauptbereich())
        splitter.setSizes([220, 800])

    def _build_sidebar(self) -> QWidget:
        """Linke Spalte: Kategorie-Liste."""
        w = QWidget()
        w.setMinimumWidth(180)
        w.setMaximumWidth(280)
        w.setStyleSheet("background:#f0f2f5;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        lbl = QLabel("  Kategorien")
        lbl.setFixedHeight(36)
        lbl.setStyleSheet(
            "background:#e0e4ea; color:#444; font-weight:bold; "
            "font-size:12px; padding-left:12px;"
        )
        layout.addWidget(lbl)

        self._kat_list = QListWidget()
        self._kat_list.setStyleSheet("""
            QListWidget {
                background:#f0f2f5;
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-bottom: 1px solid #e0e0e0;
                color: #333;
            }
            QListWidget::item:selected {
                background: #1565a8;
                color: white;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected {
                background: #dce8f8;
            }
        """)
        for kat in KATEGORIEN:
            self._kat_list.addItem(f"📁  {kat}")
        self._kat_list.setCurrentRow(0)
        self._kat_list.currentRowChanged.connect(self._kategorie_gewaehlt)
        layout.addWidget(self._kat_list, 1)

        # Vorlage-Info
        vorlage_ok = os.path.isfile(VORLAGE_PFAD)
        status_lbl = QLabel(
            "  ✅ Vorlage gefunden" if vorlage_ok else "  ⚠ Vorlage fehlt"
        )
        status_lbl.setFixedHeight(28)
        status_lbl.setStyleSheet(
            f"background:{'#e8f5e9' if vorlage_ok else '#fff3e0'};"
            f"color:{'#2d6a2d' if vorlage_ok else '#7a5000'};"
            "font-size:10px; padding-left:10px;"
        )
        status_lbl.setToolTip(VORLAGE_PFAD)
        layout.addWidget(status_lbl)

        return w

    def _build_hauptbereich(self) -> QWidget:
        """Rechte Spalte: Dateiliste + Aktionsleiste (+ DB-Browser für Stellungnahmen)."""
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(8)

        # Aktions-Buttons (immer sichtbar)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_neu = _btn("＋  Neues Dokument", FIORI_BLUE)
        self._btn_neu.setToolTip("Neues Dokument mit DRK-Kopf-/Fußzeile aus Vorlage erstellen")
        self._btn_neu.clicked.connect(lambda: self._neues_dokument())
        btn_row.addWidget(self._btn_neu)

        self._btn_stellungnahme = _btn("📝  Stellungnahme", "#107e3e", "#0a5c2e")
        self._btn_stellungnahme.setToolTip("Strukturierte Stellungnahme erstellen (Flug, Beschwerde, nicht mitgeflogen)")
        self._btn_stellungnahme.setVisible(False)
        self._btn_stellungnahme.clicked.connect(self._stellungnahme_erstellen)
        btn_row.addWidget(self._btn_stellungnahme)

        self._btn_web = _btn("🌐  Web-Ansicht", "#5c35cc", "#4a2aa0")
        self._btn_web.setToolTip("Lokale Web-Ansicht der Stellungnahmen-Datenbank im Browser öffnen")
        self._btn_web.setVisible(False)
        self._btn_web.clicked.connect(self._web_ansicht_oeffnen)
        btn_row.addWidget(self._btn_web)

        self._btn_verspaetung = _btn("⏰  Verspätung erfassen", "#b05a00", "#7a3d00")
        self._btn_verspaetung.setToolTip("Neue Meldung über unpünktlichen Dienstantritt erstellen")
        self._btn_verspaetung.setVisible(False)
        self._btn_verspaetung.clicked.connect(self._verspaetung_erfassen)
        btn_row.addWidget(self._btn_verspaetung)

        self._btn_psa = _btn("🦺  PSA-Verstoß erfassen", "#6a1a1a", "#4a1010")
        self._btn_psa.setToolTip("Neuen PSA-Verstoß erfassen")
        self._btn_psa.setVisible(False)
        self._btn_psa.clicked.connect(self._psa_erfassen)
        btn_row.addWidget(self._btn_psa)

        btn_row.addStretch()
        outer.addLayout(btn_row)

        # Kategorie-Titel
        self._kat_label = QLabel()
        self._kat_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self._kat_label.setStyleSheet(f"color:{FIORI_TEXT}; padding:4px 0;")
        outer.addWidget(self._kat_label)

        # ── QTabWidget: Tab 0 = Dateien, Tab 1 = Datenbank ───────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border:1px solid #ddd; }
            QTabBar::tab {
                padding:6px 16px; font-size:12px; min-width:100px;
                border:1px solid #ddd; border-bottom:none;
                background:#f5f5f5; color:#555;
                border-top-left-radius:4px; border-top-right-radius:4px;
            }
            QTabBar::tab:selected { background:white; color:#1565a8; font-weight:bold; }
            QTabBar::tab:hover:!selected { background:#e8f0fb; }
        """)
        outer.addWidget(self._tabs, 1)

        # ── TAB 0: Datei-Browser ──────────────────────────────────────────────
        tab_dateien = QWidget()
        tl = QVBoxLayout(tab_dateien)
        tl.setContentsMargins(0, 8, 0, 0)
        tl.setSpacing(6)

        # ── Datei-Filter (nur Stellungnahmen) ─────────────────────────────────
        self._datei_filter_frame = QFrame()
        self._datei_filter_frame.setStyleSheet(
            "QFrame{background:#f0f4ff;border:1px solid #c0ccee;"
            "border-radius:4px;padding:2px;}"
        )
        self._datei_filter_frame.setVisible(False)
        dff = QHBoxLayout(self._datei_filter_frame)
        dff.setContentsMargins(8, 4, 8, 4)
        dff.setSpacing(8)
        dff.addWidget(QLabel("Jahr:"))
        self._datei_combo_jahr = QComboBox()
        self._datei_combo_jahr.setFixedWidth(80)
        self._datei_combo_jahr.currentIndexChanged.connect(self._datei_filter_changed)
        dff.addWidget(self._datei_combo_jahr)
        dff.addWidget(QLabel("Monat:"))
        self._datei_combo_monat = QComboBox()
        self._datei_combo_monat.setFixedWidth(110)
        for i, m in enumerate([
            "Alle","Januar","Februar","März","April","Mai","Juni",
            "Juli","August","September","Oktober","November","Dezember"
        ]):
            self._datei_combo_monat.addItem(m, None if i == 0 else i)
        self._datei_combo_monat.currentIndexChanged.connect(self._datei_filter_changed)
        dff.addWidget(self._datei_combo_monat)
        dff.addStretch()
        tl.addWidget(self._datei_filter_frame)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Dateiname", "Zuletzt geändert", "Typ"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("QTableWidget{border:1px solid #ddd;font-size:12px;}")
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._auswahl_geaendert)
        self._table.itemDoubleClicked.connect(lambda _: self._dokument_oeffnen())
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._table_kontextmenu)
        tl.addWidget(self._table, 1)

        info = QLabel(
            "💡 <b>Doppelklick</b> öffnet ein Dokument direkt.  "
            "\"<b>Bearbeiten</b>\" ermöglicht Textänderungen im Popup – "
            "das Dokument wird anschließend mit der DRK-Vorlage neu erstellt."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background:#e3f2fd; color:#154360; border-radius:4px;"
            "padding:8px 12px; font-size:11px;"
        )
        tl.addWidget(info)
        self._tabs.addTab(tab_dateien, "📂  Dateien")

        # ── TAB 1: Datenbank-Suche ────────────────────────────────────────────
        self._tabs.addTab(self._build_db_browser(), "🔍  Datenbank-Suche")
        self._tabs.setTabVisible(1, False)  # nur bei Stellungnahmen sichtbar

        # ── TAB 2: Verspätungs-Protokoll ──────────────────────────────────────
        self._tabs.addTab(self._build_verspaetungen_tab(), "⏰  Verspätungs-Protokoll")
        self._tabs.setTabVisible(2, False)  # nur bei Verspätung sichtbar

        # ── TAB 3: PSA-Protokoll ──────────────────────────────────────────────
        self._tabs.addTab(self._build_psa_tab(), "🦺  PSA-Protokoll")
        self._tabs.setTabVisible(3, False)  # nur bei PSA sichtbar

        self._tabs.currentChanged.connect(self._on_tab_changed)

        return w

    def _build_db_browser(self) -> QWidget:
        """DB-Browser-Tab: Filter + Ergebnistabelle + Details."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # ── Filter-Zeile ──────────────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame{background:#f8f9fa;border:1px solid #ddd;"
            "border-radius:4px;padding:4px;}"
        )
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(10)

        fl.addWidget(QLabel("Jahr:"))
        self._db_combo_jahr = QComboBox()
        self._db_combo_jahr.setFixedWidth(80)
        self._db_combo_jahr.addItem("Alle", None)
        self._db_combo_jahr.currentIndexChanged.connect(self._db_filter_changed)
        fl.addWidget(self._db_combo_jahr)

        fl.addWidget(QLabel("Monat:"))
        self._db_combo_monat = QComboBox()
        self._db_combo_monat.setFixedWidth(110)
        _MONATE = [
            "Alle", "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ]
        for i, m in enumerate(_MONATE):
            self._db_combo_monat.addItem(m, None if i == 0 else i)
        self._db_combo_monat.currentIndexChanged.connect(self._db_filter_changed)
        fl.addWidget(self._db_combo_monat)

        fl.addWidget(QLabel("Art:"))
        self._db_combo_art = QComboBox()
        self._db_combo_art.setFixedWidth(160)
        self._db_combo_art.addItem("Alle", None)
        self._db_combo_art.addItem("✈️  Flug-Vorfall",       "flug")
        self._db_combo_art.addItem("🗣️  Passagierbeschwerde", "beschwerde")
        self._db_combo_art.addItem("🚶  Nicht mitgeflogen",  "nicht_mitgeflogen")
        self._db_combo_art.currentIndexChanged.connect(self._db_filter_changed)
        fl.addWidget(self._db_combo_art)

        fl.addWidget(QLabel("Suche:"))
        self._db_suche = QLineEdit()
        self._db_suche.setPlaceholderText("Name, Flugnummer, Sachverhalt …")
        self._db_suche.setMinimumWidth(200)
        self._db_suche.textChanged.connect(self._db_filter_changed)
        fl.addWidget(self._db_suche, 1)

        btn_reset = _btn_light("✖ Zurücksetzen")
        btn_reset.setFixedHeight(28)
        btn_reset.clicked.connect(self._db_filter_reset)
        fl.addWidget(btn_reset)

        layout.addWidget(filter_frame)

        # ── Ergebnis-Tabelle ──────────────────────────────────────────────────
        self._db_table = QTableWidget()
        self._db_table.setColumnCount(7)
        self._db_table.setHorizontalHeaderLabels(
            ["Datum Vorfall", "Mitarbeiter", "Art", "Flugnummer", "Verfasst am", "Erstellt am", "ID"]
        )
        hh = self._db_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._db_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._db_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._db_table.setAlternatingRowColors(True)
        self._db_table.setStyleSheet("QTableWidget{border:1px solid #ddd;font-size:12px;}")
        self._db_table.verticalHeader().setVisible(False)
        self._db_table.itemSelectionChanged.connect(self._db_auswahl_geaendert)
        self._db_table.itemDoubleClicked.connect(lambda _: self._db_dokument_oeffnen())
        layout.addWidget(self._db_table, 1)

        # ── Aktions-Buttons DB ────────────────────────────────────────────────
        db_btn_row = QHBoxLayout()
        db_btn_row.setSpacing(8)

        self._db_btn_oeffnen = _btn("📂  Dokument öffnen", FIORI_BLUE)
        self._db_btn_oeffnen.setEnabled(False)
        self._db_btn_oeffnen.setToolTip("Verknüpftes Word-Dokument öffnen")
        self._db_btn_oeffnen.clicked.connect(self._db_dokument_oeffnen)
        db_btn_row.addWidget(self._db_btn_oeffnen)

        self._db_btn_details = _btn_light("🔎  Details")
        self._db_btn_details.setEnabled(False)
        self._db_btn_details.setToolTip("Alle gespeicherten Felder anzeigen")
        self._db_btn_details.clicked.connect(self._db_details_anzeigen)
        db_btn_row.addWidget(self._db_btn_details)

        self._db_btn_loeschen = _btn_light("🗑  DB-Eintrag löschen")
        self._db_btn_loeschen.setEnabled(False)
        self._db_btn_loeschen.setToolTip(
            "Eintrag aus der Datenbank entfernen (Word-Datei bleibt erhalten)"
        )
        self._db_btn_loeschen.setStyleSheet(
            "QPushButton{background:#eee;color:#333;border:none;"
            "border-radius:4px;padding:4px 14px;font-size:12px;}"
            "QPushButton:hover{background:#ffcccc;color:#a00;}"
            "QPushButton:disabled{background:#f5f5f5;color:#bbb;}"
        )
        self._db_btn_loeschen.clicked.connect(self._db_eintrag_loeschen)
        db_btn_row.addWidget(self._db_btn_loeschen)

        db_btn_row.addStretch()
        self._db_treffer_lbl = QLabel()
        self._db_treffer_lbl.setStyleSheet("color:#666; font-size:11px;")
        db_btn_row.addWidget(self._db_treffer_lbl)

        layout.addLayout(db_btn_row)
        return w

    def _build_verspaetungen_tab(self) -> QWidget:
        """TAB 2: Verspätungs-Protokoll – Filterzeile, Tabelle, Aktionen."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        # ── Filter-Zeile ──────────────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame{background:#fff8e1;border:1px solid #ffe082;"
            "border-radius:4px;padding:4px;}"
        )
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(10)

        fl.addWidget(QLabel("Jahr:"))
        self._versp_combo_jahr = QComboBox()
        self._versp_combo_jahr.setFixedWidth(80)
        self._versp_combo_jahr.addItem("Alle", None)
        self._versp_combo_jahr.currentIndexChanged.connect(self._versp_filter_changed)
        fl.addWidget(self._versp_combo_jahr)

        fl.addWidget(QLabel("Monat:"))
        self._versp_combo_monat = QComboBox()
        self._versp_combo_monat.setFixedWidth(110)
        _MONATE = [
            "Alle", "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ]
        for i, m in enumerate(_MONATE):
            self._versp_combo_monat.addItem(m, None if i == 0 else i)
        self._versp_combo_monat.currentIndexChanged.connect(self._versp_filter_changed)
        fl.addWidget(self._versp_combo_monat)

        fl.addWidget(QLabel("Suche:"))
        self._versp_suche = QLineEdit()
        self._versp_suche.setPlaceholderText("Name, Begründung, Aufgenommen von …")
        self._versp_suche.setMinimumWidth(200)
        self._versp_suche.textChanged.connect(self._versp_filter_changed)
        fl.addWidget(self._versp_suche, 1)

        btn_reset = _btn_light("✖ Zurücksetzen")
        btn_reset.setFixedHeight(28)
        btn_reset.clicked.connect(self._versp_filter_reset)
        fl.addWidget(btn_reset)

        layout.addWidget(filter_frame)

        # ── Ergebnis-Tabelle ──────────────────────────────────────────────────
        self._versp_table = QTableWidget()
        self._versp_table.setColumnCount(8)
        self._versp_table.setHorizontalHeaderLabels([
            "Datum", "Mitarbeiter", "Dienst",
            "Dienstbeginn", "Dienstantritt", "Verspätung",
            "Aufgenommen von", "ID",
        ])
        hh = self._versp_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self._versp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._versp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._versp_table.setAlternatingRowColors(True)
        self._versp_table.setStyleSheet("QTableWidget{border:1px solid #ddd;font-size:12px;}")
        self._versp_table.verticalHeader().setVisible(False)
        self._versp_table.itemSelectionChanged.connect(self._versp_auswahl_geaendert)
        self._versp_table.itemDoubleClicked.connect(lambda _: self._verspaetung_oeffnen())
        layout.addWidget(self._versp_table, 1)

        # ── Aktions-Buttons ───────────────────────────────────────────────────
        vbtn_row = QHBoxLayout()
        vbtn_row.setSpacing(8)

        self._versp_btn_oeffnen = _btn("📂  Dokument öffnen", FIORI_BLUE)
        self._versp_btn_oeffnen.setEnabled(False)
        self._versp_btn_oeffnen.setToolTip("Gespeichertes Word-Dokument öffnen / drucken")
        self._versp_btn_oeffnen.clicked.connect(self._verspaetung_oeffnen)
        vbtn_row.addWidget(self._versp_btn_oeffnen)

        self._versp_btn_bearbeiten = _btn_light("✏  Bearbeiten")
        self._versp_btn_bearbeiten.setEnabled(False)
        self._versp_btn_bearbeiten.setToolTip("Eintrag bearbeiten und Dokument neu erstellen")
        self._versp_btn_bearbeiten.clicked.connect(self._verspaetung_bearbeiten)
        vbtn_row.addWidget(self._versp_btn_bearbeiten)

        self._versp_btn_mail = _btn("📧  Per E-Mail senden", "#5c35cc", "#4a2aa0")
        self._versp_btn_mail.setEnabled(False)
        self._versp_btn_mail.setToolTip("Outlook-Entwurf mit dem Dokument als Anhang erstellen")
        self._versp_btn_mail.clicked.connect(self._verspaetung_mail_senden)
        vbtn_row.addWidget(self._versp_btn_mail)

        self._versp_btn_loeschen = _btn_light("🗑  Löschen")
        self._versp_btn_loeschen.setEnabled(False)
        self._versp_btn_loeschen.setToolTip("Eintrag aus Protokoll löschen (Dokument bleibt erhalten)")
        self._versp_btn_loeschen.setStyleSheet(
            "QPushButton{background:#eee;color:#333;border:none;"
            "border-radius:4px;padding:4px 14px;font-size:12px;}"
            "QPushButton:hover{background:#ffcccc;color:#a00;}"
            "QPushButton:disabled{background:#f5f5f5;color:#bbb;}"
        )
        self._versp_btn_loeschen.clicked.connect(self._verspaetung_loeschen)
        vbtn_row.addWidget(self._versp_btn_loeschen)

        vbtn_row.addStretch()
        self._versp_treffer_lbl = QLabel()
        self._versp_treffer_lbl.setStyleSheet("color:#666; font-size:11px;")
        vbtn_row.addWidget(self._versp_treffer_lbl)

        layout.addLayout(vbtn_row)
        return w

    def _build_psa_tab(self) -> QWidget:
        """TAB 3: PSA-Protokoll – Filterzeile, Tabelle, Aktionen."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame{background:#fce4ec;border:1px solid #f48fb1;"
            "border-radius:4px;padding:4px;}"
        )
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(10)

        fl.addWidget(QLabel("Jahr:"))
        self._psa_combo_jahr = QComboBox()
        self._psa_combo_jahr.setFixedWidth(80)
        self._psa_combo_jahr.addItem("Alle", None)
        self._psa_combo_jahr.currentIndexChanged.connect(self._psa_filter_changed)
        fl.addWidget(self._psa_combo_jahr)

        fl.addWidget(QLabel("Monat:"))
        self._psa_combo_monat = QComboBox()
        self._psa_combo_monat.setFixedWidth(110)
        for i, m in enumerate([
            "Alle", "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ]):
            self._psa_combo_monat.addItem(m, None if i == 0 else i)
        self._psa_combo_monat.currentIndexChanged.connect(self._psa_filter_changed)
        fl.addWidget(self._psa_combo_monat)

        fl.addWidget(QLabel("Suche:"))
        self._psa_suche = QLineEdit()
        self._psa_suche.setPlaceholderText("Name, PSA-Typ, Bemerkung …")
        self._psa_suche.setMinimumWidth(200)
        self._psa_suche.textChanged.connect(self._psa_filter_changed)
        fl.addWidget(self._psa_suche, 1)

        btn_reset = _btn_light("✖ Zurücksetzen")
        btn_reset.setFixedHeight(28)
        btn_reset.clicked.connect(self._psa_filter_reset)
        fl.addWidget(btn_reset)

        layout.addWidget(filter_frame)

        self._psa_table = QTableWidget()
        self._psa_table.setColumnCount(7)
        self._psa_table.setHorizontalHeaderLabels([
            "Datum", "Mitarbeiter", "PSA-Typ", "Bemerkung", "Aufgenommen von", "Versendet", "ID",
        ])
        hh = self._psa_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._psa_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._psa_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._psa_table.setAlternatingRowColors(True)
        self._psa_table.setStyleSheet("QTableWidget{border:1px solid #ddd;font-size:12px;}")
        self._psa_table.verticalHeader().setVisible(False)
        self._psa_table.itemSelectionChanged.connect(self._psa_auswahl_geaendert)
        layout.addWidget(self._psa_table, 1)

        pbtn_row = QHBoxLayout()
        pbtn_row.setSpacing(8)

        self._psa_btn_bearbeiten = _btn_light("✏  Bearbeiten")
        self._psa_btn_bearbeiten.setEnabled(False)
        self._psa_btn_bearbeiten.setToolTip("Eintrag bearbeiten")
        self._psa_btn_bearbeiten.clicked.connect(self._psa_bearbeiten)
        pbtn_row.addWidget(self._psa_btn_bearbeiten)

        self._psa_btn_loeschen = _btn_light("🗑  Löschen")
        self._psa_btn_loeschen.setEnabled(False)
        self._psa_btn_loeschen.setStyleSheet(
            "QPushButton{background:#eee;color:#333;border:none;"
            "border-radius:4px;padding:4px 14px;font-size:12px;}"
            "QPushButton:hover{background:#ffcccc;color:#a00;}"
            "QPushButton:disabled{background:#f5f5f5;color:#bbb;}"
        )
        self._psa_btn_loeschen.clicked.connect(self._psa_loeschen)
        pbtn_row.addWidget(self._psa_btn_loeschen)

        pbtn_row.addStretch()
        self._psa_treffer_lbl = QLabel()
        self._psa_treffer_lbl.setStyleSheet("color:#666; font-size:11px;")
        pbtn_row.addWidget(self._psa_treffer_lbl)

        layout.addLayout(pbtn_row)
        return w

    # ── PSA: Filter / Laden ───────────────────────────────────────────────────

    def _psa_jahre_aktualisieren(self):
        current = self._psa_combo_jahr.currentData()
        self._psa_combo_jahr.blockSignals(True)
        self._psa_combo_jahr.clear()
        self._psa_combo_jahr.addItem("Alle", None)
        for j in pdb_jahre():
            self._psa_combo_jahr.addItem(str(j), j)
        for i in range(self._psa_combo_jahr.count()):
            if self._psa_combo_jahr.itemData(i) == current:
                self._psa_combo_jahr.setCurrentIndex(i)
                break
        self._psa_combo_jahr.blockSignals(False)

    def _psa_filter_reset(self):
        for w in (self._psa_combo_jahr, self._psa_combo_monat):
            w.blockSignals(True)
            w.setCurrentIndex(0)
            w.blockSignals(False)
        self._psa_suche.blockSignals(True)
        self._psa_suche.clear()
        self._psa_suche.blockSignals(False)
        self._psa_lade()

    def _psa_filter_changed(self):
        self._psa_lade()

    def _psa_lade(self):
        jahr  = self._psa_combo_jahr.currentData()
        monat = self._psa_combo_monat.currentData()
        suche = self._psa_suche.text().strip() or None
        try:
            eintraege = lade_psa_eintraege(monat=monat, jahr=jahr, suchtext=suche)
        except Exception as exc:
            QMessageBox.critical(self, "Datenbankfehler", str(exc))
            return
        self._psa_eintraege = eintraege
        self._psa_table.setRowCount(len(eintraege))
        for row, e in enumerate(eintraege):
            gesendet = bool(e.get("gesendet"))
            row_data = [
                e.get("datum", ""),
                e.get("mitarbeiter", ""),
                e.get("psa_typ", ""),
                e.get("bemerkung", "") or "—",
                e.get("aufgenommen_von", "") or "—",
                "✅ Ja" if gesendet else "⬜ Nein",
                str(e.get("id", "")),
            ]
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter if col in (0, 2, 5, 6)
                    else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                if gesendet:
                    item.setBackground(QColor("#e8f5e9"))
                self._psa_table.setItem(row, col, item)
        n = len(eintraege)
        self._psa_treffer_lbl.setText(f"{n} Eintrag{'e' if n != 1 else ''}")
        self._psa_auswahl_geaendert()

    def _psa_auswahl_geaendert(self):
        hat = bool(self._psa_aktuell_eintrag())
        for btn in (self._psa_btn_bearbeiten, self._psa_btn_loeschen):
            btn.setEnabled(hat)

    def _psa_aktuell_eintrag(self) -> dict | None:
        row = self._psa_table.currentRow()
        try:
            return self._psa_eintraege[row]
        except (AttributeError, IndexError):
            return None

    # ── PSA: Aktionen ─────────────────────────────────────────────────────────

    def _psa_erfassen(self):
        dlg = _PsaDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        daten = dlg.get_daten()
        try:
            psa_speichern(daten)
            self._psa_lade()
            QMessageBox.information(
                self, "PSA-Verstoß erfasst",
                f"Der Eintrag wurde gespeichert.\n\n"
                f"Mitarbeiter: {daten['mitarbeiter']}\n"
                f"PSA-Typ: {daten['psa_typ']}\n"
                f"Datum: {daten['datum']}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Speichern", str(exc))

    def _psa_bearbeiten(self):
        e = self._psa_aktuell_eintrag()
        if not e:
            return
        dlg = _PsaDialog(daten=dict(e), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        daten = dlg.get_daten()
        try:
            psa_aktualisieren(e["id"], daten)
            self._psa_lade()
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Bearbeiten", str(exc))

    def _psa_loeschen(self):
        e = self._psa_aktuell_eintrag()
        if not e:
            return
        antwort = QMessageBox.question(
            self, "Eintrag löschen",
            f"PSA-Eintrag wirklich löschen?\n\n"
            f"Mitarbeiter: {e.get('mitarbeiter', '')}\n"
            f"Datum: {e.get('datum', '')}\n"
            f"PSA-Typ: {e.get('psa_typ', '')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            try:
                pdb_loeschen(e["id"])
                self._psa_lade()
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", str(exc))

    def _versp_jahre_aktualisieren(self):
        current = self._versp_combo_jahr.currentData()
        self._versp_combo_jahr.blockSignals(True)
        self._versp_combo_jahr.clear()
        self._versp_combo_jahr.addItem("Alle", None)
        for j in vdb_jahre():
            self._versp_combo_jahr.addItem(str(j), j)
        for i in range(self._versp_combo_jahr.count()):
            if self._versp_combo_jahr.itemData(i) == current:
                self._versp_combo_jahr.setCurrentIndex(i)
                break
        self._versp_combo_jahr.blockSignals(False)

    def _versp_filter_reset(self):
        for w in (self._versp_combo_jahr, self._versp_combo_monat):
            w.blockSignals(True)
            w.setCurrentIndex(0)
            w.blockSignals(False)
        self._versp_suche.blockSignals(True)
        self._versp_suche.clear()
        self._versp_suche.blockSignals(False)
        self._versp_lade()

    def _versp_filter_changed(self):
        self._versp_lade()

    def _versp_lade(self):
        """Verspätungs-DB abfragen und Tabelle befüllen."""
        jahr   = self._versp_combo_jahr.currentData()
        monat  = self._versp_combo_monat.currentData()
        suche  = self._versp_suche.text().strip() or None
        try:
            eintraege = lade_verspaetungen(monat=monat, jahr=jahr, suchtext=suche)
        except Exception as exc:
            QMessageBox.critical(self, "Datenbankfehler", str(exc))
            return
        self._versp_eintraege = eintraege
        self._versp_table.setRowCount(len(eintraege))
        for row, e in enumerate(eintraege):
            vmin = e.get("verspaetung_min") or 0
            if vmin > 0:
                versp_text = f"⚠ {vmin} Min."
                color = QColor("#fff3cd")
            elif vmin < 0:
                versp_text = f"✅ {abs(vmin)} Min. früh"
                color = QColor("#d4edda")
            else:
                versp_text = "✅ Pünktlich"
                color = QColor("#d4edda")
            row_data = [
                e.get("datum", ""),
                e.get("mitarbeiter", ""),
                e.get("dienst", ""),
                e.get("dienstbeginn", ""),
                e.get("dienstantritt", ""),
                versp_text,
                e.get("aufgenommen_von", "") or "—",
                str(e.get("id", "")),
            ]
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                if col == 5:
                    item.setBackground(color)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col in (2, 3, 4, 5, 7) else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._versp_table.setItem(row, col, item)
        n = len(eintraege)
        self._versp_treffer_lbl.setText(f"{n} Eintrag{'e' if n != 1 else ''}")
        self._versp_auswahl_geaendert()

    def _versp_auswahl_geaendert(self):
        hat = bool(self._versp_aktuell_eintrag())
        for btn in (self._versp_btn_oeffnen, self._versp_btn_bearbeiten,
                    self._versp_btn_loeschen, self._versp_btn_mail):
            btn.setEnabled(hat)

    def _versp_aktuell_eintrag(self) -> dict | None:
        row = self._versp_table.currentRow()
        try:
            return self._versp_eintraege[row]
        except (AttributeError, IndexError):
            return None

    # ── Verspätungen: Aktionen ────────────────────────────────────────────────

    def _verspaetung_erfassen(self):
        """Neuen Verspätungseintrag erfassen und Dokument erstellen."""
        dlg = _VerspaetungDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        daten = dlg.get_daten()
        if not daten.get("mitarbeiter"):
            return
        try:
            dokument_pfad = erstelle_verspaetungs_dokument(daten)
            daten["dokument_pfad"] = dokument_pfad
            verspaetung_speichern(daten)
            self._versp_lade()
            antwort = QMessageBox.question(
                self,
                "Verspätungsmeldung erstellt",
                f"Das Dokument wurde erstellt und gespeichert:\n\n📄 {dokument_pfad}\n\n"
                "Dokument jetzt öffnen (drucken)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if antwort == QMessageBox.StandardButton.Yes:
                try:
                    oeffne_versp_dokument(dokument_pfad)
                except Exception as exc:
                    QMessageBox.warning(self, "Öffnen fehlgeschlagen", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Erstellen", str(exc))

    def _verspaetung_bearbeiten(self):
        """Bestehenden Eintrag bearbeiten und Dokument neu erstellen."""
        e = self._versp_aktuell_eintrag()
        if not e:
            return
        dlg = _VerspaetungDialog(daten=dict(e), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        daten = dlg.get_daten()
        try:
            dokument_pfad = erstelle_verspaetungs_dokument(daten)
            daten["dokument_pfad"] = dokument_pfad
            verspaetung_aktualisieren(e["id"], daten)
            self._versp_lade()
            antwort = QMessageBox.question(
                self,
                "Eintrag aktualisiert",
                f"Dokument wurde neu erstellt:\n\n📄 {dokument_pfad}\n\nJetzt öffnen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if antwort == QMessageBox.StandardButton.Yes:
                try:
                    oeffne_versp_dokument(dokument_pfad)
                except Exception as exc:
                    QMessageBox.warning(self, "Öffnen fehlgeschlagen", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Bearbeiten", str(exc))

    def _verspaetung_loeschen(self):
        e = self._versp_aktuell_eintrag()
        if not e:
            return
        antwort = QMessageBox.question(
            self, "Eintrag löschen",
            f"Protokoll-Eintrag wirklich löschen?\n\n"
            f"Mitarbeiter:  {e.get('mitarbeiter', '')}\n"
            f"Datum:         {e.get('datum', '')}\n\n"
            "⚠ Das Word-Dokument wird NICHT gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            try:
                vdb_loeschen(e["id"])
                self._versp_lade()
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", str(exc))

    def _verspaetung_oeffnen(self):
        e = self._versp_aktuell_eintrag()
        if not e:
            return
        pfad = e.get("dokument_pfad", "")
        if pfad and os.path.isfile(pfad):
            try:
                oeffne_versp_dokument(pfad)
            except Exception as exc:
                QMessageBox.warning(self, "Fehler", str(exc))
        else:
            QMessageBox.warning(
                self, "Datei nicht gefunden",
                f"Das Dokument wurde nicht gefunden:\n{pfad}\n\n"
                "Es wurde möglicherweise verschoben oder gelöscht."
            )

    def _verspaetung_mail_senden(self):
        """Outlook-Entwurf mit dem Verspätungsdokument als Anhang erstellen."""
        e = self._versp_aktuell_eintrag()
        if not e:
            return
        pfad = e.get("dokument_pfad", "")
        if not pfad or not os.path.isfile(pfad):
            QMessageBox.warning(
                self, "Kein Dokument",
                "Es ist kein Dokument für diesen Eintrag vorhanden.\n"
                "Bitte zuerst bearbeiten, um ein neues Dokument zu erstellen."
            )
            return
        # Mail-Dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("📧 Verspätungsmeldung per E-Mail senden")
        dlg.setMinimumWidth(520)
        vl = QVBoxLayout(dlg)
        vl.setSpacing(10)
        vl.setContentsMargins(20, 20, 20, 16)

        form = QFormLayout()
        form.setSpacing(8)

        emp_edit = QLineEdit()
        emp_edit.setPlaceholderText("z.B. bereichsleitung@drk-koeln.de")
        form.addRow("Empfänger:", emp_edit)

        betr_edit = QLineEdit()
        betr_edit.setText(
            f"Verspätungsmeldung – {e.get('mitarbeiter', '')} – {e.get('datum', '')}"
        )
        form.addRow("Betreff:", betr_edit)

        body_edit = QTextEdit()
        vmin = e.get("verspaetung_min") or 0
        body_edit.setPlainText(
            f"Guten Tag,\n\n"
            f"anbei die Meldung über unpünktlichen Dienstantritt:\n\n"
            f"  Mitarbeiter:    {e.get('mitarbeiter', '')}\n"
            f"  Datum:          {e.get('datum', '')}\n"
            f"  Dienst:         {e.get('dienst', '')}\n"
            f"  Dienstbeginn:   {e.get('dienstbeginn', '')}\n"
            f"  Dienstantritt:  {e.get('dienstantritt', '')}\n"
            f"  Verspätung:     {vmin} Minuten\n\n"
            f"Mit freundlichen Grüßen\n"
            f"Erste-Hilfe-Station CGN"
        )
        body_edit.setMinimumHeight(180)
        form.addRow("Text:", body_edit)

        anhang_lbl = QLabel(f"📎 {os.path.basename(pfad)}")
        anhang_lbl.setStyleSheet("color:#555; font-size:11px;")
        form.addRow("Anhang:", anhang_lbl)

        vl.addLayout(form)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(8)
        send_btn = _btn("📧  Outlook-Entwurf erstellen", "#5c35cc", "#4a2aa0")
        send_btn.clicked.connect(dlg.accept)
        close_btn = _btn_light("Abbrechen")
        close_btn.clicked.connect(dlg.reject)
        btns_row.addStretch()
        btns_row.addWidget(send_btn)
        btns_row.addWidget(close_btn)
        vl.addLayout(btns_row)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            from functions.mail_functions import create_outlook_draft
            create_outlook_draft(
                to=emp_edit.text().strip(),
                subject=betr_edit.text().strip(),
                body=body_edit.toPlainText(),
                attachments=[pfad],
            )
            QMessageBox.information(
                self, "Entwurf erstellt",
                "Der Outlook-Entwurf wurde erfolgreich erstellt.\n"
                "Bitte öffne Outlook und prüfe den Entwurfsordner."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim E-Mail-Erstellen", str(exc))

    # ── Refresh / Laden ───────────────────────────────────────────────────────

    def refresh(self):
        """Dateiliste neu laden."""
        sicherungsordner()
        self._dokumente = lade_dokumente_nach_kategorie()
        self._kat_liste_aktualisieren()
        self._zeige_kategorie(self._akt_kategorie)

    def _kat_liste_aktualisieren(self):
        """Sidebar: Anzahl der Dateien je Kategorie aktualisieren."""
        for row, kat in enumerate(KATEGORIEN):
            anzahl = len(self._dokumente.get(kat, []))
            item = self._kat_list.item(row)
            if item:
                if kat in ("Verspätung", "PSA"):
                    item.setText(f"📁  {kat}")
                else:
                    item.setText(f"📁  {kat}  ({anzahl})")

    def _zeige_kategorie(self, kategorie: str):
        """Tabelle mit Dateien der gewählten Kategorie befüllen."""
        self._akt_kategorie = kategorie
        self._kat_label.setText(f"📁  {kategorie}")
        is_stell = (kategorie == "Stellungnahmen")
        is_versp = (kategorie == "Verspätung")
        is_psa   = (kategorie == "PSA")
        self._btn_stellungnahme.setVisible(is_stell)
        self._btn_web.setVisible(is_stell)
        self._tabs.setTabVisible(1, is_stell)
        self._btn_verspaetung.setVisible(is_versp)
        self._btn_psa.setVisible(is_psa)
        self._btn_neu.setVisible(not is_versp and not is_psa)
        self._tabs.setTabVisible(0, not is_versp and not is_psa)  # Dateien-Tab ausblenden
        self._tabs.setTabVisible(2, is_versp)
        self._tabs.setTabVisible(3, is_psa)
        if is_psa:
            self._tabs.setCurrentIndex(3)
            self._psa_jahre_aktualisieren()
            self._psa_lade()
        elif is_versp:
            self._tabs.setCurrentIndex(2)
            self._versp_jahre_aktualisieren()
            self._versp_lade()
        else:
            self._tabs.setCurrentIndex(0)

        # Filter-Bar für Dateien-Tab bei Stellungnahmen
        self._datei_filter_frame.setVisible(is_stell)
        if is_stell:
            # Jahre aus vorhandenen Dateien befüllen
            dateien = self._dokumente.get("Stellungnahmen", [])
            jahre = sorted(
                {
                    d["geaendert"].split(".")[2].split(" ")[0]
                    for d in dateien
                    if len(d.get("geaendert", "").split(".")) >= 3
                },
                reverse=True
            )
            self._datei_combo_jahr.blockSignals(True)
            self._datei_combo_jahr.clear()
            self._datei_combo_jahr.addItem("Alle", None)
            for j in jahre:
                self._datei_combo_jahr.addItem(j, j)
            self._datei_combo_jahr.blockSignals(False)
            self._datei_combo_monat.setCurrentIndex(0)

        self._datei_filter_changed()
        self._auswahl_geaendert()

    # ── Ereignis-Handler ──────────────────────────────────────────────────────

    def _kategorie_gewaehlt(self, row: int):
        if 0 <= row < len(KATEGORIEN):
            self._zeige_kategorie(KATEGORIEN[row])

    def _auswahl_geaendert(self):
        pass  # Öffnen/Bearbeiten/Umbenennen/Löschen nur über Rechtsklick-Menü

    def _aktueller_eintrag(self) -> dict | None:
        row = self._table.currentRow()
        dateien = self._dokumente.get(self._akt_kategorie, [])
        if 0 <= row < len(dateien):
            return dateien[row]
        return None

    # ── Aktionen ──────────────────────────────────────────────────────────────

    def _ordner_oeffnen(self):
        import subprocess
        subprocess.Popen(["explorer", DOKUMENTE_BASIS], shell=False)

    def _dokument_oeffnen(self):
        eintrag = self._aktueller_eintrag()
        if eintrag:
            oeffne_datei(eintrag["pfad"])

    def _dokument_bearbeiten(self):
        eintrag = self._aktueller_eintrag()
        if not eintrag:
            return
        pfad = eintrag["pfad"]
        ext = os.path.splitext(pfad)[1].lower()
        if ext not in (".docx", ".doc", ".txt"):
            QMessageBox.information(
                self, "Bearbeiten nicht möglich",
                f"Nur .docx und .txt können im Popup bearbeitet werden.\n"
                f"Bitte öffne die Datei direkt: {pfad}"
            )
            return
        dlg = _DokumentBearbeitenDialog(eintrag, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            neuer_inhalt = dlg.get_inhalt()
            try:
                # Alten Dateinamen behalten, mit neuem Inhalt neu erstellen
                alter_name = os.path.basename(pfad)
                # Kurzen Titel aus Dateinamen ableiten
                titel = os.path.splitext(alter_name)[0]
                neuer_pfad = erstelle_dokument_aus_vorlage(
                    kategorie=self._akt_kategorie,
                    titel=titel,
                    mitarbeiter="(Bearbeitung)",
                    datum=__import__("datetime").datetime.now().strftime("%d.%m.%Y"),
                    inhalt=neuer_inhalt,
                    dateiname=alter_name,
                )
                QMessageBox.information(
                    self, "Gespeichert",
                    f"Dokument wurde aktualisiert:\n{neuer_pfad}"
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Fehler beim Speichern", str(e))

    def _neues_dokument(self, vorkategorie: str = ""):
        dlg = _NeuesDokumentDialog(vorkategorie or self._akt_kategorie, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            try:
                pfad = erstelle_dokument_aus_vorlage(
                    kategorie=d["kategorie"],
                    titel=d["titel"],
                    mitarbeiter=d["mitarbeiter"],
                    datum=d["datum"],
                    inhalt=d["inhalt"],
                )
                self.refresh()
                # Zur richtigen Kategorie wechseln
                idx = KATEGORIEN.index(d["kategorie"]) if d["kategorie"] in KATEGORIEN else 0
                self._kat_list.setCurrentRow(idx)

                antwort = QMessageBox.question(
                    self, "Dokument erstellt",
                    f"Dokument wurde erfolgreich erstellt:\n{pfad}\n\nJetzt öffnen?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if antwort == QMessageBox.StandardButton.Yes:
                    oeffne_datei(pfad)
            except Exception as e:
                QMessageBox.critical(self, "Fehler beim Erstellen", str(e))

    def _stellungnahme_erstellen(self):
        """Öffnet den Stellungnahme-Assistenten und erstellt das Word-Dokument."""
        dlg = _StellungnahmeDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        daten = dlg.get_daten()
        try:
            intern_pfad, extern_pfad = erstelle_stellungnahme(daten)
            self.refresh()
            # Zur Stellungnahmen-Kategorie wechseln
            if "Stellungnahmen" in KATEGORIEN:
                idx = KATEGORIEN.index("Stellungnahmen")
                self._kat_list.setCurrentRow(idx)
            antwort = QMessageBox.question(
                self,
                "Stellungnahme erstellt",
                f"Die Stellungnahme wurde erfolgreich gespeichert:\n\n"
                f"📂 Intern:  {intern_pfad}\n"
                f"📂 Extern:  {extern_pfad}\n\n"
                f"Dokument jetzt öffnen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if antwort == QMessageBox.StandardButton.Yes:
                oeffne_datei(intern_pfad)
        except Exception as exc:
            QMessageBox.critical(
                self, "Fehler beim Erstellen der Stellungnahme", str(exc)
            )

    def _table_kontextmenu(self, pos):
        """Rechtsklick-Menü auf Datei-Tabelle."""
        from PySide6.QtWidgets import QMenu
        import subprocess
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        dateien = [
            d for d in self._dokumente.get(self._akt_kategorie, [])
            if self._table.item(row, 0) and
            d["name"] in (self._table.item(row, 0).text() or "")
        ]
        if not dateien:
            # Fallback: Ordner der Kategorie öffnen
            pfad = os.path.join(DOKUMENTE_BASIS, self._akt_kategorie)
        else:
            pfad = dateien[0]["pfad"]

        self._table.setCurrentCell(row, 0)
        menu = QMenu(self)
        act_explorer   = menu.addAction("📂  Im Explorer anzeigen")
        act_oeffnen    = menu.addAction("📄  Öffnen")
        menu.addSeparator()
        act_bearbeiten = menu.addAction("✏  Bearbeiten")
        act_umbenennen = menu.addAction("🔤  Umbenennen")
        act_loeschen   = menu.addAction("🗑  Löschen")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == act_explorer:
            subprocess.Popen(["explorer", "/select,", pfad])
        elif action == act_oeffnen:
            oeffne_datei(pfad)
        elif action == act_bearbeiten:
            self._dokument_bearbeiten()
        elif action == act_umbenennen:
            self._dokument_umbenennen()
        elif action == act_loeschen:
            self._dokument_loeschen()

    def _datei_filter_changed(self):
        """Dateitabelle nach Jahr/Monat filtern und neu befüllen."""
        kategorie = self._akt_kategorie
        alle_dateien = self._dokumente.get(kategorie, [])

        if self._datei_filter_frame.isVisible():
            jahr_filter  = self._datei_combo_jahr.currentData()
            monat_filter = self._datei_combo_monat.currentData()
            dateien = []
            for d in alle_dateien:
                g = d.get("geaendert", "")
                # Format: dd.MM.yyyy HH:mm oder dd.MM.yyyy
                parts = g.replace(" ", ".").split(".")
                try:
                    d_monat = int(parts[1]) if len(parts) > 1 else 0
                    d_jahr  = parts[2] if len(parts) > 2 else ""
                except (ValueError, IndexError):
                    d_monat, d_jahr = 0, ""
                if jahr_filter and d_jahr != jahr_filter:
                    continue
                if monat_filter and d_monat != monat_filter:
                    continue
                dateien.append(d)
        else:
            dateien = alle_dateien

        is_stell = (kategorie == "Stellungnahmen")
        if is_stell:
            self._table.setColumnCount(7)
            self._table.setHorizontalHeaderLabels(["Dateiname", "Art", "Mitarbeiter", "Flugnummer", "Erstellt am", "Zuletzt geändert", "Typ"])
            self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
            try:
                alle_db = db_lade_alle()
                db_lookup = {os.path.basename(e.get("pfad_intern", "")): e for e in alle_db}
            except Exception:
                db_lookup = {}
        else:
            self._table.setColumnCount(3)
            self._table.setHorizontalHeaderLabels(["Dateiname", "Zuletzt geändert", "Typ"])
            self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            db_lookup = {}

        icon_map = {".docx": "📝", ".doc": "📝", ".pdf": "📕", ".txt": "📄"}
        self._table.setRowCount(len(dateien))
        for row, d in enumerate(dateien):
            ext = os.path.splitext(d["name"])[1].lower()
            self._table.setItem(row, 0, QTableWidgetItem(
                f"{icon_map.get(ext, '📄')}  {d['name']}"
            ))
            if is_stell:
                db_e = db_lookup.get(d["name"], {})
                self._table.setItem(row, 1, QTableWidgetItem(db_e.get("art_label", "—")))
                self._table.setItem(row, 2, QTableWidgetItem(db_e.get("mitarbeiter", "—")))
                fn = db_e.get("flugnummer", "") or "—"
                self._table.setItem(row, 3, QTableWidgetItem(fn))
                erstellt = db_e.get("erstellt_am", "") or "—"
                # Nur das Datum anzeigen (ohne Uhrzeit)
                self._table.setItem(row, 4, QTableWidgetItem(erstellt[:10] if erstellt != "—" else "—"))
                self._table.setItem(row, 5, QTableWidgetItem(d["geaendert"]))
                self._table.setItem(row, 6, QTableWidgetItem(ext.upper().lstrip(".")))
            else:
                self._table.setItem(row, 1, QTableWidgetItem(d["geaendert"]))
                self._table.setItem(row, 2, QTableWidgetItem(ext.upper().lstrip(".")))
        self._auswahl_geaendert()

    def _web_ansicht_oeffnen(self):
        """Öffnet die lokale Web-Ansicht im Standard-Browser."""
        try:
            from functions.stellungnahmen_html_export import generiere_html, html_pfad
            generiere_html()
            pfad = html_pfad()
            url = "file:///" + pfad.replace("\\", "/")
            webbrowser.open(url)
        except Exception as exc:
            QMessageBox.warning(self, "Web-Ansicht", f"Fehler beim Öffnen der Web-Ansicht:\n{exc}")

    # ── Datenbank-Browser ─────────────────────────────────────────────────────

    def _on_tab_changed(self, idx: int):
        if idx == 1:
            self._db_jahre_aktualisieren()
            self._db_lade()
        elif idx == 2:
            self._versp_jahre_aktualisieren()
            self._versp_lade()
        elif idx == 3:
            self._psa_jahre_aktualisieren()
            self._psa_lade()

    def _db_jahre_aktualisieren(self):
        """Jahr-Combobox mit vorhandenen Werten aus der DB befüllen."""
        current = self._db_combo_jahr.currentData()
        self._db_combo_jahr.blockSignals(True)
        self._db_combo_jahr.clear()
        self._db_combo_jahr.addItem("Alle", None)
        for j in db_jahre():
            self._db_combo_jahr.addItem(str(j), j)
        for i in range(self._db_combo_jahr.count()):
            if self._db_combo_jahr.itemData(i) == current:
                self._db_combo_jahr.setCurrentIndex(i)
                break
        self._db_combo_jahr.blockSignals(False)

    def _db_filter_reset(self):
        self._db_combo_jahr.blockSignals(True)
        self._db_combo_monat.blockSignals(True)
        self._db_combo_art.blockSignals(True)
        self._db_suche.blockSignals(True)
        self._db_combo_jahr.setCurrentIndex(0)
        self._db_combo_monat.setCurrentIndex(0)
        self._db_combo_art.setCurrentIndex(0)
        self._db_suche.clear()
        self._db_combo_jahr.blockSignals(False)
        self._db_combo_monat.blockSignals(False)
        self._db_combo_art.blockSignals(False)
        self._db_suche.blockSignals(False)
        self._db_lade()

    def _db_filter_changed(self):
        self._db_lade()

    def _db_lade(self):
        """Datenbank abfragen und Tabelle befüllen."""
        jahr   = self._db_combo_jahr.currentData()
        monat  = self._db_combo_monat.currentData()
        art    = self._db_combo_art.currentData()
        suche  = self._db_suche.text().strip() or None

        try:
            eintraege = db_lade_alle(monat=monat, jahr=jahr, art=art, suchtext=suche)
        except Exception as exc:
            QMessageBox.critical(self, "Datenbankfehler", str(exc))
            return

        self._db_table.setRowCount(len(eintraege))
        self._db_eintraege = eintraege
        for row, e in enumerate(eintraege):
            self._db_table.setItem(row, 0, QTableWidgetItem(e.get("datum_vorfall", "")))
            self._db_table.setItem(row, 1, QTableWidgetItem(e.get("mitarbeiter", "")))
            self._db_table.setItem(row, 2, QTableWidgetItem(e.get("art_label", "")))
            fn = e.get("flugnummer", "")
            self._db_table.setItem(row, 3, QTableWidgetItem(fn if fn else "\u2014"))
            self._db_table.setItem(row, 4, QTableWidgetItem(e.get("verfasst_am", "")))
            erstellt = e.get("erstellt_am", "") or ""
            self._db_table.setItem(row, 5, QTableWidgetItem(erstellt[:10] if erstellt else "\u2014"))
            id_item = QTableWidgetItem(str(e.get("id", "")))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._db_table.setItem(row, 6, id_item)

        n = len(eintraege)
        self._db_treffer_lbl.setText(f"{n} Eintrag{'e' if n != 1 else ''} gefunden")
        self._db_auswahl_geaendert()

    def _db_auswahl_geaendert(self):
        hat_auswahl = bool(self._db_aktuell_eintrag())
        self._db_btn_oeffnen.setEnabled(hat_auswahl)
        self._db_btn_details.setEnabled(hat_auswahl)
        self._db_btn_loeschen.setEnabled(hat_auswahl)

    def _db_aktuell_eintrag(self) -> dict | None:
        rows = self._db_table.selectedItems()
        if not rows:
            return None
        row = self._db_table.currentRow()
        try:
            return self._db_eintraege[row]
        except (AttributeError, IndexError):
            return None

    def _db_dokument_oeffnen(self):
        e = self._db_aktuell_eintrag()
        if not e:
            return
        pfad = e.get("pfad_intern", "")
        if os.path.isfile(pfad):
            oeffne_datei(pfad)
        else:
            pfad_ext = e.get("pfad_extern", "")
            if os.path.isfile(pfad_ext):
                antwort = QMessageBox.question(
                    self, "Datei nicht gefunden",
                    f"Die interne Datei wurde nicht gefunden:\n{pfad}\n\n"
                    f"Soll stattdessen die externe Kopie ge\u00f6ffnet werden?\n{pfad_ext}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if antwort == QMessageBox.StandardButton.Yes:
                    oeffne_datei(pfad_ext)
            else:
                QMessageBox.warning(
                    self, "Datei nicht gefunden",
                    f"Das verkn\u00fcpfte Dokument wurde nicht gefunden:\n\n{pfad}\n\n"
                    "M\u00f6glicherweise wurde es verschoben oder gel\u00f6scht."
                )

    def _db_details_anzeigen(self):
        e = self._db_aktuell_eintrag()
        if not e:
            return
        _ART_MAP = {
            "flug": "\u2708\ufe0f Flug-Vorfall",
            "beschwerde": "\U0001f5e3\ufe0f Passagierbeschwerde",
            "nicht_mitgeflogen": "\U0001f6b6 Nicht mitgeflogen",
        }
        zeilen = [
            ("ID",               str(e.get("id", ""))),
            ("Erstellt am",      e.get("erstellt_am", "")),
            ("Datum Vorfall",    e.get("datum_vorfall", "")),
            ("Verfasst am",      e.get("verfasst_am", "")),
            ("Mitarbeiter",      e.get("mitarbeiter", "")),
            ("Art",              _ART_MAP.get(e.get("art", ""), e.get("art", ""))),
            ("Flugnummer",       e.get("flugnummer", "") or "\u2014"),
            ("Versp\u00e4tung",  "\u2705 Ja" if e.get("verspaetung") else "\u274c Nein"),
            ("Onblock",          e.get("onblock", "") or "\u2014"),
            ("Offblock",         e.get("offblock", "") or "\u2014"),
            ("Flugrichtung",     e.get("richtung", "") or "\u2014"),
            ("Ankunft LFZ",      e.get("ankunft_lfz", "") or "\u2014"),
            ("Auftragsende",     e.get("auftragsende", "") or "\u2014"),
            ("Paxannahme-Zeit",  e.get("paxannahme_zeit", "") or "\u2014"),
            ("Paxannahme-Ort",   e.get("paxannahme_ort", "") or "\u2014"),
            ("Sachverhalt",      e.get("sachverhalt", "") or "\u2014"),
            ("Beschwerde-Text",  e.get("beschwerde_text", "") or "\u2014"),
            ("Datei (intern)",   e.get("pfad_intern", "")),
            ("Datei (extern)",   e.get("pfad_extern", "") or "\u2014"),
        ]
        text = "\n".join(f"{k:<22} {v}" for k, v in zeilen)

        dlg = QDialog(self)
        dlg.setWindowTitle(
            f"\U0001f50e Details \u2013 {e.get('mitarbeiter', '')} ({e.get('datum_vorfall', '')})"
        )
        dlg.resize(700, 540)
        vl = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setFont(QFont("Courier New", 10))
        te.setPlainText(text)
        vl.addWidget(te)
        btns = QHBoxLayout()
        btn_oeffnen = _btn("\U0001f4c2  Dokument \u00f6ffnen", FIORI_BLUE)
        btn_oeffnen.clicked.connect(lambda: (dlg.accept(), self._db_dokument_oeffnen()))
        btns.addWidget(btn_oeffnen)
        btns.addStretch()
        close_btn = _btn_light("Schlie\u00dfen")
        close_btn.clicked.connect(dlg.accept)
        btns.addWidget(close_btn)
        vl.addLayout(btns)
        dlg.exec()

    def _db_eintrag_loeschen(self):
        e = self._db_aktuell_eintrag()
        if not e:
            return
        antwort = QMessageBox.question(
            self, "DB-Eintrag l\u00f6schen",
            f"Datensatz wirklich aus der Datenbank entfernen?\n\n"
            f"Mitarbeiter:  {e.get('mitarbeiter', '')}\n"
            f"Datum:         {e.get('datum_vorfall', '')}\n"
            f"Art:           {e.get('art_label', '')}\n\n"
            f"\u26a0 Das Word-Dokument wird NICHT gel\u00f6scht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            try:
                db_eintrag_loeschen(e["id"])
                self._db_lade()
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", str(exc))

    def _dokument_loeschen(self):
        eintrag = self._aktueller_eintrag()
        if not eintrag:
            return
        antwort = QMessageBox.question(
            self, "Dokument löschen",
            f"Dokument wirklich dauerhaft löschen?\n\n📄 {eintrag['name']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if antwort == QMessageBox.StandardButton.Yes:
            if loesche_dokument(eintrag["pfad"]):
                self.refresh()
            else:
                QMessageBox.warning(self, "Fehler", "Datei konnte nicht gelöscht werden.")

    def _dokument_umbenennen(self):
        eintrag = self._aktueller_eintrag()
        if not eintrag:
            return
        alter_name = eintrag["name"]
        neuer_name, ok = QInputDialog.getText(
            self, "Umbenennen", "Neuer Dateiname:",
            text=alter_name
        )
        if ok and neuer_name.strip() and neuer_name.strip() != alter_name:
            neuer_name = neuer_name.strip()
            if not any(neuer_name.lower().endswith(ext)
                       for ext in (".docx", ".doc", ".pdf", ".txt")):
                neuer_name += ".docx"
            try:
                umbenennen_dokument(eintrag["pfad"], neuer_name)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Fehler beim Umbenennen", str(e))
