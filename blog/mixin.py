# blog/mixins.py
import logging
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class CachedNewsMixin:
    def get_cached_news(
        self, cache_key, queryset_func, serializer_class, limit, context, timeout
    ):
        try:
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            news = queryset_func(limit)
            serializer = serializer_class(news, many=True, context=context)
            data = serializer.data
            cache.set(cache_key, data, timeout=timeout)
            return self.success_response(data)
        except Exception as e:
            logger.exception(f"Error fetching data for {cache_key}: {str(e)}")
            return self.error_response("Failed to fetch news data")
