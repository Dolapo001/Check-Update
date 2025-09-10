from django.db import models
from django.utils import timezone
from django.utils.text import slugify
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
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        verbose_name_plural = "SubCategories"
        unique_together = ('category', 'slug')

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class News(BaseModel):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('none', 'None'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True)  # Add this line
    media = models.FileField(upload_to='news_media/', blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='none')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='news')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_foreign = models.BooleanField(default=False)
    is_top_story = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    bookmarks = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='bookmarked_news', blank=True)
    from blog.managers import NewsManager
    objects = NewsManager()

    class Meta:
        verbose_name_plural = "News"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure slug is unique
            if News.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{self.id}" if self.id else f"{self.slug}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        # Auto-generate excerpt if not provided
        if not self.excerpt and self.content:
            # Strip HTML tags and get first 150 characters
            clean_content = ''.join(BeautifulSoup(self.content, "html.parser").findAll(text=True))
            self.excerpt = clean_content[:150] + '...' if len(clean_content) > 150 else clean_content

        super().save(*args, **kwargs)

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])


class Advertisement(BaseModel):
    POSITION_CHOICES = [
        ('header', 'Header'),
        ('sidebar', 'Sidebar'),
        ('footer', 'Footer'),
        ('in_content', 'In Content'),
    ]

    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='ads/')
    link = models.URLField()
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title