"""SMTP email sender for daily summary. Skips if SMTP not configured.
"""
import os
import smtplib
from email.message import EmailMessage
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def send_daily_summary(subject: str, body_html: str, attachments: Optional[List[str]] = None, to_addr: str = 'xu.r@wustl.edu') -> Dict[str, str]:
    # Minimal safe wrapper: if SMTP not configured, skip
    smtp_host = os.getenv('SMTP_HOST', '')
    smtp_port = int(os.getenv('SMTP_PORT', '587') or 587)
    smtp_user = os.getenv('SMTP_USERNAME', '')
    smtp_pass = os.getenv('SMTP_PASSWORD', '')
    email_from = os.getenv('EMAIL_FROM', smtp_user or 'agent@example.com')

    result = {'status': 'skipped', 'reason': 'smtp_not_configured'}
    if not smtp_host or not smtp_user or not smtp_pass:
        logger.info('SMTP not fully configured; skipping email send')
        return result

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = email_from
    msg['To'] = to_addr
    msg.set_content(body_html, subtype='html')

    # Attach files if provided
    for path in (attachments or []):
        try:
            with open(path, 'rb') as f:
                data = f.read()
            msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=path.split('/')[-1])
        except Exception as e:
            logger.warning(f'Failed to attach {path}: {e}')

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        result.update({'status': 'sent'})
        return result
    except Exception as e:
        logger.warning(f'Failed to send email: {e}')
        result.update({'status': 'skipped', 'reason': str(e)})
        return result
