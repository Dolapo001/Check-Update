# blog/management/commands/backfill_content.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from blog.models import Category, SubCategory, News, Advertisement
from faker import Faker
from django.utils.text import slugify
import random


class Command(BaseCommand):
    help = 'Backfill news and advertisements for existing categories and subcategories'

    def handle(self, *args, **options):
        fake = Faker()
        User = get_user_model()

        # Get or create a user
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(
                email='admin@example.com',
                password='password123'
            )
            self.stdout.write(
                self.style.SUCCESS('Created default admin user')
            )

        media_types = ['image', 'video', 'none']
        ad_positions = ['header', 'sidebar', 'footer', 'in_content']

        # Sample image URLs
        sample_images = [
            'https://images.unsplash.com/photo-1504711434969-e33886168f5c',
            'https://images.unsplash.com/photo-1495020689067-958852a7765e',
            'https://images.unsplash.com/photo-1488590528505-98d2b5aba04b',
            'https://images.unsplash.com/photo-1563986768609-322da13575f3',
            'https://images.unsplash.com/photo-1546422904-90eab23c3d7e',
        ]

        # Sample video URLs
        sample_videos = [
            'https://www.w3schools.com/html/mov_bbb.mp4',
            'https://samplelib.com/lib/preview/mp4/sample-5s.mp4',
            'https://filesamples.com/samples/video/mp4/sample_640x360.mp4',
        ]

        # Create news articles
        for subcategory in SubCategory.objects.all():
            for i in range(5):  # Create 5 news per subcategory
                title = fake.sentence(nb_words=8)

                # Pick media type
                media_type = random.choice(media_types)

                # Decide on media file (or None)
                media_file = None
                if media_type == 'image':
                    media_file = random.choice(sample_images)
                elif media_type == 'video':
                    media_file = random.choice(sample_videos)

                news = News(
                    title=title,
                    slug=slugify(title)[:200],  # Ensure slug fits field length
                    content='\n\n'.join(fake.paragraphs(nb=10)),
                    media_type=media_type,
                    subcategory=subcategory,
                    author=user,
                    is_foreign=random.choice([True, False]),
                    is_top_story=random.choice([True, False]),
                    views=random.randint(0, 10000),
                )

                # Assign media only if not None
                if media_file:
                    news.media = media_file
                else:
                    news.media = None

                # Boost top story views
                if news.is_top_story:
                    news.views = random.randint(5000, 50000)

                news.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created news: {title} | {media_type} | views={news.views}'
                    )
                )

        # Create advertisements
        for position in ad_positions:
            for i in range(3):
                ad = Advertisement(
                    title=fake.company(),
                    link=fake.url(),
                    position=position,
                    is_active=random.choice([True, False])
                )

                if random.choice([True, False]):
                    ad.category = random.choice(Category.objects.all())
                if random.choice([True, False]):
                    ad.subcategory = random.choice(SubCategory.objects.all())

                ad.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created ad: {ad.title} for {position}')
                )

        self.stdout.write(
            self.style.SUCCESS('✅ Successfully backfilled news and advertisements')
        )
