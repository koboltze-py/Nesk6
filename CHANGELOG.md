# Changelog – Nesk3

Alle Änderungen in chronologischer Reihenfolge.  
Format: `[Datum] Beschreibung – betroffene Dateien`

---

## 14.03.2026 – v3.4.4

### Dienstplan – Word-Export bereinigt

#### `gui/dienstplan.py`
- **Doppeltes Speichern entfernt**: Der zweite „Kopie speichern unter…“-Dialog nach dem Export wurde entfernt
- **Speicherort-Button entfernt**: Der „Speicherort wählen…“-Button im Export-Dialog entfällt; der Datei-Speicherdialog öffnet sich jetzt direkt beim Klick auf „Exportieren“

#### `functions/staerkemeldung_export.py`
- Kleinere Anpassungen im Zuge des Export-Refactorings

---

## 12.03.2026 – v3.4.3 / Version 1.1

### Übergabe – Verspätungen komplett überarbeitet

#### `gui/uebergabe.py`
- **Nachtdienst**: Vortag-Verspätungen werden nicht mehr automatisch angezeigt (weder im Formular noch in der E-Mail)
- **Blaue Einträge** aus Mitarbeiter-Dokumentation werden jetzt **immer** angezeigt – auch nach dem Speichern eines Protokolls
- **Manuell hinzufügen** (➕-Button) speichert direkt in `verspaetungen.db` inkl. Datum-Feld
- **Datum-Feld** im Erfassungsdialog: Datum des Vorfalls auswählbar (Standard = Protokolldatum)
- **Sollzeit editierbar** mit oranger Warnmeldung bei manueller Änderung
- **Bugfix Dopplungen**: `db_eintraege` nach `(mitarbeiter, dienstbeginn)` dedupliziert
- **E-Mail**: Datum (📅 dd.MM.yyyy) pro Verspätungseintrag in der E-Mail
- **E-Mail**: DB-Einträge werden bevorzugt (haben Datum), Legacy-Tupel nur als Fallback

### Backup-System

#### `main.py`
- **Neue Backup-Struktur**: Tages-Ordner `db_backups/YYYY-MM-DD/` statt flacher Dateiablage
- **Max. 5 Backups** je Datenbank pro Tag (automatische Bereinigung)
- **Max. 7 Tages-Ordner** – ältere Ordner beim App-Start automatisch gelöscht

---

## 12.03.2026 – v3.4.2

### Übergabe – Verspätungs-Bugfixes & Verbesserungen

#### `gui/uebergabe.py`
- **Bugfix**: Auto-geladene Vortag-Verspätungen beim Nachtdienst wurden nach Speichern nicht mehr angezeigt → `protokoll_id is None`-Guard entfernt; Vortag wird immer geladen
- **Bugfix**: Automatisch angezeigte blaue Einträge wurden nicht in `uebergabe_verspaetungen` gespeichert → `_speichern()` persistiert jetzt auch `_verspaetungen_db_entries`
- **Bugfix**: Duplikate nach Reload → Dedup-Logik via `saved_keys`-Set
- **E-Mail-Dialog**: Datum-von/bis-Filter (`QDateEdit`) für verspätete Mitarbeiter; Default Tagdienst=heute, Nachtdienst=Vortag→heute
- **„Aus Verspätungen wählen"**: letzte 7 Tage mit `[dd.MM.yyyy]`-Datum-Prefix

#### `gui/sonderaufgaben.py`
- **Bugfix**: `_combo_to_line()` war unreachable Code hinter `return` von `_bulmor_status_style` → als eigenständige Methode wiederhergestellt; Namen aus ComboBoxen werden korrekt auf Vorlage übertragen

#### `functions/verspaetung_db.py`
- **Neue Funktion** `lade_verspaetungen_letzter_zeitraum(tage: int = 7)`: lädt alle Verspätungseinträge der letzten N Tage (Dedup, sortiert neueste zuerst)

### Einsätze & Patienten DRK Station

#### `gui/dienstliches.py`
- **Sortierung Einsätze**: von `DESC` auf `ASC` → neue Einträge werden am Ende der Liste angereiht
- **Sortierung Patienten**: gleiches Prinzip – chronologisch aufsteigend
- **Keine Pflichtfelder**: Validierung im Einsatz-Dialog (`_on_accept`) und Patienten-Dialog (`_validate`) entfernt – alle Felder optional

---

## 11.03.2026 – v3.4.1

### Hilfe-Dialog: Live-Screenshot-Galerie + Benutzeranleitung

