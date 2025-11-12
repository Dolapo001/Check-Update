from django.core.management.base import BaseCommand
from blog.models import News
from bs4 import BeautifulSoup


class Command(BaseCommand):
    help = "Populate excerpt for existing news items"

    def handle(self, *args, **options):
        news_items = News.objects.filter(excerpt="")
        count = news_items.count()
        self.stdout.write(f"Found {count} news items with empty excerpt.")

        for news in news_items:
            if news.content:
                # Strip HTML tags and get first 150 characters
                clean_content = "".join(
                    BeautifulSoup(news.content, "html.parser").findAll(text=True)
                )
                news.excerpt = (
                    clean_content[:150] + "..."
                    if len(clean_content) > 150
                    else clean_content
                )
                news.save(update_fields=["excerpt"])
                self.stdout.write(f"Updated excerpt for news: {news.title}")

        self.stdout.write(self.style.SUCCESS("Successfully populated excerpts."))


from django.db import connection

connection.close()
