import logging

from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.cache import cache
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from .mixin import CachedNewsMixin
from .models import *
from .serializers import *

logger = logging.getLogger(__name__)

CACHE_TTL = getattr(settings, "CACHE_TTL", 60)


class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response_data(self, data):
        # returns a plain dict (we'll wrap with success_response in view)
        return {
            "results": data,
            "pagination": {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "current_page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "page_size": self.get_page_size(self.request),
            },
        }

class BaseAPIView(APIView):
    def success_response(self, data, message="Success", status_code=status.HTTP_200_OK):
        return Response({
            "status": "success",
            "message": message,
            "data": data
        }, status=status_code)

    def error_response(self, message, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "status": "error",
            "message": message,
            "data": None
        }, status=status_code)

    def paginate_queryset_and_respond(self, request: Request, queryset, serializer_class, many=True, message="Success",
                                      status_code=status.HTTP_200_OK):
        """
        Paginate a queryset using CustomPagination and return success_response.
        """

        paginator = CustomPagination()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        serializer = serializer_class(paginated_qs, many=many, context={'request': request})
        data = paginator.get_paginated_response_data(serializer.data)
        return self.success_response(data, message=message, status_code=status_code)

    def maybe_paginate_or_limit(self, request: Request, queryset, serializer_class, default_limit=10):
        """
        Helper that chooses between pagination (if 'page' param present) or
        limit (if 'limit' param present). Returns a Response (success_response).
        """
        page = request.query_params.get('page', None)
        limit = request.query_params.get('limit', None)

        if page is not None:
            # use pagination
            return self.paginate_queryset_and_respond(request, queryset, serializer_class)
        else:
            # fallback to limit (keep old behaviour)
            try:
                limit_val = int(limit) if limit is not None else default_limit
            except ValueError:
                limit_val = default_limit
            sliced = queryset[:limit_val]
            serializer = serializer_class(sliced, many=True, context={'request': request})
            return self.success_response(serializer.data)


class NewsDetailView(BaseAPIView):
    # NOT CACHED - increments views
    def get(self, request, news_id):
        try:
            news = get_object_or_404(News, id=news_id)
            news.increment_views()
            serializer = NewsSerializer(news, context={'request': request})
            return self.success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching news {news_id}: {str(e)}")
            return self.error_response("Failed to fetch news")


class LatestNewsView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        cache_key = f"news:latest:limit={limit}"
        return self.get_cached_news(
            cache_key,
            News.objects.get_latest,
            NewsSerializer,
            limit,
            {'request': request},
            CACHE_TTL
        )


class TrendingNewsView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        cache_key = f"news:trending:limit={limit}"
        return self.get_cached_news(
            cache_key,
            News.objects.get_trending,
            NewsSerializer,
            limit,
            {'request': request},
            CACHE_TTL
        )


class TopStoriesView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        cache_key = f"news:topstories:limit={limit}"
        return self.get_cached_news(
            cache_key,
            News.objects.get_top_stories,
            NewsSerializer,
            limit,
            {'request': request},
            CACHE_TTL
        )


class MostWatchedView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        cache_key = f"news:mostwatched:limit={limit}"
        return self.get_cached_news(
            cache_key,
            News.objects.get_most_watched_videos,
            NewsSerializer,
            limit,
            {'request': request},
            CACHE_TTL
        )


class RecommendedNewsView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        user_part = f"user={getattr(request.user, 'id', 'anon')}"
        cache_key = f"news:recommended:{user_part}:limit={limit}"
        return self.get_cached_news(
            cache_key,
            lambda limit: News.objects.get_recommended(request.user, limit),
            NewsSerializer,
            limit,
            {'request': request},
            CACHE_TTL
        )
class BookmarkNewsView(BaseAPIView):
    def post(self, request, news_id):
        try:
            news = get_object_or_404(News, id=news_id)
            user = request.user

            if news.bookmarks.filter(id=user.id).exists():
                news.bookmarks.remove(user)
                message = "News removed from bookmarks"
            else:
                news.bookmarks.add(user)
                message = "News added to bookmarks"

            return self.success_response(None, message)
        except Exception as e:
            logger.error(f"Error toggling bookmark for news {news_id}: {str(e)}")
            return self.error_response("Failed to toggle bookmark")


class ShareNewsView(BaseAPIView):
    def get(self, request, news_id):
        try:
            news = get_object_or_404(News, id=news_id)
            share_url = f"{settings.FRONTEND_URL}/news/{news.slug}"
            return self.success_response({"share_url": share_url})
        except Exception as e:
            logger.error(f"Error generating share URL for news {news_id}: {str(e)}")
            return self.error_response("Failed to generate share URL")


class CategoryListView(BaseAPIView):
    def get(self, request):
        try:
            cache_key = "categories:all"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            categories = Category.objects.prefetch_related('subcategories').all()
            serializer = CategorySerializer(categories, many=True)
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching categories: {str(e)}")
            return self.error_response("Failed to fetch categories")


class CategoryDetailView(BaseAPIView):
    def get(self, request, category_id):
        try:
            cache_key = f"category:{category_id}"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            category = get_object_or_404(Category, id=category_id)
            serializer = CategorySerializer(category)
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching category {category_id}: {str(e)}")
            return self.error_response("Failed to fetch category")


class SubCategoryDetailView(BaseAPIView):
    def get(self, request, subcategory_id):
        try:
            cache_key = f"subcategory:{subcategory_id}"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            subcategory = get_object_or_404(SubCategory, id=subcategory_id)
            serializer = SubCategorySerializer(subcategory)
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching subcategory {subcategory_id}: {str(e)}")
            return self.error_response("Failed to fetch subcategory")


