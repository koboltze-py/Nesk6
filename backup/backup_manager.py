"""
Backup-Manager
Erstellt und verwaltet Datenbank-Backups als JSON.
Enthält außerdem Funktionen für ZIP-Backups und ZIP-Restore des gesamten Nesk3-Ordners.
"""
import os
import sys
import glob
import json
import shutil
import zipfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BACKUP_DIR, BACKUP_MAX_KEEP, BASE_DIR


def _ensure_backup_dir() -> str:
    """Erstellt das Backup-Verzeichnis falls nicht vorhanden."""
    path = os.path.join(BASE_DIR, BACKUP_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def create_backup(typ: str = "manuell") -> str:
    """
    Erstellt ein vollständiges Backup aller Tabellen als JSON.
    Gibt den Dateipfad zurück.
    """
    # TODO: Implementierung folgt
    return ""


def list_backups() -> list[dict]:
    """Gibt eine Liste aller vorhandenen Backups zurück."""
    backup_dir = _ensure_backup_dir()
    backups = []
    for fname in sorted(os.listdir(backup_dir), reverse=True):
        if fname.endswith(".json"):
            fpath = os.path.join(backup_dir, fname)
            size  = os.path.getsize(fpath)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            backups.append({
                "dateiname":  fname,
                "pfad":       fpath,
                "groesse_kb": round(size / 1024, 1),
                "erstellt":   mtime.strftime("%d.%m.%Y %H:%M"),
            })
    return backups


def restore_backup(filepath: str) -> int:
    """
    Stellt ein Backup wieder her.
    Gibt die Anzahl der wiederhergestellten Datensätze zurück.
    """
    # TODO: Implementierung folgt
    return 0


def _cleanup_old_backups(backup_dir: str):
    """Löscht ältere Backups wenn MAX_KEEP überschritten."""
    files = sorted(
        [f for f in os.listdir(backup_dir) if f.endswith(".json")]
    )
    while len(files) > BACKUP_MAX_KEEP:
        os.remove(os.path.join(backup_dir, files.pop(0)))


# ---------------------------------------------------------------------------
# Automatische Startup-DB-Backups (SQLite .db-Dateien, täglich angelegt)
# Speicherort: database SQL/Backup Data/db_backups/YYYY-MM-DD/
# ---------------------------------------------------------------------------

def _db_backup_root() -> str:
    from config import DB_PATH
    return os.path.join(os.path.dirname(DB_PATH), "Backup Data", "db_backups")


def _format_datum(tag: str) -> str:
    try:
        return datetime.strptime(tag, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return tag


def _snapshots_fuer_tag(tag_pfad: str) -> list[dict]:
    """Gibt alle Snapshots (Zeitstempel-Gruppen) eines Tages zurück."""
    snapshots: dict[str, dict] = {}
    for f in sorted(glob.glob(os.path.join(tag_pfad, "*.db"))):
        fname = os.path.basename(f)
        # Kein _wiederherstellung-Unterordner
        parts = fname.rsplit("_", 1)
        if len(parts) != 2:
            continue
        ts_raw = parts[1].replace(".db", "")
        if len(ts_raw) != 6 or not ts_raw.isdigit():
            continue
        uhrzeit = f"{ts_raw[0:2]}:{ts_raw[2:4]} Uhr"
        if ts_raw not in snapshots:
            snapshots[ts_raw] = {"zeit": uhrzeit, "ts": ts_raw, "dateien": []}
        snapshots[ts_raw]["dateien"].append({
            "name": parts[0],
            "pfad": f,
            "groesse_kb": round(os.path.getsize(f) / 1024, 1),
        })
    return sorted(snapshots.values(), key=lambda x: x["ts"])


def list_db_backups() -> list[dict]:
    """
    Listet alle automatisch angelegten Startup-DB-Backups auf.
    Gibt eine Liste von Tages-Einträgen (neueste zuerst) zurück.
    """
    basis = _db_backup_root()
    if not os.path.isdir(basis):
        return []
    result = []
    for tag in sorted(os.listdir(basis), reverse=True):
        tag_pfad = os.path.join(basis, tag)
        # Nur echte Tages-Ordner (YYYY-MM-DD), keine _wiederherstellung etc.
        if not os.path.isdir(tag_pfad) or len(tag) != 10 or tag.count("-") != 2:
            continue
        db_dateien = glob.glob(os.path.join(tag_pfad, "*.db"))
        if not db_dateien:
            continue
        gesamt = sum(os.path.getsize(f) for f in db_dateien)
        snapshots = _snapshots_fuer_tag(tag_pfad)
        db_namen = {os.path.basename(f).rsplit("_", 1)[0] for f in db_dateien}
        result.append({
            "datum":             tag,
            "datum_anzeige":     _format_datum(tag),
            "pfad":              tag_pfad,
            "anzahl_dbs":        len(db_namen),
            "anzahl_snapshots":  len(snapshots),
            "groesse_mb":        round(gesamt / (1024 * 1024), 1),
            "snapshots":         snapshots,
        })
    return result


def restore_db_backup_as_copy(tag_pfad: str, ts: str | None = None) -> dict:
    """
    Kopiert DB-Backup-Dateien eines Snapshots in einen geschützten Unterordner.
    Die Live-Datenbanken werden NICHT verändert.
    Turso hat keinen Zugriff auf diesen Ordner.

    Parameters
    ----------
    tag_pfad : Pfad zum Tages-Ordner des Backups
    ts       : Zeitstempel (HHMMSS) des gewünschten Snapshots; None = neuester

    Returns
    -------
    dict mit {'erfolg', 'ziel', 'anzahl', 'meldung'}
    """
    if ts is None:
        # Neuesten Snapshot bestimmen
        alle = sorted(glob.glob(os.path.join(tag_pfad, "*.db")))
        if not alle:
            return {"erfolg": False, "ziel": "", "anzahl": 0, "meldung": "Keine Backup-Dateien gefunden."}
        letzter_ts = os.path.basename(alle[-1]).rsplit("_", 1)[-1].replace(".db", "")
        if len(letzter_ts) != 6:
            return {"erfolg": False, "ziel": "", "anzahl": 0, "meldung": "Zeitstempel ungültig."}
        ts = letzter_ts

    muster = glob.glob(os.path.join(tag_pfad, f"*_{ts}.db"))
    if not muster:
        return {"erfolg": False, "ziel": "", "anzahl": 0, "meldung": f"Snapshot {ts} nicht gefunden."}

    # Zielordner: _wiederherstellung/<YYYY-MM-DD_HHMMSS>/
    tag_name = os.path.basename(tag_pfad)
    ziel_basis = os.path.join(_db_backup_root(), "_wiederherstellung")
    ziel_name  = f"{tag_name}_{ts}"
    ziel_ordner = os.path.join(ziel_basis, ziel_name)

    if os.path.exists(ziel_ordner):
        # Bereits kopiert – einfach Pfad zurückgeben
        vorh = glob.glob(os.path.join(ziel_ordner, "*.db"))
        return {
            "erfolg": True, "ziel": ziel_ordner, "anzahl": len(vorh),
            "meldung": (
                f"Kopie bereits vorhanden ({len(vorh)} Datenbank-Datei(en)).\n\n"
                f"Speicherort:\n{ziel_ordner}\n\n"
                "Die Live-Datenbanken wurden NICHT verändert."
            ),
        }

    os.makedirs(ziel_ordner, exist_ok=True)
    kopiert = 0
    for src in sorted(muster):
        fname  = os.path.basename(src)
        # name_HHMMSS.db  →  name.db
        teile  = fname.rsplit("_", 1)
        zielname = teile[0] + ".db" if len(teile) == 2 else fname
        shutil.copy2(src, os.path.join(ziel_ordner, zielname))
        kopiert += 1

    uhrzeit = f"{ts[0:2]}:{ts[2:4]} Uhr"
    return {
        "erfolg": True,
        "ziel":   ziel_ordner,
        "anzahl": kopiert,
        "meldung": (
            f"{kopiert} Datenbank-Kopie(n) vom {_format_datum(tag_name)} {uhrzeit} gesichert.\n\n"
            f"Speicherort (kein Turso-Zugriff):\n{ziel_ordner}\n\n"
            "Die Live-Datenbanken wurden NICHT verändert.\n"
            "Im Notfall können die Dateien von dort manuell zurückgespielt werden."
        ),
    }


def list_restored_copies() -> list[dict]:
    """Listet alle bereits erstellten Wiederherstellungs-Kopien auf."""
    basis = os.path.join(_db_backup_root(), "_wiederherstellung")
    if not os.path.isdir(basis):
        return []
    result = []
    for name in sorted(os.listdir(basis), reverse=True):
        pfad = os.path.join(basis, name)
        if not os.path.isdir(pfad):
            continue
        dateien = glob.glob(os.path.join(pfad, "*.db"))
        groesse = sum(os.path.getsize(f) for f in dateien)
        result.append({
            "name":       name,
            "pfad":       pfad,
            "anzahl":     len(dateien),
            "groesse_mb": round(groesse / (1024 * 1024), 1),
        })
    return result


# ---------------------------------------------------------------------------
# Gemeinsam.26-Ordner Backup
# ---------------------------------------------------------------------------

_GEMEINSAM_BACKUP_DIR = os.path.join(BASE_DIR, "Backup Data", "gemeinsam_backups")
_GEMEINSAM_SRC = os.path.join(os.path.dirname(BASE_DIR))  # parent von Nesk3 = !Gemeinsam.26


def _gemeinsam_src_dir() -> str:
    """Gibt den Quellordner zurück (Dateien von ... !Gemeinsam.26)."""
    return os.path.dirname(BASE_DIR)


def get_gemeinsam_backup_stats() -> dict:
    """Gibt Statistiken über den Gemeinsam.26 Quellordner zurück."""
    src = _gemeinsam_src_dir()
    if not os.path.isdir(src):
        return {"ordner_existiert": False, "dateien_count": 0, "groesse_mb": 0, "letzte_aenderung": "-"}
    anzahl = 0
    groesse = 0
    letzte = 0.0
    nesk_pfad = os.path.normpath(BASE_DIR)
    for root, dirs, files in os.walk(src):
        # Nesk-Ordner selbst überspringen
        dirs[:] = [d for d in dirs if os.path.normpath(os.path.join(root, d)) != nesk_pfad]
        for f in files:
            fp = os.path.join(root, f)
            try:
                st = os.stat(fp)
                groesse += st.st_size
                if st.st_mtime > letzte:
                    letzte = st.st_mtime
                anzahl += 1
            except OSError:
                pass
    letzte_str = datetime.fromtimestamp(letzte).strftime("%d.%m.%Y %H:%M") if letzte else "-"
    return {
        "ordner_existiert": True,
        "dateien_count": anzahl,
        "groesse_mb": round(groesse / (1024 * 1024), 1),
        "letzte_aenderung": letzte_str,
    }


def create_gemeinsam_backup(inkrementell: bool = True, progress_callback=None) -> dict:
    """
    Erstellt ein Backup des Gemeinsam.26 Ordners (ohne den Nesk-Unterordner).
    Bei inkrementell=True werden nur geänderte Dateien kopiert.
    """
    os.makedirs(_GEMEINSAM_BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ziel  = os.path.join(_GEMEINSAM_BACKUP_DIR, f"gemeinsam_{stamp}")
    os.makedirs(ziel, exist_ok=True)

    src = _gemeinsam_src_dir()
    nesk_pfad = os.path.normpath(BASE_DIR)

    # Dateien sammeln
    alle: list[str] = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if os.path.normpath(os.path.join(root, d)) != nesk_pfad]
        for f in files:
            alle.append(os.path.join(root, f))

    gesamt = len(alle)
    kopiert = 0
    uebersprungen = 0
    fehler = 0

    for i, fp in enumerate(alle):
        if progress_callback:
            progress_callback(i + 1, gesamt, os.path.basename(fp))
        rel = os.path.relpath(fp, src)
        dst = os.path.join(ziel, rel)
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if inkrementell and os.path.exists(dst):
                if os.path.getmtime(fp) <= os.path.getmtime(dst):
                    uebersprungen += 1
                    continue
            shutil.copy2(fp, dst)
            kopiert += 1
        except Exception:
            fehler += 1

    if kopiert == 0 and uebersprungen > 0:
        # Nichts Neues → leeren Ordner wieder entfernen
        try:
            shutil.rmtree(ziel)
        except Exception:
            pass
        return {
            "erfolg": True, "dateien_count": 0, "skipped_count": uebersprungen,
            "error_count": fehler,
            "meldung": f"Kein neues Backup nötig – alle {uebersprungen} Dateien sind aktuell.",
        }

    return {
        "erfolg": True,
        "dateien_count": kopiert,
        "skipped_count": uebersprungen,
        "error_count": fehler,
        "meldung": (
            f"Backup erstellt: {kopiert} Datei(en) gesichert"
            + (f", {uebersprungen} unverändert übersprungen" if uebersprungen else "")
            + (f", {fehler} Fehler" if fehler else "")
            + f".\nSpeicherort: {ziel}"
        ),
    }


def list_gemeinsam_backups() -> list[dict]:
    """Listet alle Gemeinsam.26 Backups auf."""
    if not os.path.isdir(_GEMEINSAM_BACKUP_DIR):
        return []
    result = []
    for name in sorted(os.listdir(_GEMEINSAM_BACKUP_DIR), reverse=True):
        pfad = os.path.join(_GEMEINSAM_BACKUP_DIR, name)
        if not os.path.isdir(pfad):
            continue
        dateien = []
        g = 0
        for root, _, files in os.walk(pfad):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    g += os.path.getsize(fp)
                except OSError:
                    pass
                dateien.append(fp)
        mtime = os.path.getmtime(pfad)
        result.append({
            "dateiname": name,
            "pfad": pfad,
            "groesse_mb": round(g / (1024 * 1024), 1),
            "erstellt": datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M"),
        })
    return result


# ---------------------------------------------------------------------------
# SQL-Datenbanken Backup (manuelle Sicherung via Button)
# ---------------------------------------------------------------------------

_SQL_BACKUP_DIR = os.path.join(BASE_DIR, "Backup Data", "sql_backups")


def create_sql_databases_backup(progress_callback=None) -> dict:
    """Sichert alle .db-Dateien aus dem 'database SQL' Ordner in einen Zeitstempel-Ordner."""
    from config import DB_PATH
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(_SQL_BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    ziel  = os.path.join(_SQL_BACKUP_DIR, stamp)
    os.makedirs(ziel, exist_ok=True)

    db_files = glob.glob(os.path.join(db_dir, "*.db"))
    gesamt = len(db_files)
    kopiert = 0

    for i, fp in enumerate(sorted(db_files)):
        fname = os.path.basename(fp)
        if progress_callback:
            progress_callback(i + 1, gesamt, fname)
        try:
            import sqlite3
            src_conn = sqlite3.connect(fp)
            dst_conn = sqlite3.connect(os.path.join(ziel, fname))
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            kopiert += 1
        except Exception as e:
            print(f"[Backup] Fehler bei {fname}: {e}")

    return {
        "erfolg": True,
        "dateien_count": kopiert,
        "skipped_count": 0,
        "error_count": gesamt - kopiert,
        "meldung": f"{kopiert} von {gesamt} Datenbank(en) gesichert.\nSpeicherort: {ziel}",
    }


def list_sql_backups() -> list[dict]:
    """Listet alle manuellen SQL-Datenbank-Backups auf."""
    if not os.path.isdir(_SQL_BACKUP_DIR):
        return []
    result = []
    for name in sorted(os.listdir(_SQL_BACKUP_DIR), reverse=True):
        pfad = os.path.join(_SQL_BACKUP_DIR, name)
        if not os.path.isdir(pfad):
            continue
        db_files = glob.glob(os.path.join(pfad, "*.db"))
        groesse  = sum(os.path.getsize(f) for f in db_files)
        mtime    = os.path.getmtime(pfad)
        result.append({
            "datum":       datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M"),
            "pfad":        pfad,
            "anzahl_dbs":  len(db_files),
            "groesse_mb":  round(groesse / (1024 * 1024), 1),
        })
    return result


def restore_sql_backup(backup_pfad: str) -> dict:
    """
    Stellt ein SQL-Datenbank-Backup wieder her.
    Kopiert die .db-Dateien aus dem Backup-Ordner in den Live-DB-Ordner.
    """
    from config import DB_PATH
    db_dir = os.path.dirname(DB_PATH)

    db_files = glob.glob(os.path.join(backup_pfad, "*.db"))
    if not db_files:
        return {"erfolg": False, "meldung": "Keine Datenbank-Dateien im Backup gefunden."}

    import sqlite3
    kopiert = 0
    for fp in sorted(db_files):
        fname = os.path.basename(fp)
        ziel  = os.path.join(db_dir, fname)
        try:
            src_conn = sqlite3.connect(fp)
            dst_conn = sqlite3.connect(ziel)
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            kopiert += 1
        except Exception as e:
            print(f"[Restore] Fehler bei {fname}: {e}")

    return {
        "erfolg": True,
        "meldung": f"{kopiert} Datenbank(en) wiederhergestellt.",
    }


# ---------------------------------------------------------------------------
# ZIP-Backup  /  ZIP-Restore  (gesamter Nesk3-Quellcode-Ordner)
# ---------------------------------------------------------------------------

_CODE_BACKUP_DIR = os.path.join(BASE_DIR, "Backup Data")

# Ordner/Muster die beim ZIP-Backup NICHT einbezogen werden sollen
_ZIP_EXCLUDE_DIRS  = {'__pycache__', '.git', 'Backup Data', 'backup', 'build_tmp', 'Exe'}
_ZIP_EXCLUDE_EXTS  = {'.pyc', '.pyo'}


def create_zip_backup() -> str:
    """
    Erstellt ein vollständiges ZIP-Backup des Nesk3-Ordners (alle .py, .db, .ini, .json Dateien).
    Speichert das ZIP unter 'Backup Data/Nesk3_backup_<timestamp>.zip'.
    Gibt den vollständigen ZIP-Pfad zurück.
    """
    os.makedirs(_CODE_BACKUP_DIR, exist_ok=True)
    stamp    = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f"Nesk3_backup_{stamp}.zip"
    zip_path = os.path.join(_CODE_BACKUP_DIR, zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            # Ausgeschlossene Ordner überspringen (in-place modifizieren)
            dirs[:] = [d for d in dirs if d not in _ZIP_EXCLUDE_DIRS]
            for fname in files:
                if os.path.splitext(fname)[1].lower() in _ZIP_EXCLUDE_EXTS:
                    continue
                full_path = os.path.join(root, fname)
                arcname   = os.path.relpath(full_path, BASE_DIR)
                zf.write(full_path, arcname)

    return zip_path


def list_zip_backups() -> list[dict]:
    """
    Gibt eine Liste aller ZIP-Backups im Backup-Data-Ordner zurück.
    Jedes Element: {'dateiname', 'pfad', 'groesse_kb', 'erstellt'}
    """
    if not os.path.isdir(_CODE_BACKUP_DIR):
        return []
    result = []
    for fname in sorted(os.listdir(_CODE_BACKUP_DIR), reverse=True):
        if fname.lower().endswith('.zip'):
            fpath = os.path.join(_CODE_BACKUP_DIR, fname)
            size  = os.path.getsize(fpath)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            result.append({
                'dateiname':  fname,
                'pfad':       fpath,
                'groesse_kb': round(size / 1024, 1),
                'erstellt':   mtime.strftime('%d.%m.%Y %H:%M'),
            })
    return result


def restore_from_zip(zip_path: str, ziel_ordner: str = None) -> dict:
    """
    Stellt einen Nesk3-Quellcode-Backup aus einer ZIP-Datei wieder her.

    Parameters
    ----------
    zip_path     : Vollständiger Pfad zur ZIP-Datei
    ziel_ordner  : Zielordner; Standard = BASE_DIR (= aktueller Nesk3-Ordner)

    Returns
    -------
    dict mit {'erfolg': bool, 'dateien': int, 'meldung': str}
    """
    if ziel_ordner is None:
        ziel_ordner = BASE_DIR

    if not os.path.isfile(zip_path):
        return {'erfolg': False, 'dateien': 0, 'meldung': f'ZIP nicht gefunden: {zip_path}'}

    if not zipfile.is_zipfile(zip_path):
        return {'erfolg': False, 'dateien': 0, 'meldung': 'Keine gültige ZIP-Datei.'}

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            namelist = zf.namelist()
            # Nur .py / .db / .ini / .json / .txt Dateien wiederherstellen; niemals Backup Data selbst
            restore_names = [
                n for n in namelist
                if not n.replace('\\', '/').startswith('Backup Data/')
                and os.path.splitext(n)[1].lower() not in _ZIP_EXCLUDE_EXTS
            ]
            for member in restore_names:
                target = os.path.join(ziel_ordner, member)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(member) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

        return {
            'erfolg':  True,
            'dateien': len(restore_names),
            'meldung': f'{len(restore_names)} Dateien aus {os.path.basename(zip_path)} wiederhergestellt.',
        }
    except Exception as e:
        return {'erfolg': False, 'dateien': 0, 'meldung': f'Fehler beim Wiederherstellen: {e}'}
