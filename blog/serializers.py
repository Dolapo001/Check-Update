from rest_framework import serializers
from .models import Category, SubCategory, News, Advertisement


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = '__all__'


class NewsSerializer(serializers.ModelSerializer):
    subcategory = serializers.StringRelatedField()
    is_bookmarked = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = News
        exclude = ('bookmarks',)
        read_only_fields = ('excerpt',)

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(id=request.user.id).exists()
        return False

    def get_media_url(self, obj):
        if obj.media:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.media) if request else str(obj.media)
        return None


class AdvertisementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertisement
        fields = '__all__'


class NewsSearchSerializer(serializers.ModelSerializer):
    subcategory = SubCategorySerializer(read_only=True)
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content',
            'media', 'media_type', 'subcategory',
            'is_foreign', 'is_top_story', 'views', 'is_bookmarked',
            'created', 'updated'
        ]

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(id=request.user.id).exists()
        return False


class SearchResultsSerializer(serializers.Serializer):
    news = NewsSearchSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    subcategories = SubCategorySerializer(many=True, read_only=True)
    total_results = serializers.IntegerField(read_only=True)
    news_count = serializers.IntegerField(read_only=True)
    categories_count = serializers.IntegerField(read_only=True)
    subcategories_count = serializers.IntegerField(read_only=True)
    media = serializers.SerializerMethodField()

    def get_media(self, obj):
        """
        Aggregate media details from the news results.
        Returns a list of dicts with URL, type, and associated news slug for frontend use.
        """
        request = self.context.get('request')
        if not request:
            return []  # Fallback if no request context

        media_list = []
        for news_item in obj['news']:
            if news_item.media:
                media_list.append({
                    'url': request.build_absolute_uri(news_item.media.url),
                    'type': news_item.media_type,
                    'news_slug': news_item.slug  # Or use ID if preferred
                })
        return media_list