#### `gui/hilfe_dialog.py`
- **Neuer Tab "📸 Vorschau"**: 2-spaltige Kachelgalerie aller 14 App-Seiten als Screenshots
- **`_ScreenshotCard`**: Kachel mit Thumbnail (430×210 px), Hover-Highlight, Klick öffnet Vollbild
- **`_FullscreenPreview`**: Modaler Vollbild-Dialog (maximierbar, Scrollbar, dunkler Hintergrund)
- **Schaltfläche „Screenshots erstellen / aktualisieren“**: durchläuft alle Seiten, zeigt Fortschritt
- Screenshots werden in `Daten/Hilfe/screenshots/{idx:02d}.png` gespeichert
- Status-Label: zeigt Anzahl vorhandener Screenshots und Speicherpfad
- Platzhalter-Kacheln (Emoji) wenn noch kein Bild vorhanden

#### `gui/main_window.py`
- **`grab_all_screenshots(callback=None)`**: Neue Methode navigt timer-basiert (300 ms/Seite) alle 14 Seiten durch, speichert `QStackedWidget.grab()` als PNG, ruft danach `callback(paths)` auf

#### `docs/BENUTZERANLEITUNG.md` _(neu)_
- Vollständige deutschsprachige Benutzeranleitung (17 Abschnitte)
- ASCII-UI-Mockups aller Module, Mermaid-Ablaufdiagramme, Tabellen
- Abdeckung: alle 14 nav-Bereiche inkl. Tagesausweis-Panel, ABCDE-Schema, Backup-Typen

---

## 11.03.2026 – v3.4.0

### Medikamentengabe als Tabelle, Sonderaufgaben-Erweiterungen, Dienstplan-Verbesserungen

#### `gui/dienstliches.py`
- **Medikamentengabe** komplett neu als Tabelle (wie Verbrauchsmaterial):
  - Neue DB-Tabelle `medikamente (id, patienten_id, medikament, dosis, applikation)` mit CASCADE-FK
  - Neue Funktion `lade_medikamente(patienten_id)`
  - `patient_speichern()` / `patient_aktualisieren()` speichern Medikamenteneinträge aus `daten["_medikamente"]`
  - `_build_grp_medikamente()`: neue Gruppe mit Tabelle (Medikament / Dosis / Applikation) und „➕ Medikament hinzufügen"-Button
  - `_medikament_hinzufuegen()`, `_aktualisiere_medikament_tabelle()`, `_medikament_entfernen()` als neue Methoden
  - `_befuellen()` lädt beim Bearbeiten Medikamente aus DB
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
- **Erweitertes DB-Schema** mit 35+ Feldern + automatische Migration (ALTER TABLE) bestehender Datenbanken
- **`_PatientenDialog`** komplett neu: 12 Abschnitte
  - 1 │ Zeit & Dauer
  - 2 │ Patient (Typ: Fluggast / Mitarbeiter / Besucher / Handwerker / Sonstiges, Abteilung, Name, Alter, Geschlecht)
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
- **`export_patient_word()`**: Erstellt formatiertes Word-Protokoll (.docx) mit DRK-Logo, DRK-Rot/Blau-Formatierung, allen 11 Abschnitten
- **`_PatientenMailDialog`**: Outlook-Entwurf mit .docx-Anhang, vorausgefüllter Betreff/Body
- **Buttons in `_PatientenTab`**: `📄 Word-Protokoll` + `📧 Per E-Mail senden`
- **`_PATIENTEN_PROTO_DIR`**: Speicherort `Daten/Patienten Station/Protokolle/`

#### `functions/dienstplan_parser.py`
- PermissionError-Fix beim Öffnen der Dienstplan-Excel-Datei

#### `gui/backup_widget.py` _(neu)_
- Backup-Widget für die GUI

#### `.gitignore`
- `demo/`, `Daten/Patienten Station/`, `Daten/Einsatz/Protokolle/`, `Daten/AOCC/*.xlsm`, `build_log.txt` aus Tracking ausgeschlossen

---

## 08.03.2026 – v3.2.0

### Telefonnummern-Verzeichnis (neues Modul)

Neuer Sidebar-Button **📞 Telefonnummern** bei Index 11.  
Liest Excel-Dateien aus `Daten/Telefonnummern/` in eine SQLite-Datenbank ein und stellt sie in einer tab-basierten GUI dar.

