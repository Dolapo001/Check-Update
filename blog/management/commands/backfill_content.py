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

        # Create news articles
        for subcategory in SubCategory.objects.all():
            for i in range(5):  # Create 5 news per subcategory
                title = fake.sentence(nb_words=8)
                news = News(
                    title=title,
                    content='\n\n'.join(fake.paragraphs(nb=10)),
                    media_type=random.choice(media_types),
                    subcategory=subcategory,
                    author=user,
                    is_foreign=random.choice([True, False]),
                    is_top_story=random.choice([True, False]),
                    views=random.randint(0, 1000)
                )
                news.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created news: {title} for {subcategory.name}')
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