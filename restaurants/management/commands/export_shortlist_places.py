"""Print places.json for the shortlist page (blackdiamondlodge/shortlist).

Kiosk shortlist links carry short codes that the page looks up in this file.
Re-run after adding or renaming restaurants and commit the output to the
shortlist repo; until then the kiosk sends those places in the long form.

    python manage.py export_shortlist_places --merge places.json > new.json

--merge keeps entries from an earlier export, so links from past stays still
resolve after a restaurant is removed.
"""
import json

from django.core.management.base import BaseCommand

from restaurants.catalog import short_code
from restaurants.models import Restaurant


class Command(BaseCommand):
    help = "Print the shortlist page's places.json"

    def add_arguments(self, parser):
        parser.add_argument("--merge", metavar="PATH", help="earlier places.json to keep entries from")

    def handle(self, *args, merge=None, **options):
        places = {}
        if merge:
            with open(merge, encoding="utf-8") as f:
                places.update(json.load(f).get("places", {}))
        current = {}
        for r in Restaurant.objects.order_by("slug"):
            code = short_code(r.slug)
            if code in current:
                self.stderr.write(f"code {code} is shared by {current[code]['n']} and {r.name}; "
                                  f"{r.name} will use the long link form")
                continue
            current[code] = {"n": r.name, "p": r.place_id}
        places.update(current)
        self.stdout.write(json.dumps({"v": 1, "places": places}, indent=1, sort_keys=True, ensure_ascii=False))