#### `functions/telefonnummern_db.py` _(neu)_
- SQLite-Datenbank `database SQL/telefonnummern.db` (WAL-Modus)
- Tabellen: `telefonnummern` (id, erstellt_am, quelle, sheet, kategorie, bezeichnung, nummer, email, bemerkung), `tel_import_log`
- `_CAT_NORMIERUNG`: Normalisiert rohe Excel-Spaltennamen auf saubere Kategorienamen
  - z.B. `"Check In Nummern (02203 40-)"` → `"Check In B"`, `"Checkin C"` → `"Check In C"` usw.
- `_parse_kontaktliste()`: Parst Kontaktsheets (Abt/Name/Tel/E-Mail-Format)
- `_parse_grid_sheet()`: Parst Raster-Sheets (CIC, int Gate) mit Kategorienormalisierung
- `importiere_aus_excel(clear_first=True)`: Importiert beide Excel-Dateien, gibt Anzahl zurück
- `lade_telefonnummern(suchtext, kategorie, quelle, sheet)`: Gefiltertes SELECT
- `lade_kategorien()`, `lade_sheets()`, `letzter_import()`: Hilfsfunktionen
- `ist_db_leer()`, `hat_veraltete_daten()`: Zustandsprüfung (triggert Auto-Reimport)
- `eintrag_speichern(daten)`: INSERT
- `eintrag_aktualisieren(entry_id, daten)`: UPDATE
- `eintrag_loeschen(entry_id)`: DELETE

#### `gui/telefonnummern.py` _(neu)_
- **4 Tabs**: 🔍 Alle · 📋 Kontakte · 🏪 Check-In (CIC) · 🚪 Interne & Gate
- **Aktionsleiste**: 📥 Excel neu einlesen · ＋ Neu · ✏ Bearbeiten · 🗑 Löschen · 📋 Nummer kopieren · Suchfeld
- **`_EintragDialog`**: Funktioniert für Neu-Anlage und Bearbeiten
  - Bereich-Dropdown (`QComboBox`, editierbar): alle vorhandenen Sheets
  - Kategorie-Dropdown (`QComboBox`, editierbar): Kategorien des gewählten Bereichs zuerst → logisches Einsortieren neuer Einträge
  - Bearbeiten-Modus füllt alle Felder vor
- Manuell eingetragene Zeilen gelb hervorgehoben (`#fff8e1`)
- Doppelklick auf Zeile öffnet Bearbeiten-Dialog
- Auto-Import beim ersten Start oder wenn veraltete Kategorienamen erkannt werden

#### `gui/main_window.py`
- `TelefonnummernWidget` eingehängt bei Index 11
- Backup → 12, Einstellungen → 13

---

### PSA / Einsätze – Versendet-Tracking

#### `functions/psa_db.py`
- Spalte `gesendet` in Tabelle `psa_verstoss` ergänzt
- `markiere_psa_gesendet(entry_id)`: Setzt `gesendet=1` + Zeitstempel

#### `gui/dienstliches.py`
- Spalte `gesendet` in Tabelle `einsaetze` ergänzt
- `markiere_einsatz_gesendet(entry_id)`: Setzt `gesendet=1` + Zeitstempel
- PSA-Tabelle: neue Spalte „Versendet" sichtbar
- Einsatz-Tabelle: neue Spalte „Versendet" sichtbar

#### `gui/uebergabe.py`
- PSA-Verstöße werden im Übergabe-E-Mail-Dialog angezeigt (eigener Abschnitt)
- Nach Versand: `markiere_psa_gesendet()` / `markiere_einsatz_gesendet()` wird aufgerufen

#### `gui/mitarbeiter_dokumente.py` / `functions/mitarbeiter_dokumente_functions.py`
- Kleinere Anpassungen im Zusammenhang mit PSA-Tracking

---



### WAL-Modus für alle Datenbanken

Alle 5 SQLite-Datenbanken heizen jetzt `WAL` + `synchronous=NORMAL` + `busy_timeout=5000ms`.

| DB | Datei | WAL vorher | WAL jetzt |
|---|---|---|---|
| `nesk3.db` | `database/connection.py` | ✅ | ✅ |
| `archiv.db` | `functions/archiv_functions.py` | ✅ | ✅ |
| `stellungnahmen.db` | `functions/stellungnahmen_db.py` | ❌ | ✅ |
| `einsaetze.db` | `gui/dienstliches.py` | ❌ | ✅ |
| `verspaetungen.db` | `functions/verspaetung_db.py` | ❌ | ✅ |

