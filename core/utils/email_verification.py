# core/utils/email_verification.py
import os
import time
import logging
import secrets
from datetime import timedelta
from urllib.parse import urljoin
from socket import timeout as SocketTimeout
import smtplib

from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Config via settings with sane defaults
EMAIL_ENABLED = getattr(settings, "EMAIL_ENABLED", True)
EMAIL_TIMEOUT = int(getattr(settings, "EMAIL_TIMEOUT", 10))  # seconds
DEFAULT_FROM_EMAIL = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
FRONTEND_URL = getattr(settings, "FRONTEND_URL", "https://checkupdate-tau.vercel.app/")
SUPPORT_EMAIL = getattr(settings, "SUPPORT_EMAIL", "security@checkupdate.ng")
COMPANY_NAME = getattr(settings, "COMPANY_NAME", "CheckUpdate")


def generate_verification_token():
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)


def generate_verification_link(user):
    """Generate token, store it on the user, and return full verification URL"""
    token = generate_verification_token()
    expires_at = timezone.now() + timedelta(hours=24)

    # Consider hashing token before saving in DB for extra security.
    user.verification_token = token
    user.verification_token_expires = expires_at
    user.save(update_fields=["verification_token", "verification_token_expires"])

    base_url = (
        FRONTEND_URL.rstrip("/")
        if FRONTEND_URL
        else "https://checkupdate-tau.vercel.app/"
    )
    path = f"/verify-email?token={token}&email={user.email}"
    link = urljoin(base_url + "/", path.lstrip("/"))

    return {"token": token, "link": link, "expires_at": expires_at}


def generate_password_reset_link(token, user):
    base_url = (
        FRONTEND_URL.rstrip("/")
        if FRONTEND_URL
        else "https://checkupdate-tau.vercel.app/"
    )
    path = f"/reset-password?token={token}&email={user.email}"
    return urljoin(base_url + "/", path.lstrip("/"))


def _render_templates(template_name: str, context: dict):
    """Return (plain_message, html_message). Falls back cleanly if templates missing."""
    html_message = None
    plain_message = None

    try:
        html_message = render_to_string(f"{template_name}.html", context)
    except TemplateDoesNotExist:
        logger.debug("HTML template %s not found", f"{template_name}.html")

    try:
        plain_message = render_to_string(f"{template_name}.txt", context)
    except TemplateDoesNotExist:
        # Fallback plain text
        if "verification_link" in context:
            plain_message = f"Please verify your email: {context['verification_link']}"
        elif "reset_link" in context:
            plain_message = f"Reset your password: {context['reset_link']}"
        else:
            plain_message = "Please check your email for further instructions."

        logger.debug(
            "Text template %s not found; using fallback", f"{template_name}.txt"
        )

    return plain_message, html_message


def send_email_with_template(
    subject, template_name, context, recipient_list, fail_silently=True
):
    """
    Synchronous email send (blocking). Uses explicit SMTP connection with timeout.
    Returns True on success, False on failure.
    """
    if not EMAIL_ENABLED:
        logger.info(
            "EMAIL_ENABLED=False. Skipping send for '%s' to %s", subject, recipient_list
        )
        return True

    if not recipient_list:
        logger.warning("No recipients provided for email subject=%s", subject)
        return False

    start = time.time()

    plain_message, html_message = _render_templates(template_name, context)

    # Build email
    from_email = DEFAULT_FROM_EMAIL
    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_message or "",
        from_email=from_email,
        to=recipient_list,
    )
    if html_message:
        msg.attach_alternative(html_message, "text/html")

    # Use a connection with explicit timeout. get_connection will read from EMAIL_* settings.
    # We explicitly open/close to avoid implicit per-message connection overhead.
    connection = None
    try:
        connection = get_connection(timeout=EMAIL_TIMEOUT)  # uses settings by default
        connection.open()
        num_sent = connection.send_messages(
            [msg]
        )  # returns number of successfully sent messages
        duration = time.time() - start

        if num_sent and num_sent >= 1:
            logger.info(
                "Email '%s' sent to %s (duration=%.2fs)",
                subject,
                recipient_list,
                duration,
            )
            return True
        else:
            logger.error(
                "Email '%s' failed to send to %s (duration=%.2fs)",
                subject,
                recipient_list,
                duration,
            )
            return False

    except (SocketTimeout, smtplib.SMTPException) as e:
        duration = time.time() - start
        logger.exception(
            "SMTP error sending '%s' to %s (duration=%.2fs): %s",
            subject,
            recipient_list,
            duration,
            e,
        )
        if not fail_silently:
            raise
        return False

    except Exception as e:
        duration = time.time() - start
        logger.exception(
            "Unexpected error sending '%s' to %s (duration=%.2fs): %s",
            subject,
            recipient_list,
            duration,
            e,
        )
        if not fail_silently:
            raise
        return False

    finally:
        try:
            if connection:
                connection.close()
        except Exception:
            logger.debug("Error closing email connection", exc_info=True)


def send_verification_email_sync(user, fail_silently=True):
    """Synchronous verification email send"""
    try:
        verification_data = generate_verification_link(user)

        context = {
            "user": user,
            "verification_link": verification_data["link"],
            "expiration_hours": 24,
            "support_email": SUPPORT_EMAIL,
            "company_name": COMPANY_NAME,
        }

        return send_email_with_template(
            subject="Verify Your Email Address",
            template_name="verify_email",
            context=context,
            recipient_list=[user.email],
            fail_silently=fail_silently,
        )

    except Exception as e:
        logger.exception(
            "Failed to send verification email to %s: %s",
            getattr(user, "email", "<unknown>"),
            e,
        )
        if not fail_silently:
            raise
        return False


def send_password_reset_email_sync(user, token, fail_silently=True):
    """Synchronous password reset email send"""
    try:
        reset_link = generate_password_reset_link(token, user)

        context = {
            "user": user,
            "reset_link": reset_link,
            "expiration_hours": 24,
            "support_email": SUPPORT_EMAIL,
            "company_name": COMPANY_NAME,
        }

        return send_email_with_template(
            subject="Reset Your Password",
            template_name="password_reset",
            context=context,
            recipient_list=[user.email],
            fail_silently=fail_silently,
        )

    except Exception as e:
        logger.exception(
            "Failed to send password reset email to %s: %s",
            getattr(user, "email", "<unknown>"),
            e,
        )
        if not fail_silently:
            raise
        return False


# convenience/backwards-compatible aliases if other modules call these names
def send_verification_email(user, fail_silently=True):
    return send_verification_email_sync(user, fail_silently=fail_silently)


def send_password_reset_email(user, token, fail_silently=True):
    return send_password_reset_email_sync(user, token, fail_silently=fail_silently)


def test_email_connection():
    """Test email connection and configuration"""
    try:
        connection = get_connection(timeout=EMAIL_TIMEOUT)
        connection.open()
        connection.close()
        logger.info("Email connection test successful")
        return True
    except Exception as e:
        logger.exception("Email connection test failed: %s", e)
        return False
