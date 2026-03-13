# Changelog – Nesk3

Alle Änderungen in chronologischer Reihenfolge.

---

## 12.03.2026 – v3.4.3 / Version 1.1

### Übergabe – Verspätungen komplett überarbeitet

#### `gui/uebergabe.py`
- **Nachtdienst**: Vortag-Verspätungen werden nicht mehr automatisch angezeigt (weder im Formular noch in der E-Mail)
- **Blaue Einträge** aus Mitarbeiter-Dokumentation werden jetzt **immer** angezeigt – auch nach dem Speichern eines Protokolls
- **Manuell hinzufügen** (➕-Button) speichert den Eintrag direkt in `verspaetungen.db` mit vollständigem Datum
- **Datum-Feld** im manuellen Erfassungsdialog: Datum des Vorfalls auswählbar (Standard = Protokolldatum)
- **Sollzeit editierbar** mit oranger Warnmeldung wenn die Standardzeit abgeändert wird
- **Bugfix Dopplungen**: `db_eintraege` wird nach `(mitarbeiter, dienstbeginn)` dedupliziert
- **E-Mail**: Datum (📅 dd.MM.yyyy) wird bei jedem Verspätungseintrag angezeigt
- **E-Mail**: DB-Einträge bevorzugt (haben Datum), Legacy-Tupel nur als Fallback

### Backup-System

#### `main.py`
- **Neue Backup-Struktur**: Tages-Ordner `db_backups/YYYY-MM-DD/` statt flacher Dateiablage
- **Max. 5 Backups** je Datenbank pro Tag (automatische Bereinigung)
- **Max. 7 Tages-Ordner** – ältere Ordner werden beim App-Start automatisch gelöscht
- Alte flache Backup-Dateien in Tages-Ordner migriert

---

## 12.03.2026 – v3.4.2

### Übergabe – Verspätungs-Bugfixes & Verbesserungen

#### `gui/uebergabe.py`
- **Bugfix**: Vortag-Verspätungen beim Nachtdienst nach Speichern nicht mehr angezeigt → `protokoll_id is None`-Guard entfernt
- **Bugfix**: Auto-geladene Einträge (blaue Zeilen) wurden nicht persistiert → `_speichern()` speichert auch `_verspaetungen_db_entries`
- **Bugfix**: Duplikate nach Reload → Dedup via `saved_keys`-Set
- **E-Mail-Dialog**: Datum-von/bis-Filter für verspätete Mitarbeiter
- **„Aus Verspätungen wählen"**: letzte 7 Tage mit `[dd.MM.yyyy]`-Datum-Prefix

#### `gui/sonderaufgaben.py`
- **Bugfix**: `_combo_to_line()` war unreachable Code → als eigenständige Methode wiederhergestellt

#### `functions/verspaetung_db.py`
- **Neue Funktion** `lade_verspaetungen_letzter_zeitraum(tage=7)`

### Einsätze & Patienten DRK Station

#### `gui/dienstliches.py`
- **Sortierung**: Einsätze und Patienten jetzt aufsteigend (ASC) – neue Einträge am Ende
- **Keine Pflichtfelder**: Validierung in Einsatz-Dialog und Patienten-Dialog entfernt

---

## 11.03.2026 – v3.4.1

### Hilfe-Dialog: Live-Screenshot-Galerie + Benutzeranleitung

#### `gui/hilfe_dialog.py`
- **Neuer Tab "📸 Vorschau"**: 2-spaltige Kachelgalerie aller 14 App-Seiten
- **`_ScreenshotCard`**: Kachel mit Thumbnail (430×210 px), Hover-Highlight, Klick öffnet Vollbild
- **`_FullscreenPreview`**: modaler Vollbild-Dialog (maximierbar, dunkler Hintergrund)
- **Schaltfläche „Screenshots erstellen“**: durchläuft alle Seiten mit 300 ms/Seite, Fortschrittsanzeige
- Screenshots gespeichert in `Daten/Hilfe/screenshots/{idx:02d}.png`
- Platzhalter-Kacheln (Emoji) solange kein Bild vorhanden
- Status-Label: Anzahl vorhandener Screenshots + Speicherort