- **`functions/stellungnahmen_db.py`**: `_ensured_db()` + `_db()` – WAL-Pragmas ergänzt
- **`gui/dienstliches.py`**: `_ensured_db()` + `_db()` – WAL-Pragmas ergänzt
- **`functions/verspaetung_db.py`**: neue `_connect()`-Hilfsfunktion mit WAL; alle `sqlite3.connect`-Aufrufe ersetzt
- Backup vor Änderung: `Backup Data/db_backups/pre_wal_<ts>/`

---

## 05.03.2026 – v3.1.0

### Datenbank-Konsolidierung: alle DBs in `database SQL/`

Alle 5 SQLite-Datenbanken liegen jetzt im zentralen Ordner `database SQL/`.

| DB-Datei | Vorher | Jetzt |
|---|---|---|
| `nesk3.db` | `database SQL/` | `database SQL/` _(unverändert)_ |
| `archiv.db` | `database SQL/` | `database SQL/` _(unverändert)_ |
| `stellungnahmen.db` | `Daten/Mitarbeiterdokumente/Datenbank/` | `database SQL/` |
| `einsaetze.db` | `Daten/Einsatz/` | `database SQL/` |
| `verspaetungen.db` | `Daten/Spät/` | `database SQL/` |

- **`functions/stellungnahmen_db.py`**: `DB_ORDNER` → `database SQL`
- **`gui/dienstliches.py`**: `_EINSATZ_DB_DIR` → `database SQL`; `_PROTOKOLL_DIR` (Excel-Exporte) bleibt in `Daten/Einsatz/Protokolle/`
- **`functions/verspaetung_db.py`**: `_DB_PFAD` → `database SQL/verspaetungen.db`
- Bestehende DB-Dateien physisch verschoben; Backup in `Backup Data/db_backups/pre_consolidation_<ts>/`

---

## 03.03.2026 – v3.0.0

### Verspätungs-Modul (Unpünktlicher Dienstantritt)

Neue Kategorie **„Verspätung"** in Mitarbeiterdokumente ersetzt „Lob & Anerkennung".

#### Datenbank & Dokumentenerstellung
- **`functions/mitarbeiter_dokumente_functions.py`**: Kategorie umbenannt
- **`functions/verspaetung_db.py`** _(neu)_: SQLite-Protokoll (`verspaetungen.db`) mit allen Feldern (Mitarbeiter, Datum, Dienst, Dienstbeginn, Dienstantritt, Verspätung Min., Begründung, Aufgenommen von, Dokument-Pfad)
- **`functions/verspaetung_functions.py`** _(neu)_: Füllt Word-Vorlage `FO_CGN_27_Unpünktlicher Dienstantritt.docx`, speichert in `Daten/Spät/Protokoll/`

#### GUI – `gui/mitarbeiter_dokumente.py`
- Neue Klasse `_VerspaetungDialog`: Dienst-Dropdown (T/T10/N/N10), Mitarbeiter, Datum, Auto-Dienstbeginn, QTimeEdit für Antritt, Live-Verspätungsanzeige (rot/grün), Begründung, Aufgenommen von
- Button „⏰ Verspätung erfassen" (nur bei Kategorie Verspätung sichtbar)
- Tab „⏰ Verspätungs-Protokoll" mit Filterleiste (Jahr/Monat/Suche), 8-Spalten-Tabelle, CRUD-Aktionen, Öffnen, Bearbeiten, Löschen, Mail-Versand per Outlook-Entwurf

---

### Modul „Dienstliches" – Einsatzprotokoll

Neuer Sidebar-Button **„Dienstliches"** bei Index 2 (alle Folge-Indizes +1).

#### `gui/dienstliches.py` _(neu)_
- **Tab „🚑 Einsätze"** (`_EinsaetzeTab`): Einsatzprotokoll nach Vorlage FKB
  - SQLite `einsaetze.db` mit Feldern: Datum, Uhrzeit (Alarmierung), Dauer, Einsatzstichwort, Einsatzort, Einsatznr. DRK, MA 1/2, Angenommen J/N, Grund, Bemerkung
  - 6 Einsatzstichwörter: Intern 1, Intern 2, Chirurgisch 1, Chirurgisch 2, Sandienst, Pat. Station
  - Filter: Jahr, Monat, Freitext-Suche
  - Excel-Export (`openpyxl`) in `Daten/Einsatz/Protokolle/` mit Datumszeitraum-Dialog
  - E-Mail-Versand (Outlook-Entwurf mit Excel-Anhang)
- **Tab „📊 Übersicht"** (`_UebersichtTab`): KPI-Kacheln (Gesamt, Angenommen, Abgelehnt, Ø-Dauer), Monatstabelle, Stichwort-Ranking, Mitarbeiter-Tabelle

