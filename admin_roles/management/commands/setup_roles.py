# management/commands/setup_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, ContentType
from django.contrib.auth.management import create_permissions
from django.apps import apps
from admin_roles.models import Role, AdminUser, Content, Comment, AdBanner, SEOData


class Command(BaseCommand):
    help = "Creates initial admin roles and superuser"

    def handle(self, *args, **options):
        # Create permissions for all apps
        for app_config in apps.get_app_configs():
            app_config.models_module = True
            create_permissions(app_config, verbosity=0)
            app_config.models_module = None

        # Define role permissions
        role_permissions = {
            "Administrator": ["*"],  # All permissions
            "Editor": [
                "view_content",
                "change_content",
                "delete_content",
                "can_approve_content",
                "can_publish_content",
                "view_comment",
                "change_comment",
                "view_seodata",
            ],
            "Writer": [
                "view_content",
                "add_content",
                "change_content",
                "delete_content",
                "view_comment",
            ],
            "Contributor": ["add_content", "view_content"],
            "Moderator": [
                "view_comment",
                "change_comment",
                "delete_comment",
                "can_moderate_comments",
            ],
            "SEO Analyst": [
                "view_seodata",
                "change_seodata",
                "can_manage_seo",
                "view_content",
            ],
            "Ad Manager": [
                "view_adbanner",
                "add_adbanner",
                "change_adbanner",
                "delete_adbanner",
                "can_manage_ads",
            ],
        }

        # Create roles and assign permissions
        for role_name, perm_codenames in role_permissions.items():
            role, created = Role.objects.get_or_create(name=role_name)

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created role: {role_name}"))

                # Assign permissions
                if perm_codenames == ["*"]:
                    permissions = Permission.objects.all()
                else:
                    permissions = Permission.objects.filter(codename__in=perm_codenames)

                role.permissions.set(permissions)

        # Create admin user
        if not AdminUser.objects.filter(username="admin").exists():
            admin_role = Role.objects.get(name="Administrator")
            user = AdminUser.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="adminpassword",
                role=admin_role,
            )
            self.stdout.write(self.style.SUCCESS("Created admin user"))


from django.db import connection

connection.close()
