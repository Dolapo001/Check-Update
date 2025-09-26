import logging
import threading
from urllib.parse import urljoin
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import secrets
import smtplib
from socket import timeout as SocketTimeout

logger = logging.getLogger(__name__)


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


def send_email_with_template(subject, template_name, context, recipient_list, fail_silently=False):
    """
    Generic function to send emails using Django's email system
    """
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

        # Send email
        connection = get_connection()
        result = msg.send(fail_silently=fail_silently)

        if result:
            logger.info(f"Email sent successfully to {', '.join(recipient_list)}")
            return True
        else:
            logger.error(f"Failed to send email to {', '.join(recipient_list)}")
            return False

    except Exception as e:
        logger.error(f"Error sending email to {', '.join(recipient_list)}: {str(e)}", exc_info=True)
        if not fail_silently:
            raise
        return False


def send_verification_email_async(user, fail_silently=True):
    """Send verification email in a separate thread to avoid blocking"""

    def _send_email():
        try:
            send_verification_email_sync(user, fail_silently)
        except Exception as e:
            logger.error(f"Async verification email failed: {str(e)}")

    thread = threading.Thread(target=_send_email)
    thread.daemon = True
    thread.start()
    return True  # Always return success to avoid blocking user


def send_password_reset_email_async(user, token, fail_silently=True):
    """Send password reset email in a separate thread to avoid blocking"""

    def _send_email():
        try:
            send_password_reset_email_sync(user, token, fail_silently)
        except Exception as e:
            logger.error(f"Async password reset email failed: {str(e)}")

    thread = threading.Thread(target=_send_email)
    thread.daemon = True
    thread.start()
    return True  # Always return success to avoid blocking user


def send_verification_email_sync(user, fail_silently=True):
    """Synchronous version with proper error handling"""
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

        return success

    except (SocketTimeout, smtplib.SMTPException) as e:
        logger.error(f"Email timeout/error for {user.email}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        if not fail_silently:
            raise
        return False


def send_password_reset_email_sync(user, token, fail_silently=True):
    """Synchronous version with proper error handling"""
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

        return success

    except (SocketTimeout, smtplib.SMTPException) as e:
        logger.error(f"Password reset email timeout/error for {user.email}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        if not fail_silently:
            raise
        return False


# Alternative: Keep your custom ZeptoMail implementation as backup
def send_zeptomail_custom(subject, plain_message, recipient_list, html_message=None):
    """
    Custom ZeptoMail implementation (backup method)
    """
    import smtplib
    import ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

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

        logger.info(f"ZeptoMail custom email sent successfully to {', '.join(recipient_list)}")
        return True
    except Exception as e:
        logger.error(f"ZeptoMail custom sending failed: {str(e)}", exc_info=True)
        return False


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


def validate_email_config():
    """Validate email configuration on startup"""
    required_settings = ['EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD']

    for setting in required_settings:
        if not getattr(settings, setting, None):
            logger.warning(f"Email setting {setting} is not configured")
            return False

    # Test connection
    try:
        connection = get_connection()
        connection.open()
        connection.close()
        logger.info("Email configuration is valid")
        return True
    except Exception as e:
        logger.error(f"Email configuration test failed: {e}")
        return False