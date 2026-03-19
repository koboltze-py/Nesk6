"""
Turso Sync-Schicht
==================
Synchronisiert alle lokalen SQLite-Datenbanken mit Turso (SSOT).

Ablauf:
  - Beim App-Start: pull_all() → holt neuesten Stand aus Turso in alle lokalen DBs
  - Bei jedem DB-Write: push_row() → schreibt den Datensatz parallel nach Turso
  - Hintergrund-Thread: alle 30 Sekunden pull_all() (live-aktuell auf allen PCs)

Turso-Tabellen-Namensschema:
  lokale DB     | lokale Tabelle   | Turso-Tabellenname
  ------------- | ---------------- | ---------------------
  nesk3.db      | mitarbeiter      | nesk3__mitarbeiter
  mitarbeiter.db| mitarbeiter      | ma__mitarbeiter
  einsaetze.db  | einsaetze        | einsaetze__einsaetze
  ... usw.
"""

import json
import sqlite3
import threading
import urllib.request
import urllib.error
from contextlib import contextmanager

# Lazy import – config wird erst beim ersten Aufruf geladen
_cfg = None

def _get_cfg():
    global _cfg
    if _cfg is None:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import config as _c
        _cfg = _c
    return _cfg


# ─── Mapping: (db_dateiname_ohne_pfad, tabelle) → turso_tabellenname ─────────
# Nur Haupt-Datenbanken – keine W11-Kopien
TABLE_MAP: dict[tuple[str, str], str] = {
    # nesk3.db
    ("nesk3.db", "mitarbeiter"):              "nesk3__mitarbeiter",
    ("nesk3.db", "abteilungen"):              "nesk3__abteilungen",
    ("nesk3.db", "positionen"):               "nesk3__positionen",
    ("nesk3.db", "dienstplan"):               "nesk3__dienstplan",
    ("nesk3.db", "fahrzeuge"):                "nesk3__fahrzeuge",
    ("nesk3.db", "fahrzeug_status"):          "nesk3__fahrzeug_status",
    ("nesk3.db", "fahrzeug_schaeden"):        "nesk3__fahrzeug_schaeden",
    ("nesk3.db", "fahrzeug_termine"):         "nesk3__fahrzeug_termine",
    ("nesk3.db", "uebergabe_protokolle"):     "nesk3__uebergabe_protokolle",
    ("nesk3.db", "uebergabe_fahrzeug_notizen"): "nesk3__uebergabe_fahrzeug_notizen",
    ("nesk3.db", "uebergabe_handy_eintraege"): "nesk3__uebergabe_handy_eintraege",
    ("nesk3.db", "uebergabe_verspaetungen"):  "nesk3__uebergabe_verspaetungen",
    ("nesk3.db", "settings"):                 "nesk3__settings",
    ("nesk3.db", "backup_log"):               "nesk3__backup_log",
    # mitarbeiter.db
    ("mitarbeiter.db", "mitarbeiter"):        "ma__mitarbeiter",
    ("mitarbeiter.db", "positionen"):         "ma__positionen",
    ("mitarbeiter.db", "abteilungen"):        "ma__abteilungen",
    # einsaetze.db
    ("einsaetze.db", "einsaetze"):            "einsaetze__einsaetze",
    # verspaetungen.db
    ("verspaetungen.db", "verspaetungen"):    "vers__verspaetungen",
    # telefonnummern.db
    ("telefonnummern.db", "telefonnummern"):  "tel__telefonnummern",
    ("telefonnummern.db", "tel_import_log"):  "tel__import_log",
    # patienten_station.db
    ("patienten_station.db", "patienten"):    "pat__patienten",
    ("patienten_station.db", "medikamente"):  "pat__medikamente",
    ("patienten_station.db", "verbrauchsmaterial"): "pat__verbrauchsmaterial",
    # call_transcription.db
    ("call_transcription.db", "call_logs"):   "call__call_logs",
    ("call_transcription.db", "textbausteine"): "call__textbausteine",
    # psa.db
    ("psa.db", "psa_verstoss"):               "psa__psa_verstoss",
    # stellungnahmen.db
    ("stellungnahmen.db", "stellungnahmen"):  "stelg__stellungnahmen",
}

# Umgekehrtes Mapping: turso_tabelle → (db_pfad_key, lokale_tabelle)
_REVERSE_MAP: dict[str, tuple[str, str]] = {v: k for k, v in TABLE_MAP.items()}

