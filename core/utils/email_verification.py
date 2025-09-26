import logging
import threading
from urllib.parse import urljoin
from socket import timeout as SocketTimeout
import smtplib

from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import secrets

logger = logging.getLogger(__name__)

# Global flag to track if email is configured
EMAIL_ENABLED = True


def generate_verification_token():
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)


def generate_verification_link(user):
    """Generate token, store it on the user, and return full verification URL"""
    token = generate_verification_token()
    expires_at = timezone.now() + timezone.timedelta(hours=24)

    user.verification_token = token
    user.verification_token_expires = expires_at
    user.save(update_fields=['verification_token', 'verification_token_expires'])

    # Safely get FRONTEND_URL with fallback
    base_url = getattr(settings, 'FRONTEND_URL', 'http://127.0.0.1:3000')
    base_url = base_url.rstrip('/') if base_url else 'http://127.0.0.1:3000'

    path = f'/verify-email?token={token}&email={user.email}'
    link = urljoin(base_url + '/', path.lstrip('/'))

    return {
        'token': token,
        'link': link,
        'expires_at': expires_at
    }


def generate_password_reset_link(token, user):
    """Generate password reset URL"""
    base_url = getattr(settings, 'FRONTEND_URL', "http://127.0.0.1:3000")
    base_url = base_url.rstrip('/') if base_url else 'http://127.0.0.1:3000'

    path = f'/reset-password?token={token}&email={user.email}'
    return urljoin(base_url + '/', path.lstrip('/'))


def send_email_with_template(subject, template_name, context, recipient_list, fail_silently=True):
    """
    Generic function to send emails using Django's email system
    """
    # Check if email is enabled
    if not EMAIL_ENABLED:
        logger.info(f"Email sending disabled. Would send '{subject}' to {recipient_list}")
        return True

    try:
        # Render HTML template
        try:
            html_message = render_to_string(f'{template_name}.html', context)
        except TemplateDoesNotExist:
            html_message = None
            logger.warning(f"HTML template {template_name}.html not found")

        # Render text template
        try:
            plain_message = render_to_string(f'{template_name}.txt', context)
        except TemplateDoesNotExist:
            # Fallback plain text message
            if 'verification_link' in context:
                plain_message = f"Please verify your email: {context['verification_link']}"
            elif 'reset_link' in context:
                plain_message = f"Reset your password: {context['reset_link']}"
            else:
                plain_message = "Please check your email for further instructions."
            logger.warning(f"Text template {template_name}.txt not found, using fallback")

        # Create email message
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=recipient_list
        )

        if html_message:
            msg.attach_alternative(html_message, "text/html")

        # Send email with timeout handling
        try:
            result = msg.send(fail_silently=fail_silently)

            if result:
                logger.info(f"Email sent successfully to {', '.join(recipient_list)}")
                return True
            else:
                logger.error(f"Failed to send email to {', '.join(recipient_list)}")
                return False

        except (SocketTimeout, smtplib.SMTPException) as e:
            logger.error(f"SMTP error sending to {recipient_list}: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error sending email to {', '.join(recipient_list)}: {str(e)}")
        if not fail_silently:
            raise
        return False


# ASYNC FUNCTIONS - Use these in your views
def send_verification_email_async(user, fail_silently=True):
    """Send verification email in a separate thread (NON-BLOCKING)"""

    def _send_email():
        try:
            send_verification_email_sync(user, fail_silently)
        except Exception as e:
            logger.error(f"Async verification email failed: {str(e)}")

    # Start email sending in background thread
    thread = threading.Thread(target=_send_email)
    thread.daemon = True  # Thread won't block program exit
    thread.start()

    # Always return True immediately - don't wait for email to send
    logger.info(f"Verification email queued for {user.email}")
    return True


def send_password_reset_email_async(user, token, fail_silently=True):
    """Send password reset email in a separate thread (NON-BLOCKING)"""

    def _send_email():
        try:
            send_password_reset_email_sync(user, token, fail_silently)
        except Exception as e:
            logger.error(f"Async password reset email failed: {str(e)}")

    # Start email sending in background thread
    thread = threading.Thread(target=_send_email)
    thread.daemon = True  # Thread won't block program exit
    thread.start()

    # Always return True immediately - don't wait for email to send
    logger.info(f"Password reset email queued for {user.email}")
    return True


# SYNC FUNCTIONS - Used by async functions internally
def send_verification_email_sync(user, fail_silently=True):
    """Synchronous version of verification email (used internally)"""
    try:
        verification_data = generate_verification_link(user)

        context = {
            'user': user,
            'verification_link': verification_data['link'],
            'expiration_hours': 24,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'security@checkupdate.ng'),
            'company_name': getattr(settings, 'COMPANY_NAME', 'CheckUpdate'),
        }

        success = send_email_with_template(
            subject='Verify Your Email Address',
            template_name='verify_email',
            context=context,
            recipient_list=[user.email],
            fail_silently=fail_silently
        )

        if success:
            logger.info(f"Verification email sent to {user.email}")
        else:
            logger.error(f"Failed to send verification email to {user.email}")

        return success

    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        if not fail_silently:
            raise
        return False


def send_password_reset_email_sync(user, token, fail_silently=True):
    """Synchronous version of password reset email (used internally)"""
    try:
        reset_link = generate_password_reset_link(token, user)

        context = {
            'user': user,
            'reset_link': reset_link,
            'expiration_hours': 24,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'security@checkupdate.ng'),
            'company_name': getattr(settings, 'COMPANY_NAME', 'CheckUpdate'),
        }

        success = send_email_with_template(
            subject='Reset Your Password',
            template_name='password_reset',
            context=context,
            recipient_list=[user.email],
            fail_silently=fail_silently
        )

        if success:
            logger.info(f"Password reset email sent to {user.email}")
        else:
            logger.error(f"Failed to send password reset email to {user.email}")

        return success

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        if not fail_silently:
            raise
        return False


# BACKWARD COMPATIBILITY - Keep original function names but make them async
def send_verification_email(user, fail_silently=True):
    """Backward compatibility - now calls async version"""
    return send_verification_email_async(user, fail_silently)


def send_password_reset_email(user, token, fail_silently=True):
    """Backward compatibility - now calls async version"""
    return send_password_reset_email_async(user, token, fail_silently)


# Emergency function to disable email sending completely
def disable_email_sending():
    """Completely disable email sending (emergency use)"""
    global EMAIL_ENABLED
    EMAIL_ENABLED = False
    logger.warning("Email sending has been disabled globally")


def enable_email_sending():
    """Enable email sending"""
    global EMAIL_ENABLED
    EMAIL_ENABLED = True
    logger.info("Email sending has been enabled")


def test_email_connection():
    """Test email connection and configuration"""
    try:
        connection = get_connection()
        connection.open()
        connection.close()
        logger.info("Email connection test successful")
        return True
    except Exception as e:
        logger.error(f"Email connection test failed: {str(e)}")
        return False