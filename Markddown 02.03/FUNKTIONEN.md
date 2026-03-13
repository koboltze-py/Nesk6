# Nesk3 – Vollständige Funktionsübersicht

**Stand:** 12.03.2026 – v3.4.3 / Version 1.1

---

## 1. Hauptfenster

### `gui/main_window.py` – `MainWindow`

| Index | Icon | Label |
|-------|------|-------|
| 0 | 🏠 | Dashboard |
| 1 | 👥 | Mitarbeiter |
| 2 | ☕️ | Dienstliches |
| 3 | ☀️ | Aufgaben Tag |
| 4 | 🌙 | Aufgaben Nacht |
| 5 | 📅 | Dienstplan |
| 6 | 📋 | Übergabe |
| 7 | 🚗 | Fahrzeuge |
| 8 | 🕐 | Code 19 |
| 9 | 🖨️ | Ma. Ausdrucke |
| 10 | 🤒 | Krankmeldungen |
| 11 | 📞 | Telefonnummern |
| 12 | 💾 | Backup |
| 13 | ⚙️ | Einstellungen |

Alle Navigation-Refreshes über `QTimer.singleShot(0, fn)` – keine UI-Blockierung.

---

## 2. Mitarbeiter

### `gui/mitarbeiter.py` – `MitarbeiterKombiniertWidget`

- QTabWidget mit zwei Tabs:
  - **Tab 0 📄 Dokumente** – Lazy Loading (erst beim ersten Klick geladen)
  - **Tab 1 👥 Übersicht** – sofort geladen

### `MitarbeiterWidget` (Tab 1)
- Paginierte Tabelle: 50 Zeilen initial, „▼ Nächste X laden"-Button
- Async DB-Laden via `_LoadWorker(QThread)` – kein UI-Hängen
- Suche auf allen Daten (nicht nur angezeigten)
- CRUD: Neu anlegen, Bearbeiten, Löschen
- Import aus Dienstplan-Dateien
- DB: `database SQL/mitarbeiter.db`

---

## 3. Mitarbeiter-Dokumente

### `gui/mitarbeiter_dokumente.py` – `MitarbeiterDokumenteWidget`

