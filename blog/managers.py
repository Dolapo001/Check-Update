from datetime import timezone


class NewsManager(models.Manager):
    def get_trending(self, subcategory=None, limit=10):
        queryset = self.filter(
            created__gte=timezone.now() - timezone.timedelta(days=7)
        )
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-views', '-created')[:limit]

    def get_top_stories(self, subcategory=None, limit=10):
        queryset = self.filter(is_top_story=True)
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-created')[:limit]

    def get_most_watched_videos(self, subcategory=None, limit=10):
        queryset = self.filter(
            media_type='video',
            created__gte=timezone.now() - timezone.timedelta(days=7)
        )
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-views')[:limit]

    def get_latest(self, subcategory=None, limit=10):
        queryset = self.all()
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-created')[:limit]

    def get_recommended(self, user, limit=10):
        if user.is_authenticated:
            from blog.models import News
            bookmarked_categories = News.objects.filter(
                bookmarks=user
            ).values_list('subcategory__category', flat=True).distinct()

            return self.filter(
                subcategory__category__in=bookmarked_categories
            ).exclude(bookmarks=user).order_by('-created')[:limit]
        return self.get_latest(limit=limit)

    def get_hot_stories_this_week(self, subcategory=None, limit=5):
        queryset = self.filter(
            created__gte=timezone.now() - timezone.timedelta(days=7)
        )
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-views')[:limit]

    def get_foreign_news(self, subcategory=None, is_foreign=True, limit=10):
        queryset = self.filter(is_foreign=is_foreign)
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-created')[:limit]

    def get_most_viewed(self, subcategory=None, limit=10):
        queryset = self.all()
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        return queryset.order_by('-views')[:limit]

    def get_excerpt(self, subcategory=None, limit=None):
        queryset = self.all()
        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)
        queryset = queryset.order_by('-created')
        if limit:
            queryset = queryset[:limit]
        return queryset
