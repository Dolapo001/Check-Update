from django.contrib import admin
from .models import *


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "created")
    readonly_fields = ("id", "created", "updated")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug", "created")
    list_filter = ("category",)
    readonly_fields = ("id", "created", "updated")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "category__name")


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "subcategory", "author", "is_foreign", "views", "created")
    list_filter = ("subcategory", "is_foreign", "media_type", "created")
    readonly_fields = ("id", "created", "updated", "views")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("bookmarks",)


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "position",
        "category",
        "subcategory",
        "is_active",
        "created",
    )
    list_filter = ("position", "is_active", "category")
    readonly_fields = ("id", "created", "updated")
    search_fields = ("title", "link")
