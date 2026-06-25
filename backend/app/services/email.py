"""SMTP-based email service for password reset and notifications."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger("序光.email")


def _render_reset_email(reset_url: str, code: str, site_name: str = "序光平台") -> tuple[str, str]:
    """Return (html_body, plain_body) for the password reset email."""
    plain = (
        f"您好，\n\n"
        f"我们收到了您重置密码的请求。请点击以下链接完成密码重置（15 分钟内有效）：\n\n"
        f"{reset_url}\n\n"
        f"您的验证码：{code}\n\n"
        f"如果这不是您本人的操作，请忽略此邮件。\n\n"
        f"{site_name} 团队"
    )
    html = f"""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>重置密码</title>
</head>
<body style="margin: 0; padding: 0; background: #f3f6fb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center" style="padding: 40px 16px;">
                <table width="520" cellpadding="0" cellspacing="0"
                    style="background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(15,23,42,0.06);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 40px 20px;">
                            <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;">
                                序光
                            </h1>
                            <p style="margin: 6px 0 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px;">
                                XUGUANG
                            </p>
                        </td>
                    </tr>
                    <!-- Divider -->
                    <tr>
                        <td style="padding: 0 40px;"><hr style="border: none; border-top: 1px solid #e2e8f0; margin: 0;"></td>
                    </tr>
                    <!-- Body -->
                    <tr>
                        <td style="padding: 28px 40px 20px;">
                            <h2 style="margin: 0 0 12px; font-size: 20px; font-weight: 700; color: #0f172a;">
                                重置你的密码
                            </h2>
                            <p style="margin: 0 0 8px; font-size: 15px; line-height: 1.7; color: #475569;">
                                我们收到了你重置密码的请求，请使用以下验证码完成操作：
                            </p>
                            <!-- Code box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0;">
                                <tr>
                                    <td align="center" style="padding: 18px 24px; background: #f0f6ff; border-radius: 12px;">
                                        <span style="font-size: 28px; font-weight: 800; letter-spacing: 6px; color: #1e40af; font-family: 'Courier New', monospace;">
                                            {code}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                            <!-- Reset button -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 16px 0 24px;">
                                <tr>
                                    <td align="center">
                                        <a href="{reset_url}" style="display: inline-block; padding: 12px 32px; background: #0f172a; border-radius: 12px; color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none;">
                                            重置密码
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #94a3b8;">
                                此验证码和链接 <strong>15 分钟内有效</strong>。如果你没有请求此操作，请忽略此邮件，无需任何操作。
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 16px 40px 32px;">
                            <p style="margin: 0; font-size: 12px; color: #cbd5e1;">
                                {site_name} · 多模型 AI 办公平台
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return html, plain


def send_reset_email(to_email: str, token: str, code: str) -> bool:
    """
    Send a password reset email via SMTP.
    Returns True on success, False on failure.
    """
    settings = get_settings()

    if not settings.smtp_host:
        logger.debug("SMTP host not configured — skipping email send")
        return False

    reset_url = f"{settings.site_url.rstrip('/')}/reset-password?token={token}&code={code}"
    html_body, plain_body = _render_reset_email(reset_url, code, settings.smtp_from_name)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"重置你的密码 — {settings.smtp_from_name}"
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)

        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)

        server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        server.quit()
        logger.info("Password reset email sent to %s", _mask(to_email))
        return True
    except Exception as exc:
        logger.warning("Failed to send password reset email to %s: %s", _mask(to_email), exc)
        return False


def _mask(email: str) -> str:
    """Mask an email address for logging: ab***@example.com"""
    if "@" not in email:
        return email[:2] + "***"
    local, domain = email.rsplit("@", 1)
    return f"{local[:2]}***@{domain}"
