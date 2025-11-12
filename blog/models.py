from cloudinary.models import CloudinaryField
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from blog.managers import NewsManager
from common.models import BaseModel
from core.models import User

from django.conf import settings
from bs4 import BeautifulSoup


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class SubCategory(BaseModel):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        verbose_name_plural = "SubCategories"
        unique_together = ("category", "slug")

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class News(BaseModel):
    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("none", "None"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200, unique=True, blank=True
    )  # Allow blank for auto-gen
    content = models.TextField()
    excerpt = models.TextField(blank=True)
    # Use CloudinaryField for better integration (replaces FileField)
    media = CloudinaryField(
        "media", blank=True, null=True, folder="news_media/"
    )  # Folder auto-creates
    media_type = models.CharField(
        max_length=10, choices=MEDIA_TYPE_CHOICES, default="none"
    )
    subcategory = models.ForeignKey(
        "SubCategory", on_delete=models.CASCADE, related_name="news"
    )  # Assuming SubCategory defined
    #author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_foreign = models.BooleanField(default=False)
    is_top_story = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    bookmarks = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="bookmarked_news", blank=True
    )

    objects = NewsManager()

    class Meta:
        verbose_name_plural = "News"
        ordering = ["-created"]  # Assuming 'created' from BaseModel

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-slug with uniqueness (handle pre-save properly)
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while (
                News.objects.filter(slug=self.slug).exclude(id=self.id).exists()
            ):  # Exclude self if updating
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        # Auto-excerpt (your code is fine, but ensure bs4 installed)
        if not self.excerpt and self.content:
            clean_content = "".join(
                BeautifulSoup(self.content, "html.parser").findAll(text=True)
            )
            self.excerpt = (
                clean_content[:150] + "..."
                if len(clean_content) > 150
                else clean_content
            )

        # Auto-detect media_type based on file extension (if media uploaded)
        if self.media:
            ext = (
                self.media.name.lower().split(".")[-1] if "." in self.media.name else ""
            )
            if ext in ["jpg", "jpeg", "png", "gif", "webp"]:
                self.media_type = "image"
            elif ext in ["mp4", "webm", "avi", "mov"]:
                self.media_type = "video"
            else:
                self.media_type = "none"  # Or raise ValidationError if strict

        super().save(*args, **kwargs)

    def increment_views(self):
        self.views += 1
        self.save(update_fields=["views"])


class Advertisement(BaseModel):
    POSITION_CHOICES = [
        ("header", "Header"),
        ("sidebar", "Sidebar"),
        ("footer", "Footer"),
        ("in_content", "In Content"),
    ]

    title = models.CharField(max_length=100)
    # Use CloudinaryField for images
    image = CloudinaryField(
        "image", folder="ads/"
    )  # Required? Remove blank/null if not
    link = models.URLField()
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    category = models.ForeignKey(
        "Category", on_delete=models.CASCADE, null=True, blank=True
    )  # Assuming Category defined
    subcategory = models.ForeignKey(
        "SubCategory", on_delete=models.CASCADE, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
