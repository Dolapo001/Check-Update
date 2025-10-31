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
    media_url = serializers.SerializerMethodField()  # Custom field for absolute URL

    class Meta:
        model = News
        fields = [
            'id',  # Include if needed for uniqueness
            'title',
            'slug',
            'excerpt',
            'media_url',  # Our new field
            'media_type',
            'subcategory',  # Or nested serializer if needed
            'author',  # Or nested if UserSerializer exists
            'is_foreign',
            'is_top_story',
            'views',
            # Add other fields as required (e.g., 'created', 'bookmarks' as list of IDs)
        ]
        read_only_fields = fields  # All read-only for search results

    def get_media_url(self, obj):
        """
        Returns the absolute URL of the media file if it exists.
        Uses request context for domain/protocol resolution.
        """
        if obj.media:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.media.url)
            return obj.media.url  # Fallback to relative URL
        return None  # Or '' if preferred for consistency


class SearchResultsSerializer(serializers.Serializer):
    news = NewsSearchSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    subcategories = SubCategorySerializer(many=True, read_only=True)
    total_results = serializers.IntegerField(read_only=True)
    news_count = serializers.IntegerField(read_only=True)
    categories_count = serializers.IntegerField(read_only=True)
    subcategories_count = serializers.IntegerField(read_only=True)

