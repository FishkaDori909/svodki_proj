"""Отправка готовой сводки по почте."""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

from .config import MailOut

log = logging.getLogger("svodka")


def _connect(smtp_cfg) -> smtplib.SMTP:
    context = ssl.create_default_context()
    if smtp_cfg.security == "ssl":
        return smtplib.SMTP_SSL(smtp_cfg.server, smtp_cfg.port, timeout=30, context=context)
    conn = smtplib.SMTP(smtp_cfg.server, smtp_cfg.port, timeout=30)
    if smtp_cfg.security == "starttls":
        conn.starttls(context=context)
    return conn


def send_report(mail_cfg: MailOut, src_name: str, attachments, extra_to=()) -> list:
    """Отправляет письмо с вложениями. Возвращает список реально приложенных файлов.
    Вложения, не влезающие в max_attachment_mb, не прикладываются (их перечень — в тексте)."""
    to_list = list(mail_cfg.to)
    seen = {a.lower() for a in to_list}
    for addr in extra_to:
        if addr and addr.lower() not in seen:
            to_list.append(addr)
            seen.add(addr.lower())

    limit = mail_cfg.max_attachment_mb * 1024 * 1024
    attached, skipped, total = [], [], 0
    for f in map(Path, attachments):
        size = f.stat().st_size
        if total + size > limit:
            skipped.append(f)
        else:
            attached.append(f)
            total += size

    body = f"Автоматически собранная сводка по файлу «{src_name}».\n"
    if attached:
        body += f"Вложения: {', '.join(f.name for f in attached)}\n"
    if skipped:
        body += (f"Не приложено (превышен предел {mail_cfg.max_attachment_mb} МБ на письмо): "
                 f"{', '.join(f.name for f in skipped)}. Файлы лежат в папке результатов на сервере.\n")

    msg = EmailMessage()   # сам не даёт вставить перевод строки в заголовки
    msg["From"] = mail_cfg.sender
    msg["To"] = ", ".join(to_list)
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = f"Сводка 2-х час ГПН-Ямал — {Path(src_name).stem}"
    # по этой метке программа узнаёт своё письмо и не принимает его за новый ПОНМ
    msg["X-Svodka-Auto"] = "1"
    msg.set_content(body)
    for f in attached:
        msg.add_attachment(f.read_bytes(), maintype="application", subtype="octet-stream", filename=f.name)

    conn = _connect(mail_cfg.smtp)
    try:
        if mail_cfg.smtp.login:
            conn.login(mail_cfg.smtp.login, mail_cfg.smtp.password)
        conn.send_message(msg, from_addr=mail_cfg.sender, to_addrs=to_list)
    finally:
        try:
            conn.quit()
        except smtplib.SMTPException:
            pass
    return attached