class CategoryPageView(BaseAPIView):
    def get(self, request, category_id):
        try:
            cache_key = f"category_page:{category_id}"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            category = get_object_or_404(Category, id=category_id)
            ads = Advertisement.objects.filter(
                category=category,
                is_active=True
            )[:3]  # Get 3 active ads for this category

            category_serializer = CategorySerializer(category)
            ads_serializer = AdvertisementSerializer(ads, many=True)

            data = {
                "category": category_serializer.data,
                "ads": ads_serializer.data
            }

            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching category page {category_id}: {str(e)}")
            return self.error_response("Failed to fetch category page")


from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class SubCategoryPageView(BaseAPIView):
    def get(self, request, subcategory_id):
        try:
            page = request.GET.get('page', '1')
            page_size = request.GET.get('page_size', None) or CustomPagination.page_size
            cache_key = f"subcategory_page:{subcategory_id}:page={page}:size={page_size}"

            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            subcategory = get_object_or_404(SubCategory, id=subcategory_id)

            # ---- Excerpt / Paginated News ----
            excerpt_news_qs = News.objects.get_excerpt(subcategory=subcategory)
            paginator = CustomPagination()
            paginated_excerpt = paginator.paginate_queryset(excerpt_news_qs, request)
            excerpt_serializer = NewsSerializer(paginated_excerpt, many=True, context={'request': request})

            # ---- Other News Sections (Scoped to SubCategory) ----
            top_news = News.objects.get_most_viewed(subcategory=subcategory, limit=5)
            hot_stories = News.objects.get_hot_stories_this_week(subcategory=subcategory)
            foreign_news = News.objects.get_foreign_news(subcategory=subcategory, is_foreign=True)
            local_news = News.objects.get_foreign_news(subcategory=subcategory, is_foreign=False)
            most_viewed = News.objects.get_most_viewed(subcategory=subcategory)
            latest_news = News.objects.get_latest(subcategory=subcategory)

            # ---- Ads (fallback to category/global if subcategory ads are few) ----
            ads = Advertisement.objects.filter(
                subcategory=subcategory, is_active=True
            )[:2]
            if ads.count() < 2 and subcategory.category_id:
                remaining = 2 - ads.count()
                category_ads = Advertisement.objects.filter(
                    category_id=subcategory.category_id, is_active=True
                )[:remaining]
                ads = list(ads) + list(category_ads)

            # ---- Response Data ----
            data = {
                "subcategory": SubCategorySerializer(subcategory).data,
                "excerpt_news": {
                    "results": excerpt_serializer.data,
                    "pagination": {
                        "count": paginator.page.paginator.count,
                        "next": paginator.get_next_link(),
                        "previous": paginator.get_previous_link(),
                        "current_page": paginator.page.number,
                        "total_pages": paginator.page.paginator.num_pages,
                    },
                },
                "latest_news": NewsSerializer(latest_news, many=True, context={'request': request}).data,
                "top_news": NewsSerializer(top_news, many=True, context={'request': request}).data,
                "hot_stories": NewsSerializer(hot_stories, many=True, context={'request': request}).data,
                "foreign_news": NewsSerializer(foreign_news, many=True, context={'request': request}).data,
                "local_news": NewsSerializer(local_news, many=True, context={'request': request}).data,
                "most_viewed": NewsSerializer(most_viewed, many=True, context={'request': request}).data,
                "ads": AdvertisementSerializer(ads, many=True).data,
            }

            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)

        except Exception as e:
            logger.error(f"Error fetching subcategory page {subcategory_id}: {str(e)}", exc_info=True)
            return self.error_response("Failed to fetch subcategory page")


class SearchAPIView(APIView):
    def get(self, request):
        search_query = request.query_params.get('q', '').strip()
        if not search_query:
            return Response({"error": "Search query parameter 'q' is required"}, status=status.HTTP_400_BAD_REQUEST)

        category_filter = request.query_params.get('category')
        subcategory_filter = request.query_params.get('subcategory')
        is_top_story = request.query_params.get('is_top_story')
        is_foreign = request.query_params.get('is_foreign')

        # build querysets
        news_queryset = self.search_news(search_query, category_filter, subcategory_filter, is_top_story, is_foreign)
        categories_queryset = self.search_categories(search_query)
        subcategories_queryset = self.search_subcategories(search_query)

        # paginate news using CustomPagination
        paginator = CustomPagination()
        paginated_news = paginator.paginate_queryset(news_queryset, request, view=self)
        news_serializer = NewsSerializer(paginated_news, many=True, context={'request': request})

        # counts
        news_count = news_queryset.count()
        categories_count = categories_queryset.count()
        subcategories_count = subcategories_queryset.count()

        data = {
            'news': {
                "results": news_serializer.data,
                "pagination": {
                    "count": paginator.page.paginator.count if paginator.page is not None else news_count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                    "current_page": paginator.page.number if paginator.page is not None else 1,
                    "total_pages": paginator.page.paginator.num_pages if paginator.page is not None else 1,
                    "page_size": paginator.get_page_size(request)
                }
            },
            'categories': CategorySerializer(categories_queryset, many=True, context={'request': request}).data,
            'subcategories': SubCategorySerializer(subcategories_queryset, many=True, context={'request': request}).data,
            'total_results': news_count + categories_count + subcategories_count,
            'news_count': news_count,
            'categories_count': categories_count,
            'subcategories_count': subcategories_count,
            'current_page': paginator.page.number if paginator.page is not None else 1,
            'page_size': paginator.get_page_size(request),
            'total_pages': paginator.page.paginator.num_pages if paginator.page is not None else 1,
            'search_query': search_query
        }

        serializer = SearchResultsSerializer(data, context={'request': request})
        return Response(serializer.data)
