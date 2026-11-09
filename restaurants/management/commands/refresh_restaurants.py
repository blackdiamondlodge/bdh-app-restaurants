from django.core.management.base import BaseCommand

from restaurants.places import refresh


class Command(BaseCommand):
    help = "Fetch restaurant details (and monthly photos) from Google Places."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Refetch details for every place, not just stale ones.")

    def handle(self, *args, force=False, **options):
        counts = refresh(force=force)
        if counts["skipped"]:
            self.stderr.write("No Google Places API key (GOOGLE_PLACES_API_KEY); nothing fetched.")
            return
        self.stdout.write(f"Fetched {counts['details']} places and {counts['photos']} photos "
                          f"({counts['errors']} errors).")
