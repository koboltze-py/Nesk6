"""
dienstplan_html_export.py

Generiert eine vollständig statische HTML-Datei aus dem DienstplanParser-Ergebnis.
Die Datei wird in WebNesk/dienstplan_aktuell.html gespeichert und kann
direkt per file:// im Browser geöffnet werden – kein Web-Server nötig.

Verwendung:
    from functions.dienstplan_html_export import generiere_html, html_pfad
    pfad = generiere_html(display_result)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

# --------------------------------------------------------------------------- #
#  Pfade                                                                       #
# --------------------------------------------------------------------------- #
_BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HTML_PATH = os.path.join(_BASE_DIR, "WebNesk", "dienstplan_aktuell.html")

_TAG_DIENSTE   = frozenset({'T', 'T10', 'T8', 'DT', 'DT3'})
_NACHT_DIENSTE = frozenset({'N', 'N10', 'NF', 'DN', 'DN3'})


def html_pfad() -> str:
    """Gibt den absoluten Pfad der generierten HTML-Datei zurück."""
    return _HTML_PATH


# --------------------------------------------------------------------------- #
#  Kleine Helper                                                               #
# --------------------------------------------------------------------------- #

def _esc(text: str) -> str:
    """Einfaches HTML-Escaping."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _person_row(p: dict, badge_color: str = "#4a90d9") -> str:
    name  = _esc(p.get("anzeigename") or p.get("display_name") or p.get("vollname", "—"))
    dienst = _esc(p.get("dienst_kategorie") or "—")
    von   = _esc(p.get("start_zeit") or "—")
    bis   = _esc(p.get("end_zeit") or "—")
    return (
        f'<tr>'
        f'<td><span class="badge" style="background:{badge_color}">{dienst}</span></td>'
        f'<td class="name">{name}</td>'
        f'<td class="zeit">{von}</td>'
        f'<td class="zeit">{bis}</td>'
        f'</tr>\n'
    )


def _krank_row(p: dict) -> str:
    name   = _esc(p.get("anzeigename") or p.get("display_name") or p.get("vollname", "—"))
    dienst = _esc(p.get("krank_abgeleiteter_dienst") or p.get("dienst_kategorie") or "—")
    von    = _esc(p.get("start_zeit") or "—")
    bis    = _esc(p.get("end_zeit") or "—")
    stype  = p.get("krank_schicht_typ") or "sonderdienst"
    is_d   = p.get("krank_ist_dispo", False)
    label  = ("Dispo" if is_d else "Betreuer") + (" (T)" if stype == "tagdienst" else " (N)" if stype == "nachtdienst" else " (?)")
    return (
        f'<tr class="krank-row">'
        f'<td><span class="badge badge-krank">{_esc(label)}</span></td>'
        f'<td class="name krank-name">{name}</td>'
        f'<td class="zeit krank-dienst">{dienst}</td>'
        f'<td class="zeit">{von} – {bis}</td>'
        f'</tr>\n'
    )


def _section_table(rows_html: str, empty_msg: str = "Keine Einträge") -> str:
    if not rows_html.strip():
        return f'<p class="empty">{_esc(empty_msg)}</p>'
    return (
        '<table>\n'
        '<thead><tr>'
        '<th>Kürzel</th><th>Name</th><th>Von</th><th>Bis</th>'
        '</tr></thead>\n'
        '<tbody>\n'
        + rows_html +
        '</tbody></table>\n'
    )


# --------------------------------------------------------------------------- #
#  HTML-Template                                                               #
# --------------------------------------------------------------------------- #

