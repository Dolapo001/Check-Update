# blog/signals.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django_redis import get_redis_connection
from .models import News, Category, SubCategory

logger = logging.getLogger(__name__)


def _delete_pattern_safe(pattern: str):
    """
    Try to delete keys by pattern. Use cache.delete_pattern if available,
    otherwise fall back to direct redis connection.
    """
    try:
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(pattern)
            return
        conn = get_redis_connection("default")
        keys = conn.keys(pattern)
        if keys:
            conn.delete(*keys)
    except Exception as exc:
        # Never raise on import or signal processing — just log
        logger.exception("Failed to delete cache pattern '%s': %s", pattern, exc)


@receiver([post_save, post_delete], sender=News)
def invalidate_news_cache(sender, instance, **kwargs):
    # Conservative invalidation: clear news-related keys only
    try:
        # be explicit where possible to avoid blasting unrelated keys
        _delete_pattern_safe("news:*")
    except Exception as exc:
        logger.exception("Error invalidating news cache: %s", exc)


@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    try:
        cache.delete("categories:all")
        cache.delete(f"category:{instance.id}")
    except Exception as exc:
        logger.exception("Error invalidating category cache: %s", exc)


@receiver([post_save, post_delete], sender=SubCategory)
def invalidate_subcategory_cache(sender, instance, **kwargs):
    try:
        cache.delete(f"subcategory:{instance.id}")
        _delete_pattern_safe(f"subcategory_page:{instance.id}*")
    except Exception as exc:
        logger.exception("Error invalidating subcategory cache: %s", exc)
