# blog/managers.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

class NewsManager(models.Manager):
    """
    Manager methods tailored to the fields on your News model:
    - created (DateTime)
    - views (Integer)
    - is_top_story (Boolean)
    - media_type ('image'|'video'|'none')
    - is_foreign (Boolean)
    - subcategory (FK -> SubCategory -> category)
    """

    def _base_queryset(self):
        # Use get_queryset() for flexibility (works with QuerySet chaining)
        return self.get_queryset().select_related('subcategory', 'subcategory__category', 'author')

    def get_latest(self, limit=10, subcategory=None):
        qs = self._base_queryset().order_by('-created')
        if subcategory:
            qs = qs.filter(subcategory=subcategory)
        return qs[:limit] if limit else qs

    def get_trending(self, limit=10, subcategory=None):
        """
        Trending = highest views in last 7 days (fallback to overall views if necessary).
        """
        week_ago = timezone.now() - timedelta(days=7)
        qs = self._base_queryset().filter(created__gte=week_ago)
        if subcategory:
            qs = qs.filter(subcategory=subcategory)
        # order by views then newest
        return qs.order_by('-views', '-created')[:limit] if limit else qs.order_by('-views', '-created')

    def get_top_stories(self, limit=10, subcategory=None):
        """
        Use is_top_story boolean on the model (your model has is_top_story).
        """
        qs = self._base_queryset().filter(is_top_story=True)
        if subcategory:
            qs = qs.filter(subcategory=subcategory)
        return qs.order_by('-created')[:limit] if limit else qs.order_by('-created')

    def get_most_watched_videos(self, limit=10, subcategory=None):
        """
        Filter where media_type == 'video' and order by views.
        """
        qs = self._base_queryset().filter(media_type='video')
        if subcategory:
            qs = qs.filter(subcategory=subcategory)
        return qs.order_by('-views', '-created')[:limit] if limit else qs.order_by('-views', '-created')

    def get_recommended(self, user, limit=10):
        """
        Recommendation strategy:
          1. If user has bookmarked news, get categories of those bookmarks and prefer those categories.
          2. Otherwise fallback to latest (or trending).
        """
        qs = self._base_queryset()
        if user and getattr(user, 'is_authenticated', False):
            # Get categories (via subcategory__category) from bookmarked news
            bookmarked_category_ids = list(
                qs.filter(bookmarks=user).values_list('subcategory__category', flat=True).distinct()
            )
            if bookmarked_category_ids:
                # Recommend news that belong to subcategories under those categories, exclude already bookmarked
                recommended_qs = qs.filter(subcategory__category__in=bookmarked_category_ids).exclude(bookmarks=user)
                return recommended_qs.order_by('-created')[:limit]
        # fallback to trending/latest
        return self.get_trending(limit=limit) if limit else self.get_latest(limit=limit)

    # convenience helpers used by your SubCategoryPageView earlier
    def get_hot_stories_this_week(self, subcategory=None, limit=5):
        week_ago = timezone.now() - timedelta(days=7)
        qs = self._base_queryset().filter(created__gte=week_ago)
        if subcategory:
            qs = qs.filter(subcategory=subcategory)
        return qs.order_by('-views')[:limit] if limit else qs.order_by('-views')

    def get_foreign_news(self, subcategory=None, is_foreign=True, limit=10):
        qs = self._base_queryset().filter(is_foreign=is_foreign)
        if subcategory:
            qs = qs.filter(subcategory=subcategory)
        return qs.order_by('-created')[:limit] if limit else qs.order_by('-created')

    def get_most_viewed(self, subcategory=None, limit=10):
        qs = self._base_queryset()
        if subcategory:
            qs = qs.filter(subcategory=subcategory)
        return qs.order_by('-views')[:limit] if limit else qs.order_by('-views')

    def get_excerpt(self, subcategory=None, limit=None):
        qs = self._base_queryset().order_by('-created')
        if subcategory:
            qs = qs.filter(subcategory=subcategory)
        return qs[:limit] if limit else qs
