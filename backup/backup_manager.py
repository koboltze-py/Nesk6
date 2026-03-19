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
    # BASE_DIR = .../Nesk/Nesk3  →  dirname x2 = .../!Gemeinsam.26
    return os.path.dirname(os.path.dirname(BASE_DIR))


def get_gemeinsam_backup_stats() -> dict:
    """Gibt Statistiken über den Gemeinsam.26 Quellordner zurück."""
    src = _gemeinsam_src_dir()
    if not os.path.isdir(src):
        return {"ordner_existiert": False, "dateien_count": 0, "groesse_mb": 0, "letzte_aenderung": "-"}
    anzahl = 0
    groesse = 0
    letzte = 0.0
    nesk_pfad = os.path.normpath(os.path.dirname(BASE_DIR))  # .../Nesk
    for root, dirs, files in os.walk(src):
        # Nesk-Ordner (→ enthält Nesk3) komplett überspringen
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
    nesk_pfad = os.path.normpath(os.path.dirname(BASE_DIR))  # .../Nesk

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
# SQL-Datenbanken Backup (manuell via Button, selbe Struktur wie Startup-Backup)
# Ziel: database SQL/Backup Data/db_backups/YYYY-MM-DD/<name>_HHMMSS.db
# Rotation: max. 5 Snapshots pro Tag je DB, max. 7 Tages-Ordner
# ---------------------------------------------------------------------------

def create_sql_databases_backup(progress_callback=None) -> dict:
    """
    Sichert alle .db-Dateien in die gemeinsame db_backups-Struktur
    (selbes Verzeichnis wie der automatische Startup-Backup).
    Rotation: max. 5 Snapshots pro Tag je Datenbank, max. 7 Tages-Ordner.
    """
    import sqlite3 as _sqlite3
    from config import DB_PATH
    db_dir   = os.path.dirname(DB_PATH)
    basis    = os.path.join(db_dir, "Backup Data", "db_backups")
    jetzt    = datetime.now()
    tag_ord  = os.path.join(basis, jetzt.strftime("%Y-%m-%d"))
    os.makedirs(tag_ord, exist_ok=True)
    zeitstempel = jetzt.strftime("%H%M%S")

    db_files = glob.glob(os.path.join(db_dir, "*.db"))
    gesamt   = len(db_files)
    kopiert  = 0

    for i, fp in enumerate(sorted(db_files)):
        fname = os.path.basename(fp)
        name  = os.path.splitext(fname)[0]
        ziel  = os.path.join(tag_ord, f"{name}_{zeitstempel}.db")
        if progress_callback:
            progress_callback(i + 1, gesamt, fname)
        try:
            src_conn = _sqlite3.connect(fp)
            dst_conn = _sqlite3.connect(ziel)
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            kopiert += 1
        except Exception as e:
            print(f"[Backup] Fehler bei {fname}: {e}")
            continue

        # Pro Tag max. 5 Snapshots je Datenbank behalten
        tages = sorted(glob.glob(os.path.join(tag_ord, f"{name}_*.db")))
        for alt in tages[:-5]:
            try:
                os.remove(alt)
            except Exception:
                pass

    # Max. 7 Tages-Ordner behalten
    alle_tage = sorted([
        d for d in os.listdir(basis)
        if os.path.isdir(os.path.join(basis, d)) and len(d) == 10 and d.count("-") == 2
    ])
    for alter_tag in alle_tage[:-7]:
        try:
            shutil.rmtree(os.path.join(basis, alter_tag))
        except Exception:
            pass

    return {
        "erfolg": True,
        "dateien_count": kopiert,
        "skipped_count": 0,
        "error_count": gesamt - kopiert,
        "meldung": (
            f"{kopiert} von {gesamt} Datenbank(en) gesichert.\n"
            f"Speicherort: {tag_ord}"
        ),
    }


def list_sql_backups() -> list[dict]:
    """
    Listet alle SQL-DB-Backups aus der gemeinsamen db_backups-Struktur auf.
    Gibt eine Liste von Tages-Einträgen zurück (neueste zuerst).
    """
    return list_db_backups()


