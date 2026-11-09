"""Google Places (New) client and the daily refresh.

Billing: a details call per place per day (about 700 a month for the 23
seeded places) and up to three photos per place a month, both inside
Google's free monthly allowance. Photos are stored in the database, so
page views never call Google. Without an API key nothing is fetched and the
page just shows our curated list.
"""
import datetime as dt
import logging
import threading

import requests
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from bdh_sdk.settings import app_setting

from .models import Photo, Restaurant

log = logging.getLogger(__name__)

API = "https://places.googleapis.com/v1/"
FIELDS = ",".join([
    "id", "displayName", "location", "rating", "userRatingCount", "priceLevel",
    "googleMapsUri", "websiteUri", "nationalPhoneNumber", "regularOpeningHours",
    "utcOffsetMinutes", "businessStatus", "editorialSummary", "generativeSummary", "photos",
    "takeout", "delivery", "dineIn", "reservable", "servesBreakfast", "servesBrunch",
    "servesLunch", "servesDinner", "servesCoffee", "goodForChildren", "menuForChildren",
    "goodForGroups", "outdoorSeating", "allowsDogs", "liveMusic", "goodForWatchingSports",
])
DETAILS_MAX_AGE = dt.timedelta(hours=20)
PHOTOS_MAX_AGE = dt.timedelta(days=30)
PHOTOS_PER_PLACE = 3
PHOTO_WIDTH = 1000
TIMEOUT = 20
LOCK = "restaurants:refresh"
LOCK_SECONDS = 60 * 60


def api_key():
    return app_setting("restaurants", "google_places_api_key", "", legacy=["GOOGLE_PLACES_API_KEY"])


def fetch_details(place_id, key):
    r = requests.get(API + "places/" + place_id, timeout=TIMEOUT,
                     headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELDS})
    r.raise_for_status()
    return r.json()


def fetch_photo(name, key):
    r = requests.get(f"{API}{name}/media", params={"maxWidthPx": PHOTO_WIDTH, "key": key}, timeout=TIMEOUT)
    r.raise_for_status()
    content_type = r.headers.get("Content-Type", "").split(";")[0].strip()
    if not content_type.startswith("image/"):
        raise ValueError(f"not an image: {content_type!r}")
    return r.content, content_type


def _stale(now):
    return (Restaurant.objects.exclude(place_id="")
            .filter(Q(fetched_at__isnull=True) | Q(fetched_at__lt=now - DETAILS_MAX_AGE)
                    | Q(photos_fetched_at__isnull=True) | Q(photos_fetched_at__lt=now - PHOTOS_MAX_AGE)))


def needs_refresh(now=None):
    return _stale(now or timezone.now()).exists()


def _refresh_photos(restaurant, key, now):
    new = []
    for position, photo in enumerate((restaurant.data.get("photos") or [])[:PHOTOS_PER_PLACE]):
        content, content_type = fetch_photo(photo["name"], key)
        author = ", ".join(a.get("displayName", "") for a in photo.get("authorAttributions") or [] if a.get("displayName"))
        new.append(Photo(restaurant=restaurant, position=position, image=content,
                         content_type=content_type, author=author[:200]))
    with transaction.atomic():
        restaurant.photos.all().delete()
        Photo.objects.bulk_create(new)
    return len(new)


def _claim(restaurant, field, max_age, now, force=False):
    """Atomically mark ``field`` as fetched now, unless another refresh (page
    thread or management command, possibly another process) already has.
    Only the run that wins the claim calls Google, so overlapping refreshes
    never pay twice or save duplicate photos."""
    rows = Restaurant.objects.filter(pk=restaurant.pk)
    cutoff = now if force else now - max_age
    claimed = rows.filter(Q(**{f"{field}__isnull": True}) | Q(**{f"{field}__lt": cutoff})).update(**{field: now})
    if claimed:
        setattr(restaurant, field, now)
    return bool(claimed)


def refresh(force=False, now=None):
    """Fetch details (daily) and photos (monthly) for places that need it.

    ``force`` refetches details for every place; photos still follow their
    own 30-day schedule because they cost more. Each attempt is recorded even
    when it fails, so a bad place ID is retried tomorrow, not every hour.
    """
    key = api_key()
    if not key:
        log.info("restaurants: no Google Places API key, skipping refresh")
        return {"details": 0, "photos": 0, "errors": 0, "skipped": True}
    now = now or timezone.now()
    places = Restaurant.objects.exclude(place_id="") if force else _stale(now)
    counts = {"details": 0, "photos": 0, "errors": 0, "skipped": False}
    for restaurant in places:
        if _claim(restaurant, "fetched_at", DETAILS_MAX_AGE, now, force):
            try:
                restaurant.data = fetch_details(restaurant.place_id, key)
                restaurant.save(update_fields=["data"])
                counts["details"] += 1
            except (requests.RequestException, ValueError) as e:
                log.warning("restaurants: details for %s failed: %s", restaurant.slug, e)
                counts["errors"] += 1
        else:
            restaurant.refresh_from_db(fields=["data"])
        if restaurant.data and _claim(restaurant, "photos_fetched_at", PHOTOS_MAX_AGE, now):
            try:
                counts["photos"] += _refresh_photos(restaurant, key, now)
            except (requests.RequestException, ValueError) as e:
                log.warning("restaurants: photos for %s failed: %s", restaurant.slug, e)
                counts["errors"] += 1
    return counts


def _run():
    try:
        log.info("restaurants: refreshed %s", refresh())
    except Exception:
        log.exception("restaurants: refresh failed")
    finally:
        connection.close()


def maybe_refresh_async():
    """Start a background refresh if something is stale. Checks at most once
    an hour; cheap enough to call on every page view."""
    if not api_key() or not cache.add(LOCK, True, LOCK_SECONDS):
        return False
    if not needs_refresh():
        return False
    threading.Thread(target=_run, name="restaurants-refresh", daemon=True).start()
    return True