#### `gui/main_window.py`
- `DienstlichesWidget` bei Index 2 eingehängt; alle Folgeseiten Index +1

---

### Stellungnahmen-Fixes

- **`gui/mitarbeiter_dokumente.py`**: ON/Offblock-Felder für Passagierbeschwerde nicht mehr angezeigt
- **`gui/mitarbeiter_dokumente.py`**: Flugnummer ist optional bei Passagierbeschwerde
- **`gui/mitarbeiter_dokumente.py`**: Hauptübersicht zeigt nun Flugnummer + Erstellungsdatum

---

### HTML-Dienstplan-Ansicht

- **`functions/dienstplan_html_export.py`** _(neu)_: Generiert statische HTML nach `WebNesk/dienstplan_aktuell.html`
  - Tagdienst, Nachtdienst, Krank/Abwesend als Cards
  - Dispo/Betreuer-Unterkategorien pro Card
  - Responsiv, DRK-Farbschema, Live-Zeitstempel (JS)

---

## 26.02.2026 – v2.9.4

### Erklär-Boxen und Tooltips in der gesamten App

#### Mitarbeiter: Export-Info-Box
- **`gui/mitarbeiter.py`**
  - Gelbe Info-Box unter den Aktions-Buttons erklärt den Unterschied zwischen „ausschließen" (kein Export) und „löschen"
  - Text: „Export-Spalte (✅/🚫): Zeigt ob Mitarbeiter in Stärkemeldungs-Word erscheint – bleibt in der Datenbank"

#### Aufgaben Tag – Code 19: Zeitraum-Info-Box
- **`gui/aufgaben_tag.py`**
  - Blaue Info-Box im Zeitraum-Abschnitt erklärt welche Excel-Zeilen ausgelesen werden
  - Text: „Zeitraum: Legt fest welche Dienstplaneinträge aus der Excel in die E-Mail übernommen werden. Standard: letzte 7 Tage bis heute."

#### Übergabe: Button-Tooltips + Abschluss-Info-Box
- **`gui/uebergabe.py`**
  - Tooltip auf „💾 Speichern": „Protokoll zwischenspeichern – bleibt als 'offen' bearbeitbar"
  - Tooltip auf „✓ Abschließen": „Endgültig abschließen – kein Bearbeiten mehr möglich. Abzeichner-Name wird benötigt."
  - Tooltip auf „📧 E-Mail": „Erstellt einen Outlook-Entwurf mit den Protokolldaten"
  - Tooltip auf „🗑 Löschen": „Protokoll dauerhaft aus der Datenbank löschen (nicht wiederherstellbar)"
  - Blaue Info-Box unter den Buttons fasst Speichern / Abschließen / E-Mail zusammen

#### Einstellungen: E-Mobby Beschreibung erweitert
- **`gui/einstellungen.py`**
  - Beschreibungstext der E-Mobby-GroupBox präzisiert: „… in der Übergabe-Ansicht als E-Mobby-Fahrer markiert. Nur Nachnamen – Groß-/Kleinschreibung wird ignoriert."

