# blog/management/commands/kill_idle_db_connections.py
from django.core.management.base import BaseCommand
import psycopg2
import os
from urllib.parse import urlparse

class Command(BaseCommand):
    help = "Kill idle PostgreSQL connections"

    def handle(self, *args, **options):
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            self.stderr.write(self.style.ERROR("DATABASE_URL not set"))
            return

        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port,
            sslmode="require"
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE state = 'idle'
              AND pid <> pg_backend_pid();
        """)

        killed = cur.rowcount
        self.stdout.write(self.style.SUCCESS(f"Killed {killed} idle connections."))

        cur.close()
        conn.close()
