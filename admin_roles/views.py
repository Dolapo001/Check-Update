from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from .models import AdminActionLog, Content, AdminUser, Role


class DashboardAdminView:
    def get_urls(self):
        from django.urls import path

        return [
            path(
                "dashboard/",
                admin.site.admin_view(self.dashboard_view),
                name="dashboard",
            ),
        ]

    def dashboard_view(self, request):
        if not request.user.is_authenticated:
            context = {"error": _("Authentication required")}
            return render(request, "admin/login_error.html", context, status=401)

        user = request.user
        context = {}

        # Admin dashboard data
        if hasattr(user, "role") and user.role and user.role.name == Role.ADMIN:
            recent_actions = AdminActionLog.objects.order_by("-timestamp")[:10]
            user_count = AdminUser.objects.count()
            role_count = Role.objects.count()
            content_stats = {
                "draft": Content.objects.filter(status="draft").count(),
                "submitted": Content.objects.filter(status="submitted").count(),
                "published": Content.objects.filter(status="published").count(),
            }

            context.update(
                {
                    "recent_actions": recent_actions,
                    "user_count": user_count,
                    "role_count": role_count,
                    "content_stats": content_stats,
                }
            )

        # Editor dashboard
        elif hasattr(user, "role") and user.role and user.role.name == Role.EDITOR:
            content_to_review = Content.objects.filter(status="submitted").count()
            recent_published = Content.objects.filter(status="published").order_by(
                "-publish_date"
            )[:5]

            context.update(
                {
                    "content_to_review": content_to_review,
                    "recent_published": recent_published,
                }
            )

        # Writer dashboard
        elif hasattr(user, "role") and user.role and user.role.name == Role.WRITER:
            my_content = Content.objects.filter(author=user)
            content_stats = {
                "draft": my_content.filter(status="draft").count(),
                "submitted": my_content.filter(status="submitted").count(),
                "published": my_content.filter(status="published").count(),
            }

            context.update(
                {
                    "content_stats": content_stats,
                }
            )

        # Add admin site context and title
        context.update(**admin.site.each_context(request))
        context["title"] = _("Admin Dashboard")
        return render(request, "dashboard.html", context)


# Add dashboard to admin site
dashboard_view = DashboardAdminView()
admin.site.get_urls = lambda: dashboard_view.get_urls() + admin.site.get_urls()