#### `gui/main_window.py`
- **`grab_all_screenshots(callback=None)`**: navigiert timer-basiert alle 14 Seiten durch, speichert `QStackedWidget.grab()` als PNG

#### `docs/BENUTZERANLEITUNG.md` _(neu)_
- Vollständige deutschsprachige Benutzeranleitung (17 Abschnitte)
- ASCII-UI-Mockups, Mermaid-Ablaufdiagramme, Tabellen
- Alle 14 Navigationsbereiche dokumentiert

---

## 11.03.2026 – v3.4.0

### Medikamentengabe als Tabelle, Sonderaufgaben-Erweiterungen, Dienstplan-Verbesserungen

#### `gui/dienstliches.py`
- **Medikamentengabe** komplett neu als Tabelle:
  - Neue DB-Tabelle `medikamente (id, patienten_id, medikament, dosis, applikation)` mit CASCADE-FK
  - Neue Funktion `lade_medikamente(patienten_id)`
  - `patient_speichern()` / `patient_aktualisieren()` speichern Medikamenteneinträge aus `daten["_medikamente"]`
  - `_build_grp_medikamente()`: neue Gruppe mit Tabelle (Medikament / Dosis / Applikation) und „➕ Medikament hinzufügen"-Button
  - `_medikament_hinzufuegen()`, `_aktualisiere_medikament_tabelle()`, `_medikament_entfernen()` als neue Methoden
  - `export_patient_word()`: neuer Parameter `medikamente`, Abschnitt 7 zeigt Medikamenten-Tabelle
  - `_word_protokoll()` / `_mail_protokoll()` laden und übergeben Medikamente

#### `gui/sonderaufgaben.py`
- **Bulmor-Dropdowns**: Option „a.D." immer verfügbar (auch ohne Dienstplan)
- **Fahrzeugstatus-Spalte**: jede Bulmor-Zeile zeigt aktuellen Status (fahrbereit/defekt/Werkstatt/a.D.) aus der Fahrzeug-DB mit Farb-Badge
- **„📋 Dienstplan öffnen"-Button**: nach Laden des Dienstplans wird Datei direkt in Excel geöffnet

#### `gui/dienstplan.py`
- **„📊 In Excel öffnen"-Button** in jedem Dienstplan-Pane-Header (aktiv nach Laden)
- **Nach Stärkemeldungs-Export**: Ja/Nein-Dialog „Jetzt in Word öffnen?" + „Kopie speichern unter…"-Dialog

---

## 11.03.2026 – v3.3.0

### Patienten DRK Station – vollständiges medizinisches Protokoll

#### `gui/dienstliches.py`
- **Erweitertes DB-Schema** mit 35+ Feldern + automatische Migration (ALTER TABLE)
- **`_PatientenDialog`** komplett neu: 12 Abschnitte
  - 1 │ Zeit & Dauer
  - 2 │ Patient (Typ: Fluggast / Mitarbeiter / Besucher / Handwerker / Sonstiges)
  - 3 │ Ereignis (Was / Wie / Ort)
  - 4 │ Beschwerdebild (Beschwerdeart, Symptome)
  - 5 │ ABCDE-Schema (Airway / Breathing / Circulation / Disability / Exposure)
  - 6 │ Monitoring (BZ / RR / SpO2 / HF)
  - 7 │ Vorerkrankungen & Medikamente des Patienten
  - 8 │ Behandlung (Diagnose, Maßnahmen, Medikamentengabe)
  - 9 │ Verbrauchsmaterial (Tabelle mit Material, Menge, Einheit)
  - 10 │ Arbeitsunfall / BG-Fall
  - 11 │ Personal & Abschluss (DRK MA 1/2, Weitergeleitet an)
  - 12 │ Bemerkung