def restore_sql_backup(backup_pfad: str, ts: str | None = None) -> dict:
    """
    Stellt ein SQL-Datenbank-Backup wieder her.

    Kopiert die .db-Dateien eines Snapshots aus dem Backup-Ordner
    in den Live-DB-Ordner. Der Zeitstempel-Suffix (_HHMMSS) wird dabei
    vom Live-Dateinamen entfernt (z.B. nesk_081500.db → nesk.db).

    Parameters
    ----------
    backup_pfad : Tages-Ordner des Backups (YYYY-MM-DD)
    ts          : Zeitstempel (HHMMSS) des Snapshots; None = neuester
    """
    import sqlite3 as _sqlite3
    from config import DB_PATH
    db_dir = os.path.dirname(DB_PATH)

    # Neuesten Zeitstempel ermitteln, wenn keiner angegeben
    if ts is None:
        alle_ts = set()
        for fp in glob.glob(os.path.join(backup_pfad, "*.db")):
            name = os.path.basename(fp)
            parts = name.rsplit("_", 1)
            if len(parts) == 2 and parts[1].replace(".db", "").isdigit():
                alle_ts.add(parts[1].replace(".db", ""))
        if not alle_ts:
            return {"erfolg": False, "meldung": "Keine Backup-Dateien im Tages-Ordner gefunden."}
        ts = sorted(alle_ts)[-1]

    snapshot_files = glob.glob(os.path.join(backup_pfad, f"*_{ts}.db"))
    if not snapshot_files:
        return {"erfolg": False, "meldung": f"Snapshot {ts} nicht gefunden."}

    kopiert = 0
    for fp in sorted(snapshot_files):
        # Originalnamen rekonstruieren: "<name>_HHMMSS.db" → "<name>.db"
        base = os.path.basename(fp)
        orig_name = base.rsplit(f"_{ts}", 1)[0] + ".db"
        ziel = os.path.join(db_dir, orig_name)
        try:
            src_conn = _sqlite3.connect(fp)
            dst_conn = _sqlite3.connect(ziel)
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            kopiert += 1
        except Exception as e:
            print(f"[Restore] Fehler bei {orig_name}: {e}")

    erfolg = kopiert > 0
    if erfolg:
        # Marker schreiben: beim nächsten App-Start push_all_local_to_turso()
        # statt pull_all() aufrufen, damit Turso die wiederhergestellten Daten erhält.
        try:
            set_restore_pending()
        except Exception as e:
            print(f"[Restore] Hinweis: Restore-Flag konnte nicht geschrieben werden: {e}")

    return {
        "erfolg": erfolg,
        "meldung": f"{kopiert} Datenbank(en) wiederhergestellt aus Snapshot {ts}.",
    }


def _restore_pending_flag_path() -> str:
    """Gibt den Pfad zur Marker-Datei zurück, die signalisiert dass ein Restore ausstehend ist."""
    import os
    from config import DB_PATH
    return os.path.join(os.path.dirname(DB_PATH), "_restore_pending")


def set_restore_pending() -> None:
    """Schreibt die Restore-Pending Marker-Datei (signalisiert main.py: push statt pull beim Start)."""
    with open(_restore_pending_flag_path(), "w", encoding="utf-8") as f:
        from datetime import datetime
        f.write(datetime.now().isoformat())


def clear_restore_pending() -> None:
    """Löscht die Restore-Pending Marker-Datei nach erfolgreichem Push."""
    import os
    p = _restore_pending_flag_path()
    if os.path.exists(p):
        os.remove(p)


def is_restore_pending() -> bool:
    """Prüft ob eine Wiederherstellung auf den Push nach Turso wartet."""
    import os
    return os.path.exists(_restore_pending_flag_path())


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


# ---------------------------------------------------------------------------
# DRK-Daten Backup (ausgewählte Ordner aus !Gemeinsam.26 als ZIP)
# Ziel 1: <BASE_DIR>/Backup DRK Daten/
# Ziel 2: C:\Daten\Backup Daten DRK\
# Rotation: max. 5 ZIPs pro Tag, max. 7 Tage
# Gesperrte Dateien (Word/Excel): werden übersprungen, Fehler gezählt
# ---------------------------------------------------------------------------

