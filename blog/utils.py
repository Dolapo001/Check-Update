from django.utils.text import slugify
import uuid
from .models import News


def generate_unique_slug(model, value, max_length=200):
    """
    Generate a unique slug for a model instance
    """
    slug = slugify(value)[:max_length]
    unique_slug = slug
    counter = 1

    while model.objects.filter(slug=unique_slug).exists():
        unique_slug = f"{slug}-{counter}"
        counter += 1

        if len(unique_slug) > max_length:
            # If the slug is too long, use a UUID
            unique_slug = f"{slug[:max_length - 37]}-{uuid.uuid4().hex}"

    return unique_slug


class RecommendationEngine:
    @staticmethod
    def get_recommendations(user, limit=10):
        """
        Enhanced recommendation logic based on user preferences
        """
        if not user.is_authenticated:
            return News.objects.get_latest(limit)

        # Get user's bookmarked categories
        bookmarked_categories = (
            News.objects.filter(bookmarks=user)
            .values_list("subcategory__category", flat=True)
            .distinct()
        )

        # Get user's viewed categories (you'd need to implement view tracking)
        # viewed_categories = ...

        # Combine preferences
        preferred_categories = (
            bookmarked_categories  # Add viewed_categories if available
        )

        # Get news from preferred categories
        recommendations = (
            News.objects.filter(subcategory__category__in=preferred_categories)
            .exclude(bookmarks=user)
            .order_by("-created_at", "-views")[:limit]
        )

        # If not enough recommendations, fill with popular news
        if len(recommendations) < limit:
            additional_news = News.objects.exclude(
                id__in=[news.id for news in recommendations]
            ).order_by("-views")[: limit - len(recommendations)]
            recommendations = list(recommendations) + list(additional_news)

        return recommendations
