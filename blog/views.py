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

from .mixin import CachedNewsMixin
from .models import *
from .serializers import *

logger = logging.getLogger(__name__)

CACHE_TTL = getattr(settings, "CACHE_TTL", 60)


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
    """
    Comprehensive search endpoint for news, categories, and subcategories.
    Supports full-text search, filters, and pagination on news.
    """

    def get(self, request):
        search_query = request.query_params.get('q', '').strip()
        if not search_query:
            return Response(
                {"error": "Search query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        category_filter = request.query_params.get('category')
        subcategory_filter = request.query_params.get('subcategory')
        is_top_story = request.query_params.get('is_top_story')
        is_foreign = request.query_params.get('is_foreign')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        # Search querysets
        news_queryset = self.search_news(
            search_query, category_filter, subcategory_filter, is_top_story, is_foreign
        )
        categories_queryset = self.search_categories(search_query)
        subcategories_queryset = self.search_subcategories(search_query)

        # Paginate news using Django's Paginator for efficiency
        paginator = Paginator(news_queryset, page_size)
        paginated_news = paginator.get_page(page).object_list

        # Counts (computed once to avoid redundant queries)
        news_count = paginator.count
        categories_count = categories_queryset.count()
        subcategories_count = subcategories_queryset.count()

        # Prepare data dict for serialization
        response_data = {
            'news': paginated_news,
            'categories': categories_queryset,
            'subcategories': subcategories_queryset,
            'total_results': news_count + categories_count + subcategories_count,
            'news_count': news_count,
            'categories_count': categories_count,
            'subcategories_count': subcategories_count,
            'current_page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'search_query': search_query
        }

        serializer = SearchResultsSerializer(response_data, context={'request': request})
        return Response(serializer.data)

    def search_news(self, query, category_filter=None, subcategory_filter=None,
                    is_top_story=None, is_foreign=None):
        """
        Search news with filters and full-text search (PostgreSQL preferred).
        """
        queryset = News.objects.select_related(
            'subcategory', 'subcategory__category', 'author'
        ).prefetch_related('bookmarks')

        from django.db import connection
        if connection.vendor == 'postgresql':
            # PostgreSQL full-text search
            search_vector = SearchVector('title', weight='A') + \
                            SearchVector('content', weight='B') + \
                            SearchVector('excerpt', weight='C')
            search_query = SearchQuery(query)
            queryset = queryset.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(
                Q(search=search_query) |
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query)
            ).order_by('-rank', '-created')
        else:
            # Fallback for other DBs
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query)
            ).order_by('-created')

        # Apply filters
        if category_filter:
            queryset = queryset.filter(subcategory__category__slug=category_filter)
        if subcategory_filter:
            queryset = queryset.filter(subcategory__slug=subcategory_filter)
        if is_top_story is not None:
            queryset = queryset.filter(is_top_story=is_top_story.lower() == 'true')
        if is_foreign is not None:
            queryset = queryset.filter(is_foreign=is_foreign.lower() == 'true')

        return queryset

    def search_categories(self, query):
        """
        Search categories by name or slug.
        """
        return Category.objects.filter(
            Q(name__icontains=query) | Q(slug__icontains=query)
        )

    def search_subcategories(self, query):
        """
        Search subcategories by name, slug, or parent category name.
        """
        return SubCategory.objects.select_related('category').filter(
            Q(name__icontains=query) |
            Q(slug__icontains=query) |
            Q(category__name__icontains=query)
        )