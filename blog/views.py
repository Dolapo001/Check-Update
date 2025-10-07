import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.cache import cache
from .models import *
from .serializers import *

logger = logging.getLogger(__name__)

# default TTL (seconds) - can be overridden via settings.CACHE_TTL
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


class LatestNewsView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            cache_key = f"news:latest:limit={limit}"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            news = News.objects.get_latest(limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching latest news: {str(e)}")
            return self.error_response("Failed to fetch latest news")


class TrendingNewsView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            cache_key = f"news:trending:limit={limit}"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            news = News.objects.get_trending(limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching trending news: {str(e)}")
            return self.error_response("Failed to fetch trending news")


class TopStoriesView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            cache_key = f"news:topstories:limit={limit}"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            news = News.objects.get_top_stories(limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching top stories: {str(e)}")
            return self.error_response("Failed to fetch top stories")


class MostWatchedView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            cache_key = f"news:mostwatched:limit={limit}"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            news = News.objects.get_most_watched_videos(limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching most watched videos: {str(e)}")
            return self.error_response("Failed to fetch most watched videos")


class RecommendedNewsView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            # include user id in cache key for personalized results; anonymous = "anon"
            user_part = f"user={getattr(request.user, 'id', 'anon')}"
            cache_key = f"news:recommended:{user_part}:limit={limit}"
            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            news = News.objects.get_recommended(request.user, limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching recommended news: {str(e)}")
            return self.error_response("Failed to fetch recommended news")


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
            # include page & page_size in cache key so different pages are cached separately
            page = request.GET.get('page', '1')
            page_size = request.GET.get('page_size', None) or CustomPagination.page_size
            cache_key = f"subcategory_page:{subcategory_id}:page={page}:size={page_size}"

            data = cache.get(cache_key)
            if data is not None:
                return self.success_response(data)

            subcategory = get_object_or_404(SubCategory, id=subcategory_id)

            # Get paginated excerpt news with proper ordering
            excerpt_news = News.objects.get_excerpt(subcategory=subcategory)
            paginator = CustomPagination()
            paginated_excerpt_news = paginator.paginate_queryset(excerpt_news, request)
            excerpt_serializer = NewsSerializer(paginated_excerpt_news, many=True, context={'request': request})

            # Get other data (not paginated)
            top_news = News.objects.get_most_viewed(subcategory=subcategory, limit=5)
            hot_stories = News.objects.get_hot_stories_this_week(subcategory=subcategory)
            foreign_news = News.objects.get_foreign_news(subcategory=subcategory, is_foreign=True)
            local_news = News.objects.get_foreign_news(subcategory=subcategory, is_foreign=False)
            ads = Advertisement.objects.filter(
                subcategory=subcategory,
                is_active=True
            )[:2]
            most_viewed = News.objects.get_most_viewed(subcategory=subcategory)
            latest_news = News.objects.get_latest(subcategory=subcategory)

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
                    }
                },
                "top_news": NewsSerializer(top_news, many=True, context={'request': request}).data,

                "hot_stories": NewsSerializer(hot_stories, many=True, context={'request': request}).data,
                "foreign_news": NewsSerializer(foreign_news, many=True, context={'request': request}).data,
                "local_news": NewsSerializer(local_news, many=True, context={'request': request}).data,
                "ads": AdvertisementSerializer(ads, many=True).data,
                "most_viewed": NewsSerializer(most_viewed, many=True, context={'request': request}).data,
                "latest_news": NewsSerializer(latest_news, many=True,context={'request': request}).data
            }

            cache.set(cache_key, data, timeout=CACHE_TTL)
            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching subcategory page {subcategory_id}: {str(e)}")
            return self.error_response("Failed to fetch subcategory page")
