# Changelog – Nesk3

Alle Änderungen in chronologischer Reihenfolge.

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
