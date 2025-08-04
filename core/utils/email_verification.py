import logging
from urllib.parse import urljoin
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import secrets


logger = logging.getLogger(__name__)


# Verification email functions
def generate_verification_token():
    return secrets.token_urlsafe(32)


def generate_verification_link(user):
    """Generate token, store it on the user, and return full verification URL"""
    token = generate_verification_token()
    expires_at = timezone.now() + timezone.timedelta(hours=24)

    user.verification_token = token
    user.verification_token_expires = expires_at
    user.save(update_fields=['verification_token', 'verification_token_expires'])

    # Safely get FRONTEND_URL with fallback
    base_url = getattr(settings, 'FRONTEND_URL', 'http://127.0.0.1:8000/api/v1/user-auth')
    base_url = base_url.rstrip('/') if base_url else 'http://127.0.0.1:8000/api/v1/user-auth'

    path = f'/verify-email?token={token}&email={user.email}'
    link = urljoin(base_url + '/', path.lstrip('/'))

    return {
        'token': token,
        'link': link,
        'expires_at': expires_at
    }


def send_verification_email(user):
    """Send email verification link to user"""
    subject = 'Verify Your Email Address'
    sender = settings.DEFAULT_FROM_EMAIL
    recipient = [user.email]

    try:
        verification_data = generate_verification_link(user)

        context = {
            'user': user,
            'verification_link': verification_data['link'],
            'expiration_hours': 24,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com'),
            'company_name': getattr(settings, 'COMPANY_NAME', 'CheckUpdate'),
        }

        try:
            html_message = render_to_string('verify_email.html', context)
            plain_message = render_to_string('verify_email.txt', context)
        except TemplateDoesNotExist as e:
            logger.critical(f"Missing email template: {e}")
            html_message = None
            plain_message = f"Verify your email: {verification_data['link']}"

        try:
            msg = EmailMultiAlternatives(subject, plain_message, sender, recipient)
            if html_message:
                msg.attach_alternative(html_message, "text/html")
            msg.send()
            logger.info(f"Verification email sent successfully to {user.email}")
            return True
        except Exception as send_error:
            logger.error(f"Email sending failed for {user.email}: {str(send_error)}", exc_info=True)
            return False

    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}", exc_info=True)
        return False


# Password reset email functions
def generate_password_reset_link(token, user):
    """Generate password reset URL"""
    base_url = getattr(settings, 'FRONTEND_URL', "http://127.0.0.1:8000/api/v1/user-auth")
    base_url = base_url.rstrip('/') if base_url else 'http://127.0.0.1:8000/api/v1/user-auth'

    path = f'/reset-password?token={token}&email={user.email}'
    return urljoin(base_url + '/', path.lstrip('/'))


def send_password_reset_email(user, token):
    subject = 'Reset Your Password'
    sender = settings.DEFAULT_FROM_EMAIL
    recipient = [user.email]

    try:
        reset_link = generate_password_reset_link(token, user)

        context = {
            'user': user,
            'reset_link': reset_link,
            'expiration_hours': 24,
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com'),
            'company_name': getattr(settings, 'COMPANY_NAME', 'CheckUpdate'),
        }

        html_message = render_to_string('password_reset.html', context)
        plain_message = render_to_string('password_reset.txt', context)

        msg = EmailMultiAlternatives(subject, plain_message, sender, recipient)
        msg.attach_alternative(html_message, "text/html")
        msg.send()

        logger.info(f"Password reset email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}", exc_info=True)
        return False