**Aufbau:**
- Titelleiste (blau): „📂 Ordner öffnen" + „🔄 Refresh"
- Linke Sidebar: Kategorieliste mit Dateianzahl-Badge (Ausnahme: „Verspätung" ohne Zähler) + Vorlage-Status
- Rechter Bereich: QTabWidget
  - Tab 0 „📂 Dateien": Aktions-Buttons + Dateitabelle
  - Tab 1 „🔍 Datenbank-Suche": Filter + DB-Tabelle (nur bei Kategorie Stellungnahmen)
  - Tab 2 „⏰ Verspätungs-Protokoll": Filter + Tabelle (nur bei Kategorie Verspätung)

**Aktions-Buttons:**

| Button | Sichtbar | Funktion |
|--------|----------|----------|
| ＋ Neues Dokument | alle außer Verspätung | `_NeuesDokumentDialog` |
| 📝 Stellungnahme | nur Stellungnahmen | `_StellungnahmeDialog` |
| ⏰ Verspätung erfassen | nur Verspätung | `_VerspaetungDialog` |
| 📂 Öffnen | immer | OS-Standard |
| ✏ Bearbeiten | immer | `_DokumentBearbeitenDialog` |
| 🔤 Umbenennen | immer | `QInputDialog` |
| 🗑 Löschen | immer | dauerhaft mit Bestätigung |
| 🌐 Web-Ansicht | nur Stellungnahmen | Browser öffnet `stellungnahmen_lokal.html` |

**Dateitabelle – Spalten:**

| Kategorie | Spalten |
|-----------|---------|
| Alle anderen | Dateiname · Zuletzt geändert · Typ |
| Stellungnahmen | Dateiname · **Art** · **Mitarbeiter** · Zuletzt geändert · Typ |

**Rechtsklick-Menü:** Im Explorer anzeigen · Öffnen · *(Separator)* · Bearbeiten · Umbenennen · Löschen

**`_StellungnahmeDialog`:**
- Scrollbarer Dialog, kontextabhängige Felder je Art
- Pflichtvalidierung: Mitarbeiter, Flugnummer (bei Flug/NM), Sachverhalt

**DB-Browser:**
- Filter: Jahr-CB, Monat-CB, Art-CB, Freitext-QLineEdit
- Treffer-Label, Reset-Button
- Tabelle: Datum Vorfall, Mitarbeiter, Art, Flugnummer, Verfasst am, ID
- Doppelklick: Dokument öffnen
- Buttons: 📂 Dokument öffnen, 🔎 Details, 🗑 DB-Eintrag löschen

---

## 4. Verspätungs-Protokoll

### `gui/mitarbeiter_dokumente.py` – `_VerspaetungDialog`

| Feld | Beschreibung |
|------|--------------|
| Mitarbeiter | Freitext (Pflicht) |
| Datum | Datum des Dienstes (dd.MM.yyyy) |
| Dienstart | T · T10 · N · N10 |
| Dienstbeginn | Soll-Zeit (HH:MM) |
| Dienstantritt | Tatsächliche Ankunft (HH:MM) |
| Verspätung | Auto berechnet (readonly) |
| Begründung | Freitext |
| Aufgenommen von | Freitext |

Erstellt Word-Dokument + DB-Eintrag. Öffnen/Drucken auf Nachfrage.

### Verspätungs-Protokoll Tab
- Filter: Jahr, Monat, Freitext
- Tabelle: Datum · Mitarbeiter · Dienst · Dienstbeginn · Dienstantritt · Verspätung · Aufgenommen von · ID
- Buttons: Dokument öffnen · Bearbeiten · Per E-Mail senden · Löschen

### `functions/verspaetung_db.py`

| Funktion | Beschreibung |
|----------|--------------|
| `verspaetung_speichern(daten)` | Neuen Eintrag speichern → ID |
| `verspaetung_aktualisieren(id, daten)` | Eintrag aktualisieren |
| `verspaetung_loeschen(id)` | Eintrag löschen |
| `lade_verspaetungen(monat, jahr, suchtext)` | Gefilterte Abfrage |
| `lade_verspaetungen_fuer_datum(yyyy-MM-dd)` | Alle Einträge eines Tages |
| `verfuegbare_jahre()` | Jahre mit Einträgen |

---

## 5. `functions/mitarbeiter_dokumente_functions.py`

| Symbol | Beschreibung |
|--------|-------------|
| `VORLAGE_PFAD` | Pfad zur DRK-Kopf-/Fußzeile-Vorlage |
| `DOKUMENTE_BASIS` | `Daten/Mitarbeiterdokumente/` |
| `STELLUNGNAHMEN_EXTERN_PFAD` | `...\97_Stellungnahmen\` |
| `KATEGORIEN` | Liste der 6 Kategorien |
| `sicherungsordner()` | Legt Basis + Unterordner an |
| `lade_dokumente_nach_kategorie()` | `{kat: [{name, pfad, geaendert}]}` |
| `erstelle_dokument_aus_vorlage()` | Word-Dokument aus DRK-Vorlage |
| `erstelle_stellungnahme(daten)` | Word + DB-Eintrag → `(intern, extern)` |
| `oeffne_datei(pfad)` | Windows `start` |
| `loesche_dokument(pfad)` | Sicheres Löschen |
| `umbenennen_dokument(alt, neu)` | Umbenennen |

---

## 6. `functions/stellungnahmen_db.py`

| Funktion | Beschreibung |
|----------|-------------|
| `eintrag_speichern(daten, intern, extern)` | Neuen Datensatz anlegen → ID |
| `eintrag_loeschen(id)` | Datensatz entfernen (Datei bleibt) |
| `lade_alle(monat, jahr, art, suchtext)` | Gefilterte Abfrage |
| `verfuegbare_jahre()` | Jahre mit Einträgen (absteigend) |
| `verfuegbare_monate(jahr)` | Monate im Jahr mit Einträgen |
| `get_eintrag(id)` | Einzelnen Datensatz abrufen |

---

## 7. `functions/stellungnahmen_html_export.py`

| Funktion | Beschreibung |
|----------|-------------|
| `generiere_html()` | Liest DB, schreibt `WebNesk/stellungnahmen_lokal.html` |
| `html_pfad()` | Gibt absoluten Pfad der HTML-Datei zurück |

---

## 8. Dienstplan

### `gui/dienstplan.py` – `DienstplanWidget`
- Excel laden, farbcodierte HTML-Tabelle
- Statuszeile: Tagdienst/Nachtdienst/Krank, getrennt nach Betreuer/Dispo
- `_DispoZeitenVorschauDialog`: Vergleich Excel vs. Export, manuelle Bearbeitung
- **`_excel_open_btn`** in jedem Pane-Header: „📊 In Excel öffnen" (aktiv nach Laden)
  - `_open_in_excel()`: öffnet Datei mit Windows-Standard-App
- **Nach Stärkemeldungs-Export**: QMessageBox „Jetzt in Word öffnen?" + QFileDialog „Kopie speichern unter…" (`shutil.copy2`)

### `functions/dienstplan_parser.py`
- `round_dispo=True/False`
- `parse()`: inkl. Krank-Klassifizierung und Dispo-Abschnitt-Tracking
- PermissionError-Handling beim Dateiöffnen

---

## 9. Übergabe

### `gui/uebergabe.py` – `UebergabeWidget`
- Tagdienst/Nachtdienst-Button, automatische Zeiten
- Speichern · Abschließen · E-Mail-Entwurf · Löschen
- Sektion **Verspätete Mitarbeiter**:
  - Manuelle Zeilen (Name / Soll / Ist) · ➕ Hinzufügen
  - Schreibgeschützte Zeilen aus `verspaetungen.db` (blau, „📋 MA-Doku"-Badge)
- `_email_erstellen()`: Protokoll + Fahrzeuge + Schäden + Handys + Verspätete MA + Stellungnahmen-Link
  - Zeitraumfilter (Von/Bis) mit Overnight-Support (z. B. 19:00–07:00)
  - Folgetag + heutiges Datum werden zusätzlich aus `verspaetungen.db` geladen
  - Checkboxen je Verspätung; MA-Doku-Einträge mit 📋 markiert

**`uebergabe_verspaetungen`-Tabelle (nesk3.db):**
```sql
CREATE TABLE uebergabe_verspaetungen (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    protokoll_id INTEGER,
    mitarbeiter  TEXT,
    soll_zeit    TEXT,
    ist_zeit     TEXT
);
```

---

## 10. Fahrzeuge

### `gui/fahrzeuge.py` – `FahrzeugeWidget`
- Status-Tab: aktuell + Verlauf; `_StatusBearbeitenDialog` (Doppelklick oder ✏)
- Schäden-Tab, Termine-Tab, Historie-Tab

### `functions/fahrzeug_functions.py`
- `aktualisiere_status_eintrag(id, status, von, bis, grund)`
- `setze_fahrzeug_status()`, `lade_status_historie()`, `aktueller_status()`

---

## 11. Datenbank (SQLite)

Alle SQLite-DBs liegen unter `database SQL/`. Alle nutzen WAL-Modus (`busy_timeout = 5 s`).

| Datei | Inhalt | Zugriff |
|-------|--------|---------|
| `nesk3.db` | Hauptdaten (Fahrzeuge, Übergabe, Einstellungen, Patienten, Medikamente) | `database/connection.py` |
| `mitarbeiter.db` | Mitarbeiterstammdaten | `database/connection.py` |
| `stellungnahmen.db` | Stellungnahmen-Metadaten | `functions/stellungnahmen_db.py` |
| `verspaetungen.db` | Verspätungs-Protokolle | `functions/verspaetung_db.py` |
| `telefonnummern.db` | Telefonnummern-Verzeichnis | `functions/telefonnummern_db.py` |
| `archiv.db` | Archiv-Daten | separat |

**`uebergabe_verspaetungen`** (in nesk3.db): Manuelle Verspätungseinträge je Protokoll

**`medikamente`** (in nesk3.db): Medikamentengabe je Patienten-Protokoll
```sql
CREATE TABLE medikamente (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    patienten_id INTEGER REFERENCES patienten(id) ON DELETE CASCADE,
    medikament   TEXT,
    dosis        TEXT,
    applikation  TEXT
);
```

---

## 12. Backup-System

- `create_zip_backup()` → `Backup Data/Nesk3_backup_YYYYMMDD_HHMMSS.zip`
- `list_zip_backups()`, `restore_from_zip(zip_path)`
- Ausgeschlossen: `__pycache__`, `.git`, `Backup Data`, `backup`, `build_tmp`, `Exe`

---

## 13. Telefonnummern

### `gui/telefonnummern.py` – `TelefonnummernWidget`
- **4 Tabs**: 🔍 Alle · 📋 Kontakte · 🏪 Check-In (CIC) · 🚪 Interne & Gate
- **Aktionsleiste**: 📥 Excel neu einlesen · ＋ Neu · ✏ Bearbeiten · 🗑 Löschen · 📋 Nummer kopieren · Suchfeld
- **`_EintragDialog`**: Neu-Anlage und Bearbeiten; Bereich-/Kategorie-Dropdowns editierbar
- Manuell eingetragene Zeilen gelb hervorgehoben (`#fff8e1`)
- Auto-Import beim ersten Start oder bei veralteten Kategorienamen

### `functions/telefonnummern_db.py`
| Funktion | Beschreibung |
|----------|-------------|
| `importiere_aus_excel(clear_first)` | Importiert beide Excel-Dateien |
| `lade_telefonnummern(suchtext, kategorie, quelle, sheet)` | Gefiltertes SELECT |
| `lade_kategorien()` / `lade_sheets()` | Hilfsfunktionen |
| `ist_db_leer()` / `hat_veraltete_daten()` | Zustandsprüfung |
| `eintrag_speichern(daten)` | INSERT |
| `eintrag_aktualisieren(id, daten)` | UPDATE |
| `eintrag_loeschen(id)` | DELETE |

---

## 14. Dienstliches / Patienten Station

### `gui/dienstliches.py` – `DienstlichesWidget`

#### `_PatientenDialog` – 12 Abschnitte (v3.3.0+)
| Nr. | Inhalt |
|-----|--------|
| 1 | Zeit & Dauer (Von/Bis, Dauer auto) |
| 2 | Patient (Typ, Name, Abteilung, Alter, Geschlecht) |
| 3 | Ereignis (Was / Wie / Ort) |
| 4 | Beschwerdebild (Beschwerdeart, Symptome) |
| 5 | ABCDE-Schema (Airway / Breathing / Circulation / Disability / Exposure) |
| 6 | Monitoring (BZ / RR / SpO2 / HF) |
| 7 | Vorerkrankungen & Medikamente des Patienten |
| 8 | Behandlung (Diagnose, Maßnahmen) |
| 9 | Verbrauchsmaterial (Tabelle: Material / Menge / Einheit) |
| 10 | Arbeitsunfall / BG-Fall |
| 11 | Personal & Abschluss (DRK MA 1/2, Weitergeleitet an) |
| 12 | Bemerkung |

#### `_build_grp_medikamente()` – Medikamentengabe als Tabelle (v3.4.0)
- Tabelle mit Spalten: Medikament / Dosis / Applikation
- „➕ Medikament hinzufügen"-Button (blau)
- Methoden: `_medikament_hinzufuegen()`, `_aktualisiere_medikament_tabelle()`, `_medikament_entfernen()`
- Applikation als Dropdown: i.v. / i.m. / s.c. / p.o. / inhalativ / sublingual / topisch / nasal / rektal / sonstig

#### `_PatientenTab` – Übersichtstabelle
- 13 Spalten, BG-Fall-Zeilen rot hervorgehoben
- Buttons: `📋 Neu` · `✏ Bearbeiten` · `🗑 Löschen` · `📄 Word-Protokoll` · `📧 Per E-Mail senden`

#### `export_patient_word()`
- Erstellt `.docx` mit DRK-Logo, DRK-Rot/Blau-Formatierung
- Alle 11+1 Abschnitte + Medikamenten-Tabelle
- Speicherort: `Daten/Patienten Station/Protokolle/`

#### `_PatientenMailDialog`
- Outlook-Entwurf mit `.docx`-Anhang
- Vorausgefüllter Betreff und Body

#### DB-Schema (`nesk3.db` – Tabelle `patienten`)
- 35+ Felder; automatische Migration (ALTER TABLE) bei Versions-Update
- Verknüpft: `verbrauchsmaterial`, `medikamente` (CASCADE FK)

---

## 15. Sonderaufgaben (Aufgaben Nacht)

### `gui/sonderaufgaben.py` – `SonderaufgabenWidget(QWidget)`
_(eingebettet in `gui/aufgaben.py` – Aufgaben Nacht, Tab „Sonderaufgaben")_

#### Bulmor-Abschnitt (v3.4.0)
- Dropdowns: alle aktiven Fahrzeuge + **„a.D."** immer als letzte Option
- **Fahrzeugstatus-Spalte**: zeigt aktuellen Status je Bulmor-Fahrzeug
  - Farb-Badges: 🟢 fahrbereit · 🔴 defekt · 🟡 Werkstatt · ⚫ a.D.
  - Daten aus `fahrzeug_functions.lade_alle_fahrzeuge()`
  - Hilfsmethoden: `_bulmor_status_text()`, `_bulmor_status_style()`

#### Dienstplan-Integration (v3.4.0)
- **„📋 Dienstplan öffnen"-Button**: aktiv nach Laden eines Dienstplans
- Öffnet Excel-Dienstplandatei direkt in Excel
- `_dienstplan_pfad: str = ""` als neue Instanzvariable
- `_open_dienstplan_excel()` als neue Methode