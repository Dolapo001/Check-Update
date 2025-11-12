# blog/signals.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings
from .models import News, Category, SubCategory

logger = logging.getLogger(__name__)


def _delete_pattern_safe(pattern: str):
    """
    Try to delete keys by pattern, handling both Redis and LocMemCache backends.
    """
    try:
        # Method 1: Try cache.delete_pattern if available (django-redis)
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(pattern)
            logger.debug(f"Deleted cache pattern using delete_pattern: {pattern}")
            return

        # Method 2: Try direct Redis connection
        try:
            from django_redis import get_redis_connection

            conn = get_redis_connection("default")
            # Use scan_iter instead of keys for better performance with large datasets
            keys = []
            for key in conn.scan_iter(pattern):
                keys.append(key)
            if keys:
                conn.delete(*keys)
                logger.debug(f"Deleted {len(keys)} keys matching pattern: {pattern}")
            return
        except ImportError:
            pass  # django_redis not available
        except Exception as e:
            logger.debug(f"Redis pattern deletion failed: {e}")

        # Method 3: For LocMemCache or other backends without pattern support
        # Clear specific known cache keys instead of using patterns
        if pattern == "news:*":
            known_keys = [
                "news:latest",
                "news:popular",
                "news:all",
                "news:featured",
                # Add other news-related cache keys you use
            ]
            cache.delete_many(known_keys)
            logger.debug(f"Deleted known news cache keys for pattern: {pattern}")
        else:
            logger.warning(
                f"Pattern deletion not supported for: {pattern}. Using LocMemCache?"
            )

    except Exception as exc:
        logger.warning(f"Failed to delete cache pattern '{pattern}': {exc}")


@receiver([post_save, post_delete], sender=News)
def invalidate_news_cache(sender, instance, **kwargs):
    """Invalidate news-related cache with better error handling"""
    try:
        _delete_pattern_safe("news:*")
        # Also clear specific common news cache keys
        cache.delete_many(
            [
                "news:latest",
                "news:popular",
                "news:all",
                "news:featured",
            ]
        )
    except Exception as exc:
        logger.warning(f"Error invalidating news cache: {exc}")


# Keep your existing category and subcategory signals as they are
@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    try:
        cache.delete("categories:all")
        cache.delete(f"category:{instance.id}")
    except Exception as exc:
        logger.warning(f"Error invalidating category cache: {exc}")


@receiver([post_save, post_delete], sender=SubCategory)
def invalidate_subcategory_cache(sender, instance, **kwargs):
    try:
        cache.delete(f"subcategory:{instance.id}")
        _delete_pattern_safe(f"subcategory_page:{instance.id}*")
    except Exception as exc:
        logger.warning(f"Error invalidating subcategory cache: {exc}")
