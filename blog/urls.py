from django.urls import path, re_path
from .views import *

urlpatterns = [
    re_path(r'^news/(?P<news_id>[0-9a-f-]+)/$', NewsDetailView.as_view(), name='news-detail'),
    path('news/latest/', LatestNewsView.as_view(), name='latest-news'),
    path('news/trending/', TrendingNewsView.as_view(), name='trending-news'),
    path('news/most-watched/', MostWatchedView.as_view(), name='most-watched'),
    path('news/top-stories/', TopStoriesView.as_view(), name='top-stories'),
    path('news/recommended/', RecommendedNewsView.as_view(), name='recommended-news'),
    re_path(r'^news/(?P<news_id>[0-9a-f-]+)/bookmark/$', BookmarkNewsView.as_view(), name='bookmark-news'),
    re_path(r'^news/(?P<news_id>[0-9a-f-]+)/share/$', ShareNewsView.as_view(), name='share-news'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    re_path(r'^categories/(?P<category_id>[0-9a-f-]+)/$', CategoryDetailView.as_view(), name='category-detail'),
    re_path(r'^categories/(?P<category_id>[0-9a-f-]+)/page/$', CategoryPageView.as_view(), name='category-page'),
    re_path(r'^subcategories/(?P<subcategory_id>[0-9a-f-]+)/$', SubCategoryDetailView.as_view(), name='subcategory-detail'),
    re_path(r'^subcategories/(?P<subcategory_id>[0-9a-f-]+)/page/$', SubCategoryPageView.as_view(), name='subcategory-page'),
]
