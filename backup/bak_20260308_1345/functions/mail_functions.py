"""
Mail-Funktionen – Outlook-Integration
Erstellt E-Mail-Entwürfe über win32com
"""
from __future__ import annotations
from pathlib import Path


def create_outlook_draft(
    to: str,
    subject: str,
    body_text: str,
    cc: str = "",
    attachment_path: str | None = None,
    attachments: "list[str] | None" = None,
    logo_path: str | None = None,
) -> bool:
    """
    Erstellt einen Outlook-Entwurf und öffnet ihn.

    Parameters
    ----------
    to            : E-Mail-Adresse(n) Empfänger
    subject       : Betreff
    body_text     : Klartext-Nachricht (Zeilenumbrüche werden zu <br>)
    cc            : CC-Adresse(n), optional
    attachment_path : Pfad zur Anhang-Datei, optional
    logo_path     : Pfad zum Inline-Logo, optional

    Returns
    -------
    True bei Erfolg, löst bei Fehler eine Exception aus.
    """
    import win32com.client  # noqa – nur importieren wenn Funktion aufgerufen wird

    try:
        outlook = win32com.client.GetActiveObject("Outlook.Application")
    except Exception:
        outlook = win32com.client.Dispatch("Outlook.Application")

    mail = outlook.CreateItem(0)  # 0 = olMailItem
    mail.To = to
    if cc:
        mail.CC = cc
    mail.Subject = subject

    html_text = body_text.replace("\n", "<br>")

    logo_path_obj = Path(logo_path) if logo_path else None
    has_logo = logo_path_obj and logo_path_obj.exists()

    if has_logo:
        mail.HTMLBody = f"""
<html><body>
<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt;">
{html_text}
</div>
<br><br>
<img src="cid:nesk_logo" alt="DRK Logo" style="max-width:300px;">
</body></html>
"""
        logo_att = mail.Attachments.Add(str(logo_path_obj))
        logo_att.PropertyAccessor.SetProperty(
            "http://schemas.microsoft.com/mapi/proptag/0x3712001F",
            "nesk_logo",
        )
    else:
        mail.HTMLBody = f"""
<html><body>
<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt;">
{html_text}
</div>
</body></html>
"""

    if attachment_path:
        mail.Attachments.Add(str(attachment_path))

    if attachments:
        for _a in attachments:
            if _a:
                mail.Attachments.Add(str(_a))

    mail.Display()
    return True


def create_code19_mail_with_signature(
    to: str,
    cc: str,
    subject: str,
    von_str: str,
    bis_str: str,
    attachment_path: str | None = None,
) -> bool:
    """
    Erstellt eine Code-19-Mail wie das VBS-Script:
    - Signatur wird automatisch aus Outlook übernommen
    - HTML-Body mit Adress-Footer wird vor die Signatur gesetzt
    - Anhang wird eingefügt (falls vorhanden)

    Parameters
    ----------
    to             : Empfänger
    cc             : CC-Adressen
    subject        : Betreff
    von_str        : Von-Datum als String (dd.mm.yyyy)
    bis_str        : Bis-Datum als String (dd.mm.yyyy)
    attachment_path: Pfad zur Excel-Datei, optional
    """
    import win32com.client  # noqa

    try:
        outlook = win32com.client.GetActiveObject("Outlook.Application")
    except Exception:
        outlook = win32com.client.Dispatch("Outlook.Application")

    mail = outlook.CreateItem(0)  # 0 = olMailItem

    # Mail anzeigen damit Outlook die Standardsignatur lädt
    mail.Display()
    signature = mail.HTMLBody  # enthält jetzt die Outlook-Signatur

    mail.To = to
    mail.CC = cc
    mail.Subject = subject

    # HTML-Inhalt (analog zum VBS-Script)
    body_html = (
        "<html><head><meta http-equiv='Content-Type' content='text/html; charset=utf-8'></head>"
        "<body style='font-family:Arial,sans-serif;font-size:12pt;color:#000;'>"
        "<p>Sehr geehrte Frau Eichler,</p>"
        f"<p>anbei die <strong>Code&nbsp;19-Liste</strong> vom {von_str} bis {bis_str}.</p>"
        "<p>Mit freundlichen Grüßen<br>Ihr Team vom <strong>PRM-Service</strong></p>"
        "<hr style='border:none;border-top:1px solid #cccccc;margin:16px 0;'>"
        "<p><strong>Am Köln-Bonn-Airport</strong><br>"
        "Kennedystraße<br>"
        "51147 Köln<br>"
        "Telefon: +49&nbsp;2203&nbsp;40&nbsp;–&nbsp;2323<br>"
        "E-Mail: <a href='mailto:flughafen@drk-koeln.de'>flughafen@drk-koeln.de</a></p>"
        "</body></html>"
    )

    # Neuen Inhalt + Outlook-Signatur zusammenführen
    mail.HTMLBody = body_html + signature

    if attachment_path:
        from pathlib import Path as _Path
        p = _Path(attachment_path)
        if p.exists():
            mail.Attachments.Add(str(p))

    return True
