from django.core.management.base import BaseCommand
from django.db import connection

from geo.cache import GEOCODE_CACHE_COLLECTION, ROUTE_CACHE_COLLECTION


class Command(BaseCommand):
    help = "Create the unique and TTL indexes the geo caches (route_cache, geocode_cache) rely on."

    def handle(self, *args, **options):
        database = connection.database

        database[ROUTE_CACHE_COLLECTION].create_index("coords_hash", unique=True)
        database[ROUTE_CACHE_COLLECTION].create_index("expires_at", expireAfterSeconds=0)
        database[GEOCODE_CACHE_COLLECTION].create_index("key", unique=True)
        database[GEOCODE_CACHE_COLLECTION].create_index("expires_at", expireAfterSeconds=0)

        self.stdout.write(
            self.style.SUCCESS(
                f"Ensured indexes on {ROUTE_CACHE_COLLECTION} (coords_hash unique, expires_at TTL) "
                f"and {GEOCODE_CACHE_COLLECTION} (key unique, expires_at TTL)."
            )
        )
