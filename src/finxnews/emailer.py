"""Send the generated newsletter via SMTP (Gmail app-password friendly).

Converts the Markdown content to styled HTML for a clean email experience.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown

logger = logging.getLogger(__name__)

# Inline CSS that works across Gmail, Apple Mail, Outlook, etc.
_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background-color:#f6f6f6;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background-color:#f6f6f6;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0"
       style="max-width:600px; width:100%; background:#ffffff;
              border-radius:8px; overflow:hidden;
              border:1px solid #e0e0e0;">
<tr><td style="padding:32px 28px; font-family:-apple-system,BlinkMacSystemFont,
              'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
              font-size:15px; line-height:1.6; color:#1a1a1a;">
{body}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""

# Extra inline styles injected after the markdown→HTML conversion
_STYLE_OVERRIDES = {
    "h1": (
        "font-size:22px; font-weight:700; margin:0 0 8px 0; "
        "color:#111; border-bottom:2px solid #0d6efd; padding-bottom:8px;"
    ),
    "h2": "font-size:18px; font-weight:600; margin:24px 0 8px 0; color:#222;",
    "h3": "font-size:16px; font-weight:600; margin:20px 0 6px 0; color:#333;",
    "hr": "border:none; border-top:1px solid #ddd; margin:20px 0;",
    "a": "color:#0d6efd; text-decoration:none;",
    "ul": "padding-left:20px; margin:8px 0;",
    "li": "margin-bottom:6px;",
    "p": "margin:8px 0;",
    "em": "color:#555;",
    "strong": "color:#111;",
}


def _md_to_html(md_text: str) -> str:
    """Convert Markdown to email-safe HTML with inline styles."""
    html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code"],
        output_format="html",
    )
    # Inject inline styles for each tag
    for tag, style in _STYLE_OVERRIDES.items():
        html = html.replace(f"<{tag}>", f'<{tag} style="{style}">')
        html = html.replace(f"<{tag} ", f'<{tag} style="{style}" ')
    return _HTML_TEMPLATE.format(body=html)


def send_newsletter(
    *,
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    to_addrs: list[str] | str,
    subject: str,
    body_text: str,
) -> None:
    """Send the newsletter as a styled HTML email with a plain-text fallback
    and the ``.md`` file attached.

    *to_addrs* can be a single address string or a list of addresses.
    Uses STARTTLS on *smtp_port* (typically 587 for Gmail).
    """
    # Normalise to a list
    recipients = [to_addrs] if isinstance(to_addrs, str) else list(to_addrs)

    msg = MIMEMultipart("mixed")
    msg["From"] = username
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # Multipart/alternative: plain-text + HTML (clients pick the best one)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain", "utf-8"))
    alt.attach(MIMEText(_md_to_html(body_text), "html", "utf-8"))
    msg.attach(alt)

    logger.info(
        "Sending newsletter to %s via %s:%d …",
        ", ".join(recipients), smtp_host, smtp_port,
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.sendmail(username, recipients, msg.as_string())

    logger.info("Email sent successfully to %s", ", ".join(recipients))