### HilfeDialog stark erweitert (v2.9.1 → v2.9.3 → v2.9.4 kumuliert)
- **`gui/hilfe_dialog.py`**
  - Tab „📦 Module": Jedes Modul mit 6–11 detaillierten Bullet-Points und genauen Schaltflächennamen
  - Tab „🔄 Workflow": 8 Schritte (war 6), jeder mit ausführlicher Beschreibung + neuer „Sondersituationen"-Abschnitt (4 _TipCard's)
  - Tab „💡 Tipps & FAQ": 14 Tipps (war 8) + 5 FAQ-Einträge + Versionsinfo
  - **Neuer Tab „📖 Anleitungen"**: 5 vollständige Schritt-für-Schritt-Anleitungen mit je 6–7 _StepCard's

### Dienstplan: UI-Verbesserungen
- **`gui/dienstplan.py`**
  - Button-Text bei inaktivem Export: `'Hier klicken um Datei als Wordexport auszuwählen'`
  - Button-Text bei aktivem Export: `'✓  Für Wordexport gewählt'`
  - Info-Banner oben erklärt: „Bis zu 4 Dienstpläne gleichzeitig öffnen"
  - Stärkemeldungs-Dateiname: `Staerkemeldung` → `Stärkemeldung` (Umlaut korrigiert)

### Aufgaben Tag: Template- und Umbenennen-Info-Boxen
- **`gui/aufgaben_tag.py`** (bereits in v2.9.3 dokumentiert, hier nochmals gruppiert)
  - Blauer Info-Kasten nach Template-Buttons: erklärt Checklisten- und Checks-Template
  - Gelber Info-Kasten nach Umbenennen-Checkbox: erklärt `JJJJ_MM_TT`-Umbenennung

---

## 26.02.2026 – v2.9.3

### HilfeDialog: Animationen
- **`gui/hilfe_dialog.py`** – Komplett neu geschrieben mit Animationen:
  - Fade+Slide-In beim Tab-Wechsel (`QPropertyAnimation` auf Opacity + Geometry)
  - Puls-Icon auf dem Hilfe-Button (`QSequentialAnimationGroup`)
  - Laufbanner mit aktuellem Datum + Versionsnummer
  - Workflow-Progress-Bar mit Step-Navigation

---

## 26.02.2026 – v2.9.1 / v2.9.2

### Tooltips in der gesamten App
- **`gui/main_window.py`** – Hilfe-Button + alle Nav-Buttons mit Tooltip
- **`gui/dashboard.py`** – Statistik-Karten + Flugzeug-Widget mit Tooltip
- **`gui/dienstplan.py`** – Export-Button, Close-Button, Word-Export-Button, Reload-Button
- **`gui/einstellungen.py`** – Alle Browse-Buttons, E-Mobby Add/Remove, Protokoll-Buttons
- **`gui/fahrzeuge.py`** – Edit/Delete/Status/Schaden/Termin-Buttons
- **`gui/mitarbeiter.py`** – Ausschluss-Button, Refresh-Button
- **`gui/aufgaben_tag.py`** – Template-Buttons, Anhang-Buttons, Send-Buttons, Code19-Buttons
- **`gui/sonderaufgaben.py`** – Reload-Tree-Button
- **`gui/uebergabe.py`** – Protokoll-Buttons, Such- und Filter-Felder

### HilfeDialog (v2.9.2)
- **`gui/hilfe_dialog.py`** – Neues Hilfe-Fenster mit 4 Tabs:
  - 🏠 Übersicht, 📦 Module, 🔄 Workflow, 💡 Tipps
- **`gui/main_window.py`** – Hilfe-Button oben rechts in Sidebar

---

## 26.02.2026 – v2.8

### Code-19-Button: Uhr-Symbol
- **`gui/main_window.py`** – NAV_ITEMS Code-19-Eintrag: Icon von `\ufffd` (defekt) auf `🕐` geändert

### Dashboard: Animiertes Flugzeug-Widget
- **`gui/dashboard.py`**
  - Neue Klasse `_SkyWidget(QWidget)`: QPainter-Animation – Himmelsgradient, Wolken, Landebahn, fliegendes `✈`-Emoji (~33 FPS, QTimer 30ms)
  - Neue Klasse `FlugzeugWidget(QFrame)`: Klickbare Karte mit hochzählendem Verspätungs-Ticker (jede Sekunde), `QMessageBox` beim Klick
  - Import ergänzt: `QPainter, QLinearGradient, QColor, QEvent, QTimer, QMessageBox`

### Code-19-Seite: Alice-im-Wunderland Taschenuhr
- **`gui/code19.py`** – Komplett neu geschrieben
  - Neue Klasse `_PocketWatchWidget(QWidget)` (240×300 px):
    - `_swing_timer` (25 ms) → Pendelschwingung ±14° via `sin()`
    - `_tick_timer` (1000 ms) → Sekundenzeiger-Ticking + Blink-Punkt
    - `paintEvent`: Goldenes Gehäuse (Radial-Gradient), Kette, Krone, Zifferblatt, römische Ziffern (XII/III/VI/IX), Echtzeit-Uhrzeiger, roter Blink-Punkt
  - Titelleiste: `🕐 Code 19`; Zitat: „Ich bin spät! Ich bin spät!"

### Code-19-Mail Tab → Aufgaben Nacht
- **`gui/aufgaben.py`** – Import `_Code19MailTab` aus `aufgaben_tag.py` + Tab 4 „📋 Code 19 Mail" in Aufgaben Nacht

### Sonderaufgaben: E-Mobby Fahrer Erkennung
- **`functions/emobby_functions.py`** – Neue Datei:
  - `get_emobby_fahrer()`: Liest `Daten/E-Mobby/mobby.txt`, synct neue Namen in DB (`settings`-Tabelle, Key `emobby_fahrer`)
  - `is_emobby_fahrer(name)`: Case-insensiver Substring-Match gegen DB-Liste
  - `add_emobby_fahrer(name)`: Fügt Namen zur DB-JSON-Liste hinzu (Duplikat-Check)
- **`gui/sonderaufgaben.py`**
  - `_dienstplan_geladen: bool` Flag in `__init__` (wird nach Laden auf `True` gesetzt)
  - E-Mobby-Combo: Zeigt ⚠ Warnung in Orange wenn Dienstplan geladen aber kein Fahrer erkannt
  - Erfolgsdialog enthält jetzt E-Mobby-Anzahl pro Schicht
  - Dienstplan-Abgleich: `tag_emobby` / `nacht_emobby` via `is_emobby_fahrer()`

### Einstellungen: E-Mobby-Fahrer Verwaltung
- **`gui/einstellungen.py`**
  - `QListWidget` zu Imports ergänzt
  - Neue GroupBox „🛵 E-Mobby Fahrer" mit:
    - `QListWidget` zeigt aktuelle Einträge aus DB (33 Fahrer initial aus `mobby.txt`)
    - `QLineEdit` + „+ Hinzufügen" Button (auch Enter-Taste)
    - „🗑 Entfernen" Button für markierten Eintrag mit Bestätigungsdialog
    - Zähler-Label
  - Methoden: `_load_emobby_list()`, `_add_emobby_entry()`, `_remove_emobby_entry()`
  - `_load_settings()` ruft `_load_emobby_list()` auf

### Aufgaben Tag: Checklisten-Tab Symbol
- **`gui/aufgaben_tag.py`** – Tab-Titel `"📋 Checklisten"` (Encoding-Fehler behoben)

### Übergabe: Vereinfachung
- **`gui/uebergabe.py`**
  - Abschnitt „Personal im Dienst" komplett entfernt (Textfeld, Label, Formzeile)
  - Beginn/Ende werden beim Klick auf Tagdienst/Nachtdienst-Button automatisch befüllt: Tag 07:00–19:00, Nacht 19:00–07:00

---

## 25.02.2026


### Backup ZIP + Restore
- **`backup/backup_manager.py`**
  - Neue Funktion `create_zip_backup()`: Erstellt ZIP des gesamten Nesk3-Ordners unter `Backup Data/Nesk3_backup_YYYYMMDD_HHMMSS.zip`
  - Neue Funktion `list_zip_backups()`: Listet alle vorhandenen ZIP-Backups auf
  - Neue Funktion `restore_from_zip(zip_path)`: Stellt Dateien aus ZIP wieder her (ohne `Backup Data/` zu überschreiben)
  - Import von `shutil` und `zipfile` ergänzt

### Backup-Ausschlüsse erweitert

**Problem:** ZIP-Backup enthielt `build_tmp/` (65 MB) und `Exe/` (59 MB) → Backup wuchs auf >360 MB.

- **`backup/backup_manager.py`**
  - `_ZIP_EXCLUDE_DIRS` um `'build_tmp'` und `'Exe'` erweitert
  - Backup-Größe: ~360 MB → **8,3 MB**
  - Aktuellstes Backup: `Nesk3_backup_20260225_222303.zip` (8,3 MB)

---

### Krank-Aufschlüsselung nach Tagdienst / Nachtdienst / Sonderdienst

**Problem:** Alle kranken Mitarbeiter erschienen in einem einzigen undifferenzierten Abschnitt.  
**Lösung:** Klassifizierung anhand der Von/Bis-Zeiten aus der Excel-Datei.

- **`functions/dienstplan_parser.py`**
  - Neue Methode `_ermittle_krank_typ(start_zeit, end_zeit, vollname)`:
    - Leitet `krank_schicht_typ` (`'tagdienst'` / `'nachtdienst'` / `'sonderdienst'`) ab
    - Leitet `krank_ist_dispo` (bool) ab
    - Leitet `krank_abgeleiteter_dienst` (z.B. `'T'`, `'DT'`, `'N'`, `'DN(?)') ab
    - Exakte Zeitbereiche: 06:00–18:00 → T, 07:00–19:00 → DT, 18:00–06:00 → N, 19:00–07:00 → DN usw.
    - Fallback: `T(?)`, `N(?)`, `S(?)` wenn kein exakter Treffer
  - Return-Dict um 3 Felder erweitert: `krank_schicht_typ`, `krank_ist_dispo`, `krank_abgeleiteter_dienst`

- **`gui/dienstplan.py`**
  - `_TAG_DIENSTE` um `T8` erweitert
  - `_render_table_parsed()` komplett überarbeitet:
    - 5 Krank-Listen je Typ: `krank_tag_dispo`, `krank_tag_betr`, `krank_nacht_dispo`, `krank_nacht_betr`, `krank_sonder`
    - 3 neue Tabellenabschnitte: „Krank – Tagdienst", „Krank – Nachtdienst", „Krank – Sonderdienst"
    - Neue Farbe `KrankDispo` (`#f0d0d0` / `#7a0000`) für kranke Disponenten
    - Spalte 2 (Dienst) zeigt bei Kranken das abgeleitete Kürzel
    - Spalte 0 (Kategorie) zeigt `Dispo` oder `Betreuer` auch bei Kranken

---

### Dispo-Abschnitt aus Excel-Header erkennen

**Problem:** Lytek (23.02.2026) steht unter dem `Dispo`-Abschnittsheader in der Excel, hat aber Kürzel `Krank`. Er wurde fälschlicherweise als Betreuer-Krank klassifiziert.  
**Lösung:** Abschnitts-Tracking beim Zeileniterieren.

- **`functions/dienstplan_parser.py`**
  - Neue Methode `_detect_abschnitt_header(row_list)`:
    - Erkennt `Dispo`-Zeilen → gibt `'dispo'` zurück
    - Erkennt `[Stamm FH]`/`Stamm`/`Betreuer`-Zeilen → gibt `'betreuer'` zurück
    - Normale Datenzeilen (Name-Spalte befüllt) → gibt `None` zurück
  - `parse()`: Variable `aktueller_abschnitt` trackt den aktuellen Excel-Abschnitt
  - Personen im Dispo-Abschnitt: `ist_dispo=True` wird gesetzt (auch bei Krank)
  - Kranke Disponenten: `_betr_zu_dispo_kuerzel()` wandelt Kürzel um
  - Neue Modul-Funktion `_betr_zu_dispo_kuerzel(kuerzel)`: `N→DN`, `T→DT`, `T10→DT`, `N10→DN`

---

### Zeiten für Dispo-Krankmeldungen auf Stunde runden

**Problem:** CareMan exportiert Disponenten-Zeiten mit Minutenabweichungen (`07:15`, `19:45`), die für die Anzeige korrigiert werden sollen.

- **`functions/dienstplan_parser.py`**
  - Neue Modul-Funktion `_runde_auf_volle_stunde(zeit_str)`:
    - Setzt Minutenanteil auf `00`: `07:15` → `07:00`, `19:45` → `19:00`
    - Nur für kranke Disponenten (aus Abschnitt-Kontext) angewendet
    - Betreuer-Kranke behalten Originalzeiten

---

### Statuszeile: Dispo/Betreuer-Trennung in allen Blöcken

**Problem:** Statuszeile zeigte nur Gesamtzahlen ohne Unterscheidung nach Funktion.

- **`gui/dienstplan.py`**
  - Tagdienst-Zählung: `tag_dispo_n` + `tag_betr_n` getrennt
  - Nachtdienst-Zählung: `nacht_dispo_n` + `nacht_betr_n` getrennt
  - Krank-Block: Getrennte Betreuer/Dispo-Anzeige mit Tag/Nacht-Aufschlüsselung
  - **Ausgabeformat:**
    ```
    14 Tagdienst (Betreuer 11, Dispo 3)  |  8 Nachtdienst (Betreuer 6, Dispo 2)  |  9 Krank  –  Betreuer 8 (5 Tag / 2 Nacht / 1 Sonder) | Dispo 1 (1 Nacht)
    ```

---

## Vorherige Versionen

Ältere Änderungen (vor 25.02.2026) sind in den ZIP-Backups dokumentiert:

| Backup | Datum | Größe | Hinweis |
|---|---|---|---|
| `Nesk3_backup_20260225_222303.zip` | 25.02.2026 22:23 | 8,3 MB | aktuell |
| `Nesk3_backup_20260225_205927.zip` | 25.02.2026 20:59 | 8,3 MB | |
| `Nesk3_backup_20260225_205232.zip` | 25.02.2026 20:52 | 361 MB | alt (mit Exe) |
| `Nesk3_backup_20260225_204119.zip` | 25.02.2026 20:41 | 181 MB | alt |
| `Nesk3_backup_20260225_203321.zip` | 25.02.2026 20:33 | 90 MB | alt |
| `Nesk3_Backup_20260222_181824.zip` | 22.02.2026 18:18 | 8,3 MB | |
