"""SMTP email sender for daily summary. Gracefully skips if SMTP not configured.

Supports multiple env variable naming conventions:
- SMTP_HOST (required)
- SMTP_PORT (default: 587)
- SMTP_USER or SMTP_USERNAME (required)
- SMTP_PASS or SMTP_PASSWORD (required)
- SMTP_TO or TO_EMAIL (optional, default: xu.r@wustl.edu)
"""
import os
import smtplib
from email.message import EmailMessage
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def send_daily_summary(
    subject: str,
    body_html: str,
    attachments: Optional[List[str]] = None,
    to_addr: str = 'xu.r@wustl.edu'
) -> Dict[str, str]:
    """Send HTML email with optional file attachments.
    
    Gracefully skips if SMTP not fully configured.
    
    Args:
        subject: Email subject
        body_html: HTML body content
        attachments: List of file paths to attach (optional)
        to_addr: Recipient email address
        
    Returns:
        {'status': 'sent'|'skipped', 'reason': optional_explanation}
    """
    # Read SMTP config with fallback naming
    smtp_host = os.getenv('SMTP_HOST', '').strip()
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '') or os.getenv('SMTP_USERNAME', '')
    smtp_pass = os.getenv('SMTP_PASS', '') or os.getenv('SMTP_PASSWORD', '')
    email_from = os.getenv('EMAIL_FROM', '').strip()
    if not email_from:
        email_from = smtp_user or 'agent@example.com'

    # Check if SMTP is configured
    if not smtp_host or not smtp_user or not smtp_pass:
        logger.info('SMTP not fully configured (missing SMTP_HOST, SMTP_USER/USERNAME, or SMTP_PASS/PASSWORD); skipping email send')
        return {
            'status': 'skipped',
            'reason': 'smtp_not_configured'
        }

    try:
        # Build message
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = email_from
        msg['To'] = to_addr
        msg.set_content(body_html, subtype='html')

        # Attach files if provided
        for filepath in (attachments or []):
            try:
                fpath = Path(filepath)
                if fpath.exists() and fpath.is_file():
                    with open(fpath, 'rb') as f:
                        data = f.read()
                    msg.add_attachment(
                        data,
                        maintype='application',
                        subtype='octet-stream',
                        filename=fpath.name
                    )
                    logger.debug(f"Attached file: {fpath.name}")
                else:
                    logger.warning(f"Attachment file not found: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to attach {filepath}: {e}")

        # Send via SMTP
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_addr}")
        return {
            'status': 'sent'
        }

    except smtplib.SMTPAuthenticationError as e:
        logger.warning(f"SMTP authentication failed: {e}")
        return {
            'status': 'skipped',
            'reason': 'auth_failed'
        }
    except smtplib.SMTPException as e:
        logger.warning(f"SMTP error: {e}")
        return {
            'status': 'skipped',
            'reason': f'smtp_error: {str(e)[:50]}'
        }
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return {
            'status': 'skipped',
            'reason': f'unexpected_error: {str(e)[:50]}'
        }
