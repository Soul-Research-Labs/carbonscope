"""Email notification service.

.. deprecated::
    This module is not actively used in production routes. It exists for
    reference and test coverage only. Prefer async email delivery via a
    task queue (e.g. Celery + SendGrid) for production use.

Sends transactional emails for alerts, reports, and subscription changes.
Configurable via SMTP or API-based providers (SendGrid, SES).
Currently logs emails when SMTP is not configured (development mode).
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────

SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@carbonscope.io")

_smtp_configured = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email. Returns True on success, False on failure."""
    if not _smtp_configured:
        logger.info("Email (dev mode — SMTP not configured): to=%s subject=%s", to, subject)
        logger.debug("Email body: %s", html_body[:200])
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [to], msg.as_string())

        logger.info("Email sent: to=%s subject=%s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def send_alert_email(to: str, alert_title: str, alert_message: str, severity: str) -> bool:
    """Send an alert notification email."""
    color = {"critical": "#dc2626", "warning": "#f59e0b", "info": "#3b82f6"}.get(severity, "#6b7280")
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: {color}; color: white; padding: 16px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">⚠️ CarbonScope Alert</h2>
        </div>
        <div style="border: 1px solid #e5e7eb; padding: 24px; border-radius: 0 0 8px 8px;">
            <h3 style="margin-top: 0;">{alert_title}</h3>
            <p>{alert_message}</p>
            <p style="color: #6b7280; font-size: 12px;">
                This is an automated alert from CarbonScope. Log in to your dashboard for details.
            </p>
        </div>
    </div>
    """
    return send_email(to, f"[CarbonScope] {severity.upper()}: {alert_title}", html)


def send_report_ready_email(to: str, report_year: int, total_emissions: float) -> bool:
    """Send email when a new emission report is ready."""
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #059669; color: white; padding: 16px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">📊 New Emission Report Ready</h2>
        </div>
        <div style="border: 1px solid #e5e7eb; padding: 24px; border-radius: 0 0 8px 8px;">
            <p>Your {report_year} emission report has been generated.</p>
            <p><strong>Total Emissions:</strong> {total_emissions:,.1f} tCO₂e</p>
            <p>Log in to CarbonScope to view the full breakdown, recommendations, and export options.</p>
        </div>
    </div>
    """
    return send_email(to, f"[CarbonScope] {report_year} Emission Report Ready", html)


def send_subscription_change_email(to: str, old_plan: str, new_plan: str) -> bool:
    """Send email when subscription plan changes."""
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #7c3aed; color: white; padding: 16px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">💳 Subscription Updated</h2>
        </div>
        <div style="border: 1px solid #e5e7eb; padding: 24px; border-radius: 0 0 8px 8px;">
            <p>Your subscription has been updated.</p>
            <p><strong>Previous plan:</strong> {old_plan.title()}</p>
            <p><strong>New plan:</strong> {new_plan.title()}</p>
            <p>Log in to your dashboard to see your updated features and credit balance.</p>
        </div>
    </div>
    """
    return send_email(to, f"[CarbonScope] Subscription changed to {new_plan.title()}", html)
