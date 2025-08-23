import logging
from urllib.parse import urljoin
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import secrets

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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



def send_zeptomail(subject, plain_message, recipient_list, html_message=None):
    config = getattr(settings, 'ZEPTOMAIL_CONFIG', {})

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = config.get('FROM_EMAIL', settings.DEFAULT_FROM_EMAIL)
    msg['To'] = ', '.join(recipient_list)

    # Attach plain text version
    part1 = MIMEText(plain_message, 'plain')
    msg.attach(part1)

    # Attach HTML version if exists
    if html_message:
        part2 = MIMEText(html_message, 'html')
        msg.attach(part2)

    try:
        if config.get('SMTP_PORT') == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(config['SMTP_SERVER'], config['SMTP_PORT'], context=context) as server:
                server.login(config['USERNAME'], config['PASSWORD'])
                server.send_message(msg)
        else:
            with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
                server.starttls()
                server.login(config['USERNAME'], config['PASSWORD'])
                server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"ZeptoMail sending failed: {str(e)}", exc_info=True)
        return False


def send_verification_email(user):
    subject = 'Verify Your Email Address'
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

        # Use ZeptoMail to send the email
        success = send_zeptomail(
            subject=subject,
            plain_message=plain_message,
            recipient_list=recipient,
            html_message=html_message
        )

        if success:
            logger.info(f"Verification email sent successfully to {user.email}")
        return success

    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}", exc_info=True)
        return False


def send_password_reset_email(user, token):
    subject = 'Reset Your Password'
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

        # Use ZeptoMail to send the email
        success = send_zeptomail(
            subject=subject,
            plain_message=plain_message,
            recipient_list=recipient,
            html_message=html_message
        )

        if success:
            logger.info(f"Password reset email sent to {user.email}")
        return success

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}", exc_info=True)
        return False


# Password reset email functions
def generate_password_reset_link(token, user):
    """Generate password reset URL"""
    base_url = getattr(settings, 'FRONTEND_URL', "http://127.0.0.1:8000/api/v1/user-auth")
    base_url = base_url.rstrip('/') if base_url else 'http://127.0.0.1:8000/api/v1/user-auth'

    path = f'/reset-password?token={token}&email={user.email}'
    return urljoin(base_url + '/', path.lstrip('/'))