- **`_PatientenTab`**: 13 Spalten, BG-Fall rot hervorgehoben
- **`export_patient_word()`**: Word-Protokoll (.docx) mit DRK-Logo, DRK-Rot/Blau-Formatierung
- **`_PatientenMailDialog`**: Outlook-Entwurf mit .docx-Anhang
- **Buttons**: `📄 Word-Protokoll` + `📧 Per E-Mail senden`
- **`_PATIENTEN_PROTO_DIR`**: `Daten/Patienten Station/Protokolle/`

#### `functions/dienstplan_parser.py`
- PermissionError-Fix beim Öffnen der Dienstplan-Excel-Datei

#### `gui/backup_widget.py` _(neu)_
- Backup-Widget für die GUI

---

## 08.03.2026 – v3.2.0

### Telefonnummern-Verzeichnis

- Neuer Sidebar-Button **📞 Telefonnummern** bei Index 11
- `gui/telefonnummern.py`: 4 Tabs (Alle / Kontakte / Check-In / Interne & Gate)
- `functions/telefonnummern_db.py`: SQLite-DB `database SQL/telefonnummern.db`, Import aus Excel
- Backup → 12, Einstellungen → 13

### PSA / Einsätze – Versendet-Tracking
- Spalte `gesendet` in `einsaetze` und `psa_verstoss`
- `markiere_einsatz_gesendet()` / `markiere_psa_gesendet()`

---

## 05.03.2026 – v3.2.x

### Performance-Fixes & Async Mitarbeiter-Laden

#### `gui/main_window.py`
- Alle Navigation-Refreshes über `QTimer.singleShot(0, fn)` → keine UI-Blockierung beim Klick

#### `gui/mitarbeiter.py` – `MitarbeiterWidget`
- `_LoadWorker(QThread)`: DB-Abfrage asynchron, kein `wait()` mehr
- DB-Timeout auf 3 s reduziert (`database/connection.py`)
- Pagination: nur 50 Zeilen werden initial gerendert; „▼ Nächste X laden"-Button
  - `_PAGE_SIZE = 50`, `_render_page()` statt `_render_table()`
  - Suche läuft auf allen Daten in `_alle`

#### `gui/mitarbeiter.py` – `MitarbeiterKombiniertWidget`
- Lazy Loading: `MitarbeiterDokumenteWidget` erst beim ersten Klick auf Tab 0 (Dokumente) laden
- Tab-Reihenfolge: **Tab 0 = 📄 Dokumente**, Tab 1 = 👥 Übersicht

---

### Mitarbeiter-Datenbank & Verwaltung

#### `fd9fb84` – Eigene `mitarbeiter.db`
- Neue SQLite-DB `database SQL/mitarbeiter.db`
- Tabelle `mitarbeiter`: id, name, kuerzel, funktion, export_flag

#### `a93f284` – Import aus Dienstplänen + CRUD
- `MitarbeiterWidget`: Laden aus Dienstplänen, vollständiges CRUD (Neu/Bearbeiten/Löschen)
- Import-Button scannt alle gespeicherten Dienstplan-Dateien

---

### Refactoring: Datenbanken konsolidiert

#### `dac3b9b` – Alle DBs nach `database SQL/`
- Alle 5 SQLite-Datenbanken liegen jetzt unter `database SQL/`:
  - `nesk3.db`, `mitarbeiter.db`, `stellungnahmen.db`, `verspaetungen.db`, `archiv.db`
- Einheitlicher Zugriffspfad, kein verstreuter DB-Speicher mehr

#### `464a8e7` – WAL-Modus für alle 5 SQLite-DBs
- `PRAGMA journal_mode = WAL; PRAGMA busy_timeout = 5000;` in allen `_connect()`-Funktionen
- Verhindert „database is locked"-Fehler bei parallelem Zugriff

