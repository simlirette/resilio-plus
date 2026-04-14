from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText


def send_reset_email(to_email: str, reset_url: str) -> None:
    """Send a password reset email via SMTP STARTTLS.

    Reads SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM from env.
    """
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", user)

    body = (
        f"You requested a password reset for your Resilio+ account.\n\n"
        f"Click the link below to set a new password (valid for 1 hour):\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, ignore this email."
    )
    msg = MIMEText(body)
    msg["Subject"] = "Reset your Resilio+ password"
    msg["From"] = from_addr
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
