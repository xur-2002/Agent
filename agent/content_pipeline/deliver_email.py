"""Email delivery for article drafts."""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmailSender:
    """Send emails with article drafts."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_pass: str
    ):
        """Initialize email sender.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP port (usually 587 for TLS, 465 for SSL)
            smtp_user: SMTP username/email
            smtp_pass: SMTP password
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
    
    def send_article_email(
        self,
        recipients: List[str],
        subject: str,
        title: str,
        summary_bullets: List[str],
        body_html: str,
        cover_image_path: Optional[Path] = None,
        article_link: Optional[str] = None
    ) -> bool:
        """Send article draft email.
        
        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            title: Article title
            summary_bullets: List of bullet points
            body_html: Article body as HTML
            cover_image_path: Optional cover image file path
            article_link: Optional link to article in repo
            
        Returns:
            True if sent successfully
        """
        try:
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = ", ".join(recipients)
            
            # Build HTML email
            html_content = self._build_html_email(
                title,
                summary_bullets,
                body_html,
                article_link
            )
            
            msg_alt = MIMEMultipart("alternative")
            msg.attach(msg_alt)
            
            # Attach HTML
            msg_alt.attach(MIMEText(html_content, "html"))
            
            # Attach cover image if provided
            if cover_image_path and cover_image_path.exists():
                try:
                    with open(cover_image_path, "rb") as img_file:
                        img = MIMEImage(img_file.read(), name="cover.png")
                        img.add_header("Content-ID", "<cover>")
                        img.add_header("Content-Disposition", "inline", filename="cover.png")
                        msg_alt.attach(img)
                except Exception as e:
                    logger.warning(f"Failed to attach cover image: {e}")
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.info(f"Email sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _build_html_email(
        self,
        title: str,
        summary_bullets: List[str],
        body_html: str,
        article_link: Optional[str] = None
    ) -> str:
        """Build HTML email content.
        
        Args:
            title: Article title
            summary_bullets: List of summary bullets
            body_html: Article body HTML
            article_link: Optional link
            
        Returns:
            HTML string
        """
        bullets_html = "".join(
            f"<li>{bullet}</li>" for bullet in summary_bullets
        )
        
        link_section = ""
        if article_link:
            link_section = f'<p><a href="{article_link}" style="color: #0066cc;">View Full Article</a></p>'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #000; margin-bottom: 20px; }}
                .cover {{ margin: 20px 0; text-align: center; }}
                .cover img {{ max-width: 100%; height: auto; border-radius: 8px; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-left: 4px solid #0066cc; margin: 20px 0; }}
                .summary ul {{ margin: 10px 0; padding-left: 20px; }}
                .body {{ margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{title}</h1>
                
                <div class="cover">
                    <img src="cid:cover" alt="Cover Image" style="max-width: 100%; border-radius: 8px;">
                </div>
                
                <div class="summary">
                    <h3>Key Points</h3>
                    <ul>
                        {bullets_html}
                    </ul>
                </div>
                
                <div class="body">
                    {body_html}
                </div>
                
                {link_section}
                
                <div class="footer">
                    <p>This is an auto-generated article draft. Please review before publishing.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
