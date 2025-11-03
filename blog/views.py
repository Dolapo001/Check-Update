import logging
from datetime import timedelta
from math import ceil

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
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 20
    page_query_param = 'page'

    def get_paginated_response_data(self, data):
        """
        Return a plain dict (not a Response) with consistent structure.
        Safe if self.page is None (defensive).
        """
        page_obj = getattr(self, "page", None)
        paginator = getattr(page_obj, "paginator", None) if page_obj is not None else None

        total_count = paginator.count if paginator is not None else 0
        total_pages = paginator.num_pages if paginator is not None else 1
        current_page = page_obj.number if page_obj is not None else 1

        # DRF provides .get_next_link and .get_previous_link which build full URLs if request is set.
        return {
            "results": data,
            "pagination": {
                "count": total_count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "current_page": current_page,
                "total_pages": total_pages,
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

    def paginate_queryset_and_respond(self, request: Request, queryset, serializer_class, many=True,
                                      message="Success", status_code=status.HTTP_200_OK):
        """
        Paginate a queryset using CustomPagination and return success_response.
        """
        paginator = CustomPagination()
        paginated_qs = paginator.paginate_queryset(queryset, request, view=self)
        # Note: paginate_queryset always sets paginator.request internally
        serializer = serializer_class(paginated_qs, many=many, context={'request': request})
        data = paginator.get_paginated_response_data(serializer.data)
        return self.success_response(data, message=message, status_code=status_code)

    def limited_queryset_and_respond(self, request: Request, queryset, serializer_class, default_limit=10,
                                     message="Success", status_code=status.HTTP_200_OK):
        """
        Return a limited slice of the queryset with consistent paginated structure, but no actual pagination.
        """
        try:
            limit_val = int(request.query_params.get('limit', default_limit))
        except ValueError:
            limit_val = default_limit

        sliced = queryset[:limit_val]
        serializer = serializer_class(sliced, many=True, context={'request': request})

        # Build consistent pagination metadata (fixed to page 1)
        total_count = queryset.count()
        page_size = len(serializer.data)
        data = {
            "results": serializer.data,
            "pagination": {
                "count": total_count,
                "next": None,
                "previous": None,
                "current_page": 1,
                "total_pages": 1,
                "page_size": page_size,
            },
        }

        return self.success_response(data, message=message, status_code=status_code)


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
        queryset = News.objects.get_latest()  # Assume this returns full queryset; refactor if it takes limit

        # Generate cache key based on params
        limit = request.query_params.get('limit')
        cache_key = f"news:latest:limit={limit}"

        # Check cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return self.success_response(cached_data)

        # Use helper to limit
        response = self.limited_queryset_and_respond(
            request, queryset, NewsSerializer, default_limit=10
        )

        # Cache the data part
        cache.set(cache_key, response.data['data'], timeout=CACHE_TTL)
        return response


class TrendingNewsView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        queryset = News.objects.get_trending()  # Assume full queryset

        limit = request.query_params.get('limit')
        cache_key = f"news:trending:limit={limit}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return self.success_response(cached_data)

        response = self.limited_queryset_and_respond(
            request, queryset, NewsSerializer, default_limit=10
        )
        cache.set(cache_key, response.data['data'], timeout=CACHE_TTL)
        return response


class TopStoriesView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        queryset = News.objects.get_top_stories()  # Assume full queryset

        limit = request.query_params.get('limit')
        cache_key = f"news:topstories:limit={limit}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return self.success_response(cached_data)

        response = self.limited_queryset_and_respond(
            request, queryset, NewsSerializer, default_limit=10
        )
        cache.set(cache_key, response.data['data'], timeout=CACHE_TTL)
        return response


class MostWatchedView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        queryset = News.objects.get_most_watched_videos()  # Assume full queryset

        limit = request.query_params.get('limit')
        cache_key = f"news:mostwatched:limit={limit}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return self.success_response(cached_data)

        response = self.limited_queryset_and_respond(
            request, queryset, NewsSerializer, default_limit=10
        )
        cache.set(cache_key, response.data['data'], timeout=CACHE_TTL)
        return response


class RecommendedNewsView(CachedNewsMixin, BaseAPIView):
    def get(self, request):
        queryset = News.objects.get_recommended(request.user)  # Assume full queryset; remove limit if present

        user_part = f"user={getattr(request.user, 'id', 'anon')}"
        limit = request.query_params.get('limit')
        cache_key = f"news:recommended:{user_part}:limit={limit}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return self.success_response(cached_data)

        response = self.limited_queryset_and_respond(
            request, queryset, NewsSerializer, default_limit=10
        )
        cache.set(cache_key, response.data['data'], timeout=CACHE_TTL)
        return response


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


class SubCategoryPageView(APIView):
    def get(self, request, subcategory_id):
        try:
            page = request.GET.get('page', '1')
            page_size = request.GET.get('page_size', CustomPagination.page_size)

            try:
                current_page = int(page)
                page_size = int(page_size)
                if current_page < 1 or page_size < 1:
                    raise ValueError
            except ValueError:
                return Response({"status": "error", "message": "Invalid page or page_size parameters"}, status=400)

            cache_key = f"subcategory_page:{subcategory_id}:page={page}:size={page_size}"

            data = cache.get(cache_key)
            if data is not None:
                return Response({"status": "success", "message": "Success", "data": data})

            subcategory = get_object_or_404(SubCategory, id=subcategory_id)

            sections = {}
            try:
                sections["excerpt_news"] = News.objects.filter(subcategory=subcategory).order_by('-created')
                sections["latest_news"] = News.objects.filter(subcategory=subcategory).order_by('-created')
                sections["top_news"] = News.objects.filter(subcategory=subcategory).order_by('-views')
                sections["hot_stories"] = News.objects.filter(
                    subcategory=subcategory,
                    created__gte=timezone.now() - timedelta(days=7)
                ).order_by('-views')
                sections["foreign_news"] = News.objects.filter(
                    subcategory=subcategory,
                    is_foreign=True
                ).order_by('-created')
                sections["local_news"] = News.objects.filter(
                    subcategory=subcategory,
                    is_foreign=False
                ).order_by('-created')
                sections["most_viewed"] = News.objects.filter(subcategory=subcategory).order_by('-views')
            except Exception as qs_err:
                logger.error(f"Queryset fetch error for subcategory {subcategory_id}: {str(qs_err)}")
                sections = {name: News.objects.none() for name in
                            ["excerpt_news", "latest_news", "top_news", "hot_stories", "foreign_news", "local_news",
                             "most_viewed"]}  # Empty querysets

            paginated_sections = ["excerpt_news", "latest_news", "foreign_news", "local_news"]
            non_paginated_sections = ["top_news", "hot_stories", "most_viewed"]

            start_index = (current_page - 1) * page_size
            end_index = start_index + page_size

            paginated_counts = {}
            for name in paginated_sections:
                try:
                    paginated_counts[name] = sections[name].count()
                except Exception:
                    paginated_counts[name] = 0
            max_count = max(paginated_counts.values()) if paginated_counts else 0
            total_pages = ceil(max_count / page_size) if page_size > 0 else 1
            count = max_count

            paginated_data = {}
            for name, qs in sections.items():
                try:
                    if name in non_paginated_sections:
                        sliced_qs = qs[:page_size]
                    else:
                        sliced_qs = qs[start_index:end_index]
                except Exception as slice_err:
                    logger.error(f"Slicing error for section {name}: {str(slice_err)}")
                    sliced_qs = qs.none()  # Empty

                try:
                    serializer = NewsSerializer(sliced_qs, many=True, context={'request': request})
                    paginated_data[name] = serializer.data
                except Exception as ser_err:
                    logger.error(f"Serialization error for section {name}: {str(ser_err)}")
                    paginated_data[name] = []

            ads = Advertisement.objects.filter(
                subcategory=subcategory, is_active=True
            )[:2]
            if len(ads) < 2 and subcategory.category_id:
                remaining = 2 - len(ads)
                category_ads = Advertisement.objects.filter(
                    category_id=subcategory.category_id, is_active=True
                )[:remaining]
                ads = list(ads) + list(category_ads)

            data = {
                "current_page": current_page if current_page <= total_pages else total_pages,  # Cap if out of range
                "total_pages": total_pages,
                "next": f"?page={current_page + 1}" if current_page < total_pages else None,
                "previous": f"?page={current_page - 1}" if current_page > 1 else None,
                "count": count,
                **paginated_data,
                "ads": AdvertisementSerializer(ads, many=True).data,
                "subcategory": SubCategorySerializer(subcategory).data,
            }

            cache.set(cache_key, data, timeout=CACHE_TTL)
            return Response({"status": "success", "message": "Success", "data": data})

        except Exception as e:
            logger.error(f"Critical error in subcategory page {subcategory_id}: {str(e)}", exc_info=True)
            subcategory_data = SubCategorySerializer(get_object_or_404(SubCategory, id=subcategory_id)).data
            return Response({"status": "error", "message": "Failed to fetch full page", "data": subcategory_data},
                            status=500)

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