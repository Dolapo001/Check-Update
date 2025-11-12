# management/commands/test_email.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

from core.utils.email_verification import (
    test_email_connection,
    send_email_with_template,
)


class Command(BaseCommand):
    help = "Test email configuration and send a test email"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to", type=str, required=True, help="Email address to send test email to"
        )
        parser.add_argument(
            "--method",
            type=str,
            choices=["django", "custom"],
            default="django",
            help="Email method to use (django or custom)",
        )

    def handle(self, *args, **options):
        recipient_email = options["to"]
        method = options["method"]

        self.stdout.write("Testing email configuration...")

        # Test connection
        if test_email_connection():
            self.stdout.write(self.style.SUCCESS("✓ Email connection test passed"))
        else:
            self.stdout.write(self.style.ERROR("✗ Email connection test failed"))
            return

        # Send test email
        try:
            if method == "django":
                # Test with Django's send_mail
                result = send_mail(
                    subject="Test Email from Django",
                    message="This is a test email sent using Django's email system.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
                from django.db import connection

                connection.close()

                if result:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Test email sent successfully to {recipient_email}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ Failed to send test email to {recipient_email}"
                        )
                    )

            elif method == "custom":
                # Test with custom template system
                context = {
                    "user": type(
                        "User",
                        (),
                        {
                            "get_full_name": lambda: "Test User",
                            "username": "testuser",
                            "email": recipient_email,
                        },
                    )(),
                    "verification_link": "https://example.com/verify-test",
                    "expiration_hours": 24,
                    "support_email": getattr(
                        settings, "SUPPORT_EMAIL", "security@checkupdate.ng"
                    ),
                    "company_name": getattr(settings, "COMPANY_NAME", "CheckUpdate"),
                }

                result = send_email_with_template(
                    subject="Test Template Email",
                    template_name="verify_email",
                    context=context,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )

                if result:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Template test email sent successfully to {recipient_email}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ Failed to send template test email to {recipient_email}"
                        )
                    )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error sending test email: {str(e)}"))

        # Display current email configuration
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("Current Email Configuration:")
        self.stdout.write("=" * 50)
        self.stdout.write(
            f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Not set')}"
        )
        self.stdout.write(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
        self.stdout.write(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Not set')}")
        self.stdout.write(
            f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'Not set')}"
        )
        self.stdout.write(
            f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Not set')}"
        )
        self.stdout.write(
            f"EMAIL_USE_SSL: {getattr(settings, 'EMAIL_USE_SSL', 'Not set')}"
        )
        self.stdout.write(
            f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}"
        )
        self.stdout.write("=" * 50)
