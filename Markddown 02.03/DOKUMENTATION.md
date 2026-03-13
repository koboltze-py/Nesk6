# Nesk3 – Technische Dokumentation

**Stand:** 12.03.2026 – v3.4.3 / Version 1.1
**Anwendung:** Nesk3 – DRK Flughafen Köln/Bonn
**Zweck:** Dienstplan, Stärkemeldung, Mitarbeiterverwaltung, Mitarbeiter-Dokumente, Stellungnahmen-DB, Patienten-Protokoll, Telefonnummern, Hilfe-Screenshot-Galerie

---

## Inhaltsverzeichnis

1. [Projektstruktur](#1-projektstruktur)
2. [Backup-System](#2-backup-system)
3. [Dienstplan-Parser](#3-dienstplan-parser)
4. [Mitarbeiter-Dokumente](#4-mitarbeiter-dokumente)
5. [Stellungnahmen-System](#5-stellungnahmen-system)
6. [Lokale Web-Ansicht](#6-lokale-web-ansicht)
7. [Übergabe & E-Mail](#7-übergabe--e-mail)
8. [Telefonnummern-Verzeichnis](#8-telefonnummern-verzeichnis)
9. [Patienten Station](#9-patienten-station)
10. [Sonderaufgaben-Widget](#10-sonderaufgaben-widget)
11. [Bekannte Sonderfälle](#11-bekannte-sonderfälle)

---

## 1. Projektstruktur

```
Nesk3/
├── main.py
├── config.py
├── gui/
│   ├── main_window.py               # Hauptfenster, 14 Nav-Einträge (0–13)
│   ├── dienstliches.py              # Patienten-Station, Einsätze, PSA
│   ├── telefonnummern.py            # Telefonnummern-Verzeichnis (v3.2.0+)
│   ├── mitarbeiter_dokumente.py     # Mitarbeiter-Dokumente + Stellungnahmen + DB-Browser
│   ├── uebergabe.py                 # Übergabe + E-Mail (inkl. Stellungnahmen-Link)
│   ├── sonderaufgaben.py            # Sonderaufgaben-Formular (Bulmor, E-Moby etc.)
│   └── ...
├── functions/
│   ├── mitarbeiter_dokumente_functions.py  # Word-Erstellung, STELLUNGNAHMEN_EXTERN_PFAD
│   ├── stellungnahmen_db.py                # SQLite-Datenbank für Stellungnahmen
│   ├── stellungnahmen_html_export.py       # HTML-Generator für Web-Ansicht
│   ├── telefonnummern_db.py               # SQLite-Datenbank für Telefonnummern
│   └── ...
├── WebNesk/
│   ├── stellungnahmen_lokal.html    # Lokale Web-Ansicht (kein Server nötig)
│   └── ...
└── Daten/
    ├── Mitarbeiterdokumente/
    │   ├── Stellungnahmen/
    │   ├── Datenbank/
    │   │   └── stellungnahmen.db
    │   └── ...
    └── Patienten Station/
        └── Protokolle/              # Exportierte Word-Protokolle
```

---

## 2. Backup-System

### ZIP-Backup (manuell)
- `create_zip_backup()` → `Backup Data/Nesk3_backup_YYYYMMDD_HHMMSS.zip`
- Ausschlüsse: `__pycache__`, `.git`, `Backup Data`, `backup`, `build_tmp`, `Exe`
- Größe: ~8–12 MB

### DB-Auto-Backup (App-Start)
- Funktion: `_db_startup_backup()` in `main.py`
- Zielordner: `database SQL/Backup Data/db_backups/YYYY-MM-DD/`
- Dateinamen: `<datenbankname>_HHMMSS.db`
- **Max. 5 Backups** je Datenbank pro Tag (älteste werden automatisch gelöscht)
- **Max. 7 Tages-Ordner** – überschüssige Ordner werden beim App-Start gelöscht

---

## 3. Dienstplan-Parser

### `functions/dienstplan_parser.py`

- `round_dispo=True` (Standard): Zeiten auf volle Stunden runden
- `round_dispo=False`: Rohdaten (Vergleichs-Popup)
- `_ermittle_krank_typ()`: Tag/Nacht/Sonder nach Von–Bis-Zeiten

| Von–Bis | Typ |
|---------|-----|
| 06:00–18:00 | Tagdienst (T) |
| 07:00–19:00 | Tagdienst Dispo (DT) |
| 18:00–06:00 | Nachtdienst (N) |
| 19:00–07:00 | Nachtdienst Dispo (DN) |
| Andere | Sonderdienst (S) |

---

## 4. Mitarbeiter-Dokumente

### Vorlage
`Daten/Mitarbeiter Vorlagen/Kopf und Fußzeile/Stärkemeldung 31.01.2026 bis 01.02.2026.docx`

### Dateitabelle

Die Tabelle im Tab „📂 Dateien" passt ihre Spalten je nach Kategorie an:

- **Alle Kategorien:** `Dateiname | Zuletzt geändert | Typ`
- **Stellungnahmen:** `Dateiname | Art | Mitarbeiter | Zuletzt geändert | Typ`

Art und Mitarbeiter werden via `db_lade_alle()` geladen und per Dateiname zugeordnet (`os.path.basename(pfad_intern)`). Dateien ohne DB-Eintrag zeigen `—`.

### Rechtsklick-Menü

Rechtsklick auf eine Zeile der Dateitabelle bietet:
1. 📂 Im Explorer anzeigen
2. 📄 Öffnen
3. *(Separator)*
4. ✏ Bearbeiten
5. 🔤 Umbenennen
6. 🗑 Löschen

Die Zeile wird vor dem Öffnen des Menüs automatisch selektiert.

---


| Bescheinigungen | Standard-Dokument |
| Dienstanweisungen | Standard-Dokument |
| Abmahnungen | Standard-Dokument |
| Lob & Anerkennung | Standard-Dokument |
| Sonstiges | Standard-Dokument |

### `erstelle_dokument_aus_vorlage()`
1. Vorlage laden (Kopf-/Fußzeile)
2. Body leeren
3. Titel (fett 16pt zentriert), Meta-Block, Inhalt, Unterschrift einfügen
4. Speichern unter `Daten/Mitarbeiterdokumente/{kategorie}/{dateiname}`

---

## 5. Stellungnahmen-System

### `_StellungnahmeDialog` – Felder je Typ

#### Allgemein (immer sichtbar)
- Mitarbeiter (Pflicht), Datum des Vorfalls, Verfasst am
- Art der Stellungnahme (Radio: Flug / Beschwerde / Nicht mitgeflogen)

#### Flug-bezogener Vorfall
- Flugnummer (Pflicht)
- Verspätung? CB → Onblock-Zeit, Offblock-Zeit
- Flugrichtung: Inbound / Outbound / Beides
- Inbound (wenn Inbound/Beides): Ankunft LFZ, Auftragsende
- Outbound (wenn Outbound/Beides): Paxannahme-Zeit, Ort (C72/Meetingpoint/Sonstiges)
- Sachverhalt (Pflicht)

#### Passagierbeschwerde
- Onblock-Zeit, Offblock-Zeit (immer sichtbar bei diesem Typ)
- Sachverhalt (Pflicht)
- Beschwerdetext

#### Nicht mitgeflogen (kein PRM)
- Flugnummer (Pflicht)
- Sachverhalt (Pflicht)

### Speicherpfade

| Pfad | Beschreibung |
|------|-------------|
| `Daten/Mitarbeiterdokumente/Stellungnahmen/` | Intern (App-Zugriff) |
| `...\97_Stellungnahmen\` | Extern (OneDrive-Ablage, Team-Zugriff) |

### Datenbankschema (`stellungnahmen.db`)

```sql
CREATE TABLE stellungnahmen (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    erstellt_am     TEXT,    -- ISO-Zeitstempel
    datum_vorfall   TEXT,    -- dd.MM.yyyy
    verfasst_am     TEXT,    -- dd.MM.yyyy
    mitarbeiter     TEXT,
    art             TEXT,    -- flug|beschwerde|nicht_mitgeflogen
    flugnummer      TEXT,
    verspaetung     INTEGER, -- 0/1
    onblock         TEXT,    -- HH:mm
    offblock        TEXT,    -- HH:mm
    richtung        TEXT,    -- inbound|outbound|beides
    ankunft_lfz     TEXT,    -- HH:mm
    auftragsende    TEXT,    -- HH:mm
    paxannahme_zeit TEXT,    -- HH:mm
    paxannahme_ort  TEXT,
    sachverhalt     TEXT,
    beschwerde_text TEXT,
    pfad_intern     TEXT,    -- vollständiger Dateipfad
    pfad_extern     TEXT
);
```

### `lade_alle()` Abfrage-Parameter

```python
lade_alle(
    monat=None,    # 1–12
    jahr=None,     # int
    art=None,      # "flug" | "beschwerde" | "nicht_mitgeflogen"
    suchtext=None, # Suche in Mitarbeiter, Flugnummer, Sachverhalt
)
```
Ergebnis: Liste von dicts, neueste zuerst.

---

## 6. Lokale Web-Ansicht

### `WebNesk/stellungnahmen_lokal.html`

Vollständig statische HTML-Datei, alle Daten eingebettet als JavaScript-Variable.
Läuft per `file://` ohne Web-Server.

**Generierung:** `functions/stellungnahmen_html_export.py`
- Wird automatisch nach jeder Stellungnahme-Erstellung/-Löschung aufgerufen
- Kann manuell mit `generiere_html()` aufgerufen werden

**Features:**
- Live-Suche (Name, Flugnummer, Sachverhalt)
- Filter: Jahr, Monat, Art
- Detailansicht: alle Felder aller Typen
- Word-Dokument: Pfad anzeigen + In Zwischenablage kopieren
- URL-Hash: `file:///...stellungnahmen_lokal.html#id-42` → direkt zu Datensatz 42

**Integration:**
- App-Button „🌐 Web-Ansicht" (erscheint bei Kategorie Stellungnahmen)
- Übergabe-E-Mail: optionaler Link `file:///...html` oder `...html#id-42`

---

## 7. Übergabe & E-Mail

### `gui/uebergabe.py` – `_email_erstellen()`

Bestehende Sektionen: Protokolldaten, Fahrzeugstatus, Fahrzeugschäden, Handys/Geräte

**Neue Sektion: Stellungnahmen-Link**
- Checkbox „Stellungnahmen-Link anhängen"
- ComboBox: Allgemeiner Link / Spezifischer Fall (Liste der letzten 30 Tage)
- Einfügt im Mail-Körper:
  ```
  Stellungnahmen-Datenbank:
  [Link zur lokalen Web-Ansicht]
  Referenz: Stellungnahme #42 – Max Mustermann – 02.03.2026
  ```

### Verspätungs-Sektion (`_rebuild_verspaetungen_section`)

- **Blaue Einträge** (aus MA-Dokumentation): werden **immer** angezeigt – auch nach Protokoll-Speichern
- **Nachtdienst**: Vortag-Verspätungen werden nicht mehr automatisch geladen
- **Manuell hinzufügen** (➕): Dialog mit Datum-Feld (QDateEdit), Sollzeit editierbar → Eintrag direkt in `verspaetungen.db` gespeichert
- **Deduplication**: `db_eintraege` nach `(mitarbeiter, dienstbeginn)` via `_seen_db`-Set
- **E-Mail**: Datum (📅 dd.MM.yyyy) wird pro Verspätungseintrag in die E-Mail übertragen; DB-Einträge werden gegenüber Legacy-Tupeln bevorzugt

---

## 8. Telefonnummern-Verzeichnis

### `functions/telefonnummern_db.py`
- SQLite-Datenbank `database SQL/telefonnummern.db` (WAL-Modus)
- Tabellen: `telefonnummern`, `tel_import_log`
- `_CAT_NORMIERUNG`: Normalisiert rohe Excel-Spaltennamen (z.B. `"Check In Nummern"` → `"Check In B"`)
- `importiere_aus_excel(clear_first=True)`: Importiert beide Excel-Dateien; gibt Anzahl zurück
- Auto-Import bei leerem DB oder veralteten Kategorienamen (`ist_db_leer()`, `hat_veraltete_daten()`)

### `gui/telefonnummern.py`
- **4 Tabs**: 🔍 Alle · 📋 Kontakte · 🏪 Check-In (CIC) · 🚪 Interne & Gate
- `_EintragDialog`: Neu/Bearbeiten mit editierbaren Bereich-/Kategorie-ComboBoxen
- Manuell eingetragene Zeilen: gelb hervorgehoben (`#fff8e1`)
- Doppelklick öffnet Bearbeiten-Dialog

---

## 9. Patienten Station

### `gui/dienstliches.py` – `_PatientenTab` + `_PatientenDialog`

#### DB-Schema (`nesk3.db`)
- Tabelle `patienten` mit 35+ Feldern; automatische Migration (`ALTER TABLE`)
- Tabelle `verbrauchsmaterial (id, patienten_id, material, menge, einheit)` – CASCADE FK
- Tabelle `medikamente (id, patienten_id, medikament, dosis, applikation)` – CASCADE FK (v3.4.0)

#### Protokoll-Dialog (`_PatientenDialog`)
12 Abschnitte (scrollbar), Pflichtfelder: Von, Bis. Alle Felder werden bei Bearbeiten vorausgefüllt.

Medikamentengabe (v3.4.0): Tabelle Medikament / Dosis / Applikation; Applikation als Dropdown.

#### Word-Export (`export_patient_word()`)
- Erstellt `.docx` mit DRK-Logo-Header, DRK-Rot/Blau-Überschriften
- Section 7: Medikamenten-Tabelle
- Speicherort: `Daten/Patienten Station/Protokolle/`

#### E-Mail (`_PatientenMailDialog`)
- Outlook-Entwurf via `pywin32`, `.docx`-Anhang, vorausgefüllter Betreff/Body

---

## 10. Sonderaufgaben-Widget

### `gui/sonderaufgaben.py` – `SonderaufgabenWidget`
_(eingebettet in `gui/aufgaben.py` – Aufgaben Nacht)_

#### Bulmor-Abschnitt (v3.4.0)
- Dropdowns: alle aktiven Fahrzeuge + **„a.D."** immer als letzte Option
- Fahrzeugstatus-Spalte mit Farb-Badges: 🟢 fahrbereit · 🔴 defekt · 🟡 Werkstatt · ⚫ a.D.
  - Daten aus `fahrzeug_functions.lade_alle_fahrzeuge()`

#### Dienstplan-Integration (v3.4.0)
- **„📋 Dienstplan öffnen"-Button**: aktiviert sich nach Laden des Dienstplans
- Öffnet Excel-Datei direkt mit Windows-Standard-App

---

## 11. Bekannte Sonderfälle

### CareMan-Exportfehler
- Dispo-Zeiten mit Minuten (07:15, 19:45) → `_runde_auf_volle_stunde()`

### `manuell_geaendert`-Flag
- Gesetzt in `_DispoZeitenVorschauDialog` bei manueller Zeitänderung
- Verhindert erneutes Runden in `staerkemeldung_export._add_dienst_gruppe()`

### Windows Long Path Limit
- System-Python direkt nutzen; in `.vscode/settings.json` konfigurieren
