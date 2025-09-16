# blog/management/commands/backfill_content.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from blog.models import Category, SubCategory, News, Advertisement
from faker import Faker
import random


class Command(BaseCommand):
    help = 'Backfill news and advertisements for existing categories and subcategories'

    def handle(self, *args, **options):
        fake = Faker()
        User = get_user_model()  # Get the custom user model

        # Get or create a user
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(
                email='admin@example.com',  # Use email instead of username
                password='password123'
            )
            self.stdout.write(
                self.style.SUCCESS('Created default admin user')
            )

        media_types = ['image', 'video', 'none']
        ad_positions = ['header', 'sidebar', 'footer', 'in_content']

        # Sample image URLs for news articles
        sample_images = [
            'https://images.unsplash.com/photo-1504711434969-e33886168f5c',
            'https://images.unsplash.com/photo-1495020689067-958852a7765e',
            'https://images.unsplash.com/photo-1488590528505-98d2b5aba04b',
            'https://images.unsplash.com/photo-1563986768609-322da13575f3',
            'https://images.unsplash.com/photo-1546422904-90eab23c3d7e',
        ]

        # Create news articles
        for subcategory in SubCategory.objects.all():
            for i in range(5):  # Create 5 news per subcategory
                title = fake.sentence(nb_words=8)

                # Create news instance
                news = News(
                    title=title,
                    content='\n\n'.join(fake.paragraphs(nb=10)),
                    media_type=random.choice(media_types),
                    subcategory=subcategory,
                    author=user,
                    is_foreign=random.choice([True, False]),
                    is_top_story=random.choice([True, False]),
                    views=random.randint(0, 10000)  # Increased view range
                )

                # Add image if media_type is 'image'
                if news.media_type == 'image':
                    news.media_url = random.choice(sample_images)

                # Make some articles more popular
                if news.is_top_story:
                    news.views = random.randint(5000, 50000)  # Top stories get more views

                news.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created news: {title} for {subcategory.name} with {news.views} views')
                )

        # Create advertisements
        for position in ad_positions:
            for i in range(3):  # Create 3 ads per position
                ad = Advertisement(
                    title=fake.company(),
                    link=fake.url(),
                    position=position,
                    is_active=random.choice([True, False])
                )

                # Randomly assign category/subcategory or leave null
                if random.choice([True, False]):
                    ad.category = random.choice(Category.objects.all())
                if random.choice([True, False]):
                    ad.subcategory = random.choice(SubCategory.objects.all())

                ad.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created ad: {ad.title} for position {position}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully backfilled news and advertisements')
        )