# Tabellen, die NICHT nach Turso synchronisiert werden sollen
_SKIP_TABLES = {"sqlite_sequence", "backup_log"}


# ─── HTTP-Hilfsfunktionen ─────────────────────────────────────────────────────

def _turso_request(sql: str, params: list | None = None) -> dict:
    """Sendet eine SQL-Anfrage an Turso via HTTP und gibt das Ergebnis zurück."""
    cfg = _get_cfg()
    url = cfg.TURSO_URL + "/v2/pipeline"
    stmt: dict = {"sql": sql}
    if params:
        stmt["args"] = [{"type": "text", "value": str(p) if p is not None else None}
                        if p is not None else {"type": "null"} for p in params]
    body = json.dumps({
        "requests": [
            {"type": "execute", "stmt": stmt},
            {"type": "close"}
        ]
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": "Bearer " + cfg.TURSO_TOKEN,
            "Content-Type": "application/json",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _turso_execute_batch(statements: list[dict]) -> None:
    """Führt mehrere SQL-Statements in einem Turso-Request aus."""
    cfg = _get_cfg()
    url = cfg.TURSO_URL + "/v2/pipeline"
    requests = [{"type": "execute", "stmt": s} for s in statements]
    requests.append({"type": "close"})
    body = json.dumps({"requests": requests}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": "Bearer " + cfg.TURSO_TOKEN,
            "Content-Type": "application/json",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode("utf-8"))
        # Auf Fehler prüfen
        for i, res in enumerate(result.get("results", [])):
            if res.get("type") == "error":
                raise RuntimeError(f"Turso-Fehler in Statement {i}: {res.get('error')}")


def _rows_from_turso(turso_table: str) -> list[dict]:
    """Holt alle Zeilen einer Turso-Tabelle als Liste von Dicts."""
    try:
        result = _turso_request(f'SELECT * FROM "{turso_table}"')
        res = result["results"][0]["response"]["result"]
        cols = [c["name"] for c in res["cols"]]
        rows = []
        for row in res["rows"]:
            r = {}
            for col, val in zip(cols, row):
                r[col] = val["value"] if val["type"] != "null" else None
            rows.append(r)
        return rows
    except Exception:
        return []


def _turso_table_exists(turso_table: str) -> bool:
    """Prüft ob eine Tabelle in Turso existiert."""
    try:
        result = _turso_request(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [turso_table]
        )
        rows = result["results"][0]["response"]["result"]["rows"]
        return len(rows) > 0
    except Exception:
        return False


# ─── Schema-Erstellung in Turso ───────────────────────────────────────────────

def _get_local_schema(db_path: str, table: str) -> str | None:
    """Liest das CREATE TABLE Statement aus einer lokalen DB."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _adapt_schema_for_turso(original_sql: str, turso_table: str) -> str:
    """
    Passt ein SQLite CREATE TABLE Statement für Turso an:
    - Tabellenname wird auf den Turso-Prefix-Namen gesetzt
    - IF NOT EXISTS wird hinzugefügt
    - FOREIGN KEY Constraints werden entfernt (Integrität liegt bei lokalem SQLite)
    - REFERENCES-Klauseln werden entfernt (kollidieren mit umbenannten Tabellen)
    """
    import re

    # Tabellenname ersetzen
    sql = re.sub(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"?[\w]+"?',
        f'CREATE TABLE IF NOT EXISTS "{turso_table}"',
        original_sql, flags=re.IGNORECASE
    )

    # FOREIGN KEY ... Zeilen komplett entfernen (mehrzeilig)
    sql = re.sub(
        r',?\s*FOREIGN\s+KEY\s*\([^)]+\)\s*REFERENCES\s+\w+\s*\([^)]+\)(\s*ON\s+(DELETE|UPDATE)\s+\w+(\s+\w+)?)*',
        '', sql, flags=re.IGNORECASE
    )

    # Inline REFERENCES ... ON DELETE/UPDATE entfernen
    sql = re.sub(
        r'\s+REFERENCES\s+\w+\s*\([^)]+\)(\s*ON\s+(DELETE|UPDATE)\s+\w+(\s+\w+)?)*',
        '', sql, flags=re.IGNORECASE
    )

    return sql


def ensure_turso_schema() -> None:
    """Erstellt alle fehlenden Tabellen in Turso basierend auf den lokalen Schemas."""
    cfg = _get_cfg()

    statements = []

    # _sync_meta: speichert wann zuletzt etwas geändert wurde (Delta-Sync)
    statements.append({"sql": (
        'CREATE TABLE IF NOT EXISTS _sync_meta '
        '(key TEXT PRIMARY KEY, value TEXT NOT NULL)'
    )})
    statements.append({"sql": (
        "INSERT OR IGNORE INTO _sync_meta (key, value) "
        "VALUES ('last_modified', '1970-01-01T00:00:00')"
    )})
    # _deletions: Tombstone-Tabelle für Löschungen (PC-übergreifende Sync)
    statements.append({"sql": (
        'CREATE TABLE IF NOT EXISTS _deletions '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'turso_table TEXT NOT NULL, '
        'row_id TEXT NOT NULL, '
        'deleted_at TEXT NOT NULL)'
    )})

    for (db_file, local_table), turso_table in TABLE_MAP.items():
        if local_table in _SKIP_TABLES:
            continue
        db_path = _local_db_path(db_file)
        schema_sql = _get_local_schema(db_path, local_table)
        if schema_sql:
            adapted = _adapt_schema_for_turso(schema_sql, turso_table)
            statements.append({"sql": adapted})

    if statements:
        try:
            _turso_execute_batch(statements)
            print(f"[Turso] Schema eingerichtet ({len(statements)} Tabellen)")
        except Exception as e:
            print(f"[Turso] Schema-Fehler: {e}")


def _local_db_path(db_filename: str) -> str:
    """Gibt den vollen Pfad zu einer lokalen DB-Datei zurück."""
    cfg = _get_cfg()
    return cfg._DB_DIR + "\\" + db_filename


# ─── Push: lokal → Turso ──────────────────────────────────────────────────────

def push_row(db_path: str, table: str, row: dict) -> None:
    """
    Schreibt einen einzelnen Datensatz in Turso (UPSERT).
    Wird nach jedem lokalen Write in einem Background-Thread aufgerufen.
    db_path: vollständiger Pfad zur lokalen .db-Datei
    table:   lokaler Tabellenname
    row:     dict mit den Spaltenwerten
    """
    db_file = _db_filename(db_path)
    turso_table = TABLE_MAP.get((db_file, table))
    if not turso_table or table in _SKIP_TABLES:
        return

    def _do_push():
        try:
            cols = list(row.keys())
            vals = list(row.values())
            placeholders = ", ".join(["?" for _ in cols])
            col_str = ", ".join([f'"{c}"' for c in cols])
            sql = f'INSERT OR REPLACE INTO "{turso_table}" ({col_str}) VALUES ({placeholders})'
            _turso_request(sql, vals)
            _touch_sync_meta()
        except urllib.error.URLError:
            import json
            _outbox_add("upsert_row", turso_table, db_file, table,
                        row_json=json.dumps({k: (str(v) if v is not None else None) for k, v in row.items()}))
        except Exception as e:
            print(f"[Turso] Push-Fehler {turso_table}: {e}")

    threading.Thread(target=_do_push, daemon=True).start()


def _record_deletions(turso_table: str, row_ids: list) -> None:
    """Schreibt Tombstone-Einträge in _deletions für alle übergebenen IDs."""
    if not row_ids:
        return
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    statements = []
    for rid in row_ids:
        statements.append({
            "sql": "INSERT INTO _deletions (turso_table, row_id, deleted_at) VALUES (?, ?, ?)",
            "args": [
                {"type": "text", "value": turso_table},
                {"type": "text", "value": str(rid)},
                {"type": "text", "value": now},
            ]
        })
    try:
        for i in range(0, len(statements), 50):
            _turso_execute_batch(statements[i:i + 50])
    except Exception as e:
        print(f"[Turso] Tombstone-Fehler {turso_table}: {e}")


def _get_turso_ids(turso_table: str, where_sql: str = "", args: list | None = None) -> list:
    """Holt alle IDs einer Turso-Tabelle (optional mit WHERE-Klausel)."""
    try:
        sql = f'SELECT id FROM "{turso_table}"'
        if where_sql:
            sql += " " + where_sql
        result = _turso_request(sql, args)
        rows = result["results"][0]["response"]["result"]["rows"]
        return [row[0]["value"] for row in rows if row[0]["type"] != "null"]
    except Exception:
        return []


def push_delete(db_path: str, table: str, row_id: int) -> None:
    """Löscht einen Datensatz in Turso und schreibt einen Tombstone."""
    db_file = _db_filename(db_path)
    turso_table = TABLE_MAP.get((db_file, table))
    if not turso_table or table in _SKIP_TABLES:
        return

    def _do_delete():
        try:
            _turso_request(f'DELETE FROM "{turso_table}" WHERE id = ?', [row_id])
            _record_deletions(turso_table, [row_id])
            _touch_sync_meta()
        except urllib.error.URLError:
            _outbox_add("delete_id", turso_table, db_file, table, row_id=str(row_id))
        except Exception as e:
            print(f"[Turso] Delete-Fehler {turso_table}: {e}")

    threading.Thread(target=_do_delete, daemon=True).start()


def _touch_sync_meta() -> None:
    """Setzt last_modified in _sync_meta auf den aktuellen UTC-Zeitstempel."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        _turso_request(
            "INSERT OR REPLACE INTO _sync_meta (key, value) VALUES ('last_modified', ?)",
            [now]
        )
    except Exception:
        pass


def _get_turso_last_modified() -> str:
    """Liest last_modified aus Turso (nur 1 Row Read)."""
    try:
        result = _turso_request(
            "SELECT value FROM _sync_meta WHERE key = 'last_modified'"
        )
        rows = result["results"][0]["response"]["result"]["rows"]
        if rows:
            return rows[0][0]["value"]
    except Exception:
        pass
    return "1970-01-01T00:00:00"


# ─── Offline-Outbox: fehlgeschlagene Pushes lokal zwischenspeichern ─────────────────

_OUTBOX_PATH: str | None = None


def _get_outbox_path() -> str:
    global _OUTBOX_PATH
    if _OUTBOX_PATH is None:
        import os
        cfg = _get_cfg()
        _OUTBOX_PATH = os.path.join(cfg._DB_DIR, "_turso_outbox.db")
    return _OUTBOX_PATH


def _outbox_init() -> None:
    """Erstellt die lokale Outbox-Datenbank falls nicht vorhanden."""
    conn = sqlite3.connect(_get_outbox_path(), timeout=5)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_ops (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            op          TEXT NOT NULL,
            turso_table TEXT NOT NULL,
            db_file     TEXT NOT NULL,
            local_table TEXT NOT NULL,
            row_id      TEXT,
            fk_col      TEXT,
            fk_value    TEXT,
            row_json    TEXT,
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _outbox_add(op: str, turso_table: str, db_file: str, local_table: str,
                row_id: str | None = None, fk_col: str | None = None,
                fk_value: str | None = None, row_json: str | None = None) -> None:
    """Speichert eine fehlgeschlagene Turso-Operation im lokalen Outbox."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        _outbox_init()
        conn = sqlite3.connect(_get_outbox_path(), timeout=5)
        conn.execute(
            "INSERT INTO pending_ops "
            "(op, turso_table, db_file, local_table, row_id, fk_col, fk_value, row_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (op, turso_table, db_file, local_table, row_id, fk_col, fk_value, row_json, now)
        )
        conn.commit()
        conn.close()
        print(f"[Turso] Offline – '{op}' in Outbox: {turso_table}")
    except Exception as e:
        print(f"[Turso] Outbox-Fehler beim Speichern: {e}")


def _outbox_flush() -> int:
    """
    Verarbeitet alle ausstehenden Outbox-Operationen.
    Wird im Hintergrund-Thread aufgerufen sobald Turso wieder erreichbar ist.
    """
    import json as _json
    outbox_path = _get_outbox_path()
    try:
        conn = sqlite3.connect(outbox_path, timeout=5)
        conn.row_factory = sqlite3.Row
        ops = [dict(r) for r in conn.execute("SELECT * FROM pending_ops ORDER BY id").fetchall()]
        conn.close()
    except Exception:
        return 0

    if not ops:
        return 0

    flushed_ids: list[int] = []
    for op in ops:
        try:
            op_type     = op["op"]
            turso_table = op["turso_table"]
            db_file     = op["db_file"]
            local_table = op["local_table"]

            if op_type == "upsert_row":
                row = _json.loads(op["row_json"])
                cols    = list(row.keys())
                vals    = [str(v) if v is not None else None for v in row.values()]
                col_str = ", ".join([f'"{c}"' for c in cols])
                ph      = ", ".join(["?" for _ in cols])
                args    = [{"type": "text", "value": v} if v is not None
                           else {"type": "null"} for v in vals]
                _turso_execute_batch([{
                    "sql": f'INSERT OR REPLACE INTO "{turso_table}" ({col_str}) VALUES ({ph})',
                    "args": args
                }])

            elif op_type == "delete_id":
                _turso_request(f'DELETE FROM "{turso_table}" WHERE id = ?', [op["row_id"]])
                _record_deletions(turso_table, [op["row_id"]])

            elif op_type == "delete_fk":
                fk_col, fk_val = op["fk_col"], op["fk_value"]
                ids = _get_turso_ids(turso_table, f'WHERE "{fk_col}" = ?', [str(fk_val)])
                _turso_execute_batch([{
                    "sql": f'DELETE FROM "{turso_table}" WHERE "{fk_col}" = ?',
                    "args": [{"type": "text", "value": str(fk_val)}]
                }])
                _record_deletions(turso_table, ids)

            elif op_type == "replace_fk":
                fk_col, fk_val = op["fk_col"], op["fk_value"]
                db_path = _local_db_path(db_file)
                lc = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
                lc.row_factory = sqlite3.Row
                rows = [dict(r) for r in lc.execute(
                    f'SELECT * FROM "{local_table}" WHERE "{fk_col}" = ?', [fk_val]
                ).fetchall()]
                lc.close()
                old_ids = _get_turso_ids(turso_table, f'WHERE "{fk_col}" = ?', [str(fk_val)])
                stmts: list = [{"sql": f'DELETE FROM "{turso_table}" WHERE "{fk_col}" = ?',
                                "args": [{"type": "text", "value": str(fk_val)}]}]
                for row in rows:
                    cols    = list(row.keys())
                    vals    = [str(v) if v is not None else None for v in row.values()]
                    col_str = ", ".join([f'"{c}"' for c in cols])
                    ph      = ", ".join(["?" for _ in cols])
                    args    = [{"type": "text", "value": v} if v is not None
                               else {"type": "null"} for v in vals]
                    stmts.append({"sql": f'INSERT OR REPLACE INTO "{turso_table}" ({col_str}) VALUES ({ph})',
                                  "args": args})
                _turso_execute_batch(stmts)
                _record_deletions(turso_table, old_ids)

            elif op_type in ("push_table", "clear_table"):
                if op_type == "clear_table":
                    ids = _get_turso_ids(turso_table)
                    _turso_request(f'DELETE FROM "{turso_table}"')
                    _record_deletions(turso_table, ids)
                db_path = _local_db_path(db_file)
                lc = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
                lc.row_factory = sqlite3.Row
                rows = [dict(r) for r in lc.execute(f'SELECT * FROM "{local_table}"').fetchall()]
                lc.close()
                stmts = []
                for row in rows:
                    cols    = list(row.keys())
                    vals    = [str(v) if v is not None else None for v in row.values()]
                    col_str = ", ".join([f'"{c}"' for c in cols])
                    ph      = ", ".join(["?" for _ in cols])
                    args    = [{"type": "text", "value": v} if v is not None
                               else {"type": "null"} for v in vals]
                    stmts.append({"sql": f'INSERT OR REPLACE INTO "{turso_table}" ({col_str}) VALUES ({ph})',
                                  "args": args})
                for i in range(0, len(stmts), 50):
                    _turso_execute_batch(stmts[i:i + 50])

            flushed_ids.append(op["id"])

        except urllib.error.URLError:
            break  # Noch offline – beim nächsten Intervall erneut versuchen
        except Exception as e:
            print(f"[Turso] Outbox Flush Fehler op={op['op']} {op['turso_table']}: {e}")
            flushed_ids.append(op["id"])  # Kaputte Op entfernen, nicht ewig wiederholen

    if flushed_ids:
        conn = sqlite3.connect(outbox_path, timeout=5)
        ph = ",".join(["?"] * len(flushed_ids))
        conn.execute(f"DELETE FROM pending_ops WHERE id IN ({ph})", flushed_ids)
        conn.commit()
        conn.close()
        _touch_sync_meta()
        print(f"[Turso] Outbox: {len(flushed_ids)} ausstehende Operationen übermittelt")

    return len(flushed_ids)


def push_delete_by_fk(db_path: str, table: str, fk_col: str, fk_value) -> None:
    """Löscht alle Datensätze mit einem bestimmten Fremdschlüsselwert in Turso."""
    db_file = _db_filename(db_path)
    turso_table = TABLE_MAP.get((db_file, table))
    if not turso_table or table in _SKIP_TABLES:
        return

    def _do_delete():
        try:
            ids = _get_turso_ids(turso_table, f'WHERE "{fk_col}" = ?', [str(fk_value)])
            _turso_execute_batch([{
                "sql": f'DELETE FROM "{turso_table}" WHERE "{fk_col}" = ?',
                "args": [{"type": "text", "value": str(fk_value)}],
            }])
            _record_deletions(turso_table, ids)
            _touch_sync_meta()
        except urllib.error.URLError:
            _outbox_add("delete_fk", turso_table, db_file, table,
                        fk_col=fk_col, fk_value=str(fk_value))
        except Exception as e:
            print(f"[Turso] FK-Delete-Fehler {turso_table}: {e}")

    threading.Thread(target=_do_delete, daemon=True).start()


def push_clear_table(db_path: str, table: str) -> None:
    """Löscht alle Datensätze einer Turso-Tabelle (Bulk-Clear)."""
    db_file = _db_filename(db_path)
    turso_table = TABLE_MAP.get((db_file, table))
    if not turso_table or table in _SKIP_TABLES:
        return

    def _do_clear():
        try:
            ids = _get_turso_ids(turso_table)
            _turso_request(f'DELETE FROM "{turso_table}"')
            _record_deletions(turso_table, ids)
            _touch_sync_meta()
        except urllib.error.URLError:
            _outbox_add("clear_table", turso_table, db_file, table)
        except Exception as e:
            print(f"[Turso] Clear-Fehler {turso_table}: {e}")

    threading.Thread(target=_do_clear, daemon=True).start()


def push_replace_by_fk(db_path: str, table: str, fk_col: str, fk_value) -> None:
    """
    Löscht alle Turso-Zeilen für fk_col=fk_value und schreibt
    die aktuellen lokalen Zeilen neu (atomisch).
    Für Muster: DELETE alle WHERE fk → INSERT neue Zeilen.
    """
    db_file = _db_filename(db_path)
    turso_table = TABLE_MAP.get((db_file, table))
    if not turso_table or table in _SKIP_TABLES:
        return

    def _do_replace():
        try:
            conn = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f'SELECT * FROM "{table}" WHERE "{fk_col}" = ?', [fk_value]
            ).fetchall()
            rows = [dict(r) for r in rows]
            conn.close()

            old_ids = _get_turso_ids(turso_table, f'WHERE "{fk_col}" = ?', [str(fk_value)])
            statements: list = [{
                "sql": f'DELETE FROM "{turso_table}" WHERE "{fk_col}" = ?',
                "args": [{"type": "text", "value": str(fk_value)}],
            }]
            for row in rows:
                cols = list(row.keys())
                vals = [str(v) if v is not None else None for v in row.values()]
                col_str = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["?" for _ in cols])
                args = [{"type": "text", "value": v} if v is not None
                        else {"type": "null"} for v in vals]
                statements.append({
                    "sql": f'INSERT OR REPLACE INTO "{turso_table}" ({col_str}) VALUES ({placeholders})',
                    "args": args,
                })
            _turso_execute_batch(statements)
            _record_deletions(turso_table, old_ids)
            _touch_sync_meta()
        except urllib.error.URLError:
            _outbox_add("replace_fk", turso_table, db_file, table,
                        fk_col=fk_col, fk_value=str(fk_value))
        except Exception as e:
            print(f"[Turso] Replace-FK-Fehler {turso_table}: {e}")

    threading.Thread(target=_do_replace, daemon=True).start()


def push_table_batch(db_path: str, table: str) -> None:
    """Schreibt alle Zeilen einer lokalen Tabelle nach Turso (Batch-Upload)."""
    db_file = _db_filename(db_path)
    turso_table = TABLE_MAP.get((db_file, table))
    if not turso_table or table in _SKIP_TABLES:
        return

    def _do_batch():
        try:
            conn = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            rows = [dict(r) for r in rows]
            conn.close()
            if not rows:
                return
            statements: list = []
            for row in rows:
                cols = list(row.keys())
                vals = [str(v) if v is not None else None for v in row.values()]
                col_str = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["?" for _ in cols])
                args = [{"type": "text", "value": v} if v is not None
                        else {"type": "null"} for v in vals]
                statements.append({
                    "sql": f'INSERT OR REPLACE INTO "{turso_table}" ({col_str}) VALUES ({placeholders})',
                    "args": args,
                })
            for i in range(0, len(statements), 50):
                _turso_execute_batch(statements[i:i + 50])
            _touch_sync_meta()
        except urllib.error.URLError:
            _outbox_add("push_table", turso_table, db_file, table)
        except Exception as e:
            print(f"[Turso] Batch-Upload-Fehler {turso_table}: {e}")

    threading.Thread(target=_do_batch, daemon=True).start()


# ─── Pull: Turso → lokal ──────────────────────────────────────────────────────

def pull_table(db_path: str, table: str) -> int:
    """
    Holt alle Zeilen einer Turso-Tabelle und schreibt sie in die lokale DB.
    Gibt die Anzahl synchronisierter Zeilen zurück.
    Vorhandene lokale Daten werden per INSERT OR REPLACE aktualisiert.
    """
    db_file = _db_filename(db_path)
    turso_table = TABLE_MAP.get((db_file, table))
    if not turso_table or table in _SKIP_TABLES:
        return 0

    rows = _rows_from_turso(turso_table)
    if not rows:
        return 0

    try:
        conn = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL")
        cols = list(rows[0].keys())
        col_str = ", ".join([f'"{c}"' for c in cols])
        placeholders = ", ".join(["?" for _ in cols])
        sql = f'INSERT OR REPLACE INTO "{table}" ({col_str}) VALUES ({placeholders})'
        conn.executemany(sql, [[r.get(c) for c in cols] for r in rows])
        conn.commit()
        conn.close()
        return len(rows)
    except Exception as e:
        print(f"[Turso] Pull-Fehler {table} ({db_file}): {e}")
        return 0


def pull_deletions(since_ts: str = "1970-01-01T00:00:00") -> int:
    """
    Liest alle Tombstone-Einträge aus _deletions die neuer als since_ts sind
    und löscht die entsprechenden Zeilen in den lokalen Datenbanken.
    """
    try:
        result = _turso_request(
            "SELECT turso_table, row_id FROM _deletions WHERE deleted_at > ? ORDER BY deleted_at",
            [since_ts]
        )
        rows = result["results"][0]["response"]["result"]["rows"]
        if not rows:
            return 0

        # Gruppieren nach DB-Datei und Tabelle
        from collections import defaultdict
        by_db: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            turso_table = row[0]["value"]
            row_id      = row[1]["value"]
            if turso_table in _REVERSE_MAP:
                db_file, local_table = _REVERSE_MAP[turso_table]
                by_db[db_file][local_table].append(row_id)

        total = 0
        for db_file, tables in by_db.items():
            db_path = _local_db_path(db_file)
            try:
                conn = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
                conn.execute("PRAGMA journal_mode = WAL")
                for local_table, ids in tables.items():
                    unique_ids = list(set(ids))
                    conn.executemany(
                        f'DELETE FROM "{local_table}" WHERE id = ?',
                        [(rid,) for rid in unique_ids]
                    )
                    total += len(unique_ids)
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Turso] Deletion-Pull Fehler {db_file}: {e}")

        if total:
            print(f"[Turso] {total} remote Löschungen lokal angewendet")
        return total
    except Exception as e:
        print(f"[Turso] pull_deletions Fehler: {e}")
        return 0


def cleanup_old_deletions(older_than_days: int = 7) -> None:
    """Entfernt Tombstone-Einträge die älter als older_than_days Tage sind."""
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).strftime("%Y-%m-%dT%H:%M:%S")
        _turso_request("DELETE FROM _deletions WHERE deleted_at < ?", [cutoff])
    except Exception:
        pass


def pull_all(since_ts: str = "1970-01-01T00:00:00") -> None:
    """
    Vollständiger Sync: Turso → alle lokalen Datenbanken.
    1. Zuerst Tombstones anwenden (remote Löschungen)
    2. Dann alle Tabellen upserten (neue/geänderte Daten)
    """
    pull_deletions(since_ts)
    total = 0
    errors = 0
    for (db_file, local_table), turso_table in TABLE_MAP.items():
        if local_table in _SKIP_TABLES:
            continue
        db_path = _local_db_path(db_file)
        try:
            n = pull_table(db_path, local_table)
            total += n
        except Exception as e:
            print(f"[Turso] Sync-Fehler {db_file}/{local_table}: {e}")
            errors += 1
    if total > 0 or errors == 0:
        print(f"[Turso] Sync abgeschlossen: {total} Datensätze synchronisiert")
    if errors > 0:
        print(f"[Turso] {errors} Fehler beim Sync")


# ─── Initial-Upload: lokal → Turso ───────────────────────────────────────────

def push_all_local_to_turso() -> None:
    """
    Einmaliger initialer Upload aller lokalen Daten nach Turso.
    Wird nur einmal beim ersten Setup aufgerufen.
    """
    print("[Turso] Starte initialen Upload aller lokalen Daten...")
    total = 0
    for (db_file, local_table), turso_table in TABLE_MAP.items():
        if local_table in _SKIP_TABLES:
            continue
        db_path = _local_db_path(db_file)
        try:
            conn = sqlite3.connect(db_path, timeout=5)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(f'SELECT * FROM "{local_table}"')
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

            if not rows:
                continue

            # Batch-Upload
            statements = []
            for row in rows:
                cols = list(row.keys())
                vals = [str(v) if v is not None else None for v in row.values()]
                col_str = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["?" for _ in cols])
                args = [{"type": "text", "value": v} if v is not None
                        else {"type": "null"} for v in vals]
                statements.append({
                    "sql": f'INSERT OR REPLACE INTO "{turso_table}" ({col_str}) VALUES ({placeholders})',
                    "args": args
                })

            # In Batches von 50 senden
            for i in range(0, len(statements), 50):
                batch = statements[i:i+50]
                _turso_execute_batch(batch)
            total += len(rows)
            print(f"[Turso] Upload: {turso_table} ({len(rows)} Zeilen)")
        except Exception as e:
            print(f"[Turso] Upload-Fehler {db_file}/{local_table}: {e}")

    print(f"[Turso] Initialer Upload abgeschlossen: {total} Datensätze")


# ─── Hintergrund-Thread ───────────────────────────────────────────────────────

_sync_thread: threading.Thread | None = None
_stop_event = threading.Event()
_last_synced_ts: str = "1970-01-01T00:00:00"  # Zeitstempel des letzten erfolgreichen Pulls


def start_background_sync() -> None:
    """
    Startet den Hintergrund-Sync-Thread.
    Prüft alle 30 Sekunden ob sich etwas in Turso geändert hat (1 Row Read).
    Nur bei Änderung: vollständiger Pull aller Daten.
    """
    global _sync_thread
    _stop_event.clear()

    def _loop():
        global _last_synced_ts
        cfg = _get_cfg()
        interval = getattr(cfg, "TURSO_SYNC_INTERVAL", 30)
        _outbox_init()
        cleanup_old_deletions()  # einmal beim Start aufräumen
        while not _stop_event.wait(timeout=interval):
            try:
                # Offline-Änderungen nachholen (Outbox leeren)
                _outbox_flush()
                # Delta-Prüfung: nur pullen wenn sich etwas geändert hat
                remote_ts = _get_turso_last_modified()
                if remote_ts > _last_synced_ts:
                    prev_ts = _last_synced_ts
                    pull_all(since_ts=prev_ts)
                    _last_synced_ts = remote_ts
                # else: nichts geändert → kein Pull
            except Exception as e:
                print(f"[Turso] Hintergrund-Sync Fehler: {e}")

    _sync_thread = threading.Thread(target=_loop, daemon=True, name="TursoSync")
    _sync_thread.start()
    print(f"[Turso] Delta-Sync gestartet (Prüfung alle {_get_cfg().TURSO_SYNC_INTERVAL}s)")


def stop_background_sync() -> None:
    """Stoppt den Hintergrund-Sync-Thread."""
    _stop_event.set()


# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _db_filename(db_path: str) -> str:
    """Extrahiert den Dateinamen (ohne Pfad) aus einem DB-Pfad."""
    import os
    return os.path.basename(db_path)
