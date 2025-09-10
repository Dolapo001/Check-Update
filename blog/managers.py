from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


from common.models import BaseModel


class NewsManager(models.Manager):
    def get_trending(self, limit=10):
        return self.filter(created__gte=timezone.now() - timezone.timedelta(days=7)) \
                   .order_by('-views', '-created')[:limit]

    def get_top_stories(self, limit=10):
        return self.filter(is_top_story=True).order_by('-created')[:limit]

    def get_most_watched_videos(self, limit=10):
        return self.filter(
            media_type='video',
            created__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-views')[:limit]

    def get_latest(self, limit=10):
        return self.all().order_by('-created')[:limit]

    def get_recommended(self, user, limit=10):
        # Basic implementation - can be enhanced with ML
        if user.is_authenticated:
            from blog.models import News
            # Get news from user's bookmarked categories
            bookmarked_categories = News.objects.filter(
                bookmarks=user
            ).values_list('subcategory__category', flat=True).distinct()

            return self.filter(
                subcategory__category__in=bookmarked_categories
            ).exclude(bookmarks=user).order_by('-created')[:limit]
        return self.get_latest(limit=limit)

    def get_hot_stories_this_week(self, subcategory=None):
        queryset = self.filter(
            created__gte=timezone.now() - timezone.timedelta(days=7)
        )
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-views')[:5]

    def get_foreign_news(self, subcategory=None, is_foreign=True):
        queryset = self.filter(is_foreign=is_foreign)
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-created')[:10]

    def get_most_viewed(self, subcategory=None, limit=10):
        queryset = self.all()
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-views')[:limit]

    def get_excerpt(self, subcategory=None):
        queryset = self.all()
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset
