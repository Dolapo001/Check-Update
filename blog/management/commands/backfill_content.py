from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from blog.models import Category, SubCategory, News, Advertisement
from faker import Faker
from django.utils.text import slugify
import random
import cloudinary.uploader
from django.db import transaction
from django.db.utils import IntegrityError

class Command(BaseCommand):
    help = "Backfill news and advertisements for existing categories and subcategories"

    def handle(self, *args, **options):
        fake = Faker()
        User = get_user_model()

        # Get or create a default user
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(
                email="admin@example.com", password="password123"
            )
            self.stdout.write(self.style.SUCCESS("Created default admin user"))

        media_types = ["image", "video", "none"]
        ad_positions = ["header", "sidebar", "footer", "in_content"]

        # Sample image URLs for news and ads
        sample_images = [
            "https://images.unsplash.com/photo-1504711434969-e33886168f5c",
            "https://images.unsplash.com/photo-1495020689067-958852a7765e",
            "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b",
            "https://images.unsplash.com/photo-1563986768609-322da13575f3",
            "https://images.unsplash.com/photo-1546422904-90eab23c3d7e",
        ]

        # Sample video URLs for news
        sample_videos = [
            "https://www.w3schools.com/html/mov_bbb.mp4",
        ]

        # Backfill news
        subcategories = list(SubCategory.objects.all())
        if not subcategories:
            self.stdout.write(self.style.WARNING("No subcategories found! Skipping news creation."))
            return

        for subcategory in subcategories:
            for _ in range(5):  # 5 news per subcategory
                title = fake.sentence(nb_words=8)
                media_type = random.choice(media_types)

                media_file = None
                if media_type == "image":
                    media_file = random.choice(sample_images)
                elif media_type == "video":
                    media_file = random.choice(sample_videos)
                else:
                    media_type = "none"

                news = News(
                    title=title,
                    slug=slugify(title)[:190],  # Truncate to avoid max_length issues
                    content="\n\n".join(fake.paragraphs(nb=10)),
                    subcategory=subcategory,
                    is_foreign=random.choice([True, False]),
                    is_top_story=random.choice([True, False]),
                    views=random.randint(0, 10000),
                )

                # Upload media to Cloudinary if exists
                if media_file:
                    try:
                        if media_type == "image":
                            result = cloudinary.uploader.upload(media_file, folder="news_media/")
                        elif media_type == "video":
                            result = cloudinary.uploader.upload_large(
                                media_file, resource_type="video", folder="news_media/"
                            )
                        news.media = result["public_id"]
                        news.media_type = media_type
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Failed to upload media for {title}: {e}"))
                        news.media_type = "none"

                # Boost top story views
                if news.is_top_story:
                    news.views = random.randint(5000, 50000)

                # Save with transaction
                try:
                    with transaction.atomic():
                        news.save()
                        self.stdout.write(self.style.SUCCESS(
                            f"Created news: {title} | {news.media_type} | views={news.views}"
                        ))
                except (IntegrityError, Exception) as e:
                    self.stdout.write(self.style.ERROR(f"Failed to save news {title}: {e}"))

        # Backfill advertisements (unchanged for brevity, but similar error handling can be applied)
        categories = list(Category.objects.all())
        if not categories:
            self.stdout.write(self.style.WARNING("No categories found! Skipping ad creation."))
            return

        for position in ad_positions:
            for _ in range(3):
                ad = Advertisement(
                    title=fake.company(),
                    link=fake.url(),
                    position=position,
                    is_active=random.choice([True, False]),
                )

                if categories and random.choice([True, False]):
                    ad.category = random.choice(categories)
                    subcats = list(ad.category.subcategories.all())
                    if subcats and random.choice([True, False]):
                        ad.subcategory = random.choice(subcats)

                media_file = random.choice(sample_images)
                try:
                    result = cloudinary.uploader.upload(media_file, folder="ads/")
                    ad.image = result["public_id"]
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed to upload ad image: {e}"))

                try:
                    with transaction.atomic():
                        ad.save()
                        self.stdout.write(self.style.SUCCESS(
                            f"Created ad: {ad.title} | position={ad.position}"
                        ))
                except (IntegrityError, Exception) as e:
                    self.stdout.write(self.style.ERROR(f"Failed to save ad {ad.title}: {e}"))

        self.stdout.write(self.style.SUCCESS("✅ Successfully backfilled news and advertisements"))