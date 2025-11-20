from rest_framework import serializers
from .models import Category, SubCategory, News, Advertisement
from cloudinary.utils import cloudinary_url
import re


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = "__all__"


class NewsSerializer(serializers.ModelSerializer):
    subcategory = serializers.StringRelatedField()
    is_bookmarked = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = News
        exclude = ("bookmarks",)
        read_only_fields = ("excerpt",)

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.bookmarks.filter(id=request.user.id).exists()
        return False

    def _normalize_public_id(self, stored_value):
        """
        Turn a stored value like:
          - "image/upload/v1763640880/news_media/mzlis3p9jajz3mz50mpm.jpg"
          - "news_media/mzlis3p9jajz3mz50mpm"
          - "mzlis3p9jajz3mz50mpm"
        into the Cloudinary public_id expected by cloudinary.utils.cloudinary_url:
          "news_media/mzlis3p9jajz3mz50mpm"
        """
        if not stored_value:
            return None
        if hasattr(stored_value, "name"):
            stored_value = stored_value.name

        # If it's a full URL, try to extract public_id
        if stored_value.startswith("http"):
            # crude extraction: get last path component without extension
            last = stored_value.rstrip("/").split("/")[-1]
            return last.rsplit(".", 1)[0]

        # Remove common prefixes like 'image/upload' and versions 'v1234'
        # and strip file extensions
        # Example: image/upload/v12345/news_media/abc.jpg -> news_media/abc
        parts = stored_value.split("/")
        if "upload" in parts:
            upload_idx = parts.index("upload")
            remainder = parts[upload_idx + 1 :]
            # remove version token if present (v\d+)
            if remainder and re.match(r"v\d+", remainder[0]):
                remainder = remainder[1:]
            public_id = "/".join(remainder)
        else:
            public_id = stored_value

        public_id = public_id.rsplit(".", 1)[0]  # remove extension
        return public_id

    def get_media_url(self, obj):
        if not obj.media:
            return None

        # Prefer storage .url (works if DEFAULT_FILE_STORAGE -> MediaCloudinaryStorage)
        try:
            # obj.media.url can raise or return a path-like value; ensure it's absolute
            url = getattr(obj.media, "url", None)
            if url:
                # If it is relative, make absolute when request exists
                request = self.context.get("request")
                if request and url.startswith("/"):
                    return request.build_absolute_uri(url)
                return url
        except Exception:
            # Fall through to cloudinary_url fallback
            pass

        # Fallback: build URL from stored public_id using cloudinary.utils
        public_id = self._normalize_public_id(getattr(obj.media, "name", None) or str(obj.media))
        if not public_id:
            return None

        url, _ = cloudinary_url(public_id, resource_type="image", secure=True)
        return url


class AdvertisementSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Advertisement
        fields = "__all__"

    def get_image_url(self, obj):
        if not obj.image:
            return None
        # Preferred: storage-provided URL
        try:
            url = getattr(obj.image, "url", None)
            if url:
                return url
        except Exception:
            pass

        # If your image field exposes build_url (older Cloudinary SDK objects), use that
        try:
            return obj.image.build_url(secure=True, transformation={"quality": "auto"})
        except Exception:
            pass

        # Last fallback: build via cloudinary utils
        public_id = getattr(obj.image, "name", None) or str(obj.image)
        # remove file extension if present
        public_id = public_id.rsplit(".", 1)[0]
        url, _ = cloudinary_url(public_id, resource_type="image", secure=True)
        return url


class NewsSearchSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()  # Custom field for absolute URL

    class Meta:
        model = News
        fields = [
            "id",  # Include if needed for uniqueness
            "title",
            "slug",
            "excerpt",
            "media_url",  # Our new field
            "media_type",
            "subcategory",  # Or nested serializer if needed
            "author",  # Or nested if UserSerializer exists
            "is_foreign",
            "is_top_story",
            "views",
            # Add other fields as required (e.g., 'created', 'bookmarks' as list of IDs)
        ]
        read_only_fields = fields  # All read-only for search results

    def get_media_url(self, obj):
        if obj.media:
            # Basic URL: return obj.media.url
            # With transformation (e.g., resize image/video thumbnail)
            return obj.media.build_url(
                secure=True, transformation={"width": 800, "crop": "scale"}
            )
        return None  # Or '' if preferred for consistency


class SearchResultsSerializer(serializers.Serializer):
    news = NewsSearchSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    subcategories = SubCategorySerializer(many=True, read_only=True)
    total_results = serializers.IntegerField(read_only=True)
    news_count = serializers.IntegerField(read_only=True)
    categories_count = serializers.IntegerField(read_only=True)
    subcategories_count = serializers.IntegerField(read_only=True)
