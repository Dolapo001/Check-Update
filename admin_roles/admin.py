from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from django.urls import path
from .models import Role, AdminUser, AdminActionLog, Content, AdBanner, Comment, SEOData

# Customize the default admin site
admin.site.site_header = _("Content Management System")
admin.site.site_title = _("Admin Portal")
admin.site.index_title = _("Dashboard")


class CustomAdminMixin:
    """Mixin to add role-based filtering to admin views"""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and hasattr(request.user, 'role') and request.user.role:
            return self.filter_queryset_by_role(request, qs)
        return qs

    def filter_queryset_by_role(self, request, qs):
        """Override this method in admin classes that need role-based filtering"""
        return qs

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        return self.check_role_permission(request, 'view')

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        return self.check_role_permission(request, 'add')

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        return self.check_role_permission(request, 'change')

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        return self.check_role_permission(request, 'delete')

    def check_role_permission(self, request, action):
        """Check if user's role allows the action"""
        if request.user.is_superuser:
            return True

        if not hasattr(request.user, 'role') or not request.user.role:
            return False

        role_name = request.user.role.name
        model_name = self.model._meta.model_name.lower()

        # Define role-specific permissions
        role_permissions = {
            'admin': ['*'],  # All permissions
            'editor': [
                'view_content', 'change_content', 'view_comment', 'change_comment',
            ],
            'writer': [
                'view_content', 'add_content', 'change_content', 'delete_content', 'view_comment'
            ],
            'contributor': ['add_content', 'view_content'],
            'moderator': ['view_comment', 'change_comment'],
            'seo_analyst': ['view_seodata', 'change_seodata'],
            'ad_manager': ['view_adbanner', 'change_adbanner'],
        }

        allowed_perms = role_permissions.get(role_name, [])

        if '*' in allowed_perms:
            return True

        permission_name = f"{action}_{model_name}"
        return permission_name in allowed_perms


@admin.register(AdminUser)
class CustomUserAdmin(CustomAdminMixin, UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_suspended', 'is_staff', 'is_superuser',
                       'role', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff', 'is_suspended')
    list_filter = ('role', 'is_active', 'is_staff', 'is_suspended', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    actions = ['suspend_users', 'activate_users']

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser:
            # Remove sensitive fields for non-superusers
            fieldsets = [
                fs for fs in fieldsets
                if fs[0] not in [_('Permissions'), _('Important dates')]
            ]
        return fieldsets

    @admin.action(description=_('Suspend selected users'))
    def suspend_users(self, request, queryset):
        queryset.update(is_suspended=True)
        for user in queryset:
            AdminActionLog.objects.create(
                user=request.user,
                action='suspend',
                model='AdminUser',
                object_id=str(user.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"User {user.username} suspended"
            )

    @admin.action(description=_('Activate selected users'))
    def activate_users(self, request, queryset):
        queryset.update(is_active=True, is_suspended=False)
        for user in queryset:
            AdminActionLog.objects.create(
                user=request.user,
                action='activate',
                model='AdminUser',
                object_id=str(user.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"User {user.username} activated"
            )


@admin.register(Role)
class RoleAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'is_active', 'permissions_count', 'user_count')
    filter_horizontal = ('permissions',)
    search_fields = ('name',)
    list_filter = ('is_active',)

    def permissions_count(self, obj):
        return obj.permissions.count()

    permissions_count.short_description = _("Permissions")

    def user_count(self, obj):
        return obj.users.count()

    user_count.short_description = _("Users")


@admin.register(AdminActionLog)
class ActionLogAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'action', 'model', 'timestamp', 'ip_address')
    list_filter = ('action', 'model', 'timestamp')
    search_fields = ('user__username', 'action', 'model')
    readonly_fields = ('user', 'action', 'model', 'object_id', 'timestamp', 'ip_address', 'details')
    date_hierarchy = 'timestamp'


@admin.register(Content)
class ContentAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'publish_date', 'created_at')
    list_filter = ('status', 'author', 'created_at')
    search_fields = ('title', 'content')
    actions = ['approve_content', 'publish_content', 'set_as_draft']
    fieldsets = (
        (None, {'fields': ('title', 'content')}),
        (_('Status'), {'fields': ('status', 'publish_date')}),
        (_('Regional Settings'), {'fields': ('region_restrictions',)}),
    )

    def filter_queryset_by_role(self, request, qs):
        if request.user.role and request.user.role.name == Role.WRITER:
            return qs.filter(author=request.user)
        return qs

    def get_readonly_fields(self, request, obj=None):
        if request.user.role and request.user.role.name == Role.WRITER:
            return ['status', 'publish_date', 'region_restrictions']
        return []

    @admin.action(description=_('Approve selected content'))
    def approve_content(self, request, queryset):
        if not request.user.has_perm('cms.can_approve_content'):
            self.message_user(request, _("You don't have permission to approve content"), level='ERROR')
            return

        queryset.update(status='approved')
        for content in queryset:
            AdminActionLog.objects.create(
                user=request.user,
                action='approve',
                model='Content',
                object_id=str(content.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Content '{content.title}' approved"
            )

    @admin.action(description=_('Publish selected content'))
    def publish_content(self, request, queryset):
        if not request.user.has_perm('cms.can_publish_content'):
            self.message_user(request, _("You don't have permission to publish content"), level='ERROR')
            return

        queryset.update(status='published')
        for content in queryset:
            AdminActionLog.objects.create(
                user=request.user,
                action='publish',
                model='Content',
                object_id=str(content.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Content '{content.title}' published"
            )

    @admin.action(description=_('Set as draft'))
    def set_as_draft(self, request, queryset):
        queryset.update(status='draft')
        for content in queryset:
            AdminActionLog.objects.create(
                user=request.user,
                action='update',
                model='Content',
                object_id=str(content.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Content '{content.title}' set to draft"
            )


@admin.register(AdBanner)
class AdBannerAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'is_active', 'start_date', 'end_date', 'created_by')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('name',)
    readonly_fields = ('created_by',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Comment)
class CommentAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ('content', 'author', 'is_approved', 'created_at', 'flagged')
    list_filter = ('is_approved', 'flagged', 'created_at')
    search_fields = ('author', 'text')
    actions = ['approve_comments', 'flag_comments']

    @admin.action(description=_('Approve selected comments'))
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
        for comment in queryset:
            AdminActionLog.objects.create(
                user=request.user,
                action='approve',
                model='Comment',
                object_id=str(comment.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Comment by {comment.author} approved"
            )

    @admin.action(description=_('Flag selected comments'))
    def flag_comments(self, request, queryset):
        queryset.update(flagged=True)
        for comment in queryset:
            AdminActionLog.objects.create(
                user=request.user,
                action='update',
                model='Comment',
                object_id=str(comment.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                details=f"Comment by {comment.author} flagged"
            )


@admin.register(SEOData)
class SEODataAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ('content', 'created_at', 'updated_at')
    search_fields = ('content__title', 'meta_title', 'keywords')

    def get_readonly_fields(self, request, obj=None):
        if request.user.role and request.user.role.name != Role.ADMIN:
            return ['content']
        return []