_CSS = """
:root {
  --bg:         #f4f6f9;
  --card:       #ffffff;
  --border:     #dce8f5;
  --drk-red:    #e30613;
  --drk-dark:   #7a0008;
  --dispo-col:  #0a5ba4;
  --betr-col:   #107e3e;
  --krank-col:  #c0392b;
  --night-col:  #6c3483;
  --text:       #1a1a2a;
  --muted:      #888;
  --header-bg:  #1a1a2e;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}
header {
  background: var(--header-bg);
  color: white;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 3px solid var(--drk-red);
}
.logo { font-size: 2rem; font-weight: 900; color: var(--drk-red); letter-spacing: -1px; }
.header-title { font-size: 1.2rem; font-weight: 700; }
.header-sub   { font-size: 0.8rem; color: #aaa; margin-top: 2px; }
.header-right { margin-left: auto; text-align: right; font-size: 0.8rem; color: #ccc; }
.stand { font-size: 0.7rem; color: #aaa; }

.top-bar {
  background: white;
  border-bottom: 1px solid var(--border);
  padding: 8px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.top-bar button {
  background: var(--dispo-col);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 7px 18px;
  font-size: 0.88rem;
  cursor: pointer;
  font-weight: 600;
}
.top-bar button:hover { opacity: 0.85; }
.refresh-hint { font-size: 0.77rem; color: var(--muted); }

main { padding: 20px 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media (max-width: 900px) { main { grid-template-columns: 1fr; } }

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.card.full-width { grid-column: 1 / -1; }
.card-header {
  padding: 10px 16px;
  font-weight: 700;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
}
.card-header.tag    { background: var(--dispo-col); }
.card-header.nacht  { background: var(--night-col); }
.card-header.krank  { background: var(--krank-col); }
.sub-header {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--muted);
  padding: 6px 16px 2px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border);
  background: #fafbfd;
}
table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
thead tr { background: #f0f4f8; }
th { padding: 6px 10px; font-size: 0.78rem; font-weight: 700; text-align: left; color: var(--muted); border-bottom: 1px solid var(--border); }
td { padding: 5px 10px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f8fbff; }
.name  { font-weight: 600; }
.zeit  { color: #555; font-size: 0.82rem; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: 700;
  color: white;
  white-space: nowrap;
}
.badge-krank { background: var(--krank-col); }
.krank-row td { opacity: 0.9; }
.krank-name { text-decoration: line-through; color: var(--krank-col); }
.krank-dienst { color: var(--muted); font-size: 0.8rem; }
.empty { color: var(--muted); font-size: 0.85rem; padding: 12px 16px; font-style: italic; }
.count-badge {
  margin-left: auto;
  background: rgba(255,255,255,0.25);
  border-radius: 10px;
  padding: 1px 8px;
  font-size: 0.75rem;
  font-weight: 700;
}
"""

_JS = """
function reloadPage() {
    location.reload();
}
// Zeigt die Zeit seit der letzten Generierung an
(function() {
    var genTs = document.getElementById('gen-ts');
    if (!genTs) return;
    var ts = parseInt(genTs.dataset.ts, 10);
    function update() {
        var diff = Math.round((Date.now() - ts * 1000) / 60000);
        var txt = diff < 1 ? 'gerade eben' : 'vor ' + diff + ' Min.';
        var el = document.getElementById('stand-relative');
        if (el) el.textContent = txt;
    }
    update();
    setInterval(update, 30000);
})();
"""


# --------------------------------------------------------------------------- #
#  Haupt-Export-Funktion                                                       #
# --------------------------------------------------------------------------- #

