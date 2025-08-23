from django.core.management.base import BaseCommand
from apps.categories.models import Category, SubCategory


class Command(BaseCommand):
    help = 'Backfill categories and subcategories'

    def handle(self, *args, **options):
        categories_data = {
            "🏅 Sports": ["Sports News", "Results", "Live Matches"],
            "🎭 Entertainment": ["Music", "Movies", "TV Shows", "Celebrity News", "Social Events"],
            "🎓 Education": ["Academics", "Resources"],
            "🌿 Lifestyle": ["Health", "Relationship & Family", "Beauty & Fashion", "Food", "Travel"],
            "🏛️ Politics": ["Government News", "International News"],
            "💼 Business": ["Market Trends", "Business Decisions", "Economics News", "Entrepreneurship", "Finance"],
            "🔬 Science & Tech": ["Tech News", "Innovations", "Agriculture", "Engineering", "Gadgets"],
            "🌍 Culture & Religion": ["Religion News", "Cultural Events"],
            "🌏 Earth & Wildlife": ["Climate & Weather", "Wildlife Conservation", "Natural Wonders"],
            "🚀 Opportunities": ["Job Listings", "Scholarships", "Career Development", "Grants", "Internships"],
            "🏆 CheckUpdate Awards": ["Job Listings", "Scholarships", "Career Development", "Grants", "Internships"]
        }

        for category_name, subcategories in categories_data.items():
            # Extract icon and name
            if ' ' in category_name:
                icon, name = category_name.split(' ', 1)
                name = name.strip()
            else:
                icon, name = '', category_name

            category, created = Category.objects.get_or_create(
                name=name,
                defaults={'icon': icon}
            )

            for subcategory_name in subcategories:
                SubCategory.objects.get_or_create(
                    category=category,
                    name=subcategory_name
                )

            self.stdout.write(
                self.style.SUCCESS(f'Successfully added {category.name} with {len(subcategories)} subcategories')
            )