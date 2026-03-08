# Nesk3 – Technische Dokumentation

**Stand:** 08.03.2026  
**Anwendung:** Nesk3 – DRK Flughafen Köln  
**Zweck:** Dienstplan-Verwaltung, Stärkemeldung, Mitarbeiterverwaltung, Einsatzprotokoll, Verspätungs-Meldungen, Telefonnummern-Verzeichnis, PSA-Tracking

---

## Inhaltsverzeichnis

1. [Projektstruktur](#1-projektstruktur)
2. [Backup-System](#2-backup-system)
3. [Dienstplan-Parser](#3-dienstplan-parser)
4. [Dienstplan-Anzeige (GUI)](#4-dienstplan-anzeige-gui)
5. [Krankmeldungs-Logik](#5-krankmeldungs-logik)
6. [Dienst-Definitionen](#6-dienst-definitionen)
7. [Bekannte Sonderfälle](#7-bekannte-sonderfälle)
8. [Datenbanken](#8-datenbanken)
9. [Änderungshistorie](#9-änderungshistorie)

---

## 1. Projektstruktur

```
Nesk3/
├── main.py                          # Einstiegspunkt – startet die PySide6-App
├── config.py                        # Globale Konstanten (Farben, Pfade, DB-Name)
│
├── gui/
│   ├── main_window.py               # Hauptfenster, Sidebar-Navigation (14 Seiten)
│   ├── dashboard.py                 # Dashboard (Statistik-Karten, Flugzeug-Animation)
│   ├── dienstplan.py                # Dienstplan-Tab (Excel-Import, Tabelle, Export, 4 Panes)
│   ├── dienstliches.py              # Dienstliches: Einsatzprotokoll + Übersicht [NEU]
│   ├── aufgaben.py                  # Aufgaben Nacht (4 Tabs inkl. Code-19-Mail)
│   ├── aufgaben_tag.py              # Aufgaben Tag (Code19Mail, FreieMail, Checklisten)
│   ├── sonderaufgaben.py            # Sonderaufgaben (Bulmor, E-Mobby, Dienstplan-Abgleich)
│   ├── uebergabe.py                 # Übergabe-Protokoll (auto Zeiten, kein Personal-Feld)
│   ├── fahrzeuge.py                 # Fahrzeugverwaltung
│   ├── code19.py                    # Code-19 (Taschenuhr-Animation, Protokoll)
│   ├── mitarbeiter.py               # Mitarbeiter-Verwaltung
│   ├── mitarbeiter_dokumente.py     # Mitarbeiterdokumente + Stellungnahmen + Verspätung
│   ├── einstellungen.py             # Einstellungen (Pfade, E-Mobby-Fahrerverwaltung)
│   ├── telefonnummern.py            # Telefonnummern-Verzeichnis (4 Tabs, Import, CRUD) [NEU]
│   └── checklisten.py               # Checklisten-Tab
│
├── functions/
│   ├── dienstplan_parser.py         # Excel-Parser (Kernlogik, Krank-Typen, Dispo-Abschnitt)
│   ├── dienstplan_functions.py      # DB-Funktionen für Dienstplan
│   ├── dienstplan_html_export.py    # Statische HTML-Ansicht generieren [NEU]
│   ├── emobby_functions.py          # E-Mobby-Fahrerliste (TXT↔DB-Sync, Matching)
│   ├── psa_db.py                    # PSA-Verstöße: gesendet-Tracking [NEU]
│   ├── telefonnummern_db.py         # Telefonnummern SQLite-Backend (Import, CRUD) [NEU]
│   ├── fahrzeug_functions.py        # DB-Funktionen für Fahrzeuge
│   ├── mail_functions.py            # Outlook-COM-Integration
│   ├── mitarbeiter_dokumente_functions.py  # Kategorien, Dokumenten-Funktionen
│   ├── mitarbeiter_functions.py     # DB-Funktionen für Mitarbeiter
│   ├── settings_functions.py        # Key-Value-Einstellungen (get/set)
│   ├── staerkemeldung_export.py     # Word-Export Stärkemeldung
│   ├── stellungnahmen_db.py         # SQLite-Protokoll für Stellungnahmen
│   ├── uebergabe_functions.py       # DB-Funktionen für Übergabe-Protokolle
│   ├── verspaetung_db.py            # SQLite-Protokoll für Verspätungs-Meldungen [NEU]
│   └── verspaetung_functions.py     # Word-Vorlage FO_CGN_27 ausfüllen/speichern [NEU]
│
├── database/
│   ├── connection.py                # SQLite-Verbindung
│   ├── models.py                    # ORM-Modelle
│   └── migrations.py               # DB-Migrationen (beim Start ausgeführt)
│
├── backup/
│   └── backup_manager.py            # JSON + ZIP Backup/Restore
│
├── Daten/
│   └── E-Mobby/
│       └── mobby.txt                # E-Mobby-Fahrerliste (ein Name/Zeile)
│
├── docs/                            # Reproduktions-Protokoll (NEU)
│   ├── FUNKTIONEN.md                # Vollständige Funktionsübersicht aller Module
│   └── REPRODUKTION.md              # Schritt-für-Schritt Neuerstellung
│
├── database SQL/
│   ├── nesk3.db                     # Hauptdatenbank (WAL-Modus)
│   ├── archiv.db                    # Archivierte Protokolle
│   ├── stellungnahmen.db            # Passagierbeschwerde-Stellungnahmen
│   ├── einsaetze.db                 # Einsatzprotokoll FKB
│   └── verspaetungen.db             # Verspätungs-Meldungen
│
└── Backup Data/
    ├── Nesk3_backup_YYYYMMDD_HHMMSS.zip   # Vollständige ZIP-Backups
    └── db_backups/                  # SQLite-Snapshots (automatisch + vor Migrationen)
```

---

## 2. Backup-System

### 2.1 ZIP-Backup erstellen

ZIP-Backups werden im Ordner `Nesk3/Backup Data/` gespeichert und enthalten den **gesamten Nesk3-Quellcode** inkl. Datenbank.

**Programmatisch (empfohlen):**
```python
from backup.backup_manager import create_zip_backup

zip_pfad = create_zip_backup()
print(f"Backup erstellt: {zip_pfad}")
```

**Ausgeschlossene Ordner** (werden nicht ins ZIP aufgenommen):

| Ordner | Grund |
|---|---|
| `Backup Data/` | Keine rekursiven Backup-Zips |
| `build_tmp/` | PyInstaller-Build-Artefakte |
| `Exe/` | Kompilierte Executables |
| `__pycache__/` | Python-Bytecode-Cache |
| `.git/` | Versionskontroll-Daten |

### 2.2 ZIP-Backup wiederherstellen

```python
from backup.backup_manager import restore_from_zip

ergebnis = restore_from_zip(r"...\Nesk3\Backup Data\Nesk3_backup_20260225_205232.zip")
print(ergebnis['meldung'])
# → "362 Dateien aus Nesk3_backup_20260225_205232.zip wiederhergestellt."
```

**Was wird wiederhergestellt:** Alle `.py`, `.db`, `.ini`, `.json`, `.txt`-Dateien.  
**Was wird NICHT überschrieben:** Der `Backup Data/`-Ordner selbst (kein rekursives Backup-Backup).

### 2.3 Backups auflisten

```python
from backup.backup_manager import list_zip_backups

for b in list_zip_backups():
    print(b['dateiname'], b['groesse_kb'], 'KB', b['erstellt'])
```

### 2.4 Vorhandene Backups (Stand 25.02.2026)

| Dateiname | Größe | Erstellt | Hinweis |
|---|---|---|---|
| `Nesk3_backup_20260225_222303.zip` | 8,3 MB | 25.02.2026 22:23 | Ohne build_tmp/Exe |
| `Nesk3_backup_20260225_205927.zip` | 8,3 MB | 25.02.2026 20:59 | Ohne build_tmp/Exe |
| `Nesk3_backup_20260225_205232.zip` | ~361 MB | 25.02.2026 20:52 | Enthält alte Ordner |
| `Nesk3_backup_20260225_204119.zip` | ~181 MB | 25.02.2026 20:41 | Enthält alte Ordner |
| `Nesk3_backup_20260225_203321.zip` | ~90 MB | 25.02.2026 20:33 | Enthält alte Ordner |

---

## 3. Dienstplan-Parser

**Datei:** `functions/dienstplan_parser.py`  
**Klasse:** `DienstplanParser`

### 3.1 Verwendung

```python
from functions.dienstplan_parser import DienstplanParser

# alle_anzeigen=True  → keine Ausschlüsse (für Anzeige)
# alle_anzeigen=False → Ausgeschlossene Personen filtern (für Export)
result = DienstplanParser("pfad/zum/Dienstplan.xlsx", alle_anzeigen=True).parse()

# Rückgabe-Struktur:
# {
#   'success':             bool,
#   'betreuer':            list[dict],   # Betreuer im Dienst
#   'dispo':               list[dict],   # Disponenten im Dienst
#   'kranke':              list[dict],   # alle Krankmeldungen
#   'datum':               str,          # z.B. '23.02.2026'
#   'excel_path':          str,
#   'column_map':          dict,
#   'unbekannte_dienste':  list[str],
#   'error':               str | None
# }
```

### 3.2 Person-Dict (Felder)

Jede Person in `betreuer`, `dispo` und `kranke` ist ein Dictionary mit folgenden Feldern:

| Feld | Typ | Beschreibung |
|---|---|---|
| `vorname` | str | Vorname |
| `nachname` | str | Nachname |
| `vollname` | str | `"Vorname Nachname"` |
| `anzeigename` | str | Nachname (bei Doppelnamen + Initial) |
| `dienst_kategorie` | str\|None | Kürzel aus Excel: `T`, `DT`, `N`, `DN3`, … |
| `start_zeit` | str\|None | `"HH:MM"` |
| `end_zeit` | str\|None | `"HH:MM"` |
| `schicht_typ` | str\|None | `'tagdienst_vormittag'` / `'nachtschicht_frueh'` / … |
| `ist_dispo` | bool | `True` wenn Dispo-Dienst oder im Dispo-Abschnitt der Excel |
| `ist_krank` | bool | `True` wenn Kürzel `KRANK` oder `K` |
| `krank_schicht_typ` | str\|None | `'tagdienst'` / `'nachtdienst'` / `'sonderdienst'` |
| `krank_ist_dispo` | bool | `True` wenn krank+Dispo (via Abschnitt oder Zeitableitung) |
| `krank_abgeleiteter_dienst` | str\|None | Abgeleitetes Kürzel: `T`, `DT`, `N`, `DN`, `T(?)`, … |
| `ist_bulmorfahrer` | bool | `True` wenn Name-Zelle gelb hinterlegt |
| `excel_row` | int | Zeilennummer in der Excel (für Rückschreiben) |

### 3.3 Abschnitts-Erkennung (Dispo vs. Betreuer)

Die Excel-Dateien enthalten **Abschnitts-Trennzeilen**:

```
Zeile 5:  [Stamm FH]     ← Betreuer-Abschnitt beginnt
...
Zeile 60: Dispo          ← Dispo-Abschnitt beginnt
Zeile 61: Spinczyk, Gregor  |  DT  |  07:00  |  19:15  ← Dispo
Zeile 68: Lytek, Martin     |  Krank  |  19:30  |  07:45  ← Dispo-Krank!
```

Die Methode `_detect_abschnitt_header()` erkennt diese Zeilen und setzt `aktueller_abschnitt`:

| Erkannter Text | Abschnitt |
|---|---|
| `Dispo` (Startswith) | `'dispo'` |
| `Stamm`, `[Stamm`, `Betreuer` | `'betreuer'` |

**Wichtig:** Personen im Dispo-Abschnitt erhalten automatisch `ist_dispo=True` – unabhängig vom Dienst-Kürzel. Das betrifft vor allem Krank-Einträge im Dispo-Bereich.

### 3.4 Modul-Hilfsfunktionen

#### `_betr_zu_dispo_kuerzel(kuerzel)`

Wandelt ein Betreuer-Kürzel in das entsprechende Dispo-Kürzel um (für Krank-Dispo aus dem Excel-Abschnitt):

| Eingabe | Ausgabe |
|---|---|
| `T` | `DT` |
| `T10` | `DT` |
| `T8` | `DT` |
| `N` | `DN` |
| `N10` | `DN` |
| `T(?)` | `DT(?)` |
| `N(?)` | `DN(?)` |
| `S(?)` | `DN3(?)` |

#### `_runde_auf_volle_stunde(zeit_str)`

Rundet Zeitangaben auf die volle Stunde ab – wird für **Dispo-Krankmeldungen** angewendet, da Disponent-Zeiten in CareMan oft Abweichungen enthalten (z.B. `07:15` statt `07:00`):

```python
_runde_auf_volle_stunde("07:15")  # → "07:00"
_runde_auf_volle_stunde("19:45")  # → "19:00"
_runde_auf_volle_stunde("18:00")  # → "18:00"
```

---

## 4. Dienstplan-Anzeige (GUI)

**Datei:** `gui/dienstplan.py`

### 4.1 Dienst-Mengen (Konstanten)

```python
_TAG_DIENSTE   = frozenset({'T', 'T10', 'T8', 'DT', 'DT3'})
_NACHT_DIENSTE = frozenset({'N', 'N10', 'NF', 'DN', 'DN3'})
```

Diese bestimmen, in welchem **Tabellenabschnitt** ein aktiver Mitarbeiter erscheint.

### 4.2 Tabellenabschnitte

Die Tabelle wird nach folgendem Schema aufgebaut (Methode `_render_table_parsed`):

| Abschnitt | Hintergrund | Zeigt |
|---|---|---|
| **Tagdienst** | Weiß / Blau-Header | Alle Mitarbeiter mit Tag-Dienst-Kürzel |
| **Nachtdienst** | Hellblau / Dunkelblau-Header | Alle Mitarbeiter mit Nacht-Dienst-Kürzel |
| **Sonstige** | Weiß / Grau-Header | Alle anderen Kürzel (z.B. RS, B1) |
| **Krank – Tagdienst** | Hellrot / Dunkelrot-Header | Kranke deren Zeiten auf Tagdienst hinweisen |
| **Krank – Nachtdienst** | Noch helleres Rot | Kranke deren Zeiten auf Nachtdienst hinweisen |
| **Krank – Sonderdienst** | Bräunlich | Kranke ohne eindeutige Zeitableitung |

### 4.3 Farben in der Tabelle

| Kategorie | Zeilenhintergrund | Textfarbe | Bedeutung |
|---|---|---|---|
| `Dispo` | `#dce8f5` (Blau) | `#0a5ba4` | Aktiver Disponent |
| `Betreuer` | `#ffffff` (Weiß) | `#1a1a1a` | Aktiver Betreuer |
| `Stationsleitung` | `#fff8e1` (Gelb) | `#7a5000` | Lars Peters |
| `Krank` | `#fce8e8` (Rosa) | `#bb0000` | Kranker Betreuer |
| `KrankDispo` | `#f0d0d0` (Dunkler Rosa) | `#7a0000` | Kranker Disponent |
| Bulmorfahrer | `#fff3b0` (Gelb) | – | Gelb hinterlegte Zelle in Excel |

### 4.4 Statuszeile (Spalte unten rechts)

Zeigt eine vollständige Aufschlüsselung:

```
14 Tagdienst (Betreuer 11, Dispo 3)  |  8 Nachtdienst (Betreuer 6, Dispo 2)  |  1 Sonstige  |  9 Krank  –  Betreuer 8 (5 Tag / 2 Nacht / 1 Sonder) | Dispo 1 (1 Nacht)
```

**Aufbau:**
- `X Tagdienst (Betreuer Y, Dispo Z)` → Alle im Tagdienst, getrennt nach Funktion
- `X Nachtdienst (Betreuer Y, Dispo Z)` → Alle im Nachtdienst, getrennt nach Funktion
- `X Sonstige` → Alle anderen Dienste
- `X Krank – Betreuer Y (A Tag / B Nacht / C Sonder) | Dispo Z (D Tag / E Nacht)` → Krank-Aufschlüsselung

### 4.5 Spalten der Tabelle

| Spalte | Inhalt für aktive MA | Inhalt für Kranke |
|---|---|---|
| 0 | `Dispo` / `Betreuer` / `Stationsleitung` | `Dispo` / `Betreuer` |
| 1 | Anzeigename (Nachname) | Anzeigename |
| 2 | Dienst-Kürzel aus Excel | **Abgeleitetes Kürzel** (z.B. `T`, `DN(?)`) |
| 3 | Von-Zeit | Von-Zeit (Dispo: auf Stunde gerundet) |
| 4 | Bis-Zeit | Bis-Zeit (Dispo: auf Stunde gerundet) |

---

## 5. Krankmeldungs-Logik

### 5.1 Ablauf der Klassifizierung

```
Excel-Zeile mit Kürzel "KRANK" oder "K"
        │
        ▼
_parse_row() → ist_krank=True, start_zeit, end_zeit gesetzt
        │
        ▼
_ermittle_krank_typ(start_zeit, end_zeit, vollname)
        │
        ├─► Exaktes Zeitmatching → Dienst-Kürzel ableiten
        │       06:00–18:00 → T (Betreuer Tag)
        │       07:00–19:00 → DT (Dispo Tag)
        │       09:00–19:00 → T10
        │       10:00–18:00 → T8
        │       18:00–06:00 → N (Betreuer Nacht)
        │       21:00–07:00 → N10
        │       19:00–07:00 → DN (Dispo Nacht)
        │       kein Treffer → T(?) / N(?) / S(?)
        │
        ├─► Schichttyp:
        │       Start 05:00–14:59 → 'tagdienst'
        │       Start 15:00–04:59 → 'nachtdienst'
        │       sonstiges        → 'sonderdienst'
        │
        └─► Dispo-Erkennung:
                Name enthält "bauschke" → immer Dispo
                Kürzel DT/DN abgeleitet → Dispo
        │
        ▼
Abschnitts-Override in parse():
        Person steht im "Dispo"-Abschnitt der Excel?
        → ist_dispo=True, krank_ist_dispo=True
        → Kürzel via _betr_zu_dispo_kuerzel() anpassen (N→DN, T→DT)
        → Zeiten via _runde_auf_volle_stunde() runden
        │
        ▼
GUI: _render_table_parsed()
        → Einsortieren in krank_tag_dispo / krank_tag_betr /
          krank_nacht_dispo / krank_nacht_betr / krank_sonder
        → Tabellenabschnitt + Farbe wählen
        → Statuszeile aufbauen
```

### 5.2 Praxisbeispiel (23.02.2026)

| Name | Excel-Kürzel | Von | Bis | Ergebnis in App |
|---|---|---|---|---|
| Parso | Krank | 06:00 | 18:00 | Krank – Tagdienst, Betreuer, `T` |
| Rivola | krank | 18:00 | 06:00 | Krank – Nachtdienst, Betreuer, `N` |
| Chugh | Krank | 21:00 | 07:00 | Krank – Nachtdienst, Betreuer, `N10` |
| **Lytek** | Krank (im **Dispo-Abschnitt**) | 19:30 | 07:45 | Krank – Nachtdienst, **Dispo**, `DN(?)`, Zeiten: `19:00–07:00` |
| Lehmann G. | Krank | 11:00 | 19:00 | Krank – Tagdienst, Betreuer, `T(?)` |

### 5.3 Priorität der Dispo-Erkennung

1. **Abschnitts-Header** in der Excel (`Dispo`-Zeile) → höchste Priorität
2. **Dienst-Kürzel** (`DT`, `DT3`, `DN`, `DN3`) → direkte Erkennung
3. **Zeitabgleich** in `_ermittle_krank_typ()` → 07:00–19:00 = DT, 19:00–07:00 = DN
4. **Name** (`Bauschke`) → immer Dispo

---

## 6. Dienst-Definitionen

### 6.1 Tagdienste

| Kürzel | Typ | Von | Bis | Beschreibung |
|---|---|---|---|---|
| `T` | Betreuer | 06:00 | 18:00 | Standard-Tagdienst |
| `T10` | Betreuer | 09:00 | 19:00 | Späterer Tagdienst |
| `T8` | Betreuer | 10:00 | 18:00 | Kurzer Tagdienst |
| `DT` | Dispo | 07:00 | 19:00 | Dispo Tagdienst |
| `DT3` | Dispo | 19:00 | 07:00 | Dispo Tag (CareMan-Sonderklassifizierung) |

### 6.2 Nachtdienste

| Kürzel | Typ | Von | Bis | Beschreibung |
|---|---|---|---|---|
| `N` | Betreuer | 18:00 | 06:00 | Standard-Nachtdienst |
| `N10` | Betreuer | 21:00 | 07:00 | Späterer Nachtdienst |
| `NF` | Betreuer | variabel | variabel | Nachtdienst Früh |
| `DN` | Dispo | 19:00 | 07:00 | Dispo Nachtdienst |
| `DN3` | Dispo | 19:00 | 07:00 | Dispo Nacht (Variante) |

### 6.3 Sonderdienste

| Kürzel | Typ | Beschreibung |
|---|---|---|
| `R` | Sonder | Rufbereitschaft (kann auch Krank melden) |
| `B1` | Sonder | Stationsdienst 1 (Bauschke o.ä.) |
| `B2` | Sonder | Stationsdienst 2 |
| `RS` | Sonder | Wird in `Sonstige`-Abschnitt angezeigt |
| `KRANK` / `K` | Krank | Krankmeldung |

> **Hinweis:** `R`, `B1`, `B2` sind in `STILLE_DIENSTE` – sie werden im Export-Modus (`alle_anzeigen=False`) ohne Warnung ignoriert. Im Anzeigemodus erscheinen sie unter „Sonstige".

---

## 7. Bekannte Sonderfälle

### 7.1 Mitarbeiter Bauschke

- Dienst `B1` = Stationsdienst → erscheint unter „Sonstige"
- Bei Kombination mit Dispo-Kürzel (`DT`, `DN` etc.) → Disponent
- Bei Krankmeldung → immer als **Dispo** klassifiziert (Name-Erkennung)

### 7.2 Stationsleitung Lars Peters

- Wird gefiltert über `AUSGESCHLOSSENE_VOLLNAMEN` in nicht-alle_anzeigen-Modus
- Im Anzeigemodus (`alle_anzeigen=True`): erscheint mit gelber Hintergrundfarbe `#fff8e1` und brauner Schrift

### 7.3 Doppelte Nachnamen

- Wenn zwei Mitarbeiter denselben Nachnamen haben, wird der Anzeigename um die ersten 2 Vorname-Buchstaben ergänzt: `Müller` → `Müller Ma` und `Müller Jo`

### 7.4 Bulmorfahrer (gelbe Zellen)

- Mitarbeiter mit gelb hinterlegten Name-Zellen in der Excel werden als Bulmorfahrer markiert
- Erkennung: Zellfarbe AARRGGBB mit `FFFF**` im RG-Kanal und ≤ `4F` im B-Kanal
- Darstellung: Zeile wird mit `#fff3b0` (Hellgelb) überschrieben

### 7.5 Abweichende Zeiten bei Disponenten

CareMan exportiert Disponenten-Zeiten mit minimalen Abweichungen (z.B. `07:15` statt `07:00`). Daher:
- Aktive Disponenten: `round_to_hour=True` in `_parse_time()` → sofortiges Runden beim Lesen
- Kranke Disponenten (aus Abschnitt): `_runde_auf_volle_stunde()` nachträglich angewendet

---

## 8. Datenbanken

Alle SQLite-Datenbanken liegen seit **05.03.2026** zentral im Ordner `database SQL/`.

| Datei | Beschreibung | WAL | Zugriff über |
|---|---|---|---|
| `nesk3.db` | Hauptdatenbank (Dienstplan, Mitarbeiter, Fahrzeuge, Übergabe, …) | ✅ | `database/connection.py` |
| `archiv.db` | Archivierte Übergabe-Protokolle | ✅ | `functions/archiv_functions.py` |
| `stellungnahmen.db` | Passagierbeschwerde-Stellungnahmen | ✅ | `functions/stellungnahmen_db.py` |
| `einsaetze.db` | Einsatzprotokoll FKB (Dienstliches) | ✅ | `gui/dienstliches.py` |
| `verspaetungen.db` | Verspätungs-Meldungen (Unpünktlicher Dienstantritt) | ✅ | `functions/verspaetung_db.py` |

**Hinweis zu OneDrive/Netzwerkbetrieb:** SQLite ist nicht für echten Mehrbenutzer-Schreibzugriff über Netzlaufwerke geeignet. WAL-Modus (`nesk3.db`) verbessert die Lese-Parallelität, schützt aber nicht vor Schreibkonflikten bei gleichzeitigem Zugriff von mehreren PCs. Für Nur-Lese-Zugriffe (Anzeige) ist OneDrive-Sync ausreichend.

**Backup:** `main.py` erstellt beim Start automatisch einen Snapshot von `nesk3.db` in `Backup Data/db_backups/`. Für alle 5 DBs liegen manuelle Snapshots unter `Backup Data/db_backups/pre_consolidation_<ts>/`.

---

## 9. Änderungshistorie

### 25.02.2026 – Session

#### v1 – Krank-Aufschlüsselung nach Dienst

**Problem:** Alle Kranken erschienen in einem einzigen „Krank"-Abschnitt ohne Unterscheidung nach Tagdienst/Nachtdienst.

**Lösung:**
- `_ermittle_krank_typ()` in Parser: Ableitung von `krank_schicht_typ`, `krank_ist_dispo`, `krank_abgeleiteter_dienst` aus Start-/Endzeiten
- GUI: 3 separate Krank-Abschnitte (Tagdienst / Nachtdienst / Sonderdienst)
- Dienst-Spalte zeigt abgeleitetes Kürzel statt leer
- `T8` zu `_TAG_DIENSTE` hinzugefügt

#### v2 – Dispo-Abschnitt aus Excel-Header erkennen

**Problem:** Lytek (23.02.2026) steht im Dispo-Abschnitt der Excel, hat aber Kürzel `Krank` → wurde als Betreuer-Krank klassifiziert.

**Lösung:**
- `_detect_abschnitt_header()`: Erkennt `Dispo`- und `[Stamm FH]`-Trennzeilen
- Abschnitts-Tracking (`aktueller_abschnitt`) während des Zeilenlesens
- Dispo-Abschnitt-Personen erhalten `ist_dispo=True` unabhängig vom Kürzel
- `_betr_zu_dispo_kuerzel()`: Kürzel-Übersetzung für Dispo-Kranke (N→DN, T→DT)
- ZIP-Backup/Restore-Funktionen in `backup_manager.py`

#### v3 – Zeiten für Dispo-Kranke auf Stunde runden

**Problem:** CareMan-Abweichungen (`07:15`, `19:45`) wurden unverändert angezeigt.

**Lösung:**
- `_runde_auf_volle_stunde()`: Neue Hilfsfunktion
- Wird nur für **kranke Disponenten** (aus Abschnitt) angewendet
- Betreuer-Kranke behalten ihre Originalzeiten

#### v4 – Statuszeile: Dispo/Betreuer getrennt

**Problem:** Statuszeile zeigte nur Gesamtzählung, keine Unterscheidung.

**Lösung:**
- Krank-Block: `Betreuer X (A Tag / B Nacht) | Dispo Y (C Tag / D Nacht)`
- Tagdienst-Block: `14 Tagdienst (Betreuer 11, Dispo 3)`
- Nachtdienst-Block: `8 Nachtdienst (Betreuer 6, Dispo 2)`

#### v5 – Backup-Ausschlüsse erweitert

**Problem:** ZIP-Backups wuchsen auf >360 MB da `build_tmp/` (65 MB) und `Exe/` (59 MB) mitgesichert wurden.

**Lösung:**
- `_ZIP_EXCLUDE_DIRS` in `backup_manager.py` um `'build_tmp'` und `'Exe'` erweitert
- Backup-Größe reduziert: 361 MB → **8,3 MB**