def generiere_html(display_result: dict) -> str:
    """
    Generiert die HTML-Datei aus dem DienstplanParser-Ergebnis.

    Args:
        display_result: Rückgabe von DienstplanParser(..., alle_anzeigen=True).parse()

    Returns:
        Absoluter Pfad zur generierten HTML-Datei.

    Raises:
        ValueError: Wenn display_result['success'] == False.
        IOError: Bei Schreibfehler.
    """
    if not display_result.get("success"):
        raise ValueError(
            f"Dienstplan konnte nicht geparst werden: {display_result.get('error')}"
        )

    now    = datetime.now()
    datum  = display_result.get("datum") or now.strftime("%d.%m.%Y")
    quelle = os.path.basename(display_result.get("excel_path", "—"))
    ts_int = int(now.timestamp())
    ts_str = now.strftime("%d.%m.%Y %H:%M")

    betreuer_alle = display_result.get("betreuer", [])
    dispo_alle    = display_result.get("dispo", [])
    kranke_alle   = display_result.get("kranke", [])

    # ── Tagdienste ────────────────────────────────────────────────────────────
    betr_tag  = [p for p in betreuer_alle if (p.get("dienst_kategorie") or "").upper() in _TAG_DIENSTE]
    dispo_tag = [p for p in dispo_alle    if (p.get("dienst_kategorie") or "").upper() in _TAG_DIENSTE]

    # ── Nachtdienste ──────────────────────────────────────────────────────────
    betr_nacht  = [p for p in betreuer_alle if (p.get("dienst_kategorie") or "").upper() in _NACHT_DIENSTE]
    dispo_nacht = [p for p in dispo_alle    if (p.get("dienst_kategorie") or "").upper() in _NACHT_DIENSTE]

    # Sonstiges
    betr_sond  = [p for p in betreuer_alle if p not in betr_tag  and p not in betr_nacht]
    dispo_sond = [p for p in dispo_alle    if p not in dispo_tag and p not in dispo_nacht]

    # ── Krank-Gruppen ─────────────────────────────────────────────────────────
    krank_tag_dispo   = [p for p in kranke_alle if p.get("krank_schicht_typ") == "tagdienst"   and     p.get("krank_ist_dispo")]
    krank_tag_betr    = [p for p in kranke_alle if p.get("krank_schicht_typ") == "tagdienst"   and not p.get("krank_ist_dispo")]
    krank_nacht_dispo = [p for p in kranke_alle if p.get("krank_schicht_typ") == "nachtdienst" and     p.get("krank_ist_dispo")]
    krank_nacht_betr  = [p for p in kranke_alle if p.get("krank_schicht_typ") == "nachtdienst" and not p.get("krank_ist_dispo")]
    krank_sonder      = [p for p in kranke_alle
                         if p not in krank_tag_dispo and p not in krank_tag_betr
                         and p not in krank_nacht_dispo and p not in krank_nacht_betr]

    # ── HTML-Bausteine ────────────────────────────────────────────────────────

    def _rows_for(lst: list, color: str) -> str:
        return "".join(_person_row(p, color) for p in lst)

    def _section_card(cls: str, icon: str, title: str, count: int,
                      dispo_lst: list, betr_lst: list,
                      sond_lst: Optional[list] = None,
                      full_width: bool = False) -> str:
        fw = " full-width" if full_width else ""
        dispo_color = "#0a5ba4" if cls == "tag" else "#6c3483"
        betr_color  = "#107e3e" if cls == "tag" else "#6c3483"

        dispo_rows = _rows_for(dispo_lst, dispo_color)
        betr_rows  = _rows_for(betr_lst, betr_color)
        sond_html  = ""
        if sond_lst:
            sond_rows = _rows_for(sond_lst, "#888")
            if sond_rows.strip():
                sond_html = (
                    '<div class="sub-header">Sonstiges</div>'
                    + _section_table(sond_rows, "Keine Sonstigen")
                )

        html = f'<div class="card{fw}">\n'
        html += f'  <div class="card-header {cls}">{icon} {_esc(title)} <span class="count-badge">{count}</span></div>\n'
        if dispo_rows.strip():
            html += '<div class="sub-header">Dispo</div>'
            html += _section_table(dispo_rows)
        if betr_rows.strip():
            html += '<div class="sub-header">Betreuer</div>'
            html += _section_table(betr_rows)
        if not dispo_rows.strip() and not betr_rows.strip():
            html += '<p class="empty">Keine Einträge</p>'
        html += sond_html
        html += '</div>\n'
        return html

    total_tag   = len(betr_tag) + len(dispo_tag)
    total_nacht = len(betr_nacht) + len(dispo_nacht)
    total_sond  = len(betr_sond) + len(dispo_sond)
    total_krank = len(kranke_alle)

    tag_card   = _section_card("tag",   "☀️",  "Tagdienst",   total_tag,   dispo_tag,   betr_tag,   dispo_sond + betr_sond if total_sond else None)
    nacht_card = _section_card("nacht", "🌙",  "Nachtdienst", total_nacht, dispo_nacht, betr_nacht)

    # Krank-Karte
    krank_rows = ""
    for group, label in (
        (krank_tag_dispo,   "Krank – Tagdienst Dispo"),
        (krank_tag_betr,    "Krank – Tagdienst Betreuer"),
        (krank_nacht_dispo, "Krank – Nachtdienst Dispo"),
        (krank_nacht_betr,  "Krank – Nachtdienst Betreuer"),
        (krank_sonder,      "Krank – Sonstiges"),
    ):
        if group:
            krank_rows += f'<div class="sub-header">{_esc(label)}</div>'
            krank_rows += _section_table("".join(_krank_row(p) for p in group))

    krank_card = (
        f'<div class="card full-width">\n'
        f'  <div class="card-header krank">🤒 Krank / Abwesend <span class="count-badge">{total_krank}</span></div>\n'
        + (krank_rows if krank_rows.strip() else '<p class="empty">Keine Krankmeldungen</p>')
        + '</div>\n'
    )

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dienstplan {_esc(datum)} – DRK Köln e.V.</title>
<style>{_CSS}</style>
</head>
<body>

<header>
  <div class="logo">DRK</div>
  <div>
    <div class="header-title">Dienstplan – EHS Flughafen Köln/Bonn</div>
    <div class="header-sub">DRK Kreisverband Köln e.V.</div>
  </div>
  <div class="header-right">
    <div style="font-size:1.1rem;font-weight:700;">{_esc(datum)}</div>
    <div class="stand">
      Stand: {_esc(ts_str)}
      &nbsp;·&nbsp;
      <span id="stand-relative" style="color:#e8a0a0;"></span>
    </div>
    <div class="stand" style="margin-top:3px;color:#777;">{_esc(quelle)}</div>
    <span id="gen-ts" data-ts="{ts_int}" style="display:none;"></span>
  </div>
</header>

<div class="top-bar">
  <button onclick="reloadPage()">🔄&nbsp; Seite neu laden</button>
  <span class="refresh-hint">
    Diese Seite zeigt den Stand vom letzten Klick auf „Als Webseite anzeigen" in Nesk3.
    Klicke in Nesk3 erneut auf den Button, um die Seite zu aktualisieren.
  </span>
</div>

<main>
  {tag_card}
  {nacht_card}
  {krank_card}
</main>

<script>{_JS}</script>
</body>
</html>
"""

    # ── In Datei schreiben ────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(_HTML_PATH), exist_ok=True)
    with open(_HTML_PATH, "w", encoding="utf-8") as fh:
        fh.write(html)

    return _HTML_PATH