# Ordner relativ zum !Gemeinsam.26-Verzeichnis (= os.path.dirname(BASE_DIR))
_DRK_BACKUP_ORDNER_NAMEN = [
    "00 Weihnachten",
    "00_CODE 19",
    "01_Checklisten_Vorlage",
    "02_Sonderaufgaben",
    "03_Krankmeldungen",
    "04_Tagesdienstpläne",
    "05_STAFF_Meldungen",
    "06_Stärkemeldung",
    "07_Checklisten",
    "08_Vorlagen",
    "09_Fuhrpark",
    "10_Schadenprotokolle",
    "11_Notfalleinsätze",
    "93_Abrechnung",
    "94_Beschwerde",
    "95_Ausbildung_Weiterbildung",
    "96_Unterlagen PRM Schulung",
    "97_Stellungnahmen",
    "98_AVTECH_Fehler",
    "98_Dispodienstplan",
    "99_Druckvorlagen",
    "101_ZÜP",
]

# Zielverzeichnisse
_DRK_BACKUP_ZIEL_NESK   = os.path.join(BASE_DIR, "Backup DRK Daten")
_DRK_BACKUP_ZIEL_LOKAL  = r"C:\Daten\Backup Daten DRK"


def _drk_quelle_ordner() -> str:
    """!Gemeinsam.26 Verzeichnis (= Elternordner von BASE_DIR/../../)"""
    # BASE_DIR = .../Nesk/Nesk3  →  parent(parent) = .../Gemeinsam.26
    return os.path.dirname(os.path.dirname(BASE_DIR))


def _drk_backup_tag_ordner(basis: str, datum_str: str) -> str:
    return os.path.join(basis, datum_str)


def _drk_rotate(basis: str, datum_str: str, zip_prefix: str, max_pro_tag: int = 5, max_tage: int = 7):
    """Löscht überschüssige ZIPs pro Tag und alte Tages-Ordner."""
    tag_ord = _drk_backup_tag_ordner(basis, datum_str)
    if os.path.isdir(tag_ord):
        zips = sorted(glob.glob(os.path.join(tag_ord, f"{zip_prefix}_*.zip")))
        for alt in zips[:-max_pro_tag]:
            try:
                os.remove(alt)
            except Exception:
                pass

    # Tages-Ordner Rotation
    alle_tage = sorted([
        d for d in os.listdir(basis)
        if os.path.isdir(os.path.join(basis, d))
    ])
    for alter_tag in alle_tage[:-max_tage]:
        try:
            shutil.rmtree(os.path.join(basis, alter_tag))
        except Exception:
            pass


def _try_copy_file(src: str, dst: str) -> bool:
    """
    Versucht eine Datei zu kopieren.
    Bei gesperrten Dateien (PermissionError / WinError 32) wird False zurückgegeben.
    """
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return True
    except PermissionError:
        return False
    except OSError as e:
        # WinError 32: Datei wird von einem anderen Prozess verwendet
        if hasattr(e, 'winerror') and e.winerror in (32, 33):
            return False
        return False
    except Exception:
        return False


