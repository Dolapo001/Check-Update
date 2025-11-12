from django.db import models
from django.contrib.auth.models import AbstractUser, Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from common.models import BaseModel


class Role(BaseModel):
    ADMIN = "admin"
    EDITOR = "editor"
    WRITER = "writer"
    CONTRIBUTOR = "contributor"
    MODERATOR = "moderator"
    SEO_ANALYST = "seo_analyst"
    AD_MANAGER = "ad_manager"

    ROLE_CHOICES = (
        (ADMIN, "Administrator"),
        (EDITOR, "Editor"),
        (WRITER, "Writer"),
        (CONTRIBUTOR, "Contributor"),
        (MODERATOR, "Moderator"),
        (SEO_ANALYST, "SEO Analyst"),
        (AD_MANAGER, "Ad Manager"),
    )

    name = models.CharField(
        max_length=50, choices=ROLE_CHOICES, unique=True, verbose_name=_("Role Name")
    )
    permissions = models.ManyToManyField(
        Permission, blank=True, related_name="roles", verbose_name=_("Permissions")
    )
    description = models.TextField(blank=True, verbose_name=_("Role Description"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active Status"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Admin Role")
        verbose_name_plural = _("Admin Roles")
        ordering = ["name"]

    def __str__(self):
        return self.get_name_display()


class AdminUser(AbstractUser):
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("System Role"),
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_suspended = models.BooleanField(
        default=False, verbose_name=_("Suspended Status")
    )
    last_login_ip = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("Last Login IP")
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name=_("Phone Number"))
    timezone = models.CharField(
        max_length=50, default="UTC", verbose_name=_("Timezone")
    )

    class Meta:
        verbose_name = _("Admin User")
        verbose_name_plural = _("Admin Users")
        permissions = [
            ("can_suspend_user", "Can suspend users"),
            ("can_activate_user", "Can activate users"),
            ("can_manage_roles", "Can manage user roles"),
        ]

    def __str__(self):
        return self.username


class AdminActionLog(BaseModel):
    ACTION_CHOICES = (
        ("create", _("Created")),
        ("update", _("Updated")),
        ("delete", _("Deleted")),
        ("publish", _("Published")),
        ("approve", _("Approved")),
        ("suspend", _("Suspended")),
        ("activate", _("Activated")),
        ("login", _("Logged in")),
        ("logout", _("Logged out")),
    )

    user = models.ForeignKey(
        AdminUser, on_delete=models.SET_NULL, null=True, verbose_name=_("User")
    )
    action = models.CharField(
        max_length=20, choices=ACTION_CHOICES, verbose_name=_("Action")
    )
    model = models.CharField(max_length=100, verbose_name=_("Model"))
    object_id = models.CharField(max_length=100, null=True, verbose_name=_("Object ID"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Timestamp"))
    ip_address = models.GenericIPAddressField(verbose_name=_("IP Address"))
    details = models.TextField(blank=True, verbose_name=_("Action Details"))
    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to.",
        related_name="adminuser_groups",
        related_query_name="adminuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="adminuser_permissions",
        related_query_name="adminuser",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = _("Action Log")
        verbose_name_plural = _("Action Logs")

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} at {self.timestamp}"


class Content(BaseModel):
    STATUS_CHOICES = (
        ("draft", _("Draft")),
        ("submitted", _("Submitted")),
        ("approved", _("Approved")),
        ("published", _("Published")),
        ("archived", _("Archived")),
    )

    title = models.CharField(max_length=255, verbose_name=_("Title"))
    content = models.TextField(verbose_name=_("Content"))
    author = models.ForeignKey(
        AdminUser,
        on_delete=models.CASCADE,
        related_name="contents",
        verbose_name=_("Author"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name=_("Status")
    )
    publish_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Publish Date")
    )
    region_restrictions = models.CharField(
        max_length=100, blank=True, verbose_name=_("Region Restrictions")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Content")
        verbose_name_plural = _("Contents")
        permissions = [
            ("can_approve_content", "Can approve content"),
            ("can_publish_content", "Can publish content"),
            ("can_schedule_content", "Can schedule content publishing"),
        ]

    def __str__(self):
        return self.title


class AdBanner(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("Banner Name"))
    image = models.ImageField(upload_to="ads/", verbose_name=_("Banner Image"))
    url = models.URLField(verbose_name=_("Target URL"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active Status"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    created_by = models.ForeignKey(
        AdminUser, on_delete=models.SET_NULL, null=True, verbose_name=_("Created By")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Ad Banner")
        verbose_name_plural = _("Ad Banners")
        permissions = [
            ("can_manage_ads", "Can manage advertisement banners"),
        ]

    def __str__(self):
        return self.name


class Comment(BaseModel):
    content = models.ForeignKey(
        Content,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Content"),
    )
    author = models.CharField(max_length=100, verbose_name=_("Author"))
    text = models.TextField(verbose_name=_("Comment Text"))
    is_approved = models.BooleanField(default=False, verbose_name=_("Approved Status"))
    created_at = models.DateTimeField(auto_now_add=True)
    flagged = models.BooleanField(default=False, verbose_name=_("Flagged Status"))

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        permissions = [
            ("can_moderate_comments", "Can moderate comments"),
        ]

    def __str__(self):
        return f"Comment by {self.author} on {self.content}"


class SEOData(BaseModel):
    content = models.OneToOneField(
        Content,
        on_delete=models.CASCADE,
        related_name="seo_data",
        verbose_name=_("Content"),
    )
    meta_title = models.CharField(max_length=100, verbose_name=_("Meta Title"))
    meta_description = models.TextField(verbose_name=_("Meta Description"))
    keywords = models.CharField(max_length=255, verbose_name=_("Keywords"))
    canonical_url = models.URLField(blank=True, verbose_name=_("Canonical URL"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("SEO Data")
        verbose_name_plural = _("SEO Data")
        permissions = [
            ("can_manage_seo", "Can manage SEO data"),
        ]

    def __str__(self):
        return f"SEO for {self.content}"
