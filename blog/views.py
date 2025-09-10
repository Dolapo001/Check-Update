import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import *
from .serializers import *
logger = logging.getLogger(__name__)


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
            news = News.objects.get_latest(limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            return self.success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching latest news: {str(e)}")
            return self.error_response("Failed to fetch latest news")


class TrendingNewsView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            news = News.objects.get_trending(limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            return self.success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching trending news: {str(e)}")
            return self.error_response("Failed to fetch trending news")


class TopStoriesView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            news = News.objects.get_top_stories(limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            return self.success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching top stories: {str(e)}")
            return self.error_response("Failed to fetch top stories")


class MostWatchedView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            news = News.objects.get_most_watched_videos(limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            return self.success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching most watched videos: {str(e)}")
            return self.error_response("Failed to fetch most watched videos")


class RecommendedNewsView(BaseAPIView):
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            news = News.objects.get_recommended(request.user, limit)
            serializer = NewsSerializer(news, many=True, context={'request': request})
            return self.success_response(serializer.data)
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
            categories = Category.objects.prefetch_related('subcategories').all()
            serializer = CategorySerializer(categories, many=True)
            return self.success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching categories: {str(e)}")
            return self.error_response("Failed to fetch categories")


class CategoryDetailView(BaseAPIView):
    def get(self, request, category_id):
        try:
            category = get_object_or_404(Category, id=category_id)
            serializer = CategorySerializer(category)
            return self.success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching category {category_id}: {str(e)}")
            return self.error_response("Failed to fetch category")


class SubCategoryDetailView(BaseAPIView):
    def get(self, request, subcategory_id):
        try:
            subcategory = get_object_or_404(SubCategory, id=subcategory_id)
            serializer = SubCategorySerializer(subcategory)
            return self.success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching subcategory {subcategory_id}: {str(e)}")
            return self.error_response("Failed to fetch subcategory")


class CategoryPageView(BaseAPIView):
    def get(self, request, category_id):
        try:
            category = get_object_or_404(Category, id=category_id)
            ads = Advertisement.objects.filter(
                category=category,
                is_active=True
            )[:3]  # Get 3 active ads for this category

            category_serializer = CategorySerializer(category)
            ads_serializer = AdvertisementSerializer(ads, many=True)

            return self.success_response({
                "category": category_serializer.data,
                "ads": ads_serializer.data
            })
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
            subcategory = get_object_or_404(SubCategory, id=subcategory_id)

            # Get paginated excerpt news
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
            }

            return self.success_response(data)
        except Exception as e:
            logger.error(f"Error fetching subcategory page {subcategory_id}: {str(e)}")
            return self.error_response("Failed to fetch subcategory page")