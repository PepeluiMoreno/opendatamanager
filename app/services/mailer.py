"""Envío de email por SMTP, configurado por entorno. No-op si no hay SMTP
configurado (se registra y se sigue): los avisos son informativos, no críticos.

Variables: ODM_SMTP_HOST, ODM_SMTP_PORT (587), ODM_SMTP_USER, ODM_SMTP_PASSWORD,
ODM_SMTP_FROM, ODM_SMTP_TLS (true).
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import List, Optional

logger = logging.getLogger(__name__)


def smtp_configurado() -> bool:
    return bool(os.environ.get("ODM_SMTP_HOST"))


def enviar_email(destinatario: str, asunto: str, cuerpo: str, html: Optional[str] = None) -> bool:
    host = os.environ.get("ODM_SMTP_HOST")
    if not host or not destinatario:
        return False
    port = int(os.environ.get("ODM_SMTP_PORT", "587"))
    user = os.environ.get("ODM_SMTP_USER")
    pwd = os.environ.get("ODM_SMTP_PASSWORD")
    remite = os.environ.get("ODM_SMTP_FROM") or user or "odm@localhost"
    usar_tls = os.environ.get("ODM_SMTP_TLS", "true").lower() != "false"

    msg = EmailMessage()
    msg["From"] = remite
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.set_content(cuerpo)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(host, port, timeout=30) as s:
            if usar_tls:
                s.starttls(context=ssl.create_default_context())
            if user:
                s.login(user, pwd)
            s.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"[mailer] fallo enviando a {destinatario}: {e}")
        return False
