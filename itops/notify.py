"""Optional alert channels. Secrets are read from environment variables only."""

from __future__ import annotations

import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage


def send_telegram(text: str) -> bool:
    """Send a message via Telegram Bot API.

    Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment.
    Returns False (and sends nothing) if either is missing.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except OSError:
        return False


def send_email(subject: str, body: str) -> bool:
    """Send a plain-text email through SMTP.

    Needs SMTP_HOST, SMTP_FROM, SMTP_TO; optional SMTP_PORT (default 587),
    SMTP_USER and SMTP_PASSWORD. Returns False if the basics are missing.
    """
    host = os.environ.get("SMTP_HOST")
    sender = os.environ.get("SMTP_FROM")
    recipient = os.environ.get("SMTP_TO")
    if not (host and sender and recipient):
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender, recipient
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=15) as smtp:
            smtp.starttls()
            user = os.environ.get("SMTP_USER")
            if user:
                smtp.login(user, os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException):
        return False