def create_drk_daten_backup(progress_callback=None) -> dict:
    """
    Erstellt ein ZIP-Backup der konfigurierten DRK-Daten-Ordner.

    - Sichert jeden Quellordner einzeln in die ZIP
    - Gesperrte Dateien (Word/Excel geöffnet) werden übersprungen (kein Crash)
    - Backup landet in zwei Zielorten: Nesk3/Backup DRK Daten/ und C:\\Daten\\Backup Daten DRK\\
    - Rotation: max. 5 ZIPs pro Tag, max. 7 Tage in jedem Zielordner
    - Speichert Eintrag in drk_daten_backup_log (SQLite)

    Returns
    -------
    dict mit 'erfolg', 'meldung', 'pfad_nesk', 'pfad_lokal',
             'gesicherte_ordner', 'fehler_ordner', 'uebersprungene_dateien'
    """
    quelle_basis = _drk_quelle_ordner()
    jetzt        = datetime.now()
    datum_str    = jetzt.strftime("%Y-%m-%d")
    ts_str       = jetzt.strftime("%H%M%S")
    zip_name     = f"DRK_Daten_{datum_str}_{ts_str}.zip"

    # Zielordner
    for ziel_basis in (_DRK_BACKUP_ZIEL_NESK, _DRK_BACKUP_ZIEL_LOKAL):
        tag_ord = _drk_backup_tag_ordner(ziel_basis, datum_str)
        try:
            os.makedirs(tag_ord, exist_ok=True)
        except Exception:
            pass  # C:\Daten könnte nicht schreibbar sein

    zip_pfad_nesk  = os.path.join(_DRK_BACKUP_ZIEL_NESK, datum_str, zip_name)
    zip_pfad_lokal = os.path.join(_DRK_BACKUP_ZIEL_LOKAL, datum_str, zip_name)

    # Dateien sammeln
    alle_dateien: list[tuple[str, str]] = []   # (abs_pfad, arcname)
    fehlende_ordner: list[str] = []

    for ordner_name in _DRK_BACKUP_ORDNER_NAMEN:
        src_ord = os.path.join(quelle_basis, ordner_name)
        if not os.path.isdir(src_ord):
            fehlende_ordner.append(ordner_name)
            continue
        for root, _, files in os.walk(src_ord):
            for fname in files:
                abs_pfad = os.path.join(root, fname)
                arc_pfad = os.path.join(ordner_name, os.path.relpath(abs_pfad, src_ord))
                alle_dateien.append((abs_pfad, arc_pfad))

    gesamt            = len(alle_dateien)
    gesicherte_ordner = len(_DRK_BACKUP_ORDNER_NAMEN) - len(fehlende_ordner)
    uebersprungen     = 0
    zip_groesse_mb    = 0.0

    # ZIP erstellen (Nesk-Pfad als primären)
    try:
        os.makedirs(os.path.dirname(zip_pfad_nesk), exist_ok=True)
        with zipfile.ZipFile(zip_pfad_nesk, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for i, (abs_pfad, arc_pfad) in enumerate(alle_dateien):
                if progress_callback:
                    progress_callback(i + 1, gesamt, os.path.basename(abs_pfad))
                try:
                    zf.write(abs_pfad, arc_pfad)
                except (PermissionError, OSError):
                    # Gesperrte Datei – überspringen, nicht abbrechen
                    uebersprungen += 1
                except Exception:
                    uebersprungen += 1
        zip_groesse_mb = round(os.path.getsize(zip_pfad_nesk) / (1024 * 1024), 1)
    except Exception as e:
        return {
            "erfolg": False,
            "meldung": f"Fehler beim Erstellen der ZIP: {e}",
            "pfad_nesk": "", "pfad_lokal": "",
            "gesicherte_ordner": 0, "fehler_ordner": len(fehlende_ordner),
            "uebersprungene_dateien": 0,
        }

    # Rotation Nesk-Ziel
    _drk_rotate(_DRK_BACKUP_ZIEL_NESK, datum_str, "DRK_Daten")

    # Zweite Kopie: C:\Daten\Backup Daten DRK\
    pfad_lokal_ergebnis = ""
    try:
        os.makedirs(os.path.dirname(zip_pfad_lokal), exist_ok=True)
        shutil.copy2(zip_pfad_nesk, zip_pfad_lokal)
        pfad_lokal_ergebnis = zip_pfad_lokal
        _drk_rotate(_DRK_BACKUP_ZIEL_LOKAL, datum_str, "DRK_Daten")
    except Exception as e:
        print(f"[DRK-Backup] Zweite Kopie fehlgeschlagen ({zip_pfad_lokal}): {e}")

    # Datenbankeintrag
    _drk_backup_log_eintragen(
        dateiname=zip_name,
        pfad_nesk=zip_pfad_nesk,
        pfad_lokal=pfad_lokal_ergebnis,
        groesse_mb=zip_groesse_mb,
        gesicherte_ordner=gesicherte_ordner,
        fehler_ordner=len(fehlende_ordner),
    )

    meldung_teile = [
        f"{gesicherte_ordner} Ordner gesichert ({zip_groesse_mb} MB)",
        f"ZIP: {zip_name}",
    ]
    if fehlende_ordner:
        meldung_teile.append(f"Nicht gefunden: {', '.join(fehlende_ordner)}")
    if uebersprungen:
        meldung_teile.append(
            f"{uebersprungen} Datei(en) übersprungen (wahrscheinlich in Word/Excel geöffnet)"
        )
    if pfad_lokal_ergebnis:
        meldung_teile.append(f"Zweite Kopie: {pfad_lokal_ergebnis}")

    return {
        "erfolg": True,
        "meldung": "\n".join(meldung_teile),
        "pfad_nesk": zip_pfad_nesk,
        "pfad_lokal": pfad_lokal_ergebnis,
        "gesicherte_ordner": gesicherte_ordner,
        "fehler_ordner": len(fehlende_ordner),
        "uebersprungene_dateien": uebersprungen,
    }


def _drk_backup_log_eintragen(dateiname, pfad_nesk, pfad_lokal,
                               groesse_mb, gesicherte_ordner, fehler_ordner):
    """Schreibt einen Eintrag in die drk_daten_backup_log Tabelle."""
    try:
        from database.connection import get_connection
        conn = get_connection()
        conn.execute(
            """INSERT INTO drk_daten_backup_log
               (dateiname, pfad_nesk, pfad_lokal, groesse_mb, gesicherte_ordner, fehler_ordner)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (dateiname, pfad_nesk, pfad_lokal,
             groesse_mb, gesicherte_ordner, fehler_ordner),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DRK-Backup] Log-Eintrag fehlgeschlagen: {e}")


def list_drk_daten_backups() -> list[dict]:
    """
    Listet alle DRK-Daten-Backups aus der Datenbank auf (neueste zuerst).
    Zeigt auch den Dateistatus (ZIP noch vorhanden?).
    """
    try:
        from database.connection import get_connection
        conn = get_connection()
        rows = conn.execute(
            """SELECT id, dateiname, pfad_nesk, pfad_lokal,
                      groesse_mb, gesicherte_ordner, fehler_ordner, erstellt_am
               FROM drk_daten_backup_log
               ORDER BY erstellt_am DESC
               LIMIT 200"""
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[DRK-Backup] Listenabfrage fehlgeschlagen: {e}")
        return []

    result = []
    for row in rows:
        (rid, dateiname, pfad_nesk, pfad_lokal,
         groesse_mb, gesicherte_ordner, fehler_ordner, erstellt_am) = row
        # Datum anzeigen
        try:
            dt = datetime.fromisoformat(erstellt_am)
            datum_anzeige = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            datum_anzeige = erstellt_am

        result.append({
            "id":                 rid,
            "dateiname":          dateiname,
            "pfad_nesk":          pfad_nesk or "",
            "pfad_lokal":         pfad_lokal or "",
            "groesse_mb":         groesse_mb or 0,
            "gesicherte_ordner":  gesicherte_ordner or 0,
            "fehler_ordner":      fehler_ordner or 0,
            "datum_anzeige":      datum_anzeige,
            "zip_vorhanden":      os.path.isfile(pfad_nesk or ""),
        })
    return result


def drk_backup_quellordner_info() -> dict:
    """Gibt Info über Quellordner zurück (existiert? Anzahl Dateien?)."""
    quelle = _drk_quelle_ordner()
    vorhandene, fehlende = [], []
    gesamt_dateien = 0
    gesamt_mb = 0.0
    for name in _DRK_BACKUP_ORDNER_NAMEN:
        pfad = os.path.join(quelle, name)
        if os.path.isdir(pfad):
            vorhandene.append(name)
            for root, _, files in os.walk(pfad):
                for f in files:
                    try:
                        s = os.path.getsize(os.path.join(root, f))
                        gesamt_dateien += 1
                        gesamt_mb += s / (1024 * 1024)
                    except OSError:
                        pass
        else:
            fehlende.append(name)
    return {
        "quelle": quelle,
        "vorhandene": vorhandene,
        "fehlende": fehlende,
        "gesamt_dateien": gesamt_dateien,
        "gesamt_mb": round(gesamt_mb, 1),
    }
