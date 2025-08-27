from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class EmailVerifiedFilter(admin.SimpleListFilter):
    title = 'Email Verification Status'
    parameter_name = 'email_verified'

    def lookups(self, request, model_admin):
        return (
            ('verified', 'Verified'),
            ('not_verified', 'Not Verified'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(email_verified=True)
        if self.value() == 'not_verified':
            return queryset.filter(email_verified=False)


class CustomUserAdmin(UserAdmin):
    # Fields to display in the user list view
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'email_verified', 'date_joined',
                    'get_full_name')

    # Fields that can be used to search for users
    search_fields = ('email', 'first_name', 'last_name')

    # Fields that can be used to filter users
    list_filter = ('is_staff', 'is_active', 'email_verified', 'date_joined')

    # How to order the users in the list
    ordering = ('email',)

    # Fields to include in the add/edit forms
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Email Verification', {'fields': ('email_verified', 'verification_token', 'verification_token_expires')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fields to include in the add user form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'phone_number'),
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name()

    get_full_name.short_description = 'Full Name'

    actions = ['activate_users', 'deactivate_users']

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_users.short_description = "Deactivate selected users"


# Register the User model with the custom admin class
admin.site.register(User, CustomUserAdmin)
