import json

from django.db.models import Prefetch
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from bdh_sdk.settings import app_setting

from . import catalog
from .models import Photo, Restaurant
from .places import maybe_refresh_async

NOTE_MAX = 500


def _photos(restaurant):
    return [{"url": reverse("restaurants_photo", args=[p.pk]), "by": p.author}
            for p in restaurant.photos.all()]


def build_items(owner, now=None):
    now = now or timezone.now()
    # Prefetch photos without their image bytes.
    restaurants = Restaurant.objects.prefetch_related(Prefetch("photos", queryset=Photo.objects.defer("image")))
    if not owner:
        restaurants = restaurants.filter(hidden=False)
    items = [catalog.item(r, _photos(r), now) for r in restaurants]
    items.sort(key=catalog.sort_key)
    return items


def index(request):
    maybe_refresh_async()
    owner = request.user.is_authenticated
    now = timezone.now()
    items = build_items(owner, now)
    visible = [i for i in items if not i["hidden"]]
    open_now = sum(1 for i in visible if i["st"][0] == "open")
    config = {
        "owner": owner,
        "ownerUrl": reverse("restaurants_owner", args=["__slug__"]),
        "shortlistUrl": app_setting("restaurants", "shortlist_url", "https://blackdiamondlodge.github.io/shortlist/"),
        "today": catalog.DAYS[(catalog.local_now(None, now).weekday() + 1) % 7],
        "lodge": catalog.LODGE,
        "summary": f"{open_now} of {len(visible)} open now",
    }
    return render(request, "restaurants/index.html", {
        "items": items,
        "data": {i["slug"]: i for i in items},
        "config": config,
        "filter_groups": catalog.FILTER_GROUPS,
        "summary": config["summary"],
    })


def photo(request, pk):
    p = get_object_or_404(Photo.objects.select_related("restaurant"), pk=pk)
    if p.restaurant.hidden and not request.user.is_authenticated:
        raise Http404
    response = HttpResponse(bytes(p.image), content_type=p.content_type)
    # A refresh stores new rows (new URLs), so a photo URL never changes.
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@require_POST
def owner_update(request, slug):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in to edit restaurants."}, status=403)
    restaurant = get_object_or_404(Restaurant, slug=slug)
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    if "pick" in body:
        restaurant.pick = bool(body["pick"])
    if "hidden" in body:
        restaurant.hidden = bool(body["hidden"])
    if "note" in body:
        restaurant.note = str(body["note"] or "").strip()[:NOTE_MAX]
    restaurant.save(update_fields=["pick", "hidden", "note"])
    photos = [{"url": reverse("restaurants_photo", args=[p.pk]), "by": p.author}
              for p in restaurant.photos.defer("image")]
    return JsonResponse(catalog.item(restaurant, photos))