---

### Verspätungs-Modul

#### `ccb363f` – Neues Verspätungs-Protokoll

##### `functions/verspaetung_db.py` (NEU)
- SQLite-DB `database SQL/verspaetungen.db`
- Tabelle `verspaetungen`: id, erstellt_am, mitarbeiter, datum (dd.MM.yyyy), dienst (T/T10/N/N10), dienstbeginn (HH:MM), dienstantritt (HH:MM), verspaetung_min, begruendung, aufgenommen_von, dokument_pfad
- CRUD: `verspaetung_speichern()`, `verspaetung_aktualisieren()`, `verspaetung_loeschen()`, `lade_verspaetungen()`, `verfuegbare_jahre()`
- **NEU 05.03:** `lade_verspaetungen_fuer_datum(yyyy-MM-dd)` mit korrektem `row_factory = sqlite3.Row`

##### `gui/mitarbeiter_dokumente.py` – `_VerspaetungDialog`
- Dialog: Mitarbeiter, Datum, Dienstart (T/T10/N/N10), Dienstbeginn/Dienstantritt, Verspätung (readonly, auto), Begründung, Aufgenommen von
- Erstellt Verspätungsdokument per `erstelle_verspaetungs_dokument()`
- Speichert in `verspaetungen.db`
- Tab „⏰ Verspätungs-Protokoll": Filter (Jahr/Monat/Suche), Tabelle, Aktionen (öffnen, bearbeiten, E-Mail senden, löschen)
- **UI-Fix:** Kategorie „Verspätung" zeigt keinen Datei-Zähler; „Neues Dokument"-Button bei Verspätung ausgeblendet

---

### Übergabe – Verspätungsanzeige

#### `ad7b8f7` – Verspätete Mitarbeiter in Übergabe
- Neue DB-Tabelle `uebergabe_verspaetungen` in `nesk3.db`
- Sektion im Formular: Name, Soll-Zeit, Ist-Zeit (editierbar, ➕ Button)
- E-Mail-Dialog: Zeitraumfilter (Von/Bis), Checkboxen je Verspätung → in Mail-Body

