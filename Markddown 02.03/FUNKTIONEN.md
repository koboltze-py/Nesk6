# Nesk3 – Vollständige Funktionsübersicht

**Stand:** 05.03.2026 – v3.2.x

---

## 1. Hauptfenster

### `gui/main_window.py` – `MainWindow`

| Index | Icon | Label |
|-------|------|-------|
| 0 | 🏠 | Dashboard |
| 1 | 👥 | Mitarbeiter |
| 2 | ☀️ | Aufgaben Tag |
| 3 | 🌙 | Aufgaben Nacht |
| 4 | 📅 | Dienstplan |
| 5 | 📋 | Übergabe |
| 6 | 🚗 | Fahrzeuge |
| 7 | 🕐 | Code 19 |
| 8 | 🖨️ | Ma. Ausdrucke |
| 9 | 🤒 | Krankmeldungen |
| 10 | 💾 | Backup |
| 11 | ⚙️ | Einstellungen |

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

### `functions/dienstplan_parser.py`
- `round_dispo=True/False`
- `parse()`: inkl. Krank-Klassifizierung und Dispo-Abschnitt-Tracking

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

Alle 5 SQLite-DBs liegen unter `database SQL/`. Alle nutzen WAL-Modus (`busy_timeout = 5 s`).

| Datei | Inhalt | Zugriff |
|-------|--------|---------|
| `nesk3.db` | Hauptdaten (Fahrzeuge, Übergabe, Einstellungen) | `database/connection.py` |
| `mitarbeiter.db` | Mitarbeiterstammdaten | `database/connection.py` |
| `stellungnahmen.db` | Stellungnahmen-Metadaten | `functions/stellungnahmen_db.py` |
| `verspaetungen.db` | Verspätungs-Protokolle | `functions/verspaetung_db.py` |
| `archiv.db` | Archiv-Daten | separat |

**`uebergabe_verspaetungen`** (in nesk3.db): Manuelle Verspätungseinträge je Protokoll

---

## 12. Backup-System

- `create_zip_backup()` → `Backup Data/Nesk3_backup_YYYYMMDD_HHMMSS.zip`
- `list_zip_backups()`, `restore_from_zip(zip_path)`
- Ausgeschlossen: `__pycache__`, `.git`, `Backup Data`, `backup`, `build_tmp`, `Exe`