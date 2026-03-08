# Nesk3

**DRK Flughafen Köln – Erste-Hilfe-Station**  
Dienstplan-Verwaltung, Stärkemeldung und Mitarbeiterverwaltung

**Version:** v3.2.0 (08.03.2026)  
**Module:** Dashboard · Mitarbeiter · Dienstliches · Aufgaben Tag/Nacht · Dienstplan · Übergabe · Fahrzeuge · Code 19 · Ma. Ausdrucke · Krankmeldungen · **Telefonnummern** · Backup · Einstellungen · Hilfe

---

## Starten

```powershell
cd "...\Nesk\Nesk3"
python main.py
```

Erfordert Python 3.13+ und folgende Pakete:
```
PySide6, openpyxl, python-docx
```

## Backup erstellen

```python
from backup.backup_manager import create_zip_backup
zip_pfad = create_zip_backup()
print(f"Backup: {zip_pfad}")
```

Oder direkt per Skript:
```powershell
python C:\Users\DRKairport\AppData\Local\Temp\do_backup.py
```

**Ausgeschlossen:** `Backup Data/`, `build_tmp/`, `Exe/`, `__pycache__/` → Größe ~8 MB

## Backup wiederherstellen

```python
from backup.backup_manager import restore_from_zip
restore_from_zip(r"...\Backup Data\Nesk3_backup_YYYYMMDD_HHMMSS.zip")
```

## Dokumentation

→ [DOKUMENTATION.md](DOKUMENTATION.md)  
→ [CHANGELOG.md](CHANGELOG.md)