#### `252cfe9` – Verspätungen aus MA-Doku in Übergabe
- `_rebuild_verspaetungen_section()`: liest zusätzlich aus `verspaetungen.db` nach Protokoll-Datum
- Schreibgeschützte Zeilen (blau, „📋 MA-Doku"-Badge)
- `_add_verspaetung_db_row()`: Read-only-Widget für MA-Doku-Einträge
- `_vsp_label()` erkennt beide Dict-Formate (soll_zeit/ist_zeit vs. dienstbeginn/dienstantritt)

#### `77ca947` – Bugfix row_factory
- `lade_verspaetungen_fuer_datum()`: `conn.row_factory = sqlite3.Row` hinzugefügt (fehlte → silent TypeError)
- `refresh()` in `UebergabeWidget` baut Verspätungssektion neu auf → neue MA-Doku-Einträge sichtbar auf Tab-Wechsel

#### `6f881a1` – Overnight-Zeitfilter & Folgetag-Laden
- Zeitraumfilter erkennt Overnight-Dienste (19:00–07:00): `t_ist >= t_von OR t_ist <= t_bis`
- E-Mail-Dialog lädt Folgetag + heutiges Datum aus `verspaetungen.db` (Verspätungen nach Mitternacht)

---

## 02.03.2026 – v3.1.1

### Stellungnahmen Dateien-Tab: Art + Mitarbeiter Spalten

#### `_datei_filter_changed()` (gui/mitarbeiter_dokumente.py)
- Bei Kategorie „Stellungnahmen": Tabelle wechselt auf **5 Spalten**
  - `Dateiname | Art | Mitarbeiter | Zuletzt geändert | Typ`
- Art + Mitarbeiter werden per `db_lade_alle()` aus der SQLite-DB nachgeschlagen
  - Lookup-Key: Dateiname (`os.path.basename(pfad_intern)`)
  - Falls kein DB-Eintrag vorhanden: zeigt `—`
- Für alle anderen Kategorien bleiben 3 Spalten (`Dateiname | Zuletzt geändert | Typ`)
- Spaltenbreiten: Dateiname Stretch, alle anderen ResizeToContents

#### `_table_kontextmenu()` (gui/mitarbeiter_dokumente.py)
- Rechtsklick-Menü erweitert um (nach Separator):
  - `✏  Bearbeiten` → ruft `_dokument_bearbeiten()` auf
  - `🔤  Umbenennen` → ruft `_dokument_umbenennen()` auf
  - `🗑  Löschen` → ruft `_dokument_loeschen()` auf
- Zeile wird vor Menu-Öffnen via `setCurrentCell(row, 0)` selektiert

---

## 02.03.2026 – v3.1.0

### Stellungnahmen: Assistent + Datenbank + lokale Web-Ansicht

#### `_StellungnahmeDialog` (gui/mitarbeiter_dokumente.py)
- Kontextabhängiger Dialog mit 3 Vorfall-Typen:
  - **Flug-Vorfall**: Flugnummer, Verspätungs-CB → Onblock/Offblock, Richtung (Inbound/Outbound/Beides), Inbound-Zeiten (Ankunft LFZ, Auftragsende), Outbound-Zeiten (Paxannahme-Zeit + Ort), Sachverhalt
  - **Passagierbeschwerde**: Onblock, Offblock, Sachverhalt, Beschwerdetext
  - **Nicht mitgeflogen**: Flugnummer + Sachverhalt
- Pflichtfeld-Validierung vor Speichern
- Speichert in ZWEI Pfaden: intern (`Daten/Mitarbeiterdokumente/Stellungnahmen/`) + extern (`97_Stellungnahmen/`)
- Word-Dokument mit DRK-Kopf-/Fußzeile, formatierte Abschnitte je Typ

#### `functions/stellungnahmen_db.py`
- SQLite-DB: `Daten/Mitarbeiterdokumente/Datenbank/stellungnahmen.db`
- Speichert Metadaten (kein Word-Inhalt): Mitarbeiter, Datum, Art, Flugnummer, alle Zeitfelder, Sachverhalt, Dateipfade
- `lade_alle(monat, jahr, art, suchtext)`, `verfuegbare_jahre()`, `eintrag_speichern()`, `eintrag_loeschen()`
- Automatischer DB-Eintrag nach `erstelle_stellungnahme()`
- HTML-Ansicht wird automatisch nach Save/Delete regeneriert

#### DB-Browser Tab (gui/mitarbeiter_dokumente.py)
- Tab „🔍 Datenbank-Suche" – nur sichtbar bei Kategorie "Stellungnahmen"
- Filter: Jahr, Monat, Art, Freitext (Mitarbeiter/Flugnummer/Sachverhalt)
- Tabelle: Datum, Mitarbeiter, Art, Flugnummer, Verfasst am, ID
- Aktionen: Dokument öffnen (intern→extern Fallback), Details, DB-Eintrag löschen

#### Lokale Web-Ansicht (`WebNesk/stellungnahmen_lokal.html`)
- Statische HTML-Seite – läuft ohne Server direkt per `file://`
- Generiert von `functions/stellungnahmen_html_export.py`  
- Volltextsuche, Filter (Jahr/Monat/Art), Detailansicht aller Felder
- Dateipfad-Anzeige + Copy-to-Clipboard
- URL-Hash-Navigation: `#id-42` springt direkt zu Datensatz 42
- Button „🌐 Web-Ansicht" in der App öffnet Seite im Standardbrowser

#### Übergabe-E-Mail Erweiterung (gui/uebergabe.py)
- Neues Optionsfeld „📋 Stellungnahmen-Link anhängen"
  - Allgemeiner Link zur HTML-Seite (`file:///...stellungnahmen_lokal.html`)
  - Optional: Direktverweis auf Einzelfall (`...html#id-42`)
  - Auswahl-ComboBox mit den letzten 30 Stellungnahmen

---

## 02.03.2026 – v3.0.0

### Mitarbeiter-Dokumente Widget

#### gui/main_window.py
- `NAV_ITEMS`: `("👥", "Mitarbeiter", 1)` eingefügt, alle Folge-Indizes +1
- Import + Stack: `MitarbeiterDokumenteWidget` an Index 1

#### gui/mitarbeiter_dokumente.py
- `MitarbeiterDokumenteWidget`: Titelleiste, Kategorieliste (6 Kat.), Dateitabelle
- Buttons: ＋ Neues Dokument · 📝 Stellungnahme · 📂 Öffnen · ✏ Bearbeiten · 🔤 Umbenennen · 🗑 Löschen
- `_NeuesDokumentDialog`, `_DokumentBearbeitenDialog`, `_StellungnahmeDialog`

#### functions/mitarbeiter_dokumente_functions.py
- `STELLUNGNAHMEN_EXTERN_PFAD` → `../97_Stellungnahmen/`
- `erstelle_stellungnahme(daten)` → `(intern_pfad, extern_pfad)`
- `erstelle_dokument_aus_vorlage()`, `lade_dokumente_nach_kategorie()`

#### Fahrzeuge
- `aktualisiere_status_eintrag(id, status, von, bis, grund)` in fahrzeug_functions.py
- `_StatusBearbeitenDialog` + Doppelklick-Support in gui/fahrzeuge.py

#### Dienstplan
- `_DispoZeitenVorschauDialog`: 6-spaltig, manuell bearbeitbar
- `round_dispo=True/False` Parameter in DienstplanParser
- `manuell_geaendert`-Flag verhindert erneutes Runden beim Export

---

## 26.02.2026 – v2.9.x

| Version | Inhalt |
|---------|--------|
| v2.9.4 | Info-Boxen + Tooltips gesamte App, HilfeDialog (Module/Workflow/FAQ/Anleitungen) |
| v2.9.3 | HilfeDialog Animationen (Fade+Slide-In, Puls, Laufbanner) |
| v2.9.1/2 | Tooltips alle Module, HilfeDialog 4 Tabs |

---

## 26.02.2026 – v2.8

- Dashboard: `_SkyWidget` QPainter-Animation (~33 FPS)
- Code-19: `_PocketWatchWidget` Taschenuhr mit Echtzeit-Zeigern
- Aufgaben Nacht: Tab „📋 Code 19 Mail"
- Sonderaufgaben + Einstellungen: E-Mobby-Fahrerkennung und -Verwaltung

---

## 25.02.2026 – v2.7

- Backup: `backup_manager.py` – ZIP-Backup/Restore
- Dienstplan: Krank-Aufschlüsselung (Tag/Nacht/Sonder), Dispo-Abschnitt-Tracking
- Statuszeile: Betreuer/Dispo-Trennung nach Schichttyp

---

## Backups

| Datei | Datum | Größe |
|-------|-------|-------|
| `Nesk3_backup_20260305_065843.zip` | 05.03.2026 06:58 | 142,3 MB |
| `Nesk3_backup_20260302_170729.zip` | 02.03.2026 17:07 | ~10 MB |
| `Nesk3_backup_20260302_151916.zip` | 02.03.2026 15:19 | ~10 MB |
| `Nesk3_backup_20260302_150415.zip` | 02.03.2026 15:04 | ~10 MB |
| `Nesk3_backup_20260302_144548.zip` | 02.03.2026 14:45 | ~10 MB |
| `Nesk3_backup_20260225_222303.zip` | 25.02.2026 22:23 | 8,3 MB |
